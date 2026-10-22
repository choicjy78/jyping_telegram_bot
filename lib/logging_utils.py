"""명시적으로 호출할 때만 파일 로깅을 설정한다."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(path, logger_name="", level=logging.INFO):
    path = Path(path).resolve()
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    if any(isinstance(handler, RotatingFileHandler) and handler.baseFilename == str(path)
           for handler in logger.handlers):
        return logger
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=5 * 1024 * 1024,
                                  backupCount=3, encoding="utf-8", delay=True)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    return logger
