# BrightHR Time Review MVP

A Python tool that reads a BrightHR/Blip timesheet CSV export, detects common time-log exceptions, and produces a formatted Excel review workbook.

---

## Quick Start — no software installation required

The tool runs automatically inside GitHub.  No Python, pip, or command line needed on your laptop.

### Step 1 — Upload your BrightHR CSV export

1. Open this repository on GitHub.
2. Navigate to **`data/input/`**.
3. Click **Add file → Upload files**, drag in your BrightHR CSV export, and commit it directly in the browser.

> **Privacy note:** this repository must be **private**.  Never commit real employee data to a public repo.

### Step 2 — Run the review (two options)

**Option A — automatic (recommended)**  
The **BrightHR Time Review** GitHub Actions workflow starts automatically the moment you commit a CSV to `data/input/`.  Jump straight to Step 3.

**Option B — manual trigger**  
1. Go to the **Actions** tab in this repository.
2. Click **BrightHR Time Review** in the left-hand list.
3. Click **Run workflow**, optionally type your CSV filename (default: `sample_bright_hr_export.csv`), and click **Run workflow** again.

### Step 3 — Download the workbook

1. Wait for the workflow to complete (typically 1–2 minutes; check the **Actions** tab for a green ✓).
2. Click the completed run, then click **brighthr-time-review-workbook** under *Artifacts*.
3. A `.zip` file downloads — unzip it to get the `.xlsx` Excel workbook.
4. Open the workbook and start on the **Exception Report** tab.

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

Follow the three-step Quick Start above — upload, trigger, download.  No local software needed.

After downloading the workbook:

4. **Review exceptions** — work through the **Exception Report** tab.
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

## Local Development (optional)

Only needed if you want to run tests or modify the tool itself.

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 2. Install the package and dev dependencies
pip install -e .[dev]

# 3. Run the sample CSV against the tool
python -m brighthr_time_review.main

# 4. Run tests
pytest
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