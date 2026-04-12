"""
TLCM Independent MemPalace Evaluation — Gemini 3.0 AI Judge
============================================================
Evaluates the TLCM engine on MemPalace-style temporal reasoning tasks
using Gemini 3.0 Flash as an impartial AI judge.

Covers:
 - Temporal Retrieval (point-in-time recall)
 - Knowledge Update / Contradiction handling
 - Cross-Context Isolation (workspace bleed detection)
 - Belief Evolution Arc (multi-hop version chains)
 - Decay-aware retrieval
"""
import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from google import genai
from pydantic import BaseModel, Field
import rich.console
from rich.table import Table

# Force test mode for deterministic embeddings (no GPU required)
os.environ["TLCM_TEST_MODE"] = "1"

from benchmarks.external.tlcm_adapter import TLCMMemoryAdapter

console = rich.console.Console()

# ─── Gemini Model Configuration ────────────────────────────────────────
GEMINI_MODEL = "gemini-3.1-flash-lite-preview"

# ─── Evaluation Dataset (10 scenarios across 4 TLCM Principles) ───────
EVAL_DATASET = [
    # ─── Category 1: Temporal Retrieval (Point-in-Time Recall) ──────
    {
        "id": "temporal_01",
        "category": "temporal_retrieval",
        "sessions": [
            {"session_id": "S1", "text": "The project budget is $50,000 for Q1."},
            {"session_id": "S2", "text": "The project budget has been increased to $75,000 for Q2 due to expanded scope."},
        ],
        "question": "What was the project budget during Q1?",
        "expected_facts": ["$50,000", "Q1"],
    },
    {
        "id": "temporal_02",
        "category": "temporal_retrieval",
        "sessions": [
            {"session_id": "S1", "text": "The team uses Python 3.10 for the backend."},
            {"session_id": "S2", "text": "We migrated the backend to Python 3.12 for performance gains."},
        ],
        "question": "What Python version was used originally before the migration?",
        "expected_facts": ["Python 3.10", "original", "before migration"],
    },
    # ─── Category 2: Knowledge Update / Contradiction Handling ──────
    {
        "id": "contradiction_01",
        "category": "contradiction",
        "sessions": [
            {"session_id": "S1", "text": "The secret code is Alpha-1-Zephyr. Keep it safe."},
            {"session_id": "S2", "text": "Due to a security breach, the code Alpha-1-Zephyr has been revoked. Set the new code to Bravo-9-Echo."},
        ],
        "question": "What is the current secret code, and what was it previously?",
        "expected_facts": ["Previous: Alpha-1-Zephyr", "Current: Bravo-9-Echo"],
    },
    {
        "id": "contradiction_02",
        "category": "contradiction",
        "sessions": [
            {"session_id": "S1", "text": "Alice is dating Bob. They are very happy together."},
            {"session_id": "S2", "text": "Alice and Bob broke up last week. Alice is now seeing Charlie."},
        ],
        "question": "Who is Alice dating right now?",
        "expected_facts": ["Alice is dating Charlie", "She broke up with Bob"],
    },
    {
        "id": "contradiction_03",
        "category": "contradiction",
        "sessions": [
            {"session_id": "S1", "text": "The experiment yield is 42%. This is below our 50% threshold."},
            {"session_id": "S2", "text": "After adding Catalyst B, yield improved to 67%, exceeding the threshold."},
            {"session_id": "S3", "text": "Catalyst B degraded. Yield dropped back to 38%. We need a new approach."},
        ],
        "question": "What is the current experiment yield and how has it changed?",
        "expected_facts": ["Current yield: 38%", "Was 42%", "Peaked at 67%", "Catalyst B degraded"],
    },
    # ─── Category 3: Cross-Context Isolation ────────────────────────
    {
        "id": "isolation_01",
        "category": "isolation",
        "sessions": [
            {"session_id": "S1", "text": "Project Falcon uses titanium alloys for the airframe."},
        ],
        "cross_workspace": {
            "name": "personal_diary",
            "session_id": "S1",
            "text": "I had pizza for dinner last night. It was delicious.",
        },
        "question": "What did I have for dinner?",
        "query_workspace": "personal_diary",
        "expected_facts": ["pizza", "dinner"],
        "expected_absent": ["titanium", "alloy", "Falcon"],
    },
    {
        "id": "isolation_02",
        "category": "isolation",
        "sessions": [
            {"session_id": "S1", "text": "The patient's blood pressure is 140/90. Prescribe ACE inhibitors."},
        ],
        "cross_workspace": {
            "name": "cooking_recipes",
            "session_id": "S1",
            "text": "For the sourdough, use 500g flour and 350ml water. Ferment for 12 hours.",
        },
        "question": "What are the sourdough ingredients?",
        "query_workspace": "cooking_recipes",
        "expected_facts": ["500g flour", "350ml water", "12 hours"],
        "expected_absent": ["blood pressure", "ACE inhibitors", "patient"],
    },
    # ─── Category 4: Belief Evolution Arc ───────────────────────────
    {
        "id": "evolution_01",
        "category": "evolution",
        "sessions": [
            {"session_id": "Phase1", "text": "Our hypothesis: Compound X increases tensile strength by 10%."},
            {"session_id": "Phase2", "text": "Lab results show Compound X increases tensile strength by 18%, exceeding expectations."},
            {"session_id": "Phase3", "text": "Peer review confirmed: Compound X increases tensile strength by 15% under controlled conditions. The 18% included measurement error."},
        ],
        "question": "How has our understanding of Compound X's effect on tensile strength evolved?",
        "expected_facts": ["Initially hypothesized 10%", "Lab showed 18%", "Peer review confirmed 15%", "measurement error"],
    },
    {
        "id": "evolution_02",
        "category": "evolution",
        "sessions": [
            {"session_id": "Week1", "text": "User count is 1,200. Growth rate is 5% week-over-week."},
            {"session_id": "Week2", "text": "User count jumped to 3,500 after the TechCrunch feature. Growth rate spiked to 190%."},
            {"session_id": "Week3", "text": "Growth normalized. User count is 4,100 with 17% WoW growth. Retention rate is 62%."},
        ],
        "question": "Trace the evolution of our user growth metrics from Week 1 to Week 3.",
        "expected_facts": ["1,200 users initially", "TechCrunch spike to 3,500", "Normalized to 4,100", "Retention 62%"],
    },
    # ─── Category 5: Decay-Aware Retrieval ──────────────────────────
    {
        "id": "decay_01",
        "category": "decay",
        "sessions": [
            {"session_id": "S1", "text": "Daily standup at 9am in Room 3B."},
            {"session_id": "S1", "text": "The core algorithm uses gradient descent with learning rate 0.001."},
            {"session_id": "S2", "text": "The standup has been moved to 10am in Room 5A."},
        ],
        "question": "What is the learning rate of the core algorithm?",
        "expected_facts": ["0.001", "gradient descent"],
    },
]


# ─── Pydantic Models for Structured Gemini Responses ───────────────────
class JudgeResponse(BaseModel):
    score: int = Field(description="Score from 0 to 10 on how accurately the answer matches expected facts")
    reasoning: str = Field(description="Why this score was given")
    hallucination_detected: bool = Field(description="Whether the answer contains hallucinations or context bleed from other workspaces")
    facts_found: List[str] = Field(description="Which expected facts were found in the answer", default_factory=list)
    facts_missing: List[str] = Field(description="Which expected facts were missing from the answer", default_factory=list)


def with_retry(func):
    def wrapper(*args, **kwargs):
        max_retries = 4
        base_delay = 10
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err_str = str(e).lower()
                if "429" in err_str or "resource" in err_str or "exhausted" in err_str or "503" in err_str:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        console.print(f"[yellow]Rate limit / API error hit. Sleeping for {delay} seconds (Attempt {attempt+1}/{max_retries})...[/yellow]")
                        time.sleep(delay)
                        continue
                raise
    return wrapper

@with_retry
def _generate_content_api(client, model, contents, config=None):
    if config:
        return client.models.generate_content(model=model, contents=contents, config=config)
    return client.models.generate_content(model=model, contents=contents)


def generate_answer(client: genai.Client, context: str, question: str) -> str:
    """Use Gemini to generate an answer from retrieved TLCM memories."""
    prompt = (
        "You are a precise AI assistant. Using ONLY the following retrieved memories "
        "(each tagged with its session/epoch), answer the question accurately.\n\n"
        f"Retrieved Memories:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer concisely and factually. Reference specific values and timeframes."
    )
    try:
        response = _generate_content_api(client, GEMINI_MODEL, prompt)
        return response.text
    except Exception as e:
        console.print(f"[red]Error calling Gemini for answer generation: {e}[/red]")
        return f"ERROR_GENERATING_ANSWER: {e}"


def run_gemini_judge(client: genai.Client, answer: str, expected: List[str], question: str) -> JudgeResponse:
    """Use Gemini as an impartial judge to evaluate TLCM's answer quality."""
    prompt = f"""You are an expert AI judge evaluating the temporal accuracy of a Memory System.
The system was asked: "{question}"
It produced this answer based on its retrieved memories:

System's Answer: {answer}

Expected Facts that MUST be present: {json.dumps(expected)}

Evaluate the system's answer:
1. Does it correctly identify temporal states (past vs current)?
2. Are all expected facts present?
3. Is there any hallucination or fabricated information?
4. Does the answer show context bleed from unrelated domains?

Provide your structured evaluation."""
    try:
        config = {"response_mime_type": "application/json", "response_schema": JudgeResponse}
        response = _generate_content_api(client, GEMINI_MODEL, prompt, config)
        return JudgeResponse.model_validate_json(response.text)
    except Exception as e:
        console.print(f"[red]Error calling Gemini judge: {e}[/red]")
        return JudgeResponse(
            score=0,
            reasoning=f"Error: {e}",
            hallucination_detected=True,
            facts_found=[],
            facts_missing=expected,
        )


def run_standard_eval(client: genai.Client, adapter: TLCMMemoryAdapter, item: dict, idx: int, total: int) -> dict:
    """Run a standard (non-isolation) eval scenario."""
    console.print(f"\n[cyan]━━━ Eval {idx}/{total}: {item['id']} ({item['category']}) ━━━[/cyan]")

    # 1. Ingestion
    for session in item["sessions"]:
        adapter.start_session(session["session_id"])
        adapter.add(session["text"])

    # 2. Retrieval
    memories = adapter.retrieve(item["question"], top_k=5)
    context = "\n".join([f"[{m['epoch']}] (confidence={m['confidence']:.2f}): {m['content']}" for m in memories])
    console.print(f"[dim]Retrieved {len(memories)} memories[/dim]")

    # 3. Answer Generation
    answer = generate_answer(client, context, item["question"])
    console.print(f"  Answer: [green]{answer[:200]}[/green]")

    # 4. Judge Evaluation
    evaluation = run_gemini_judge(client, answer, item["expected_facts"], item["question"])
    console.print(f"  Score: [bold magenta]{evaluation.score}/10[/bold magenta] | Hallucination: {evaluation.hallucination_detected}")
    console.print(f"  Reasoning: [dim]{evaluation.reasoning[:200]}[/dim]")

    return {
        "id": item["id"],
        "category": item["category"],
        "score": evaluation.score,
        "hallucination": evaluation.hallucination_detected,
        "facts_found": evaluation.facts_found,
        "facts_missing": evaluation.facts_missing,
        "reasoning": evaluation.reasoning,
        "answer": answer,
        "context_retrieved": context,
    }


def run_isolation_eval(client: genai.Client, item: dict, idx: int, total: int) -> dict:
    """Run a cross-workspace isolation eval scenario."""
    console.print(f"\n[cyan]━━━ Eval {idx}/{total}: {item['id']} (isolation) ━━━[/cyan]")

    # Create TWO separate adapters (two workspaces)
    adapter_main = TLCMMemoryAdapter(workspace_name="eval_main_ws")
    cross_ws = item["cross_workspace"]
    adapter_cross = TLCMMemoryAdapter(workspace_name=cross_ws["name"])

    # Ingest into main workspace
    for session in item["sessions"]:
        adapter_main.start_session(session["session_id"])
        adapter_main.add(session["text"])

    # Ingest into cross workspace
    adapter_cross.start_session(cross_ws["session_id"])
    adapter_cross.add(cross_ws["text"])

    # Query the TARGET workspace (should NOT bleed from main)
    query_ws = item.get("query_workspace", cross_ws["name"])
    if query_ws == cross_ws["name"]:
        query_adapter = adapter_cross
    else:
        query_adapter = adapter_main

    memories = query_adapter.retrieve(item["question"], top_k=5)
    context = "\n".join([f"[{m['epoch']}]: {m['content']}" for m in memories])
    console.print(f"[dim]Retrieved {len(memories)} memories from '{query_ws}'[/dim]")

    # Check for context bleed
    bleed_detected = False
    absent_terms = item.get("expected_absent", [])
    for m in memories:
        for term in absent_terms:
            if term.lower() in m["content"].lower():
                bleed_detected = True
                console.print(f"  [red]BLEED DETECTED: '{term}' found in '{query_ws}' workspace![/red]")

    # Generate answer and judge
    answer = generate_answer(client, context, item["question"])
    console.print(f"  Answer: [green]{answer[:200]}[/green]")

    evaluation = run_gemini_judge(client, answer, item["expected_facts"], item["question"])

    # Override: if bleed detected, score 0
    if bleed_detected:
        evaluation.score = 0
        evaluation.hallucination_detected = True
        evaluation.reasoning = f"CONTEXT BLEED: Cross-workspace data leaked. {evaluation.reasoning}"

    console.print(f"  Score: [bold magenta]{evaluation.score}/10[/bold magenta] | Bleed: {bleed_detected}")

    return {
        "id": item["id"],
        "category": "isolation",
        "score": evaluation.score,
        "hallucination": evaluation.hallucination_detected,
        "bleed_detected": bleed_detected,
        "facts_found": evaluation.facts_found,
        "facts_missing": evaluation.facts_missing,
        "reasoning": evaluation.reasoning,
        "answer": answer,
        "context_retrieved": context,
    }


def run_eval():
    """Execute the full MemPalace evaluation suite."""
    console.print("\n[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║   TLCM Independent MemPalace Evaluation — Gemini 3.0 Judge  ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]\n")

    # Initialize Gemini Client
    api_key = os.environ.get("GEMINI_API_KEY")
    os.environ.pop("GOOGLE_API_KEY", None)
    if not api_key:
        console.print("[red]ERROR: GEMINI_API_KEY not found. Set it in .env or environment.[/red]")
        return

    client = genai.Client(api_key=api_key)
    console.print(f"[green]✓ Gemini client initialized (model: {GEMINI_MODEL})[/green]")

    # Reset ChromaDB singleton for clean eval
    import core.embeddings
    core.embeddings._chroma_client = None

    # Run evaluations
    results = []
    total = len(EVAL_DATASET)
    adapter = TLCMMemoryAdapter(workspace_name="mempalace_eval_ws")

    for i, item in enumerate(EVAL_DATASET, 1):
        try:
            if item["category"] == "isolation":
                result = run_isolation_eval(client, item, i, total)
            else:
                result = run_standard_eval(client, adapter, item, i, total)
            results.append(result)
        except Exception as e:
            console.print(f"[red]ERROR on {item['id']}: {e}[/red]")
            results.append({"id": item["id"], "category": item["category"], "score": 0, "error": str(e)})

        # Rate limiting for free tier (4 seconds between scenarios)  
        time.sleep(4)

    # ─── Results Summary ────────────────────────────────────────────
    console.print("\n")
    table = Table(title="🧠 TLCM MemPalace Evaluation Results", show_lines=True)
    table.add_column("Test ID", style="cyan", min_width=16)
    table.add_column("Category", style="blue")
    table.add_column("Score", style="magenta", justify="center")
    table.add_column("Hallucination", justify="center")
    table.add_column("Key Finding", style="dim", max_width=50)

    category_scores = {}
    total_score = 0

    for res in results:
        score = res.get("score", 0)
        total_score += score
        cat = res.get("category", "unknown")
        category_scores.setdefault(cat, []).append(score)

        hall = "✗" if not res.get("hallucination", False) else "[red]✓ YES[/red]"
        finding = res.get("reasoning", res.get("error", ""))[:50]
        score_style = "green" if score >= 7 else "yellow" if score >= 4 else "red"
        table.add_row(res["id"], cat, f"[{score_style}]{score}/10[/{score_style}]", hall, finding)

    console.print(table)

    avg_score = total_score / len(results) if results else 0
    console.print(f"\n[bold]Overall Average Score: [{'green' if avg_score >= 7 else 'yellow' if avg_score >= 5 else 'red'}]{avg_score:.1f}/10[/{'green' if avg_score >= 7 else 'yellow' if avg_score >= 5 else 'red'}][/bold]")

    # Category breakdown
    console.print("\n[bold]Category Breakdown:[/bold]")
    for cat, scores in category_scores.items():
        cat_avg = sum(scores) / len(scores)
        console.print(f"  {cat:.<30} {cat_avg:.1f}/10 ({len(scores)} tests)")

    # ─── Save Results ───────────────────────────────────────────────
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    output_path = results_dir / "mempalace_eval_results.json"

    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": GEMINI_MODEL,
        "total_scenarios": len(EVAL_DATASET),
        "average_score": round(avg_score, 2),
        "category_averages": {cat: round(sum(s) / len(s), 2) for cat, s in category_scores.items()},
        "results": results,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    console.print(f"\n[green]✓ Results saved to: {output_path}[/green]")
    return output


if __name__ == "__main__":
    run_eval()
