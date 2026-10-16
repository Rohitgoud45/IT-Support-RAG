# Resume bullets (only verified claims; update after the full eval run)

- Built a production-grade Retrieval-Augmented Generation (RAG) IT support assistant (Python, FastAPI, ChromaDB, Gemini/OpenAI/Claude API, React) that answers technical queries grounded in an IT knowledge base with interactive citations.
- Engineered a two-stage refusal guardrail combining embedding cosine-distance thresholding (MAX_DISTANCE = 0.75) and LLM-level refusal prompts; the distance guard correctly refused 4/4 out-of-scope questions without an LLM call.
- Built a resumable automated evaluation harness (retrieval hit rate, LLM-judged accuracy and hallucination, refusal correctness, latency) with 13 passing automated tests; full model-judged results pending.
- Implemented multi-provider LLM support with auto-detection for Google Gemini, OpenAI, Anthropic, and local models (Ollama/vLLM) with graceful offline fallback.
