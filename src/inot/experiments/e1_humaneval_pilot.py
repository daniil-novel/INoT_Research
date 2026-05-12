"""E1 — Pilot on HumanEval (§7.2 of the article).

Verifies hypothesis H1:
    "There exists a context length τ⋆ such that for |C0|>τ⋆ Hybrid-INoT
    achieves U_tok improvement >= 15% over Classical-MAS while pass@1 does
    not degrade by more than 2 p.p."

Configurations compared:
    B0 SingleLarge | B1 SelfRefine | B2 ClassicalMAS | B3 HybridINoT

Each task is run at three context lengths {512, 2048, 8192} (article spec)
across the chosen seeds. Statistical testing follows §7.1:
    * paired Wilcoxon signed-rank on per-task U_tok arrays;
    * 95% bootstrap percentile CI (10⁴ resamples) on ΔU_tok;
    * Holm-Bonferroni across the three context-length subgroups;
    * McNemar on paired pass/fail vectors for B3 vs B2.

Outputs (in ``results/e1/``):
    runs.json                      — raw RunResult dump
    summary.json                   — per-(arch, ctx) summaries
    pairwise_b3_vs_b2.json         — Wilcoxon + bootstrap + Holm-Bonferroni
    table.txt                      — rich table snapshot
    fig_tokens_by_context.png      — bar plot tokens/task per arch×ctx
    fig_utok_by_context.png        — line plot U_tok vs context length
    fig_pass_at_1_by_context.png   — pass@1 by context length
    H1_VERDICT.md                  — explicit pass/fail of the hypothesis
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from rich.console import Console

from ..architectures import make
from ..config import Config
from ..llm import make_client
from ..metrics import (
    holm_bonferroni,
    pairwise_compare,
    summarize_runs,
)
from ..metrics.stats import mcnemar_paired
from ..runner import (
    align_pairs,
    latency_breakdown_by_role,
    run_grid,
    save_results,
    summary_table,
)
from ..tasks import load_humaneval
from ..types import RunResult

console = Console()


# ---------------------------------------------------------------------------
def run(
    cfg: Config,
    *,
    n: int = 20,
    seeds: Sequence[int] = (42, 123),
    out_dir: Path = Path("results/e1"),
    dry_run: bool = False,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    context_lengths = list(cfg.get("experiments.e1_context_lengths", [512, 2048, 8192]))

    llm = make_client(cfg, dry_run=dry_run)
    try:
        all_results: list[RunResult] = []
        for ctx_len in context_lengths:
            tasks = load_humaneval(n=n, context_target_tokens=ctx_len, seed=42)
            agents = {
                "B0_SingleLarge":   make("B0", llm=llm, config=cfg),
                "B1_SelfRefine":    make("B1", llm=llm, config=cfg),
                "B2_ClassicalMAS":  make("B2", llm=llm, config=cfg),
                "B3_HybridINoT":    make("B3", llm=llm, config=cfg),
            }
            console.rule(f"[bold]E1 :: context length = {ctx_len} tokens[/bold]")
            r = run_grid(agents, tasks, seeds=seeds, progress_label=f"E1 ctx={ctx_len}")
            for x in r:
                x.extra["context_target_tokens"] = ctx_len
            all_results.extend(r)
            console.log(f"Cumulative spend: ${llm.spent_usd:.4f}")
    finally:
        llm.close()

    save_results(all_results, out_dir / "runs.json")

    # ---------- per-(arch, ctx) summaries -----------------------------------
    summaries: dict[tuple[str, int], dict] = {}
    for ctx_len in context_lengths:
        for arch in ("B0_SingleLarge", "B1_SelfRefine", "B2_ClassicalMAS", "B3_HybridINoT"):
            subset = [r for r in all_results
                      if r.architecture == arch and r.extra.get("context_target_tokens") == ctx_len]
            s = summarize_runs(subset, lam=cfg.get("metrics.lambda_maintainability", 0.5))
            summaries[(arch, ctx_len)] = s.__dict__

    (out_dir / "summary.json").write_text(
        json.dumps({f"{k[0]}@ctx{k[1]}": v for k, v in summaries.items()}, indent=2, default=str),
        encoding="utf-8",
    )

    # ---------- pairwise B3 vs B2 by ctx + Holm-Bonferroni -----------------
    pairwise: list[dict] = []
    pvals: list[float] = []
    for ctx_len in context_lengths:
        b2 = [r for r in all_results
              if r.architecture == "B2_ClassicalMAS" and r.extra.get("context_target_tokens") == ctx_len]
        b3 = [r for r in all_results
              if r.architecture == "B3_HybridINoT" and r.extra.get("context_target_tokens") == ctx_len]
        # Per-task U_tok: pass / (tokens/1000)  approximated per-task as
        # 1000 / total_tokens if passed else 0  (so the *mean* per task aligns
        # with the overall U_tok formula).
        def _per_task_utok(r: RunResult) -> float:
            return (1000.0 / r.total_tokens) if (r.passed and r.total_tokens > 0) else 0.0

        a, b = align_pairs(b2, b3, metric_a=_per_task_utok, metric_b=_per_task_utok)
        cmp = pairwise_compare(b, a, label=f"U_tok B3-B2 @ctx{ctx_len}",
                               bootstrap_resamples=cfg.get("statistics.bootstrap_resamples", 10000),
                               ci_level=cfg.get("statistics.ci_level", 0.95))
        # paired pass/fail
        pa, pb = align_pairs(b2, b3, metric_a=lambda r: 1 if r.passed else 0,
                             metric_b=lambda r: 1 if r.passed else 0)
        chi2, p_mc = mcnemar_paired(pa, pb)
        pairwise.append({
            "context_length": ctx_len,
            "n_pairs": cmp.n,
            "wilcoxon_stat": cmp.statistic,
            "wilcoxon_p": cmp.p_value,
            "diff_mean": cmp.diff_mean,
            "ci_low": cmp.bootstrap_ci_low,
            "ci_high": cmp.bootstrap_ci_high,
            "mcnemar_chi2": chi2,
            "mcnemar_p_pass1": p_mc,
        })
        pvals.append(cmp.p_value)
    rejected = holm_bonferroni(pvals, alpha=cfg.get("statistics.alpha", 0.05))
    for d, rej in zip(pairwise, rejected):
        d["holm_bonferroni_rejected"] = bool(rej)
    (out_dir / "pairwise_b3_vs_b2.json").write_text(
        json.dumps(pairwise, indent=2), encoding="utf-8")

    # ---------- H1 verdict --------------------------------------------------
    delta = float(cfg.get("experiments.delta_H1", 0.15))
    pp_tol = float(cfg.get("experiments.pass_at_1_tolerance_pp", 2.0)) / 100.0
    long_ctx = max(context_lengths)
    s_b2 = summaries[("B2_ClassicalMAS", long_ctx)]
    s_b3 = summaries[("B3_HybridINoT", long_ctx)]
    rel_utok_gain = (s_b3["utok_per_kilo"] - s_b2["utok_per_kilo"]) / max(1e-12, s_b2["utok_per_kilo"])
    pass1_drop = s_b2["pass_at_1"] - s_b3["pass_at_1"]
    pvalue_long = next(d["wilcoxon_p"] for d in pairwise if d["context_length"] == long_ctx)
    holm_long = next(d["holm_bonferroni_rejected"] for d in pairwise if d["context_length"] == long_ctx)
    h1_verdict = (
        "CONFIRMED"
        if (rel_utok_gain >= delta and pass1_drop <= pp_tol and holm_long)
        else "NOT CONFIRMED"
    )

    verdict_md = (
        f"# H1 Verdict (E1, context={long_ctx} tokens)\n\n"
        f"- ΔU_tok (B3-B2) / B2 = **{rel_utok_gain*100:+.2f}%**  (threshold δ_H1 = {delta*100:.0f}%)\n"
        f"- pass@1 drop (B2-B3) = **{pass1_drop*100:+.2f} p.p.**  (tolerance ≤ {pp_tol*100:.0f} p.p.)\n"
        f"- Wilcoxon p (per-task U_tok B3 vs B2) = **{pvalue_long:.4g}**\n"
        f"- Holm-Bonferroni rejection at α=0.05: **{holm_long}**\n\n"
        f"## Decision\n\n**H1: {h1_verdict}**\n"
    )
    (out_dir / "H1_VERDICT.md").write_text(verdict_md, encoding="utf-8")
    console.print(verdict_md)

    # ---------- pretty summary table --------------------------------------
    flat_summaries = []
    for (arch, ctx_len), s_dict in summaries.items():
        from ..metrics import Summary
        s = Summary(**s_dict)
        s.architecture = f"{arch}@ctx{ctx_len}"
        flat_summaries.append(s)
    table = summary_table(flat_summaries, title="E1 — per-architecture × context")
    console.print(table)
    with (out_dir / "table.txt").open("w", encoding="utf-8") as f:
        from rich.console import Console as _C
        _C(file=f, force_terminal=False, width=160).print(table)

    # ---------- plots -----------------------------------------------------
    _plot_grouped_bar(
        summaries, metric="mean_tokens", ylabel="Mean tokens / task",
        title="E1 — Token cost by architecture × context",
        out=out_dir / "fig_tokens_by_context.png",
    )
    _plot_grouped_line(
        summaries, metric="utok_per_kilo", ylabel="U_tok = pass@1 / (tokens / 1000)",
        title="E1 — Token efficiency vs context length",
        out=out_dir / "fig_utok_by_context.png",
    )
    _plot_grouped_line(
        summaries, metric="pass_at_1", ylabel="pass@1",
        title="E1 — pass@1 vs context length",
        out=out_dir / "fig_pass_at_1_by_context.png",
    )

    breakdown = latency_breakdown_by_role(all_results)
    (out_dir / "role_token_breakdown.json").write_text(
        json.dumps(breakdown, indent=2), encoding="utf-8")

    return {"verdict": h1_verdict, "summaries": summaries, "pairwise": pairwise}


# ---------------------------------------------------------------------------
def _plot_grouped_bar(summaries: dict, metric: str, ylabel: str, title: str, out: Path) -> None:
    archs = sorted({k[0] for k in summaries.keys()})
    ctxs = sorted({k[1] for k in summaries.keys()})
    fig, ax = plt.subplots(figsize=(9, 5))
    bar_w = 0.18
    x = np.arange(len(ctxs))
    for i, arch in enumerate(archs):
        vals = [summaries[(arch, c)][metric] for c in ctxs]
        ax.bar(x + i * bar_w, vals, width=bar_w, label=arch.split("_", 1)[-1])
    ax.set_xticks(x + bar_w * (len(archs) - 1) / 2)
    ax.set_xticklabels([f"|C0|≈{c}" for c in ctxs])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)


def _plot_grouped_line(summaries: dict, metric: str, ylabel: str, title: str, out: Path) -> None:
    archs = sorted({k[0] for k in summaries.keys()})
    ctxs = sorted({k[1] for k in summaries.keys()})
    fig, ax = plt.subplots(figsize=(8, 5))
    for arch in archs:
        ys = [summaries[(arch, c)][metric] for c in ctxs]
        ax.plot(ctxs, ys, marker="o", label=arch.split("_", 1)[-1])
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Context length |C0| (tokens)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=8)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    fig.tight_layout()
    fig.savefig(out, dpi=140)
    plt.close(fig)
