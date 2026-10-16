"""Evaluation harness. Run from repo root:  python -m eval.run_eval

Metrics
- hit@k:             expected source appears in the retrieved top-k (answerable questions)
- answer accuracy:   LLM judge says the answer matches the reference (answerable questions)
- hallucination:     LLM judge says the answer contains claims NOT supported by the cited context
- refusal accuracy:  correct "no answer found" on unanswerable questions
- false refusal:     refused an answerable question
"""
import json
import sys
import time
from pathlib import Path

from app import config
from app.generate import answer_question
from app.llm import call_llm, get_active_provider, get_effective_model, parse_json

QUESTIONS = Path(__file__).parent / "questions.jsonl"
RESULTS = Path(__file__).parent / "results.json"
CHECKPOINT = Path(__file__).parent / ".checkpoint.jsonl"

JUDGE_SYSTEM = "You are a strict evaluator. Reply with a single JSON object and nothing else."

ACCURACY_PROMPT = """Question: {q}
Reference answer: {ref}
Candidate answer: {ans}

Does the candidate answer convey the key facts of the reference answer without contradicting it?
Reply: {{"correct": true|false}}"""

FAITHFUL_PROMPT = """Context passages:
{ctx}

Answer: {ans}

Is EVERY factual claim in the answer supported by the context passages? Extra, unsupported specifics count as unsupported.
Reply: {{"faithful": true|false}}"""


def judge(prompt: str, key: str) -> bool:
    raw = call_llm(JUDGE_SYSTEM, prompt, config.JUDGE_MODEL, max_tokens=50)
    return bool(parse_json(raw)[key])


def main() -> None:
    provider = get_active_provider()
    if provider == "mock" and "--allow-mock" not in sys.argv:
        sys.exit(
            "Refusing to run: no LLM API key configured (provider=mock).\n"
            "The mock judge always answers 'true', so scores would be meaningless.\n"
            "Set GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY in .env, "
            "or pass --allow-mock for a smoke test only."
        )
    print(f"Provider: {provider} | answer model: {get_effective_model()} | judge model: {get_effective_model(config.JUDGE_MODEL)}\n")

    rows = [json.loads(line) for line in QUESTIONS.read_text().splitlines() if line.strip()]

    # Checkpoint: finished questions are cached so transient API errors don't lose work.
    # Keyed by model so switching models never mixes results. Use --fresh to start over.
    run_key = (f"{provider}:{get_effective_model()}:{get_effective_model(config.JUDGE_MODEL)}:"
               f"{config.CHUNK_STRATEGY}:{config.CHUNK_SIZE}:{config.TOP_K}:{config.MAX_DISTANCE}")
    if "--fresh" in sys.argv and CHECKPOINT.exists():
        CHECKPOINT.unlink()
    done = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("run_key") == run_key:
                done[rec["question"]] = rec["result"]
        if done:
            print(f"Resuming: {len(done)}/{len(rows)} questions already done for {run_key}\n")

    results, failed = [], []
    for r in rows:
        if r["question"] in done:
            res = done[r["question"]]
            results.append(res)
            print(f"{'ok ' if (res['answered'] == r['answerable']) else 'MISS'} {r['question']}  (cached)")
            continue
        try:
            t0 = time.time()
            out = answer_question(r["question"])
            latency = round(time.time() - t0, 2)
            res = {"question": r["question"], "answerable_gt": r["answerable"], "answered": out["answerable"], "latency_s": latency, "answer": out["answer"]}
            if r["answerable"]:
                res["hit"] = r["expected_source"] in [h["source"] for h in out["retrieved"]]
                if out["answerable"]:
                    ctx = "\n\n".join(f"[{s['id']}] {s['snippet']}" for s in out["sources"])
                    res["correct"] = judge(ACCURACY_PROMPT.format(q=r["question"], ref=r["reference"], ans=out["answer"]), "correct")
                    res["faithful"] = judge(FAITHFUL_PROMPT.format(ctx=ctx, ans=out["answer"]), "faithful")
        except Exception as exc:  # noqa: BLE001 - keep going; retry on next run
            failed.append(r["question"])
            print(f"ERR  {r['question']}  ->  {str(exc)[:100]}")
            continue
        with CHECKPOINT.open("a") as f:
            f.write(json.dumps({"run_key": run_key, "question": r["question"], "result": res}) + "\n")
        results.append(res)
        print(f"{'ok ' if (res['answered'] == r['answerable']) else 'MISS'} {r['question']}")

    if failed:
        sys.exit(f"\n{len(failed)}/{len(rows)} questions failed (provider errors). "
                 f"Progress is saved -- re-run `python -m eval.run_eval` to retry only those.")

    ans = [x for x in results if x["answerable_gt"]]
    unans = [x for x in results if not x["answerable_gt"]]
    answered = [x for x in ans if x["answered"]]

    def pct(n, d):
        return f"{100 * n / d:.0f}% ({n}/{d})" if d else "n/a"

    summary = {
        "n_questions": len(results),
        "retrieval_hit_rate": pct(sum(x["hit"] for x in ans), len(ans)),
        "answer_accuracy": pct(sum(x["correct"] for x in answered), len(ans)),
        "hallucination_rate": pct(sum(not x["faithful"] for x in answered), len(answered)),
        "refusal_accuracy_unanswerable": pct(sum(not x["answered"] for x in unans), len(unans)),
        "false_refusal_rate": pct(sum(not x["answered"] for x in ans), len(ans)),
        "median_latency_s": sorted(x["latency_s"] for x in results)[len(results) // 2],
        "config": {
            "provider": provider,
            "model": get_effective_model(),
            "judge_model": get_effective_model(config.JUDGE_MODEL),
            "chunk_strategy": config.CHUNK_STRATEGY,
            "chunk_size": config.CHUNK_SIZE,
            "top_k": config.TOP_K,
            "max_distance": config.MAX_DISTANCE,
        },
    }
    RESULTS.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    CHECKPOINT.unlink(missing_ok=True)  # run complete; next run starts fresh
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
