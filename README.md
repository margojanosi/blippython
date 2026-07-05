# BrightHR Time Review MVP

A Python tool that reads a BrightHR/Blip timesheet CSV export, detects common time-log exceptions, and produces a formatted Excel review workbook.

---

## Quick Start

### 1. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 2. Install requirements

```bash
pip install -r requirements.txt
```

### 3. Run the sample MVP

```bash
python -m brighthr_time_review.main
```

The tool reads `data/input/sample_bright_hr_export.csv` and writes the workbook to:

```
data/output/brighthr_time_review_exception_workbook.xlsx
```

### 4. Open the generated workbook

Open the file above in Microsoft Excel (or LibreOffice Calc).  
Start on the **Exception Report** tab to review flagged records.

### 5. Run tests

```bash
pytest
```

---

## Optional arguments

```bash
python -m brighthr_time_review.main \
    --input  path/to/export.csv \
    --output path/to/review_workbook.xlsx \
    --rules  path/to/exception_rules.yml \
    --employee-rules path/to/employee_rules.yml \
    --log-level DEBUG
```

---

## MVP Boundaries

| What this tool DOES | What this tool does NOT do |
|---|---|
| Reads a BrightHR/Blip CSV export | Modify BrightHR, Dayforce, or any payroll system |
| Detects common time-log exceptions | Approve, reject, or submit payroll |
| Produces an Excel review workbook | Automatically correct employee records |
| Flags records for human review | Submit anything to Dayforce |

**A human reviewer must confirm every exception.  
BrightHR is the authoritative source of truth.**

---

## How to Use With Real BrightHR Exports

1. **Export the CSV** from BrightHR / Blip under the Timesheets section.
2. **Save a copy** of the CSV into `data/input/` (rename it to avoid accidental overwrites).
3. **Run the tool** with the real file path:
   ```bash
   python -m brighthr_time_review.main --input data/input/my_export.csv
   ```
4. **Review the workbook** – open the generated `.xlsx` file and work through the Exception Report tab.
5. **Correct confirmed issues** in BrightHR manually, following your usual payroll correction process.
6. **Save the reviewed workbook** as payroll support documentation (update Status and Reviewer Notes columns before saving).

---

## Configuring Exception Rules

Edit `config/exception_rules.yml` to adjust thresholds:

- `max_shift_hours_default` – maximum acceptable shift length  
- `min_shift_hours_default` – minimum acceptable shift length  
- `break_required_after_hours` – shifts longer than this must have a break  
- `min_break_minutes` / `max_break_minutes` – break duration bounds  
- `weekend_work_allowed_default` – set `true` if weekend work is normal  
- Enable / disable any rule with `enabled: true / false`

Employee-specific overrides can be added to `config/employee_rules.yml`  
(see `config/employee_rules.sample.yml` for the format).

---

## Repository Structure

```
brighthr_time_review/
├── README.md
├── ASSUMPTIONS.md
├── CHANGELOG.md
├── requirements.txt
├── pyproject.toml
├── config/
│   ├── exception_rules.yml          ← edit thresholds here
│   └── employee_rules.sample.yml   ← template for per-employee rules
├── data/
│   ├── input/
│   │   └── sample_bright_hr_export.csv
│   └── output/                      ← generated workbooks land here
├── src/
│   └── brighthr_time_review/
│       ├── main.py                  ← CLI entry point
│       ├── config.py                ← rule/config loading
│       ├── loader.py                ← CSV ingestion
│       ├── normalizer.py            ← data normalisation
│       ├── rules.py                 ← exception detection
│       ├── exceptions.py            ← ExceptionRecord model
│       ├── workbook_builder.py      ← Excel generation
│       └── logging_config.py
├── tests/
│   ├── test_loader.py
│   ├── test_normalizer.py
│   ├── test_rules.py
│   └── test_workbook_builder.py
└── docs/
    ├── process_overview.md
    ├── exception_rule_definitions.md
    ├── handoff_instructions.md
    └── reviewer_user_guide.md
```

---

## Next Enhancements

The following improvements are planned for future iterations:

1. **SharePoint folder automation** – automatically pick up new CSV exports from a watched SharePoint folder.
2. **Power Automate trigger** – trigger a review run when a new file appears in SharePoint.
3. **Teams notification** – send a Teams message when exceptions are detected, linking to the workbook.
4. **BrightHR API integration** – read time logs directly via API (if BrightHR approves API access).
5. **Dayforce import preparation** – generate a Dayforce-compatible correction file after human approval.
6. **Employee-specific rules** – full per-employee threshold configuration via a managed YAML or database.
7. **Historical trend reporting** – compare exception counts across payroll periods.
8. **Manager sign-off workflow** – add an approval column and email notification to line managers.

---

## Data Privacy Notice

This tool is designed for **fake / sample data only** during MVP development.  
When used with real BrightHR exports, treat the generated workbooks as **payroll-sensitive documents**.  
Do not commit real employee data to source control.