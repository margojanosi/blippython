# Handoff Instructions – BrightHR Time Review MVP

This document is for the person taking ownership of this process after the initial build.

---

## What You Are Taking Over

A tool that:

1. Detects a new BrightHR/Blip timesheet CSV export in a private SharePoint folder.
2. Runs it automatically through an exception-detection engine in GitHub's cloud.
3. Produces a formatted Excel workbook for human review before payroll is processed.

**No software installation is required on your laptop.**  The tool runs entirely in GitHub Actions — a free CI/CD service built into GitHub.

The tool does **not** modify BrightHR, approve payroll, or connect to Dayforce.

---

## What You Need

| Requirement | Details |
|---|---|
| Access to this GitHub repository | Must be **private** — contact the repository owner if you need to be added |
| Access to the designated SharePoint folder | Where BrightHR CSV exports are dropped; contact your Microsoft 365 admin |
| Microsoft 365 / Power Automate | Included in most Microsoft 365 business plans |

That's it.  No Python, no pip, no command line.

---

## How to Run Each Payroll Period

1. **Export the CSV** from BrightHR → Timesheets section.
2. **Drop it** into the designated SharePoint folder.
3. Power Automate detects the file automatically and triggers the GitHub Actions workflow.
4. **Wait 1–2 minutes** — check the GitHub **Actions** tab for a green ✓.
5. Click the completed run, then click **brighthr-time-review-workbook** under *Artifacts*.
6. A `.zip` file downloads — unzip it to get the `.xlsx` Excel workbook.
7. Open the workbook and work through the **Exception Report** tab.
8. **Correct confirmed issues** in BrightHR manually, following your usual payroll correction process.
9. **Save the reviewed workbook** as payroll support documentation (update Status and Reviewer Notes columns).

> **Manual trigger (backup):** If the automatic trigger is unavailable, go to GitHub → **Actions** tab → **BrightHR Time Review** → **Run workflow**.  This processes the sample CSV and is useful for testing.

---

## Adjusting Exception Thresholds

All detection thresholds are in `config/exception_rules.yml` in this repository.  You can edit this file directly in the GitHub web browser — no tools required:

1. Open `config/exception_rules.yml` in the repository.
2. Click the **pencil (Edit)** icon.
3. Change the value (e.g. `max_shift_hours_default: value: 12` → `10`).
4. Click **Commit changes**.

Key settings:

```yaml
max_shift_hours_default:
  value: 12    ← maximum acceptable shift length in hours

min_break_minutes:
  value: 20    ← shortest acceptable break in minutes

weekend_work_allowed_default:
  value: false   ← change to true if weekend work is normal for your team
```

To disable a rule entirely, set `enabled: false` for that rule.

---

## Adding Employee-Specific Rules

1. In the repository, open `config/employee_rules.sample.yml` to see the format.
2. Create (or ask a developer to create) `config/employee_rules.yml` following the same format.
3. The workflow will pick it up automatically on the next run.

---

## Files to Know

| File | Purpose |
|---|---|
| `config/exception_rules.yml` | All detection thresholds — edit here |
| `config/employee_rules.sample.yml` | Template for per-employee rules |
| `.github/workflows/run_time_review.yml` | The automated workflow — do not modify unless you know what you are doing |
| `docs/sharepoint_power_automate_setup.md` | Step-by-step guide for setting up the SharePoint trigger |
| `docs/reviewer_user_guide.md` | Guide for the person reviewing the output workbook |
| `src/brighthr_time_review/` | Python source code — only modify if changing logic |

---

## Who to Contact

- **For changes to thresholds:** edit `config/exception_rules.yml` in GitHub (no code change needed).
- **For SharePoint or Power Automate issues:** see `docs/sharepoint_power_automate_setup.md`; contact your Microsoft 365 admin if needed.
- **For changes to the detection logic or new rules:** consult the original developer or a Python-capable colleague.
- **For BrightHR export format changes:** a developer needs to update `loader.py::COLUMN_MAP` to match the new column names.

---

## Important Reminders

- The CSV export stays in SharePoint — **never commit real employee data to the GitHub repository**.
- Save each reviewed workbook as a payroll audit record.
- All corrections to time records must be made in BrightHR by an authorised person.
- This tool flags issues for review only — it does not make any changes automatically.

