import logging
from datetime import datetime
from pathlib import Path


def get_logger(name: str, log_dir: str = "./logs") -> logging.Logger:
    """Create a logger that writes to a timestamped file in log_dir."""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = Path(log_dir) / f"{name}_{timestamp}.log"

    logger = logging.getLogger(f"{name}_{id(log_path)}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    handler = logging.FileHandler(log_path, mode="w")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

    return logger
