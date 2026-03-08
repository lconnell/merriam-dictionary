"""
Entry point: python -m merriam_dictionary [options]
"""

import argparse
import json
import logging
import sys

from .auth import login_and_get_cookies
from .config import DEFAULT_LOG_FILE, DEFAULT_OUTPUT_FILE, load_config
from .dictionary import enrich_words
from .wordlist import fetch_saved_words


_LEVEL_COLORS: dict[str, str] = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[35m",  # magenta
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{_RESET}"
        return super().format(record)


def _setup_logging(log_to_stderr: bool, log_file: str | None) -> None:
    """
    Configures the root logger. Logs always go to stderr (never stdout) so that
    --print-json can pipe clean JSON without interleaved log lines.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if log_to_stderr:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(_ColorFormatter(fmt))
        root.addHandler(stderr_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, mode="w")
        file_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_handler)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export Merriam-Webster saved words with definitions and examples."
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_FILE,
        metavar="FILE",
        help=f"Output JSON file path (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print JSON output to stdout in addition to writing the output file",
    )
    parser.add_argument(
        "--no-stderr-log",
        action="store_true",
        help="Suppress log output to stderr",
    )
    parser.add_argument(
        "--no-logfile",
        action="store_true",
        help="Suppress log output to file",
    )
    parser.add_argument(
        "--log-file",
        default=DEFAULT_LOG_FILE,
        metavar="FILE",
        help=f"Log file path (default: {DEFAULT_LOG_FILE})",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    _setup_logging(
        log_to_stderr=not args.no_stderr_log,
        log_file=None if args.no_logfile else args.log_file,
    )
    logger = logging.getLogger(__name__)

    try:
        config = load_config(output_file=args.output)
    except EnvironmentError as exc:
        logger.error(str(exc))
        sys.exit(1)

    try:
        cookies = login_and_get_cookies(config.email, config.password)
        words = fetch_saved_words(cookies)
        entries = enrich_words(words, config.api_key)
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)

    output = {
        "total_words": len(entries),
        "data": [entry.to_dict() for entry in entries],
    }
    final_json = json.dumps(output, indent=2)

    with open(config.output_file, "w") as f:
        f.write(final_json)
    logger.info("Output saved to %s", config.output_file)

    if args.print_json:
        print(final_json)


if __name__ == "__main__":
    main()
