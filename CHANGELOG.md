# История изменений

## 0.3.0 — окружение, ключи и RUB-учёт

- Добавлены Windows-скрипты:
  - `scripts/setup_windows.ps1` создаёт `.venv`, ставит пакет и готовит `.env`;
  - `scripts/inot.ps1` запускает CLI через проектный Python.
- README полностью переведён на русский.
- Добавлено описание хранения `OPENROUTER_API_KEY` в локальном `.env`.
- `.env.*` исключены из git, кроме `.env.example`.
- Добавлен воспроизводимый пересчёт стоимости в рубли через
  `accounting.usd_to_rub` в `config.yaml`.
- `TokenUsage`, `RunResult`, summary-таблицы и `runs.json` теперь содержат
  `cost_rub` наряду с `cost_usd`.
- Добавлен preflight budget guard для OpenRouter-запросов.

## 0.2.0 — усиление научной постановки

- Добавлен контрольный baseline `CTRL_NoAssistant`.
- Добавлен controlled-context benchmark для H1.
- Команда E1 получила параметр `--suite humaneval|controlled|both`.
- Добавлен deterministic tool-latency harness для H3:
  serial Hybrid-style execution против parallel Classical-MAS-style execution.
- E2c теперь сохраняет `tool_latency_serial.json` и
  `tool_latency_parallel.json`.
- Добавлены тесты для новых research-модулей.

## 0.1.0 — первичная исследовательская инфраструктура

- Реализованы архитектуры B0, B1, B2, B3.
- Добавлены E1–E5.
- Добавлен OpenRouter backend и deterministic `DryRunClient`.
- Добавлены метрики `pass@1`, `U_tok`, `Q$`, `VCR`, `MAS_i`.
- Добавлены Wilcoxon signed-rank, McNemar, bootstrap CI и Holm-Bonferroni.
- Добавлен rich terminal viewer: `python -m inot view <experiment>`.
- Добавлены markdown-документы `docs/e1.md`–`docs/e5.md`.
