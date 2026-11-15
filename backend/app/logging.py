import json
import logging
import sys

_HANDLER_NAME = "app-json-stdout"
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED})
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.set_name(_HANDLER_NAME)
    root = logging.getLogger()
    # Replace only our own handler, so repeated calls and test log capture keep working.
    root.handlers = [h for h in root.handlers if h.get_name() != _HANDLER_NAME] + [handler]
    root.setLevel(level.upper())
    # httpx logs every request URL at INFO; upstream calls are already logged with timings.
    # The S3 SDK logs request params (object bodies) and signed headers at DEBUG (SEC-501).
    for name in ("httpx", "httpcore", "boto3", "botocore", "s3transfer", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)
