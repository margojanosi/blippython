# Changelog – BrightHR Time Review MVP

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.1.0] – 2024-06

### Added
- Initial MVP scaffold and full working implementation.
- `loader.py` – reads BrightHR/Blip CSV exports with configurable column mapping.
- `normalizer.py` – parses and calculates shift hours, break minutes, paid hours, and presence flags.
- `rules.py` – detects 10 exception types: missing clock-in, missing clock-out, missing break, short/long break, short/long shift, duplicate shift, overlapping shift, weekend entry.
- `workbook_builder.py` – generates a formatted six-tab Excel workbook.
- `config.py` – loads `exception_rules.yml` and optional `employee_rules.yml`.
- `main.py` – CLI entry point with `--input`, `--output`, `--rules`, `--employee-rules`, `--log-level` arguments.
- `config/exception_rules.yml` – all thresholds and feature flags with documentation.
- `config/employee_rules.sample.yml` – template for per-employee rule overrides.
- `data/input/sample_bright_hr_export.csv` – fake sample data covering all exception types.
- `tests/` – pytest test suite for loader, normalizer, rules, and workbook builder.
- `docs/` – process overview, exception rule definitions, handoff instructions, reviewer user guide.
- `ASSUMPTIONS.md` – documented design assumptions.
- `README.md` – quick start, boundaries, and next-enhancement sections.
