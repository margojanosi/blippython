# Exception Rule Definitions – BrightHR Time Review MVP

This document explains each exception type in plain language.

All thresholds are configurable in `config/exception_rules.yml`.

---

## 1. Missing Clock Out

**What it means:**  
An employee clocked in but there is no clock-out time recorded for that shift.

**Why it matters:**  
Without a clock-out, the system cannot calculate how long the employee worked.  
Payroll may pay for time that was not worked, or fail to calculate the shift at all.

**Default severity:** High  
**Suggested action:** Confirm the actual end time with the employee or their manager, then update BrightHR.

---

## 2. Missing Clock In

**What it means:**  
A clock-out is recorded but there is no corresponding clock-in for that shift.

**Why it matters:**  
Without a clock-in, the start of the shift is unknown.  
This could result in incorrect pay or a missed attendance record.

**Default severity:** High  
**Suggested action:** Confirm the actual start time with the employee or their manager, then update BrightHR.

---

## 3. Missing Break

**What it means:**  
The employee worked a shift longer than the configured threshold (default: 6 hours) but no break was recorded.

**Why it matters:**  
Employees are typically required to take a break after a certain number of hours under employment law / company policy.  
A missing break may indicate the employee did not take a break (compliance risk) or simply forgot to record it in BrightHR.

**Configurable threshold:** `break_required_after_hours` (default: 6 hours)  
**Default severity:** Medium  
**Suggested action:** Confirm whether a break was taken and update BrightHR if needed.

---

## 4. Break Too Short

**What it means:**  
A break was recorded but its duration is below the minimum acceptable length (default: 20 minutes).

**Why it matters:**  
Very short breaks may indicate a data entry error or a compliance concern if the organisation has a minimum break policy.

**Configurable threshold:** `min_break_minutes` (default: 20 minutes)  
**Default severity:** Low  
**Suggested action:** Confirm the actual break duration with the employee.

---

## 5. Break Too Long

**What it means:**  
A break was recorded but its duration exceeds the maximum expected length (default: 60 minutes).

**Why it matters:**  
An unusually long break may indicate the employee forgot to clock back in after their break,  
which would result in underreported shift time and potentially incorrect pay.

**Configurable threshold:** `max_break_minutes` (default: 60 minutes)  
**Default severity:** Low  
**Suggested action:** Confirm whether the employee forgot to clock back in, or whether the break was genuinely that long.

---

## 6. Shift Too Long

**What it means:**  
The calculated shift duration (clock-in to clock-out) exceeds the maximum expected shift length (default: 12 hours).

**Why it matters:**  
An unusually long shift may indicate a forgotten clock-out from the previous day, unauthorised overtime, or a system error.

**Configurable threshold:** `max_shift_hours_default` (default: 12 hours)  
**Default severity:** High  
**Suggested action:** Review the record for a possible forgotten clock-out, overtime, or schedule exception.

---

## 7. Shift Too Short

**What it means:**  
A complete shift (both clock-in and clock-out present) is shorter than the minimum expected duration (default: 1 hour).

**Why it matters:**  
A very short shift may indicate an accidental clock-in/out, a test entry, or a record that needs investigation before payroll.

**Configurable threshold:** `min_shift_hours_default` (default: 1 hour)  
**Default severity:** Low  
**Suggested action:** Review for an accidental clock-in or an incomplete shift record.

---

## 8. Duplicate Shift

**What it means:**  
The same employee has two or more records with exactly the same date, clock-in time, and clock-out time.

**Why it matters:**  
Duplicate entries would result in double-paying the employee for the same period.

**Default severity:** High  
**Suggested action:** Confirm which entry is correct and remove the duplicate from BrightHR.

---

## 9. Overlapping Shift

**What it means:**  
The same employee has two or more shifts on the same date whose time ranges overlap (one starts before the other ends).

**Why it matters:**  
An employee cannot physically work two shifts at the same time.  
Overlapping records indicate a data entry error that could result in overpayment.

**Default severity:** High  
**Suggested action:** Confirm which shift records are correct and remove or adjust the incorrect entry in BrightHR.

---

## 10. Weekend Entry

**What it means:**  
An employee has a time-log entry on a Saturday or Sunday, and the rules configuration does not expect weekend work.

**Why it matters:**  
Unexpected weekend entries may indicate unauthorised working, a system error, or entries made on the wrong date.

**Configuration:** `weekend_work_allowed_default` (default: false)  
Employee-specific overrides can mark individual employees as permitted for weekend work.  
**Default severity:** Medium  
**Suggested action:** Confirm whether the weekend work was authorised before including it in payroll.
