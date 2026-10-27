"""Interactive CLI demo for the IT Support RAG Assistant.

Run from repository root:
    python scripts/demo.py
"""
import sys
import time
from app import config
from app.generate import answer_question, NO_ANSWER_TEXT
from app.llm import get_active_provider, get_effective_model
from app.retrieval import retrieve
from app.store import get_collection


class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


PRESET_QUERIES = [
    {
        "title": "In-Domain (VPN Error 809)",
        "question": "What does VPN error 809 mean and how do I fix it?",
        "expected": "Grounds in vpn-troubleshooting.md, recommends TCP profile on port 443 with citations.",
    },
    {
        "title": "In-Domain (Password Expiration)",
        "question": "How often do passwords expire and what happens if I enter the wrong password 5 times?",
        "expected": "Grounds in password-reset.md, cites 90-day expiry and 30-minute lockout.",
    },
    {
        "title": "Out-of-Domain Refusal (Stage 1 Distance Guardrail)",
        "question": "What is the best recipe for homemade chocolate chip cookies?",
        "expected": "Refused immediately by distance cutoff (MAX_DISTANCE = 0.75) with ZERO LLM calls.",
    },
    {
        "title": "Unanswerable In-Domain (Stage 2 Model Guardrail)",
        "question": "How do I set up a Linux dual boot alongside Windows on my corporate laptop?",
        "expected": "Retrieved docs don't answer; LLM sets answerable=false and refuses without hallucinating.",
    },
]


def print_banner():
    provider = get_active_provider()
    model = get_effective_model()
    chunks = get_collection().count()
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*68}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}       IT Support RAG Assistant - Interactive Demonstration{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*68}{Colors.RESET}")
    print(f" {Colors.BOLD}Provider:{Colors.RESET} {provider:<12} | {Colors.BOLD}Model:{Colors.RESET} {model}")
    print(f" {Colors.BOLD}Index:{Colors.RESET}    {chunks} chunks      | {Colors.BOLD}Threshold (MAX_DISTANCE):{Colors.RESET} {config.MAX_DISTANCE}")
    print(f"{Colors.CYAN}{'='*68}{Colors.RESET}\n")


def run_query(question: str):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}>> Question:{Colors.RESET} {question}")
    
    # 1. Retrieval inspect
    t0 = time.time()
    raw_hits = retrieve(question, k=config.TOP_K)
    retrieval_ms = round((time.time() - t0) * 1000, 1)

    print(f"\n{Colors.DIM}[Step 1: ChromaDB Local Vector Search (all-MiniLM-L6-v2)]{Colors.RESET}")
    print(f"  Retrieved {len(raw_hits)} candidate chunks in {retrieval_ms}ms:")
    for i, h in enumerate(raw_hits, 1):
        dist_color = Colors.GREEN if h["distance"] <= config.MAX_DISTANCE else Colors.RED
        status = "PASSED" if h["distance"] <= config.MAX_DISTANCE else "FILTERED"
        print(f"    [{i}] {dist_color}{h['distance']:.4f}{Colors.RESET} | {status:<8} | {h['source']:<24} ({h['title']})")

    # 2. End-to-end execution
    t1 = time.time()
    try:
        out = answer_question(question)
        total_ms = round((time.time() - t1) * 1000, 1)
    except Exception as exc:
        total_ms = round((time.time() - t1) * 1000, 1)
        print(f"\n{Colors.RED}[Provider Call Failed after {total_ms}ms]: {exc}{Colors.RESET}")
        print(f"{Colors.YELLOW}Tip: You can test offline demo mode anytime with: LLM_PROVIDER=mock python scripts/demo.py{Colors.RESET}")
        return

    # 3. Guardrail inspection
    relevant_count = sum(1 for h in raw_hits if h["distance"] <= config.MAX_DISTANCE)
    if relevant_count == 0:
        guard_triggered = "Stage 1 (Cosine Distance Cutoff) - No LLM invoked"
    elif not out["answerable"]:
        guard_triggered = "Stage 2 (Model Grounding Refusal) - LLM identified missing facts"
    else:
        guard_triggered = "None (Fully Grounded Answer Generated)"

    print(f"\n{Colors.DIM}[Step 2: Two-Stage Guardrails & Generation ({total_ms}ms)]{Colors.RESET}")
    print(f"  Guardrail Decision: {Colors.BOLD}{guard_triggered}{Colors.RESET}")

    if out["answerable"]:
        print(f"\n{Colors.BOLD}{Colors.GREEN}[Answer Grounded in Knowledge Base]:{Colors.RESET}")
        print(f"{out['answer']}\n")
        print(f"{Colors.BOLD}Verified Citations ({len(out['sources'])}):{Colors.RESET}")
        for s in out["sources"]:
            print(f"  [{s['id']}] {Colors.CYAN}{s['source']}{Colors.RESET} - {s['title']}")
            snippet_preview = s['snippet'].replace('\n', ' ')[:140]
            print(f"      {Colors.DIM}\"{snippet_preview}...\"{Colors.RESET}")
    else:
        print(f"\n{Colors.BOLD}{Colors.RED}[Refusal Output]:{Colors.RESET}")
        print(f"{Colors.YELLOW}{out['answer']}{Colors.RESET}\n")


def main():
    print_banner()

    while True:
        print(f"{Colors.BOLD}Select a demonstration scenario:{Colors.RESET}")
        for i, p in enumerate(PRESET_QUERIES, 1):
            print(f"  {Colors.CYAN}{i}.{Colors.RESET} {p['title']}")
            print(f"     {Colors.DIM}Goal: {p['expected']}{Colors.RESET}")
        print(f"  {Colors.CYAN}5.{Colors.RESET} Type your own custom question")
        print(f"  {Colors.CYAN}q.{Colors.RESET} Exit")

        choice = input(f"\n{Colors.BOLD}Enter selection [1-5, q]: {Colors.RESET}").strip()
        if choice.lower() in ("q", "quit", "exit"):
            print("Exiting demo. Goodbye!")
            break

        if choice in ("1", "2", "3", "4"):
            preset = PRESET_QUERIES[int(choice) - 1]
            run_query(preset["question"])
        elif choice == "5":
            custom_q = input(f"\n{Colors.BOLD}Enter IT support question: {Colors.RESET}").strip()
            if len(custom_q) < 3:
                print(f"{Colors.RED}Question too short (minimum 3 characters).{Colors.RESET}")
                continue
            run_query(custom_q)
        else:
            print(f"{Colors.RED}Invalid selection. Please choose 1-5 or q.{Colors.RESET}")

        print(f"\n{Colors.DIM}{'-'*68}{Colors.RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDemo interrupted. Bye!")
        sys.exit(0)
