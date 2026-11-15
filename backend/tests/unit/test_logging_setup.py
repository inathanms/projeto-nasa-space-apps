import logging

from app.logging import setup_logging


def test_sdk_loggers_stay_quiet_even_at_debug():
    """SEC-501: the S3 SDK must not log signed requests or object bodies, even with debug."""
    root = logging.getLogger()
    previous = root.level
    try:
        setup_logging("debug")
        for name in ("botocore", "boto3", "s3transfer", "urllib3", "httpx"):
            assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING, name
    finally:
        setup_logging(logging.getLevelName(previous))
