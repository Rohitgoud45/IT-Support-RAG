# How I reviewed AI-generated code

## Process
- **Tools used:** Antigravity AI pair programming
- **Review checklist:** input validation, error handling, secrets protection, dependency versions, edge cases, multi-provider resiliency, automated tests, offline test isolation, latency benchmarking

## Findings log
| Date | File | What the AI generated | Problem I found | What I changed |
|---|---|---|---|---|
| 2026-10-08 | `app/llm.py` | Anthropic-only hardcoded client | Vendor lock-in; crashed immediately if `ANTHROPIC_API_KEY` was missing | Added multi-provider dispatch for Gemini, OpenAI, Anthropic, and offline mock fallback |
| 2026-10-08 | `app/config.py` | Fixed model string | No provider-specific default model configuration | Added `LLM_PROVIDER`, `OPENAI_BASE_URL`, and smart model defaults per provider |
| 2026-10-08 | `tests/test_core.py` | Only chunking & JSON parsing tests | Missing test coverage for retrieval, guardrails, API endpoints | Added 7 comprehensive test cases including refusal guards, API health, and query endpoints |
| 2026-10-08 | `frontend/src/App.jsx` | Basic barebones UI | No provider visibility, no copy functionality, missing status indicators | Added health check indicator, model badge, copy-to-clipboard button, and polished CSS |
| 2026-10-27 | `pytest.ini` | Missing pytest configuration | `pytest` raised `ModuleNotFoundError: No module named 'app'` unless invoked with `python -m pytest` | Added `pytest.ini` with `pythonpath = .` and testpath discovery |
| 2026-10-27 | `tests/conftest.py` | Tests lacked provider isolation | When `GEMINI_API_KEY` was in `.env`, unit tests called live Google APIs, exhausting daily 20-req quota and failing test runs | Created `tests/conftest.py` with an autouse mock provider fixture; tests now run 100% offline in <5s |
| 2026-10-27 | `tests/test_guardrails.py` | Missing explicit guardrail boundary tests | Distance cutoff (Stage 1) and schema refusal (Stage 2) boundary conditions were not isolated | Added 11 new tests covering boundary conditions, citation bounds sanitization, and deduplication (total: 24 passing tests) |
| 2026-10-27 | `scripts/demo.py` | No standalone terminal demonstration | Users without Node.js or browser dev servers could not easily demo the two-stage guardrails and citations | Created interactive colorized CLI demo (`scripts/demo.py`) with preset and custom query modes |

## Things I verified by hand
- [x] Refusal behavior on out-of-scope questions (4/4 refused by distance guard with 0 LLM calls and <30ms latency)
- [x] Citations point to the exact source passage used (verified against `vpn-troubleshooting.md`, `password-reset.md`, `printer-setup.md`)
- [x] No API key hardcoded in the repo or Docker image
- [x] Full automated test suite running and passing (`24/24` passed in <5 seconds offline)
- [x] End-to-end evaluation with real LLM (`gemini-3.5-flash`: 100% Hit@4, 100% accuracy, 0% hallucination rate on primary benchmark)
