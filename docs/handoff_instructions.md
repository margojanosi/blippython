# Handoff Instructions – BrightHR Time Review MVP

This document is for the person taking ownership of this process after the initial build.

---

## What You Are Taking Over

A Python-based tool that:

1. Reads a BrightHR/Blip timesheet CSV export.
2. Detects common time-log exceptions automatically.
3. Produces a formatted Excel workbook for human review.

The tool does **not** modify BrightHR, approve payroll, or connect to Dayforce.

---

## What You Need to Run It

| Requirement | Details |
|---|---|
| Python 3.11 or newer | Install from python.org or via your system package manager |
| pip | Included with Python |
| The repository | Clone or download from GitHub |

---

## First-Time Setup

```bash
# 1. Clone the repository
git clone <repository-url>
cd brighthr-time-review-mvp

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Running the Tool Each Payroll Period

```bash
# Place the BrightHR export in data/input/
# Then run:
python -m brighthr_time_review.main --input data/input/your_export.csv

# The workbook is generated at:
# data/output/brighthr_time_review_exception_workbook.xlsx
```

Open the workbook and work through the Exception Report tab.

---

## Adjusting Exception Thresholds

Edit `config/exception_rules.yml` to change any threshold.  
No Python knowledge is required – the file is plain text.

Key settings:

```yaml
max_shift_hours_default:
  value: 12    ← change this number

min_break_minutes:
  value: 20    ← change this number

weekend_work_allowed_default:
  value: false   ← change to true if weekend work is normal
```

---

## Adding Employee-Specific Rules

1. Copy `config/employee_rules.sample.yml` to `config/employee_rules.yml`.
2. Add or edit entries following the sample format.
3. Run with `--employee-rules config/employee_rules.yml`.

---

## Running Tests

```bash
pytest
```

All tests should pass before and after any changes.

---

## Files to Know

| File | Purpose |
|---|---|
| `config/exception_rules.yml` | All detection thresholds – edit here |
| `config/employee_rules.sample.yml` | Template for per-employee rules |
| `data/input/` | Place BrightHR CSV exports here |
| `data/output/` | Generated workbooks land here |
| `src/brighthr_time_review/` | Python source code |
| `docs/` | Documentation |

---

## Who to Contact

- **For changes to exception rules or thresholds:** edit `config/exception_rules.yml` (no code change needed).
- **For changes to the Python logic:** consult the original developer or a Python-capable colleague.
- **For BrightHR export format changes:** update `loader.py::COLUMN_MAP` to match the new column names.

---

## Important Reminders

- Never commit real employee data to source control.
- Save each reviewed workbook as a payroll audit record.
- All corrections to time records must be made in BrightHR by an authorised person.
- This tool flags issues for review only – it does not make any changes automatically.
