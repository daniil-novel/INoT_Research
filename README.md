# Hybrid-INoT empirical validation suite

Reproducible code for the experimental program of the article

> Privezentsev D. **Hybrid-INoT: гибридная агентная архитектура с внутренней
> ролевой сегрегацией для инженерных задач в условиях длинного общего
> контекста.** HSE, Moscow, 2026.

The suite implements the four architectures compared in §7 of the article
(B0 / B1 / B2 / B3) and the five experiments E1–E5, with statistical tests
prescribed in §3.2 / §7.1 (Wilcoxon signed-rank, McNemar, 95% bootstrap CI
with 10⁴ resamples, Holm–Bonferroni FWER correction).

LLM calls go through **OpenRouter** so the same code can target any of
GPT-4o, Claude Sonnet, etc. Token and dollar counts come from the provider's
own `usage` block (with `tiktoken` `cl100k_base` fallback).

---

## Quickstart

### 1. Install

```bash
cd hybrid_inot_research
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Unix:
source .venv/bin/activate

pip install -e .
```

Python 3.10+ required.

### 2. Configure your OpenRouter key

```bash
copy .env.example .env       # Windows
# or:  cp .env.example .env  # Unix
# Then edit .env and put your key in OPENROUTER_API_KEY
```

Get a key at <https://openrouter.ai/keys>.
The default models are `openai/gpt-4o-2024-11-20` (large) and
`openai/gpt-4o-mini-2024-07-18` (small); change them in `config.yaml`.

A hard budget cap (`llm.hard_budget_usd`, default **$50**) raises
`BudgetExceeded` if you exceed it — adjust before launching the full suite.

### 3. Smoke-test plumbing (no spending)

```bash
python -m inot check
```

This runs every architecture once on two HumanEval tasks against the
deterministic `DryRunClient` — no network, no money.

### 4. Run experiments

Single experiment:

```bash
python -m inot e1 --n 20 --seeds "42,123"
python -m inot view e1
```

Full pipeline (E1..E5, sequential):

```bash
python -m inot all --n 30 --seeds "42,123,456"
python -m inot view e3
```

The article's full spec (`--n 164 --seeds "42,123,456,789,1337"`) costs on
the order of **$10–30** at GPT-4o prices for the full suite. Pilot mode
(`--n 20 --seeds "42"`) typically lands under **$2**.

---

## What gets validated

| ID | Hypothesis / quantity | Code | Verdict file |
|---|---|---|---|
| H1 | `ΔU_tok ≥ 15%` at `|C0| > 2048`, `pass@1` regression ≤ 2 p.p. | `experiments/e1_humaneval_pilot.py` | `results/e1/H1_VERDICT.md` |
| τ⋆ | exists and `< 16384` tokens | `experiments/e3_context_scaling.py` | `results/e3/tau_star.json` |
| H2 | `C^S_check < (ρ0−ρ1) · C^L_rerun` (eq. 16) | `experiments/e4_self_check.py` | `results/e4/H2_VERDICT.md` |
| H3 | B3 latency advantage vanishes at `p_‖ ≥ 2` | `experiments/e2_ablation.py::_e2c_parallel_tools` | `results/e2/e2c/summary.json` |
| ablations | each component (compress / critic / self-check) significant | `experiments/e2_ablation.py::_e2a_ablation` | `results/e2/e2a/pairwise_vs_full.json` |
| TCO | monthly Δcost > 0 at lower CI, robust to ±50% prices | `experiments/e5_tco.py` | `results/e5/tco_summary.json` |

---

## Repository layout

```
hybrid_inot_research/
├── README.md                       <- you are here
├── pyproject.toml
├── config.yaml                     <- model, prices, hyperparams (K, I, λ, …)
├── .env.example                    <- template for OPENROUTER_API_KEY
├── docs/                           <- one Markdown card per experiment
│   ├── e1.md … e5.md
├── data/                           <- HumanEval JSONL cached on first run
├── results/                        <- all artefacts land here
└── src/inot/
    ├── types.py                    Task, TokenUsage, RunResult, VerificationResult
    ├── config.py                   YAML + .env loader
    ├── llm/__init__.py             OpenRouterClient (real) + DryRunClient (mock)
    ├── tasks/__init__.py           HumanEval, SWE-bench Lite, Synthetic Tool-Use
    ├── compression.py              Algorithm 2 surrogate
    ├── verification/__init__.py    sandboxed pytest + lint + sec + maintainability
    ├── architectures/
    │   ├── base.py                 BaseAgent + role-system prompts
    │   ├── single_large.py         B0
    │   ├── self_refine.py          B1 (Madaan et al. 2023)
    │   ├── classical_mas.py        B2 (planner+worker+critic; separate calls)
    │   └── hybrid_inot.py          B3 (Algorithm 1 + RouteMode + selective rerun)
    ├── metrics/
    │   ├── core.py                 formulas (17)–(23) — U_tok, Q$, VCR, MAS_i
    │   └── stats.py                Wilcoxon, McNemar, bootstrap, Holm–Bonferroni
    ├── runner.py                   shared run/save/align/table helpers
    ├── doc_viewer.py               `inot view` — rich panels in the terminal
    ├── experiments/
    │   ├── e1_humaneval_pilot.py
    │   ├── e2_ablation.py          (E2a, E2b, E2c, E2d)
    │   ├── e3_context_scaling.py
    │   ├── e4_self_check.py
    │   └── e5_tco.py
    └── cli.py                      Typer entrypoint (`python -m inot`)
```

---

## Mapping article ↔ code

Every formula and algorithm of the article has a literal counterpart:

| Article | Code |
|---|---|
| Definition 1 (Task `(x, C0, Z, V)`) | `inot.types.Task` |
| Equation (1) (`Θ(\|A\|·\|C0\|) + Θ(\|A\|²ħ)`) | `B2_ClassicalMAS` payload size + role count |
| Definition 3 (Hybrid-INoT) | `inot.architectures.HybridINoTAgent` |
| Definition 4 (`RouteMode`) | `HybridINoTAgent._route_mode` |
| Algorithm 1 (inner loop) | `HybridINoTAgent._solve` |
| Algorithm 2 (compression) | `inot.compression.compress` |
| Algorithm 3 (selective rerun) | `HybridINoTAgent._selective_rerun` |
| Statement 2 (eq. 7) | E1 (paired Wilcoxon) + E3 (τ⋆ bootstrap) |
| Statement 3 (eq. 13) | upper bound asserted in `_solve` via `B`, `I`, `K` caps |
| Inequality (16) | E4 (`H2_VERDICT.md`) |
| Formulas (17)–(20) | `inot.metrics.core` |
| Formula (21) M_i | `inot.verification.maintainability_score` |
| Eq. (22) SCR | reported via `verification.tests_passed` |
| Eq. (24) TCO | E5 |

---

## Reproducibility checklist (article §7.1)

- ✅ task IDs fixed (`humaneval.jsonl` cached and read deterministically),
- ✅ five default seeds `{42, 123, 456, 789, 1337}`,
- ✅ model snapshot IDs pinned in `config.yaml`,
- ✅ token prices captured in `config.yaml` with measurement date in the YAML
  comment,
- ✅ statistical pipeline: paired Wilcoxon, McNemar (binary), 10⁴ bootstrap,
  Holm–Bonferroni (`statistics:` block in `config.yaml`).

---

## Cost & runtime estimates (rough, GPT-4o mid-2025 prices)

| Command | Calls | Time | Cost |
|---|---|---|---|
| `inot check` | 4 dry-run | <1 s | $0.00 |
| `inot e1 --n 10 --seeds "42"` | ~120 calls | ~5 min | ~$0.30 |
| `inot e1 --n 164 --seeds "42,123,456,789,1337"` | ~10 000 calls | hours | ~$10 |
| `inot all --n 30 --seeds "42,123"` | ~5 000 calls | ~30 min | ~$3 |

---

## Troubleshooting

- **`OPENROUTER_API_KEY is empty`** — copy `.env.example` to `.env` and fill it in.
- **`BudgetExceeded`** — raise `llm.hard_budget_usd` in `config.yaml`.
- **`ModuleNotFoundError: datasets`** — `pip install -e .` reinstalls;
  HumanEval download falls back to GitHub raw URL if `datasets` is missing.
- **Tests time out** — bump the timeout in `Verifier(config, timeout_seconds=...)`
  or in `inot/verification/__init__.py::run_tests`.
- **Different model** — edit `llm.large_model` / `llm.small_model` in `config.yaml`
  and add the new model to `llm.prices_usd_per_mtok`.

---

## Citing

If you use this code, please cite the article:

```bibtex
@article{Privezentsev2026HybridINoT,
  author  = {Privezentsev, Daniil},
  title   = {Hybrid-INoT: гибридная агентная архитектура с внутренней
             ролевой сегрегацией для инженерных задач в условиях длинного
             общего контекста},
  journal = {Manuscript, HSE},
  year    = {2026},
}
```
