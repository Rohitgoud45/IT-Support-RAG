# IT support assistant (RAG)

Ask a plain-language IT question and get an answer grounded in a knowledge base, with the source passages shown. If the knowledge base doesn't cover the question, the assistant says so instead of guessing.

**Stack:** Python, FastAPI, Chroma (local ONNX embeddings), Gemini / OpenAI / Anthropic / Local models, React (Vite), Docker.

## How it works

1. `app/ingest.py` reads `data/docs/*.md`, chunks the text (`paragraph` or `fixed` strategy), embeds it with Chroma's built-in MiniLM model, and stores it.
2. `app/retrieval.py` embeds the question and returns the top-k chunks with cosine distances.
3. `app/generate.py` applies two refusal guards before answering:
   - **Distance guard:** if no chunk is within `MAX_DISTANCE`, refuse without calling the LLM.
   - **Model guard:** the LLM must return `answerable: false` when the passages don't contain the answer.
4. Answers come back with numbered citations that map to expandable source passages in the UI.

## Run locally

```bash
# Backend setup
python -m venv .venv && source .venv/bin/activate  # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # set GEMINI_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY
python -m app.ingest            # build the vector index
uvicorn app.main:app --reload   # API on :8000
```

In a second terminal:

```bash
# Frontend setup
cd frontend && npm install && npm run dev   # UI on :5173, proxies /api to :8000
```

## Evaluate

```bash
python -m eval.run_eval
```

Reports retrieval hit rate, answer accuracy (LLM judge vs. a reference), hallucination rate (LLM judge checks every claim against the cited passages), refusal accuracy on unanswerable questions, false refusal rate, and median latency. Results are saved to `eval/results.json`.

To compare chunking strategies or tune the refusal threshold, change the env var, re-ingest, and re-run:

```bash
CHUNK_STRATEGY=fixed python -m app.ingest && CHUNK_STRATEGY=fixed python -m eval.run_eval
MAX_DISTANCE=0.6 python -m eval.run_eval
```

Record each run in the table below.

| Run | Chunking | Size | top-k | MAX_DISTANCE | Hit rate | Accuracy | Hallucination | Refusal acc. | False refusal |
|---|---|---|---|---|---|---|---|---|---|
| baseline | paragraph | 800 | 4 | 0.75 | 100% | 100% | 0% | 100% | 0% |

## Test

```bash
pytest
```

## Docker and deployment

```bash
docker compose up --build      # http://localhost:8000
```

To get a live URL, push this repo to GitHub and create a **Web Service** on Render (or Fly.io / Railway) using the Dockerfile. Set `ANTHROPIC_API_KEY` as a secret. The index rebuilds automatically on first boot. Add a spending cap on your API key and consider rate limiting `/api/ask` before sharing the link publicly.

## Using your own knowledge base

The files in `data/docs/` are a small written sample so the project runs out of the box. For a stronger portfolio piece, replace them with 50 to 100 real public documents (for example, open-source project docs or public IT help pages whose licenses allow reuse), keep the license and source URL in each file, then write 60 to 100 evaluation questions in `eval/questions.jsonl`, including at least 20 percent that the docs can't answer.

## Limitations

- The LLM judge is itself a model; spot-check 20 judgments by hand and report the agreement.
- Chroma's default embedding model is small. Swapping in a stronger embedding model is a good experiment to report.
- No conversation memory: each question is answered independently.
