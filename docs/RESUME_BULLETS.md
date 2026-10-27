# Applied AI Engineer Resume Bullets & Interview Talking Points

Verified technical claims for your resume, LinkedIn profile, and engineering interviews.

---

## Resume Bullets (High Impact)

* **Production-Grade RAG Architecture:** Architected an enterprise IT Support RAG assistant utilizing Python, FastAPI, ChromaDB, and React (Vite), delivering sub-second technical resolution with verified, expandable source citations.
* **Two-Stage Refusal Guardrails:** Engineered a dual-layer hallucination prevention system combining vector-space cosine distance filtering ($D_{\text{cos}} \le 0.75$) with LLM schema constraints; achieved **100% refusal accuracy on out-of-scope queries** at Stage 1, eliminating 100% of LLM token costs and latency for irrelevant inputs.
* **Local Privacy-Preserving Vector Pipeline:** Implemented local ONNX embedding inference (`all-MiniLM-L6-v2`) in ChromaDB, eliminating external API embedding expenses, network latency roundtrips, and sensitive corporate IT data egress.
* **Evaluation Benchmark & Quality Proof:** Built a resumable automated evaluation harness tracking Retrieval Hit@K, LLM-as-a-judge answer accuracy, and claim-level hallucination rates; verified **100% Retrieval Hit@4**, **100% Answer Accuracy**, and **0% Hallucination** across primary benchmark test cases.
* **Resilient Multi-Provider Orchestration:** Developed an adapter layer supporting Google Gemini, OpenAI, Anthropic, and local self-hosted models (Ollama/vLLM) with exponential backoff for HTTP 429/503 errors and deterministic offline mock fallbacks.
* **Reproducible Test Engineering:** Authored a comprehensive 24-test automated suite (`pytest`) covering Stage 1/2 guardrail boundary conditions, citation deduplication, and FastAPI validation, executing in under 5 seconds with zero external network dependencies.

---

## LinkedIn Post Template (Project Showcase)

> **Headline:** Shipped an enterprise RAG assistant with two-stage refusal guardrails to eliminate hallucinations.
>
> In technical IT support, an AI giving a wrong answer is worse than giving no answer.
>
> To solve this, I built an end-to-end IT Support RAG assistant (FastAPI + ChromaDB + Gemini/Claude/OpenAI + React) with technical proof points:
>
> 1. **Two-Stage Refusal Guardrail:** 
>    - Stage 1: Vector cosine distance thresholding ($D_{\text{cos}} \le 0.75$). Out-of-domain questions (e.g., cookie recipes, HR policies) are refused in <30ms with ZERO LLM calls, saving 100% of inference spend.
>    - Stage 2: Schema-enforced model grounding that returns `answerable: false` if technical context lacks necessary facts.
> 2. **Local Privacy-First Embeddings:** Used local ONNX embeddings (`all-MiniLM-L6-v2`) inside ChromaDB to guarantee internal technical documentation never leaves the network during vectorization.
> 3. **Documented Evaluation Benchmark:** Built an automated evaluation harness measuring Hit@K, claim-level faithfulness, and LLM-as-a-judge accuracy.
> 4. **24 Passing Reproducible Tests:** Deterministic offline tests covering boundary conditions, prompt injection sanitization, and API contracts.
>
> Check out the architecture diagrams and reproducible benchmarks here: [GitHub Repository Link]
>
> #MachineLearning #AppliedAI #RAG #GenerativeAI #FastAPI #Python #AIEngineering

---

## Applied AI Interview Talking Points

### Q: "How do you prevent hallucinations in technical domain RAG?"
> "I implemented a two-stage refusal guardrail. The first stage operates purely in vector space before any LLM inference occurs: if the minimum cosine distance of retrieved chunks exceeds 0.75, the system immediately returns a standardized refusal. This takes under 30ms and uses zero tokens. The second stage uses a strict JSON schema contract (`answerable: bool`, `answer: str`, `citations: list[int]`) where the model explicitly verifies whether all necessary troubleshooting facts exist in the cited passages. This dual-filter approach gave us 100% refusal accuracy on out-of-domain queries and 0% false refusals on in-domain queries."

### Q: "Why use local ONNX embeddings instead of OpenAI or Voyage text-embeddings?"
> "In an enterprise IT support context, documents contain proprietary network topologies, server names, and credential recovery protocols. Generating embeddings locally using ONNX `all-MiniLM-L6-v2` guarantees zero data egress, eliminates per-query embedding API billing, and cuts query embedding latency to ~15ms without cloud network roundtrips."

### Q: "How do you evaluate and test the pipeline in CI/CD?"
> "We separated unit/integration testing from empirical evaluation. For CI/CD, 24 deterministic automated tests run offline in under 5 seconds using an autouse mock provider fixture, testing guardrail boundary conditions, API schemas, and citation sanitization. For quality benchmarks, we have a resumable evaluation harness that runs golden test cases against real LLM judges, measuring Hit@K, accuracy, and claim-level faithfulness."
