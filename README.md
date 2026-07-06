# BrightHR Time Review MVP

A Python tool that reads a BrightHR/Blip timesheet CSV export, detects common time-log exceptions, and produces a formatted Excel review workbook.

---

## Quick Start — no software installation required

The tool runs automatically inside GitHub.  No Python, pip, or command line needed on your laptop.

### Production path — SharePoint trigger (recommended)

BrightHR CSV exports stay in a private SharePoint folder.  Power Automate detects new files and triggers the review automatically.  The output workbook is written back to SharePoint — it is never stored as a public GitHub artifact.

1. **Drop the CSV** into the designated SharePoint folder (see `docs/sharepoint_power_automate_setup.md` for one-time setup).
2. **Wait 1–2 minutes** — Power Automate triggers GitHub Actions automatically.
3. The completed workbook appears in the SharePoint folder configured via the `SHAREPOINT_FOLDER_PATH` secret.
4. Open the `.xlsx` workbook in SharePoint and start on the **Exception Report** tab.

> The CSV never enters the GitHub repository.  
> The output workbook is uploaded directly to SharePoint and never stored as a downloadable GitHub artifact.

### Testing path — manual trigger

Useful for verifying the setup with sample data, or if the SharePoint trigger is unavailable.

1. Go to the **Actions** tab in this repository.
2. Click **BrightHR Time Review** in the left-hand list.
3. Click **Run workflow** and then **Run workflow** again (uses the bundled sample CSV).
4. The workbook is uploaded to SharePoint (if the `SHAREPOINT_*` secrets are configured).  For `push`-triggered runs using sample data, the workbook is also available as a temporary artifact under the Actions run for developer convenience.

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

Follow the production Quick Start path above — drop in SharePoint, wait, download.

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
│   └── output/                      ← generated workbooks land here locally
├── src/
│   └── brighthr_time_review/
│       ├── main.py                  ← CLI entry point
│       ├── config.py                ← rule/config loading
│       ├── loader.py                ← CSV ingestion
│       ├── normalizer.py            ← data normalisation
│       ├── rules.py                 ← exception detection
│       ├── exceptions.py            ← ExceptionRecord model
│       ├── workbook_builder.py      ← Excel generation
│       ├── sharepoint_uploader.py   ← Graph API upload to SharePoint
│       └── logging_config.py
├── tests/
│   ├── test_loader.py
│   ├── test_normalizer.py
│   ├── test_rules.py
│   ├── test_workbook_builder.py
│   └── test_sharepoint_uploader.py
└── docs/
    ├── process_overview.md
    ├── exception_rule_definitions.md
    ├── handoff_instructions.md
    ├── sharepoint_power_automate_setup.md
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

1. **Teams notification** – send a Teams message when exceptions are detected, linking to the workbook.
2. **BrightHR API integration** – read time logs directly via API (if BrightHR approves API access).
3. **Dayforce import preparation** – generate a Dayforce-compatible correction file after human approval.
4. **Employee-specific rules** – full per-employee threshold configuration via a managed YAML or database.
5. **Historical trend reporting** – compare exception counts across payroll periods.
6. **Manager sign-off workflow** – add an approval column and email notification to line managers.

---

## Data Privacy Notice

This tool is designed for **fake / sample data only** during MVP development.  
When used with real BrightHR exports, treat the generated workbooks as **payroll-sensitive documents**.  
Do not commit real employee data to source control.