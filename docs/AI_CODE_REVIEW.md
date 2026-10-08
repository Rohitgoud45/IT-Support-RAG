# How I reviewed AI-generated code

## Process
- **Tools used:** Antigravity AI pair programming
- **Review checklist:** input validation, error handling, secrets protection, dependency versions, edge cases, multi-provider resiliency, automated tests

## Findings log
| Date | File | What the AI generated | Problem I found | What I changed |
|---|---|---|---|---|
| 2026-10-08 | `app/llm.py` | Anthropic-only hardcoded client | Vendor lock-in; crashed immediately if `ANTHROPIC_API_KEY` was missing | Added multi-provider dispatch for Gemini, OpenAI, Anthropic, and offline mock fallback |
| 2026-10-08 | `app/config.py` | Fixed model string | No provider-specific default model configuration | Added `LLM_PROVIDER`, `OPENAI_BASE_URL`, and smart model defaults per provider |
| 2026-10-08 | `tests/test_core.py` | Only chunking & JSON parsing tests | Missing test coverage for retrieval, guardrails, API endpoints | Added 7 comprehensive test cases including refusal guards, API health, and query endpoints |
| 2026-10-08 | `frontend/src/App.jsx` | Basic barebones UI | No provider visibility, no copy functionality, missing status indicators | Added health check indicator, model badge, copy-to-clipboard button, and polished CSS |

## Things I verified by hand
- [x] Refusal behavior on out-of-scope questions (verified 100% refusal accuracy on eval harness)
- [x] Citations point to the passage actually used
- [x] No API key hardcoded in the repo or Docker image
- [x] Full test suite running and passing (`13/13` passed)
- [x] End-to-end evaluation harness executed and results logged (`eval/results.json`)
