"""CSV loader for BrightHR/Blip timesheet exports.

Reads the raw CSV and returns a pandas DataFrame with consistent column
names used throughout the rest of the pipeline.

NOTE: BrightHR column names may vary between export formats / regions.
      If your export uses different headers, update COLUMN_MAP below.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column mapping: CSV header → internal name
# Adjust left-hand keys to match the actual BrightHR export column names.
# ---------------------------------------------------------------------------
COLUMN_MAP: dict[str, str] = {
    # BrightHR export column   → internal column name
    "Employee Name": "employee_name",
    "Employee ID": "employee_id",
    "Work Date": "work_date_raw",
    "Clock In": "clock_in_raw",
    "Clock Out": "clock_out_raw",
    "Break Start": "break_start_raw",
    "Break End": "break_end_raw",
    "Break Minutes": "break_minutes_raw",
    "Location": "location",
    "Notes": "notes",
}

# Columns that MUST be present in the CSV for the tool to function.
REQUIRED_COLUMNS = {"Employee Name", "Work Date", "Clock In", "Clock Out"}


def load_csv(input_path: Path) -> pd.DataFrame:
    """Load a BrightHR/Blip timesheet CSV file.

    Reads the CSV, validates required columns are present, renames headers
    to internal names, and returns the resulting DataFrame.  An index column
    ``source_row`` is added that reflects the original 1-based row number
    in the CSV (header = row 0, first data row = row 1).

    Args:
        input_path: Path to the CSV file.

    Returns:
        DataFrame with internal column names.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError:        If required columns are missing.
    """
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    logger.info("Loading CSV from %s", path)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    # Trim leading/trailing whitespace from column names
    df.columns = [c.strip() for c in df.columns]

    # Check required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {missing}. "
            f"Found columns: {list(df.columns)}"
        )

    # Warn about unexpected / unmapped columns
    known = set(COLUMN_MAP.keys())
    unknown_cols = set(df.columns) - known
    if unknown_cols:
        logger.warning(
            "CSV contains unmapped columns (they will be ignored): %s",
            sorted(unknown_cols),
        )

    # Keep only known columns that are present
    cols_to_keep = [c for c in df.columns if c in COLUMN_MAP]
    df = df[cols_to_keep].copy()

    # Rename to internal names
    df.rename(columns=COLUMN_MAP, inplace=True)

    # Add source row number (1-based, matching the original CSV data rows)
    df.insert(0, "source_row", range(1, len(df) + 1))

    logger.info("Loaded %d rows from %s", len(df), path)
    return df
