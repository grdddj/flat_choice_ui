import json
import logging
from pathlib import Path
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "asctime": self.formatTime(record, self.datefmt),
            "levelname": record.levelname,
        }

        if isinstance(record.msg, dict):
            log_record.update(record.msg)
        else:
            log_record["message"] = record.getMessage()

        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def get_json_logger(file: str | Path) -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler(file))
    json_formatter = JsonFormatter()
    for handler in logger.handlers:
        handler.setFormatter(json_formatter)
    return logger


if __name__ == "__main__":
    logger = get_json_logger(Path(__file__).with_suffix(".log"))
    logger.info("Test message")
    logger.info({"key": "value", "key2": "value2"})
