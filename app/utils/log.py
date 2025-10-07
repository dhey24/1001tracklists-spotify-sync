import logging
import os
from datetime import datetime
from typing import Optional


def ensure_logs_dir(logs_dir: str = "logs") -> str:
    """Ensure the logs directory exists and return its absolute path."""
    abs_dir = os.path.abspath(logs_dir)
    os.makedirs(abs_dir, exist_ok=True)
    return abs_dir


def default_log_path(prefix: str = "sync", logs_dir: str = "logs") -> str:
    """Generate a timestamped log file path inside logs_dir."""
    ensure_logs_dir(logs_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.log"
    return os.path.join(logs_dir, filename)


def setup_logger(name: str = "1001tracklists_spotify_sync", log_file: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger that writes to console and a file."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(ch)

    # File handler
    log_path = log_file or default_log_path()
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)

    logger.info(f"Logging to file: {log_path}")
    return logger
