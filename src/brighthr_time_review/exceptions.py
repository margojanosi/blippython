"""Exception data model for BrightHR Time Review MVP.

Each detected anomaly is represented as an :class:`ExceptionRecord`.
"""

from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class ExceptionRecord:
    """Represents a single detected time-log exception.

    All fields map to a column in the *Exception Report* tab of the
    generated workbook.
    """

    # Valid status values
    STATUS_OPEN: ClassVar[str] = "Open"
    STATUS_CONFIRMED_CORRECT: ClassVar[str] = "Confirmed Correct"
    STATUS_CORRECTED: ClassVar[str] = "Corrected in BrightHR"
    STATUS_PAYROLL_ADJUSTMENT: ClassVar[str] = "Payroll Adjustment Needed"
    STATUS_ESCALATED: ClassVar[str] = "Escalated"
    STATUS_CLOSED: ClassVar[str] = "Closed"

    # Severity levels
    SEVERITY_HIGH: ClassVar[str] = "High"
    SEVERITY_MEDIUM: ClassVar[str] = "Medium"
    SEVERITY_LOW: ClassVar[str] = "Low"

    employee_name: str = ""
    employee_id: str = ""
    work_date: str = ""        # ISO date string for display
    exception_type: str = ""
    severity: str = "Medium"
    clock_in: str = ""
    clock_out: str = ""
    total_shift_hours: str = ""
    break_minutes: str = ""
    raw_value: str = ""
    rule_triggered: str = ""
    suggested_action: str = ""
    source_row: int = 0
    status: str = field(default="Open")
    reviewer_notes: str = ""

    def as_dict(self) -> dict:
        """Return exception fields as an ordered dict for DataFrame construction."""
        return {
            "Employee Name": self.employee_name,
            "Employee ID": self.employee_id,
            "Work Date": self.work_date,
            "Exception Type": self.exception_type,
            "Severity": self.severity,
            "Clock In": self.clock_in,
            "Clock Out": self.clock_out,
            "Total Shift Hours": self.total_shift_hours,
            "Break Minutes": self.break_minutes,
            "Raw Value": self.raw_value,
            "Rule Triggered": self.rule_triggered,
            "Suggested Action": self.suggested_action,
            "Source Row Number": self.source_row,
            "Status": self.status,
            "Reviewer Notes": self.reviewer_notes,
        }
