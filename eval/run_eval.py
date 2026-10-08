"""Evaluation harness. Run from repo root:  python -m eval.run_eval

Metrics
- hit@k:             expected source appears in the retrieved top-k (answerable questions)
- answer accuracy:   LLM judge says the answer matches the reference (answerable questions)
- hallucination:     LLM judge says the answer contains claims NOT supported by the cited context
- refusal accuracy:  correct "no answer found" on unanswerable questions
- false refusal:     refused an answerable question
"""
import json
import time
from pathlib import Path

from app import config
from app.generate import answer_question
from app.llm import call_llm, parse_json

QUESTIONS = Path(__file__).parent / "questions.jsonl"
RESULTS = Path(__file__).parent / "results.json"

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
    rows = [json.loads(line) for line in QUESTIONS.read_text().splitlines() if line.strip()]
    results = []
    for r in rows:
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
        results.append(res)
        print(f"{'ok ' if (res['answered'] == r['answerable']) else 'MISS'} {r['question']}")

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
        "config": {"chunk_strategy": config.CHUNK_STRATEGY, "chunk_size": config.CHUNK_SIZE, "top_k": config.TOP_K, "max_distance": config.MAX_DISTANCE, "model": config.LLM_MODEL},
    }
    RESULTS.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
