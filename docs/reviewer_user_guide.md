# Reviewer User Guide – BrightHR Time Review Workbook

**This guide is written for operations and payroll reviewers.**  
No technical knowledge is required.

---

## What Is This Workbook?

This workbook was automatically generated from a BrightHR/Blip timesheet export.

It flags time records that may need to be checked before payroll is processed.

> ⚠️ **Important:**  
> This workbook does **not** approve payroll, correct BrightHR, or submit anything to Dayforce.  
> It is a **review tool only**.  
> All corrections must be made manually in BrightHR by an authorised person.

---

## Your Job as a Reviewer

1. Open the **Exception Report** tab (second tab in this workbook).
2. Work through each row.
3. Decide whether the exception is a real issue or is already correct.
4. Update the **Status** column for each row.
5. Add any notes in the **Reviewer Notes** column.
6. When finished, **save the workbook** – it becomes your payroll documentation.

---

## The Tabs Explained

| Tab | What It Shows |
|---|---|
| **Instructions** | How to use this workbook (you are reading the guide version now) |
| **Exception Report** | Every flagged exception – **this is your main working tab** |
| **Summary** | Count of exceptions by severity, type, and employee |
| **Rules Used** | The detection thresholds that were applied |
| **Raw Normalized Data** | The cleaned version of the BrightHR export |
| **Review Log** | When the tool was run, which file was used, and any warnings |

---

## The Exception Report Columns

| Column | What It Means |
|---|---|
| **Employee Name** | Who the exception is for |
| **Employee ID** | Their BrightHR employee ID |
| **Work Date** | The date of the shift |
| **Exception Type** | What type of problem was detected |
| **Severity** | High / Medium / Low (colour-coded) |
| **Clock In** | Recorded clock-in time |
| **Clock Out** | Recorded clock-out time |
| **Total Shift Hours** | Calculated shift length in hours |
| **Break Minutes** | Recorded break duration |
| **Raw Value** | The actual value that triggered the rule |
| **Rule Triggered** | Which rule detected this exception |
| **Suggested Action** | What to check or do |
| **Source Row Number** | The row in the original CSV export |
| **Status** | Your review decision (update this column) |
| **Reviewer Notes** | Your free-text comments |

---

## Status Values – What to Choose

| Status | When to Use It |
|---|---|
| **Open** | Not yet reviewed (default) |
| **Confirmed Correct** | You checked and the record is fine – no BrightHR change needed |
| **Corrected in BrightHR** | You (or a colleague) have already updated BrightHR |
| **Payroll Adjustment Needed** | A payroll change is required before this period is processed |
| **Escalated** | You need to raise this with a manager or HR before deciding |
| **Closed** | Fully resolved – no further action needed |

---

## Colour Coding

The **Severity** column is colour-coded to help you prioritise:

- 🔴 **Red = High** – Review these first (missing clock-ins/outs, duplicates, overlaps, very long shifts).
- 🟠 **Amber = Medium** – Review next (missing breaks, weekend entries).
- 🟢 **Green = Low** – Review last (short/long breaks, very short shifts).

---

## Step-by-Step Review

1. Open the **Exception Report** tab.
2. Sort or filter by **Severity** (High first).
3. For each row:
   - Read the **Exception Type** and **Suggested Action**.
   - Check the record in BrightHR if needed.
   - If a correction is required, make it in BrightHR (not in this workbook).
   - Update the **Status** column.
   - Add notes if helpful.
4. Once all rows are reviewed, check the **Summary** tab to confirm no open exceptions remain.
5. Save the workbook with a meaningful file name (e.g. `Payroll_Review_June2024.xlsx`).

---

## Common Exceptions and What to Do

| Exception Type | Typical Cause | What to Do |
|---|---|---|
| Missing Clock Out | Forgot to clock out | Ask the employee / check schedule, update BrightHR |
| Missing Clock In | Forgot to clock in | Ask the employee / check schedule, update BrightHR |
| Missing Break | Break not recorded | Confirm break was taken; update BrightHR if needed |
| Break Too Short | Possible entry error | Confirm with employee; correct if needed |
| Break Too Long | Forgot to clock back in | Check if extra time should be unpaid; correct in BrightHR |
| Shift Too Long | Possible forgotten clock-out | Confirm end time; correct in BrightHR |
| Shift Too Short | Accidental clock-in | Confirm with employee; remove if incorrect |
| Duplicate Shift | Duplicate data entry | Remove the duplicate in BrightHR |
| Overlapping Shift | Two entries overlap | Correct the dates/times in BrightHR |
| Weekend Entry | Unexpected weekend work | Confirm if authorised; escalate if not |

---

## Questions?

If you are unsure about a specific exception, add a note in the **Reviewer Notes** column and set the **Status** to **Escalated**.  
Then raise it with your manager or the payroll team before the payroll deadline.
