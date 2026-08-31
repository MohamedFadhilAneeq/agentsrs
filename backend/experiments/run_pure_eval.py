"""
AgentSRS — PURE Dataset Evaluation (Study 3)
Runs completeness detection on the same 102 cases used by ReCompGPT.

All 102 cases in re_data.json are INCOMPLETE by design (ground truth = True for all).

Two metrics are reported per method:
  1. detection_rate  — did the model flag *anything* as missing? (complete=False)
                       This is the OLD metric. Not comparable to ReCompGPT.
  2. match_rate      — did the model's predicted gap semantically match the
                       specific missing requirement? (LLM-as-judge validated)
                       This is the VALID metric, comparable to ReCompGPT pass@1.

ReCompGPT reference numbers (GPT-4o, same dataset):
    pass@1 = 81.4%    pass@3 = 93.8%
    Our system uses gpt-oss-20b — model difference must be disclosed.

Usage:
    python -m backend.experiments.run_pure_eval groq
    python -m backend.experiments.run_pure_eval groq --force   # re-run even if saved
    python -m backend.experiments.run_pure_eval --show         # display saved results
"""

import json
import os
import pathlib
import sys
import time
import zipfile

os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from backend.llm.client import LLMClient
from backend.agents.quality_agent import COMPLETENESS_SYSTEM_PROMPT_WITH_DESCRIPTION

ZIP_PATH    = pathlib.Path("backend/data/ReGen.zip")
RESULTS_DIR = pathlib.Path("backend/experiments/results")
RESULTS_FILE = RESULTS_DIR / "pure_102.json"

console = Console()

# ── Prompts ────────────────────────────────────────────────────────────────────

PURE_SINGLE_PROMPT = (
    "You are evaluating whether a set of formal software requirements is complete "
    "with respect to an informal description. Check if anything mentioned or clearly "
    "implied in the description is missing from the specification set — an unhandled "
    "condition, a missing action, or an incomplete scenario.\n\n"
    "Respond ONLY with JSON:\n"
    '{"complete": true|false, "issue": "short description or null", "explanation": "..."}' 
)

JUDGE_SYSTEM_PROMPT = """You are a requirements engineering evaluator.

You will be given:
1. The ground-truth missing requirement — the specific requirement that was deliberately removed from a spec set
2. A predicted gap — what a system flagged as missing after analysing the incomplete spec

Your task: decide whether the predicted gap semantically describes the same missing requirement as the ground truth.

Rules:
- Accept if the core concept matches, even if wording differs
- Accept partial matches if the main missing behaviour is correctly identified
- Reject if the predicted gap describes something entirely different or unrelated
- Reject if the predicted gap is too vague to confirm a match (e.g. "something is missing")

Respond ONLY with JSON:
{"match": true|false, "confidence": "high"|"medium"|"low", "reason": "one sentence explaining your decision"}"""


# ── Load dataset ───────────────────────────────────────────────────────────────

def load_pure_cases():
    if not ZIP_PATH.exists():
        console.print(f"[red]Dataset not found at {ZIP_PATH}[/red]")
        sys.exit(1)
    with zipfile.ZipFile(ZIP_PATH) as z:
        raw = z.read("data/re_data.json").decode("utf-8")
    data = json.loads(raw)

    cases = []
    for doc_id, doc in data.items():
        for spec in doc["specifications"]:
            cases.append({
                "id": f"{doc_id}::{spec['function_name']}",
                "doc_id": doc_id,
                "topic": doc["topic"],
                "function_name": spec["function_name"],
                "description": spec["function_description"],
                "specifications": spec["function_specifications"],
                "sample_level": spec["sample_level"],
                "gap_type": spec["type"],
                "label": spec["label"],        # full ground truth missing requirement
                "absence": spec["absence"],    # short label
                "ground_truth": True,          # all cases ARE incomplete
            })
    return cases


def fmt_specs(spec_list):
    return "\n".join(f"{i+1}. {s.strip()}" for i, s in enumerate(spec_list))


# ── Judge function ─────────────────────────────────────────────────────────────

def judge_match(llm, case, predicted_issue):
    """Run LLM-as-judge to check if predicted_issue matches the ground truth gap."""
    if not predicted_issue or predicted_issue.startswith("ERROR"):
        return False, "low", "No valid prediction to judge"

    ground_truth = case.get('label') or case.get('absence', '')
    user_prompt = (
        f'Ground-truth missing requirement: "{ground_truth}"\n'
        f'Ground-truth absence label: "{case.get("absence", "")}"\n\n'
        f'Predicted gap: "{predicted_issue}"\n\n'
        "Does the predicted gap describe the same missing requirement as the ground truth?"
    )
    try:
        result = llm.generate_json(JUDGE_SYSTEM_PROMPT, user_prompt, temperature=0.0)
        matched    = result.get("match", False) is True
        confidence = result.get("confidence", "low")
        reason     = result.get("reason", "")
        return matched, confidence, reason
    except Exception as e:
        return False, "low", f"Judge error: {e}"


# ── Run evaluation ─────────────────────────────────────────────────────────────

def run_pure_eval(provider, force=False):
    if RESULTS_FILE.exists() and not force:
        saved = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        # Check if judge fields already present
        if saved and "multi_agent_matched" in saved[0]:
            console.print("[dim]  Loaded saved PURE results with judge scores (--force to re-run)[/dim]")
            return saved
        else:
            console.print("[yellow]  Saved results found but missing judge scores — running judge pass only.[/yellow]")
            # Load saved preds and only run the judge
            return run_judge_only(saved, provider)

    cases = load_pure_cases()
    llm = LLMClient(provider=provider)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        # ── Pass 1: Multi-agent completeness ────────────────────────────────
        task = progress.add_task("[cyan]Multi-agent completeness...", total=len(cases))
        for i, case in enumerate(cases):
            progress.update(task, description=f"[cyan]Multi-agent [{i+1}/{len(cases)}] {case['function_name'][:35]}")
            specs_text = fmt_specs(case["specifications"])
            user_prompt = (
                f"Description (informal source text):\n{case['description']}\n\n"
                f"Specification set (formal requirements):\n{specs_text}"
            )
            try:
                result = llm.generate_json(COMPLETENESS_SYSTEM_PROMPT_WITH_DESCRIPTION, user_prompt, temperature=0.2)
                cases[i]["_multi_pred"]  = result.get("complete") is False
                cases[i]["_multi_issue"] = result.get("issue", "")
            except Exception as e:
                cases[i]["_multi_pred"]  = False
                cases[i]["_multi_issue"] = f"ERROR: {e}"
            progress.advance(task)
            if i < len(cases) - 1:
                time.sleep(2)

        # ── Pass 2: Single-prompt baseline ───────────────────────────────────
        task2 = progress.add_task("[yellow]Single-prompt baseline...", total=len(cases))
        for i, case in enumerate(cases):
            progress.update(task2, description=f"[yellow]Baseline [{i+1}/{len(cases)}] {case['function_name'][:35]}")
            specs_text = fmt_specs(case["specifications"])
            user_prompt = (
                f"Description:\n{case['description']}\n\n"
                f"Specification set:\n{specs_text}"
            )
            try:
                result = llm.generate_json(PURE_SINGLE_PROMPT, user_prompt, temperature=0.2)
                cases[i]["_single_pred"]  = result.get("complete") is False
                cases[i]["_single_issue"] = result.get("issue", "")
            except Exception as e:
                cases[i]["_single_pred"]  = False
                cases[i]["_single_issue"] = f"ERROR: {e}"
            progress.advance(task2)
            if i < len(cases) - 1:
                time.sleep(2)

        # ── Pass 3: LLM-as-judge ─────────────────────────────────────────────
        console.print()
        console.print("[bold]Running LLM-as-judge to validate gap matches against ground truth...[/bold]")
        console.print("[dim]Judge only runs when system predicted incomplete (pred=True)[/dim]")

        task3 = progress.add_task("[magenta]Judge — multi-agent gaps...", total=len(cases))
        for i, case in enumerate(cases):
            progress.update(task3, description=f"[magenta]Judge multi [{i+1}/{len(cases)}] {case['function_name'][:35]}")
            if cases[i].get("_multi_pred"):
                matched, conf, reason = judge_match(llm, case, cases[i].get("_multi_issue", ""))
                cases[i]["_multi_matched"]     = matched
                cases[i]["_multi_judge_conf"]  = conf
                cases[i]["_multi_judge_reason"] = reason
                if i < len(cases) - 1:
                    time.sleep(1)
            else:
                cases[i]["_multi_matched"]     = False
                cases[i]["_multi_judge_conf"]  = "n/a"
                cases[i]["_multi_judge_reason"] = "Not predicted as incomplete"
            progress.advance(task3)

        task4 = progress.add_task("[magenta]Judge — single-prompt gaps...", total=len(cases))
        for i, case in enumerate(cases):
            progress.update(task4, description=f"[magenta]Judge single [{i+1}/{len(cases)}] {case['function_name'][:35]}")
            if cases[i].get("_single_pred"):
                matched, conf, reason = judge_match(llm, case, cases[i].get("_single_issue", ""))
                cases[i]["_single_matched"]     = matched
                cases[i]["_single_judge_conf"]  = conf
                cases[i]["_single_judge_reason"] = reason
                if i < len(cases) - 1:
                    time.sleep(1)
            else:
                cases[i]["_single_matched"]     = False
                cases[i]["_single_judge_conf"]  = "n/a"
                cases[i]["_single_judge_reason"] = "Not predicted as incomplete"
            progress.advance(task4)

    # Build result records
    results = []
    for case in cases:
        results.append({
            "id":            case["id"],
            "doc_id":        case["doc_id"],
            "topic":         case["topic"],
            "function_name": case["function_name"],
            "sample_level":  case["sample_level"],
            "gap_type":      case["gap_type"],
            "absence":       case["absence"],
            "label":         case["label"],
            "ground_truth":  True,
            # Old metric (detection — any gap)
            "multi_agent_pred":   case.get("_multi_pred", False),
            "multi_agent_issue":  case.get("_multi_issue", ""),
            "single_prompt_pred": case.get("_single_pred", False),
            "single_prompt_issue": case.get("_single_issue", ""),
            # New metric (judge-validated match)
            "multi_agent_matched":      case.get("_multi_matched", False),
            "multi_agent_judge_conf":   case.get("_multi_judge_conf", "n/a"),
            "multi_agent_judge_reason": case.get("_multi_judge_reason", ""),
            "single_prompt_matched":      case.get("_single_matched", False),
            "single_prompt_judge_conf":   case.get("_single_judge_conf", "n/a"),
            "single_prompt_judge_reason": case.get("_single_judge_reason", ""),
        })

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(results, indent=2), encoding="utf-8")
    console.print(f"\n[green]Results saved to {RESULTS_FILE}[/green]")
    return results


def run_judge_only(saved_results, provider):
    """Add judge scores to already-saved results without re-running detection passes."""
    cases = {r["id"]: r for r in saved_results}
    llm = LLMClient(provider=provider)

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  BarColumn(), MofNCompleteColumn(), TimeElapsedColumn(), console=console) as progress:

        task = progress.add_task("[magenta]Judge — multi-agent...", total=len(saved_results))
        for r in saved_results:
            if r.get("multi_agent_pred"):
                m, c, reason = judge_match(llm, r, r.get("multi_agent_issue", ""))
                r["multi_agent_matched"] = m
                r["multi_agent_judge_conf"] = c
                r["multi_agent_judge_reason"] = reason
                time.sleep(1)
            else:
                r["multi_agent_matched"] = False
                r["multi_agent_judge_conf"] = "n/a"
                r["multi_agent_judge_reason"] = "Not predicted as incomplete"
            progress.advance(task)

        task2 = progress.add_task("[magenta]Judge — single-prompt...", total=len(saved_results))
        for r in saved_results:
            if r.get("single_prompt_pred"):
                m, c, reason = judge_match(llm, r, r.get("single_prompt_issue", ""))
                r["single_prompt_matched"] = m
                r["single_prompt_judge_conf"] = c
                r["single_prompt_judge_reason"] = reason
                time.sleep(1)
            else:
                r["single_prompt_matched"] = False
                r["single_prompt_judge_conf"] = "n/a"
                r["single_prompt_judge_reason"] = "Not predicted as incomplete"
            progress.advance(task2)

    RESULTS_FILE.write_text(json.dumps(saved_results, indent=2), encoding="utf-8")
    console.print(f"[green]Judge scores added and saved to {RESULTS_FILE}[/green]")
    return saved_results


# ── Compute metrics ────────────────────────────────────────────────────────────

def compute_metrics(results):
    n = len(results)
    multi_detected  = sum(1 for r in results if r.get("multi_agent_pred"))
    single_detected = sum(1 for r in results if r.get("single_prompt_pred"))
    multi_matched   = sum(1 for r in results if r.get("multi_agent_matched"))
    single_matched  = sum(1 for r in results if r.get("single_prompt_matched"))

    has_judge = "multi_agent_matched" in results[0]

    breakdown = {}
    for level in [1, 2, 3]:
        subset = [r for r in results if r["sample_level"] == level]
        if subset:
            breakdown[f"L{level}"] = {
                "n": len(subset),
                "multi_detected":  sum(1 for r in subset if r.get("multi_agent_pred")),
                "single_detected": sum(1 for r in subset if r.get("single_prompt_pred")),
                "multi_matched":   sum(1 for r in subset if r.get("multi_agent_matched")),
                "single_matched":  sum(1 for r in subset if r.get("single_prompt_matched")),
            }

    type_breakdown = {}
    for gap_type in sorted({r["gap_type"] for r in results}):
        subset = [r for r in results if r["gap_type"] == gap_type]
        if subset:
            type_breakdown[gap_type] = {
                "n": len(subset),
                "multi_detected":  sum(1 for r in subset if r.get("multi_agent_pred")),
                "single_detected": sum(1 for r in subset if r.get("single_prompt_pred")),
                "multi_matched":   sum(1 for r in subset if r.get("multi_agent_matched")),
                "single_matched":  sum(1 for r in subset if r.get("single_prompt_matched")),
            }

    return {
        "n": n,
        "has_judge": has_judge,
        "multi_detection_rate":  round(multi_detected  / n, 3),
        "single_detection_rate": round(single_detected / n, 3),
        "multi_match_rate":      round(multi_matched   / n, 3) if has_judge else None,
        "single_match_rate":     round(single_matched  / n, 3) if has_judge else None,
        "multi_detected":  multi_detected,
        "single_detected": single_detected,
        "multi_matched":   multi_matched,
        "single_matched":  single_matched,
        "by_level": breakdown,
        "by_type":  type_breakdown,
    }


# ── Print results ──────────────────────────────────────────────────────────────

def print_pure_results(results):
    m = compute_metrics(results)
    n = m["n"]

    console.print()
    console.rule("[bold bright_blue]Study 3 — PURE Dataset Completeness  (102 cases)[/bold bright_blue]")
    console.print(
        "[dim]Same benchmark as ReCompGPT (Sheng, Wang & Liu, IEEE TSE 2025).\n"
        "All 102 cases are incomplete by design — ground truth = True for all.\n"
        "Two metrics: (1) Detection Rate — any gap flagged  (2) Match Rate — correct gap identified (LLM-as-judge)\n"
        "ReCompGPT used GPT-4o; AgentSRS uses openai/gpt-oss-20b.[/dim]"
    )
    console.print()

    recomp_pass1 = 0.814
    recomp_pass3 = 0.938

    # ── Main comparison table ────────────────────────────────────────────────
    t = Table(
        box=box.DOUBLE_EDGE, border_style="bright_blue",
        header_style="bold white on #1e293b", padding=(0, 1),
        title="Main Comparison",
    )
    t.add_column("Method",               width=26)
    t.add_column("n",                    justify="center", width=5)
    t.add_column("Detection Rate\n(any gap)", justify="center", width=14)
    t.add_column("Match Rate\n(correct gap, judge)", justify="center", width=20)
    t.add_column("vs ReCompGPT",         width=34)

    multi_det  = m["multi_detection_rate"]
    single_det = m["single_detection_rate"]
    multi_mat  = m["multi_match_rate"]
    single_mat = m["single_match_rate"]

    t.add_row(
        "[cyan]AgentSRS Multi-Agent[/cyan]",
        str(n),
        Text(f"{multi_det:.1%} ({m['multi_detected']}/{n})",   style="dim"),
        Text(f"{multi_mat:.1%} ({m['multi_matched']}/{n})" if multi_mat is not None else "—",
             style="bold green" if (multi_mat or 0) >= recomp_pass1 else "yellow"),
        f"ReCompGPT pass@1={recomp_pass1:.1%}  pass@3={recomp_pass3:.1%}",
    )
    t.add_row(
        "[dim]Single-Prompt Baseline[/dim]",
        str(n),
        Text(f"{single_det:.1%} ({m['single_detected']}/{n})", style="dim"),
        Text(f"{single_mat:.1%} ({m['single_matched']}/{n})" if single_mat is not None else "—",
             style="green" if (single_mat or 0) >= recomp_pass1 else "dim"),
        "[dim](same model, flat prompt — fair baseline)[/dim]",
    )
    console.print(t)

    console.print("[dim]  Detection Rate = OLD metric (any gap flagged). "
                  "Match Rate = VALID metric comparable to ReCompGPT pass@1.[/dim]")

    # ── Breakdown by level ───────────────────────────────────────────────────
    console.print()
    t2 = Table(
        box=box.SIMPLE_HEAVY, border_style="bright_blue",
        header_style="bold white", padding=(0, 1),
        title="Match Rate by Difficulty Level",
    )
    t2.add_column("Level",          width=10)
    t2.add_column("n",              justify="center", width=5)
    t2.add_column("Multi Match",    justify="center", width=14)
    t2.add_column("Single Match",   justify="center", width=14)
    t2.add_column("Description",    width=28)

    level_labels = {
        "L1": "Easy   (gap obvious from desc.)",
        "L2": "Medium (gap needs inference)",
        "L3": "Hard   (subtle implied gap)",
    }
    for lv, ldata in m["by_level"].items():
        ln  = ldata["n"]
        mmr = ldata["multi_matched"]  / ln
        smr = ldata["single_matched"] / ln
        t2.add_row(
            f"[bold]{lv}[/bold]", str(ln),
            Text(f"{mmr:.1%}  ({ldata['multi_matched']}/{ln})",  style="cyan"  if mmr > 0.7 else "yellow"),
            Text(f"{smr:.1%}  ({ldata['single_matched']}/{ln})", style="green" if smr > 0.7 else "dim"),
            level_labels.get(lv, ""),
        )
    console.print(t2)

    # ── Breakdown by gap type ────────────────────────────────────────────────
    console.print()
    t3 = Table(
        box=box.SIMPLE_HEAVY, border_style="bright_blue",
        header_style="bold white", padding=(0, 1),
        title="Match Rate by Gap Type",
    )
    t3.add_column("Gap Type",      width=22)
    t3.add_column("n",             justify="center", width=5)
    t3.add_column("Multi Match",   justify="center", width=14)
    t3.add_column("Single Match",  justify="center", width=14)

    for gt, gdata in m["by_type"].items():
        gn  = gdata["n"]
        mmr = gdata["multi_matched"]  / gn
        smr = gdata["single_matched"] / gn
        t3.add_row(
            gt, str(gn),
            Text(f"{mmr:.1%}  ({gdata['multi_matched']}/{gn})",  style="cyan"  if mmr > 0.7 else "yellow"),
            Text(f"{smr:.1%}  ({gdata['single_matched']}/{gn})", style="green" if smr > 0.7 else "dim"),
        )
    console.print(t3)

    console.print()
    multi_mat_str  = f"{multi_mat:.1%}"  if multi_mat  is not None else "pending judge"
    single_mat_str = f"{single_mat:.1%}" if single_mat is not None else "pending judge"
    console.print(Panel(
        f"[bold]Match Rate (judge-validated, comparable to ReCompGPT pass@1):[/bold]\n"
        f"  Multi-Agent:    [cyan]{multi_mat_str}[/cyan]\n"
        f"  Single-Prompt:  [dim]{single_mat_str}[/dim]\n\n"
        f"[bold]ReCompGPT reference (GPT-4o):[/bold] pass@1 = [bold]{recomp_pass1:.1%}[/bold]  "
        f"|  pass@3 = [bold]{recomp_pass3:.1%}[/bold]\n\n"
        "[dim]Detection rate (any gap) was the old metric — not comparable to ReCompGPT.\n"
        "Match rate uses LLM-as-judge to verify the predicted gap matches the specific "
        "removed requirement.\n"
        "Model difference must be disclosed: ReCompGPT used GPT-4o, AgentSRS uses gpt-oss-20b.[/dim]\n\n"
        "[bold green]Novel contribution:[/bold green] ReCompGPT measures completeness only. "
        "AgentSRS additionally detects ambiguity — a quality dimension not in the base paper.",
        title="[bold]Study 3 Summary[/bold]",
        border_style="bright_blue",
        padding=(0, 2),
    ))

    return m


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args     = sys.argv[1:]
    force    = "--force" in args
    show     = "--show"  in args
    provider = next((a for a in args if not a.startswith("--")), "groq")

    console.print()
    console.print(Panel.fit(
        "[bold white]AgentSRS — PURE Dataset Evaluation (Study 3)[/bold white]\n"
        "[dim]102 cases from ReCompGPT (Sheng, Wang & Liu, IEEE TSE 2025)[/dim]\n"
        "[dim]Model: openai/gpt-oss-20b via Groq[/dim]\n"
        "[dim]Metric: LLM-as-judge match rate (comparable to pass@1)[/dim]",
        box=box.DOUBLE, border_style="bright_blue", padding=(0, 2),
    ))

    if show:
        if not RESULTS_FILE.exists():
            console.print("[red]No saved results. Run without --show first.[/red]")
            sys.exit(1)
        results = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
    else:
        console.print(
            f"\n[bold]Running on {ZIP_PATH}[/bold]\n"
            "[dim]Expected time: ~45 min (102 cases x 3 passes + 2s/1s sleep each)[/dim]\n"
            "[dim]Pass 1: Multi-agent detection (~30 min)[/dim]\n"
            "[dim]Pass 2: Single-prompt detection (~30 min)[/dim]\n"
            "[dim]Pass 3: LLM-as-judge for valid predictions (~10 min)[/dim]\n"
        )
        results = run_pure_eval(provider, force=force)

    metrics = print_pure_results(results)

    # Save summary used by run_full_eval --show
    summary = {
        "n": metrics["n"],
        "completeness_detection_rate_multi":  metrics["multi_detection_rate"],
        "completeness_detection_rate_single": metrics["single_detection_rate"],
        "completeness_match_rate_multi":      metrics["multi_match_rate"],
        "completeness_match_rate_single":     metrics["single_match_rate"],
        "has_judge": metrics["has_judge"],
        "by_level": metrics["by_level"],
        "by_type":  metrics["by_type"],
        "recompgpt_pass1": 0.814,
        "recompgpt_pass3": 0.938,
    }
    (RESULTS_DIR / "pure_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
