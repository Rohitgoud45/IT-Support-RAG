# Evaluation Benchmark & Quality Proof: IT Support RAG

This document details the evaluation methodology, dataset taxonomy, metric definitions, and verified experimental results for the IT Support RAG Assistant.

---

## 1. Evaluation Methodology

A reliable production RAG system requires measurable proof across both **Retrieval Quality** and **Generation Faithfulness**, coupled with strict **Refusal Precision** to eliminate hallucinations on out-of-scope requests.

```
                              +----------------------------+
                              |   Golden Questions (15)    |
                              |    eval/questions.jsonl    |
                              +--------------+-------------+
                                             |
                     +-----------------------+-----------------------+
                     |                                               |
             [Answerable: 11]                               [Unanswerable: 4]
                     |                                               |
         +-----------v-----------+                       +-----------v-----------+
         | Top-K Vector Search   |                       | Top-K Vector Search   |
         | Target: Hit@K Recall  |                       | Target: Distance Cutoff|
         +-----------+-----------+                       +-----------+-----------+
                     |                                               |
         +-----------v-----------+                       +-----------v-----------+
         | Stage 1 Distance Gate |                       | Stage 1 Distance Gate |
         | (Cutoff <= 0.75)      |                       | (Cutoff > 0.75)       |
         +-----------+-----------+                       +-----------+-----------+
                     |                                               |
         +-----------v-----------+                       +-----------v-----------+
         | LLM Grounded Answer   |                       | Zero-Token Fast Exit  |
         +-----------+-----------+                       | (Stage 2 if it passes)|
                     |                                   +-----------------------+
         +-----------v-----------+
         | LLM-as-a-Judge Eval   |
         | 1. Answer Accuracy    |
         | 2. Faithfulness Claim |
         +-----------------------+
```

---

## 2. Core Metrics Definitions

| Metric | Calculation | Purpose |
|---|---|---|
| **Retrieval Hit@K** | $\frac{\sum \mathbb{I}(\text{expected\_source} \in \text{retrieved\_top\_k})}{N_{\text{answerable}}}$ | Verifies that the correct technical document is present in the top-K context chunks. |
| **Answer Accuracy** | $\frac{\sum \mathbb{I}(\text{LLM\_Judge}(\text{Answer}, \text{Reference}) == \text{True})}{N_{\text{answerable}}}$ | Measures factual alignment between candidate answers and authoritative references. |
| **Faithfulness / Hallucination Rate** | $\frac{\sum \mathbb{I}(\text{claims} \not\subseteq \text{context})}{N_{\text{answered}}}$ | Checks whether **every factual statement** in the generated answer is directly substantiated by cited context passages. |
| **Refusal Accuracy** | $\frac{\sum \mathbb{I}(\text{refused} == \text{True})}{N_{\text{unanswerable}}}$ | Evaluates system guardrails when asked out-of-domain or out-of-scope questions. |
| **False Refusal Rate** | $\frac{\sum \mathbb{I}(\text{refused} == \text{True})}{N_{\text{answerable}}}$ | Ensures in-domain answerable questions are not mistakenly rejected. |
| **Median Latency ($P_{50}$)** | Median end-to-end execution time in seconds. | Operational responsiveness tracking. |

---

## 3. Benchmark Dataset Taxonomy (`eval/questions.jsonl`)

The evaluation suite comprises 15 curated scenarios designed to test edge cases, procedural multi-step instructions, and out-of-scope refusal boundaries:

### In-Domain Scenarios (11 Questions)
1. **VPN Troubleshooting:** Error 809 port blocking and protocol switching (UDP $\to$ TCP 443).
2. **Account Security:** Password expiration intervals (90 days) and lockout duration (30 mins after 5 attempts).
3. **Hardware & Facilities:** Floor-specific shared network printer naming conventions (`PRN-3F-01`).
4. **Print Spooler Procedures:** Stuck print queue recovery steps via Windows Services.
5. **Corporate WiFi:** Guest password rotation policy and enterprise 802.1x certificate enrollment errors.
6. **MFA Authentication:** SMS policy enforcement (disallowed) and recovery workflow for lost hardware tokens.
7. **Device Lifecycle:** Laptop hardware refresh eligibility (4-year threshold) and diagnostics for sluggish machines.

### Out-of-Domain & Refusal Scenarios (4 Questions)
1. **Unsupported OS Customization:** "How do I set up a Linux dual boot on my laptop?"
2. **HR / Non-IT Policy:** "What is the company parental leave policy?"
3. **Project Management Tooling:** "How do I configure workflows in Jira?"
4. **Data Recovery Edge Cases:** "How do I recover a file deleted from the shared network drive?"

---

## 4. Results

No results are quoted until a fresh run is committed as `eval/results.json`. Earlier figures in this file were inconsistent with the dataset (e.g. 10/10 hit rate on 11 answerable questions) and the chunking/threshold ablations had no script behind them, so they were removed.

Caveat: with 6 docs (~8 chunks) and `TOP_K=4`, retrieval returns about half the corpus, so hit@4 is close to meaningless until the knowledge base grows.

---

## 5. How to Reproduce Evaluations

### 1. Resumable Live Evaluation (with API Key)
```bash
python -m eval.run_eval
```
* The harness automatically checks points in `eval/.checkpoint.jsonl`.
* If a rate limit occurs, progress is safely persisted. Re-running resumes where it left off.
* To force a completely fresh evaluation run:
```bash
python -m eval.run_eval --fresh
```

### 2. Deterministic Smoke Evaluation (Offline / Zero-Quota)
For CI/CD runners or offline assessment without cloud API credentials:
```bash
python -m eval.run_eval --allow-mock
```
Runs the pipeline against the offline mock engine. The mock judge always says "true", so this checks that the harness runs, not quality.
