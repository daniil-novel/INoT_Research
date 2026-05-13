# Hybrid-INoT: воспроизводимая исследовательская инфраструктура

Этот репозиторий содержит код для эмпирической проверки гипотез статьи и
курсовой работы о Hybrid-INoT: гибридной агентной архитектуре с внутренней
ролевой сегрегацией для инженерных задач в условиях длинного общего контекста.

Цель проекта: не имитация эксперимента, а повторяемый научный запуск с
реальными LLM-вызовами через OpenRouter, учётом токенов, стоимости в USD/RUB,
статистическими тестами, графиками, таблицами и терминальным просмотром
результатов.

## Что проверяется

Сравниваются пять конфигураций:

| Конфигурация | Смысл |
|---|---|
| `CTRL_NoAssistant` | контрольный сценарий без ассистента и без LLM-вызовов |
| `B0_SingleLarge` | один вызов большой модели |
| `B1_SelfRefine` | self-refine цикл одной большой модели |
| `B2_ClassicalMAS` | классическая MAS: planner / worker / critic отдельными вызовами |
| `B3_HybridINoT` | роли planner / worker / critic внутри одного вызова по сжатому контексту |

Гипотезы:

| ID | Проверка | Основной модуль | Артефакт |
|---|---|---|---|
| H1 | рост `U_tok` минимум на 15% при длинном контексте без падения `pass@1` более чем на 2 п.п. | `src/inot/experiments/e1_humaneval_pilot.py` | `results/e1/H1_VERDICT.md` |
| H2 | малая модель самопроверки экономически оправдана: `C_check^S < (ρ0−ρ1)·C_rerun^L` | `src/inot/experiments/e4_self_check.py` | `results/e4/H2_VERDICT.md` |
| H3 | при независимых параллельных tool-вызовах преимущество Hybrid-INoT по latency исчезает | `src/inot/experiments/e2_ablation.py`, `src/inot/tools/synthetic.py` | `results/e2/e2c/summary.json` |
| τ* | пороговая длина контекста, где Hybrid-INoT начинает выигрывать по `U_tok` | `src/inot/experiments/e3_context_scaling.py` | `results/e3/tau_star.json` |
| TCO | экстраполяция полной стоимости владения и чувствительность к ценам | `src/inot/experiments/e5_tco.py` | `results/e5/tco_summary.json` |
| E6 | насколько `gemini-3.1-flash-lite` хуже/дешевле `gemini-3.1-pro-preview` на B2 и B3 | `src/inot/experiments/e6_model_sweep.py` | `results/e6/E6_VERDICT.md` |

Статистика: парный критерий Вилкоксона, McNemar для `pass/fail`, bootstrap CI
95% с 10 000 ресэмплирований, поправка Холма-Бонферрони.

## Быстрый старт на Windows

Из вашей ситуации ошибка

```text
C:\Python311\python.exe: No module named inot
```

возникает потому, что команда была запущена из `E:\JarvisSonoma` системным
Python, а пакет установлен в проекте `E:\JarvisSonoma\hybrid_inot_research`.

Правильный запуск:

```powershell
cd E:\JarvisSonoma\hybrid_inot_research
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -Dev
.\.venv\Scripts\Activate.ps1
python -m inot check
```

После активации окружения реальные эксперименты запускаются так:

```powershell
python -m inot e1 --n 20 --seeds "42,123" --suite both
python -m inot view e1
```

Если не хотите активировать venv, используйте проектный Python явно:

```powershell
cd E:\JarvisSonoma\hybrid_inot_research
.\.venv\Scripts\python.exe -m inot e1 --n 20 --seeds "42,123" --suite both
```

Или wrapper:

```powershell
.\scripts\inot.ps1 e1 --n 20 --seeds "42,123" --suite both
```

## OpenRouter-ключи

Ключ хранится локально в файле:

```text
E:\JarvisSonoma\hybrid_inot_research\.env
```

Файл создаётся из шаблона:

```powershell
copy .env.example .env
```

Внутри должно быть:

```env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_HTTP_REFERER=https://github.com/daniil-novel/INoT_Research
OPENROUTER_X_TITLE=hybrid-inot-research
```

`.env` и `.env.*` добавлены в `.gitignore`, поэтому ключ не должен попасть в
GitHub. Код читает ключ через `Config.api_key()`: имя переменной задано в
`config.yaml`:

```yaml
llm:
  api_key_env: OPENROUTER_API_KEY
```

Важно: `python -m inot check` использует `DryRunClient` и не делает сетевых
запросов. Все команды `e1`–`e5` без `--dry-run` используют реальный
`OpenRouterClient`.

## Учёт токенов и стоимости

Каждый LLM-вызов сохраняет:

- модель;
- роль (`planner`, `worker`, `critic`, `inot_combined`, `small_check`, ...);
- `input_tokens`;
- `output_tokens`;
- `cost_usd`;
- `cost_rub`;
- latency.

Главный эксперимент E1 строит графики:

- `fig_tokens_by_context.png` — общий расход токенов по архитектурам;
- `fig_cost_usd_by_context.png` — стоимость одного задания в USD;
- `fig_cost_rub_by_context.png` — стоимость одного задания в RUB;
- `fig_utok_by_context.png` — токенная эффективность;
- `fig_pass_at_1_by_context.png` — `pass@1` в процентах;
- `fig_cumulative_errors.png` — накопление ошибок по мере запуска;
- `fig_context_transfer_tokens.png` — сколько input/context токенов передано в LLM-вызовы;
- `fig_context_juggling_events.png` — как часто архитектура перекидывает контекст между ролевыми/model-вызовами.

На основных графиках по длине контекста красная пунктирная линия показывает
порог H1 из `experiments.h1_context_threshold_tokens`.

Источник токенов:

1. сначала используется `usage` block из ответа OpenRouter;
2. если провайдер не вернул usage, используется fallback через `tiktoken`.

Цены задаются в `config.yaml`:

```yaml
llm:
  prices_usd_per_mtok:
    openai/gpt-4o-2024-11-20:      {input: 2.50, output: 10.00}
    openai/gpt-4o-mini-2024-07-18: {input: 0.15, output: 0.60}
```

Рубли считаются по фиксированному курсу для воспроизводимости:

```yaml
accounting:
  usd_to_rub: 100.0
```

Если нужен другой курс, измените `accounting.usd_to_rub` перед запуском.
Научная отчётность всё равно остаётся в USD, а RUB используется как удобная
локальная оценка.

Жёсткий бюджет:

```yaml
llm:
  hard_budget_usd: 50.0
```

Клиент делает preflight-оценку стоимости запроса и выбрасывает
`BudgetExceeded`, если следующий запрос может превысить лимит.

## Основные команды

Проверка без денег и без сети:

```powershell
python -m inot check
```

Проверка реального OpenRouter-ключа и баланса перед экспериментами:

```powershell
python -m inot api-check
```

Эта команда делает один короткий реальный запрос к `llm.small_model` и
печатает input/output токены, стоимость в USD и RUB. Если OpenRouter вернёт
`401/402`, эксперимент нужно не запускать: без валидного ключа и кредитов
научные метрики будут недостоверны.

H1 на HumanEval:

```powershell
python -m inot e1 --n 20 --seeds "42,123" --suite humaneval
```

H1 на кастомном controlled-context бенчмарке:

```powershell
python -m inot e1 --n 20 --seeds "42,123" --suite controlled
```

H1 на обоих наборах:

```powershell
python -m inot e1 --n 20 --seeds "42,123" --suite both
```

Все эксперименты:

```powershell
python -m inot all --n 30 --seeds "42,123,456"
```

Сравнение Gemini Pro и Gemini Flash-Lite:

```powershell
python -m inot e6 --n 20 --seeds "42,123" --suite controlled
python -m inot view e6
```

Просмотр результатов в терминале:

```powershell
python -m inot view e1
python -m inot view e2
python -m inot view e3
python -m inot view e4
python -m inot view e5
python -m inot view e6
```

## Исследования

### E6: Gemini Pro vs Gemini Flash-Lite

Последний сохранённый реальный запуск:

```powershell
python -m inot e6 --n 10 --seeds 42 --suite controlled --output results\e6
```

Условия:

- набор задач: `controlled`;
- задач: `10`;
- seed: `42`;
- длины контекста: `512`, `2048`, `8192`;
- архитектуры: `B2_ClassicalMAS`, `B3_HybridINoT`;
- дорогая модель: `google/gemini-3.1-pro-preview`;
- дешёвая модель: `google/gemini-3.1-flash-lite`;
- суммарная стоимость запуска: примерно `$2.34`, то есть ниже лимита `$10`.

Главный вывод: на этом controlled-наборе Flash-Lite не ухудшил `pass@1`
относительно Pro ни в Classical-MAS, ни в Hybrid-INoT, но оказался существенно
дешевле.

| Архитектура | Δpass@1 Flash-Lite − Pro | Средняя стоимость Flash-Lite от Pro |
|---|---:|---:|
| `B2_ClassicalMAS` | `+0.00 п.п.` | `7.15%` |
| `B3_HybridINoT` | `+0.00 п.п.` | `5.61%` |

По длинам контекста:

| Архитектура | Контекст | Стоимость Flash-Lite от Pro | p-value Вилкоксона по `U_tok` |
|---|---:|---:|---:|
| `B2_ClassicalMAS` | `512` | `4.85%` | `0.001953` |
| `B2_ClassicalMAS` | `2048` | `6.92%` | `0.001953` |
| `B2_ClassicalMAS` | `8192` | `9.70%` | `0.001953` |
| `B3_HybridINoT` | `512` | `4.41%` | `0.001953` |
| `B3_HybridINoT` | `2048` | `5.40%` | `0.001953` |
| `B3_HybridINoT` | `8192` | `7.02%` | `0.001953` |

Интерпретация:

- Для данных controlled-задач дешёвая модель достаточно сильна: падения
  `pass@1` не наблюдается.
- Экономия сильнее проявилась в Hybrid-INoT: Flash-Lite стоил около `5.61%`
  от Pro против `7.15%` в Classical-MAS.
- По `U_tok` различия между Flash-Lite и Pro статистически значимы по парному
  критерию Вилкоксона, но это связано не с падением качества, а с другой
  токенной и стоимостной структурой ответов.
- Ограничение: это не финальный большой вывод по статье, а недорогой реальный
  прогон на `10` controlled-задачах и одном seed. Для финального вывода лучше
  повторить E6 на HumanEval и нескольких seed-ах.

Сохранённые артефакты:

- [results/e6/E6_VERDICT.md](results/e6/E6_VERDICT.md)
- [results/e6/summary.json](results/e6/summary.json)
- [results/e6/flash_vs_pro.json](results/e6/flash_vs_pro.json)
- [results/e6/table.txt](results/e6/table.txt)
- [results/e6/fig_cost_usd_flash_vs_pro.png](results/e6/fig_cost_usd_flash_vs_pro.png)
- [results/e6/fig_pass_at_1_flash_vs_pro.png](results/e6/fig_pass_at_1_flash_vs_pro.png)
- [results/e6/fig_quality_degradation_pp.png](results/e6/fig_quality_degradation_pp.png)
- [results/e6/fig_utok_flash_vs_pro.png](results/e6/fig_utok_flash_vs_pro.png)

## Структура проекта

```text
hybrid_inot_research/
├── README.md
├── CHANGELOG.md
├── config.yaml
├── .env.example
├── docs/                         Markdown-описания E1–E5
├── scripts/                      Windows setup и CLI wrapper
├── data/                         кэш HumanEval
├── results/                      результаты запусков
├── tests/                        pytest-проверки инфраструктуры
└── src/inot/
    ├── llm/                      OpenRouterClient + DryRunClient
    ├── architectures/            CTRL, B0, B1, B2, B3
    ├── tasks/                    HumanEval, controlled context, SWE-bench Lite, synthetic tools
    ├── tools/                    измерение serial/parallel tool latency для H3
    ├── metrics/                  U_tok, Q$, VCR, MAS_i, статистика
    ├── experiments/              E1–E5
    ├── verification/             sandboxed verification
    ├── runner.py                 запуск grid, сохранение, таблицы
    └── doc_viewer.py             красивый терминальный viewer
```

## Проверки разработки

```powershell
python -m ruff check src tests
python -m pytest -q
python -m inot check
```

## Типичные проблемы

### `No module named inot`

Вы не в venv или не в папке проекта. Решение:

```powershell
cd E:\JarvisSonoma\hybrid_inot_research
.\.venv\Scripts\Activate.ps1
python -m inot check
```

### `OPENROUTER_API_KEY is empty`

Создайте `.env`:

```powershell
copy .env.example .env
notepad .env
```

И впишите реальный ключ.

### `BudgetExceeded`

Сработал лимит `llm.hard_budget_usd`. Для пилотов уменьшайте `--n` и число
seed-ов; для полного запуска осознанно повышайте лимит в `config.yaml`.

## Лицензирование и цитирование

Если используете код в работе, цитируйте статью/курсовую:

```bibtex
@article{Privezentsev2026HybridINoT,
  author  = {Privezentsev, Daniil},
  title   = {Hybrid-INoT: гибридная агентная архитектура с внутренней
             ролевой сегрегацией для инженерных задач в условиях длинного
             общего контекста},
  year    = {2026}
}
```
