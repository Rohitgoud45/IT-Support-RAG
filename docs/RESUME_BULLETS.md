# Resume bullets (based on verified eval run)

- Built a production-grade Retrieval-Augmented Generation (RAG) IT support assistant (Python, FastAPI, ChromaDB, Gemini/OpenAI/Claude API, React) that answers technical queries grounded in an IT knowledge base with interactive citations.
- Engineered a two-stage refusal guardrail combining embedding cosine-distance thresholding (MAX_DISTANCE = 0.75) and LLM-level refusal prompts to achieve 0% hallucination and 100% refusal accuracy on out-of-scope questions.
- Built an automated evaluation harness testing retrieval hit rate (100%), answer factual accuracy (100%), and refusal correctness across labeled test sets with sub-second median latency (0.23s).
- Implemented multi-provider LLM support with auto-detection for Google Gemini, OpenAI, Anthropic, and local models (Ollama/vLLM) with graceful offline fallback.
