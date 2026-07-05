# Assumptions – BrightHR Time Review MVP

This document records the assumptions made during the initial design and implementation of the MVP.  
If any assumption proves incorrect, update the relevant module and re-document the change here.

---

## Data & Input

1. **CSV column names** – The BrightHR/Blip export uses the exact column headers listed in `loader.py::COLUMN_MAP`.  
   If the export format differs (e.g. localised headers or additional columns), update the mapping and re-run.

2. **Date format** – Work dates are expected in `YYYY-MM-DD`, `DD/MM/YYYY`, or `MM/DD/YYYY` format.  
   Multiple formats are attempted in order. Add further formats to `normalizer._DATE_FORMATS` if needed.

3. **Time format** – Clock-in / clock-out / break times are expected in `HH:MM` or `HH:MM:SS` (24-hour) or `HH:MM AM/PM` (12-hour).

4. **No overnight shifts in MVP** – All shifts are assumed to start and end on the same calendar date.  
   Shifts crossing midnight are not currently handled and will produce negative shift hours (flagged as a warning).

5. **Break minutes fallback** – If Break Start and Break End are blank but Break Minutes is populated, the raw Break Minutes value is used for calculations.

6. **Empty strings vs. blank cells** – BrightHR CSV exports may use empty strings (`""`) for missing values. The loader reads all columns as strings to avoid silent dtype conversions.

---

## Business Rules

7. **Break threshold** – A break is required for any shift ≥ 6 hours (configurable in `exception_rules.yml`).  
   This is a common UK / Irish employment standard but should be confirmed with the organisation's policy.

8. **Minimum break** – 20 minutes is assumed as the minimum acceptable break (configurable).

9. **Maximum break** – 60 minutes is assumed as the maximum expected break (configurable).  
   Longer breaks may indicate a forgotten clock-in after break.

10. **Max shift hours** – 12 hours is assumed as the maximum expected shift length (configurable).

11. **Min shift hours** – 1 hour is assumed as the minimum expected shift length for a complete shift (configurable).

12. **Weekend policy** – Weekend work is **not** expected by default (`weekend_work_allowed_default: false`).  
    This can be overridden globally or per employee.

13. **Duplicate detection** – Two records are considered duplicates if they share the same employee name,  
    work date, clock-in time, and clock-out time.

14. **Overlap detection** – Two shifts overlap if the clock-out of the earlier shift is after the clock-in of the later shift for the same employee on the same date.

---

## Architecture & Design

15. **Single-file input** – The MVP processes one CSV file per run.

16. **No database** – All state is in-memory for each run; no persistence between runs.

17. **No authentication** – The tool reads local files only. No BrightHR API credentials are required or used.

18. **Employee rules are optional** – The tool runs correctly without an employee_rules.yml.

19. **Output directory is created automatically** – If `data/output/` does not exist, it is created at runtime.

20. **Workbook overwrites previous output** – Each run overwrites the previous workbook at the default output path.  
    Users should save a copy before re-running if they want to preserve a reviewed version.

---

## Scope & Exclusions

21. **No payroll calculations** – This tool does not calculate pay, overtime rates, or deductions.

22. **No BrightHR API** – This is a pure offline CSV analysis tool.

23. **No email / Teams integration in MVP** – Notifications are out of scope for the initial version.

24. **No multi-tenant support** – The MVP is designed for a single organisation.
