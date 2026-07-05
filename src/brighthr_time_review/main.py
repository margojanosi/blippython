"""Command-line entry point for BrightHR Time Review MVP.

Usage:
    python -m brighthr_time_review.main
    python -m brighthr_time_review.main --input path/to/file.csv --output path/to/output.xlsx
    python -m brighthr_time_review.main --rules path/to/exception_rules.yml
    python -m brighthr_time_review.main --employee-rules path/to/employee_rules.yml
"""

import argparse
import logging
import sys
from pathlib import Path

from brighthr_time_review.config import load_employee_rules, load_exception_rules
from brighthr_time_review.loader import load_csv
from brighthr_time_review.logging_config import configure_logging
from brighthr_time_review.normalizer import normalize
from brighthr_time_review.rules import detect_all
from brighthr_time_review.workbook_builder import build_workbook

logger = logging.getLogger(__name__)

# Default paths (relative to the project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_INPUT = _PROJECT_ROOT / "data" / "input" / "sample_bright_hr_export.csv"
_DEFAULT_OUTPUT = (
    _PROJECT_ROOT / "data" / "output" / "brighthr_time_review_exception_workbook.xlsx"
)
_DEFAULT_RULES = _PROJECT_ROOT / "config" / "exception_rules.yml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="brighthr-time-review",
        description=(
            "BrightHR Time Review MVP – analyses a BrightHR/Blip timesheet CSV "
            "and generates an Excel exception review workbook."
        ),
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=_DEFAULT_INPUT,
        metavar="CSV_PATH",
        help=f"Path to the BrightHR export CSV (default: {_DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_DEFAULT_OUTPUT,
        metavar="XLSX_PATH",
        help=f"Output workbook path (default: {_DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=_DEFAULT_RULES,
        metavar="RULES_YML",
        help=f"Path to exception_rules.yml (default: {_DEFAULT_RULES})",
    )
    parser.add_argument(
        "--employee-rules",
        type=Path,
        default=None,
        metavar="EMPLOYEE_RULES_YML",
        help="Path to employee_rules.yml (optional).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = parse_args(argv)
    configure_logging(log_level=args.log_level)

    logger.info("=" * 60)
    logger.info("BrightHR Time Review MVP")
    logger.info("=" * 60)

    warnings: list[str] = []

    try:
        # 1. Load rules
        logger.info("Loading exception rules from %s", args.rules)
        rules = load_exception_rules(args.rules)
        employee_rules = load_employee_rules(args.employee_rules)

        # 2. Load CSV
        logger.info("Loading input CSV from %s", args.input)
        raw_df = load_csv(args.input)

        # 3. Normalise
        logger.info("Normalising data …")
        norm_df = normalize(raw_df)

        # Collect any normalization warnings for the workbook Review Log
        for _, row in norm_df.iterrows():
            if row.get("normalization_warnings"):
                warnings.append(
                    f"Row {row['source_row']}: {row['normalization_warnings']}"
                )

        # 4. Detect exceptions
        logger.info("Running exception detection …")
        exceptions = detect_all(norm_df, rules, employee_rules)

        # 5. Build workbook
        logger.info("Building Excel workbook …")
        out_path = build_workbook(
            df_normalized=norm_df,
            exceptions=exceptions,
            rules=rules,
            input_path=args.input,
            output_path=args.output,
            warnings=warnings,
        )

        logger.info("=" * 60)
        logger.info("✅  Done!  Workbook saved to: %s", out_path)
        logger.info(
            "   %d records reviewed, %d exception(s) flagged.",
            len(norm_df),
            len(exceptions),
        )
        logger.info("=" * 60)
        return 0

    except FileNotFoundError as exc:
        logger.error("File not found: %s", exc)
        return 1
    except ValueError as exc:
        logger.error("Data error: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
