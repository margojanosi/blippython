# Process Overview – BrightHR Time Review MVP

## Purpose

The BrightHR Time Review MVP automates the detection of common time-log exceptions in BrightHR/Blip export data.  
It produces an Excel workbook for human review **before** payroll is processed.

It does **not** correct BrightHR records, approve payroll, or integrate with Dayforce.

---

## High-Level Process

```
BrightHR Export (CSV)
        │
        ▼
 SharePoint Folder          ← drop the file here (private, no repo commit)
        │
        ▼  Power Automate detects new file and calls GitHub API
        │
        ▼
   [1] CSV Loader
        │   Reads raw data, validates columns
        ▼
   [2] Data Normalizer
        │   Parses dates/times, calculates shift hours,
        │   break minutes, paid hours, presence flags
        ▼
   [3] Exception Rules Engine
        │   Applies each enabled rule in exception_rules.yml
        │   Produces a list of ExceptionRecord objects
        ▼
   [4] Workbook Builder
        │   Generates formatted Excel workbook with 6 tabs
        ▼
 GitHub Actions Artifact     ← download from the Actions tab
        │
        ▼
 Human Reviewer
        │   Reviews exceptions in Excel
        │   Corrects records in BrightHR manually
        ▼
 Payroll Processed
```

---

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `loader.py` | Read and validate the CSV; rename columns to internal names |
| `normalizer.py` | Parse raw strings into typed values; calculate derived fields |
| `rules.py` | Apply each exception detection rule; return ExceptionRecord list |
| `exceptions.py` | ExceptionRecord data model |
| `config.py` | Load YAML rule files; provide helper accessors |
| `workbook_builder.py` | Build and style the Excel workbook |
| `main.py` | CLI entry point; orchestrate the full pipeline |
| `logging_config.py` | Configure structured console / file logging |

---

## Data Flow

1. The payroll team exports a CSV from BrightHR and drops it into the designated SharePoint folder.
2. Power Automate detects the new file and calls the GitHub Actions workflow via `repository_dispatch`, passing the CSV content (the file never enters the repository).
3. `main.py` calls `load_csv()` to read the file into a raw DataFrame.
4. `normalize()` enriches the DataFrame with calculated fields.
5. `detect_all()` runs every enabled rule and collects exceptions.
6. `build_workbook()` writes the `.xlsx` output to `data/output/`.
7. GitHub Actions uploads the workbook as a downloadable artifact.
8. The reviewer downloads the artifact from the Actions tab and works through the Exception Report tab.
9. Any corrections are applied directly in BrightHR by the appropriate staff member.
10. The reviewed workbook is saved as payroll documentation.

---

## Key Design Decisions

- **All thresholds are configurable** – no business logic is hard-coded in Python modules.
- **Rules are independently enable/disable-able** – turn off any rule without touching code.
- **Employee-specific overrides** – future support for per-employee thresholds via YAML.
- **No side effects** – the tool only reads the CSV and writes the Excel file; nothing else is modified.
