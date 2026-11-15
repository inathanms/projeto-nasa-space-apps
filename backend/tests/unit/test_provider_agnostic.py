"""AC-520 / CON-502 / CON-504 / SEC-503: the code under app/ is S3-generic.

No provider name, no ACL, no presigned URL and no bucket-level operation. The only allowed
exception is boto3's generic credential keyword names in `build_s3_client` (spec cache 4.7).
"""

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
FORBIDDEN = re.compile(r"r2|cloudflare|gcs|aws|ACL=|generate_presigned_url", re.IGNORECASE)
BUCKET_OPERATIONS = re.compile(
    r"\b(create_bucket|delete_bucket|head_bucket|list_buckets|list_objects\w*|"
    r"put_bucket_\w+|get_bucket_\w+|delete_objects?)\b"
)
ALLOWED = {
    ("storage/s3_store.py", "aws_access_key_id"),
    ("storage/s3_store.py", "aws_secret_access_key"),
}


def _python_files() -> list[Path]:
    files = sorted(APP.rglob("*.py"))
    assert files
    return files


def test_ac520_no_provider_specific_identifiers_in_app():
    found = []
    for path in _python_files():
        rel = path.relative_to(APP).as_posix()
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            for match in FORBIDDEN.finditer(line):
                word = re.search(r"\w*" + re.escape(match.group()) + r"\w*", line[match.start() :])
                token = word.group() if word else match.group()
                if (rel, token) not in ALLOWED:
                    found.append(f"{rel}:{lineno}: {token}")
    assert found == []


def test_sec503_no_bucket_operations_in_app():
    found = [
        f"{path.relative_to(APP)}:{lineno}"
        for path in _python_files()
        for lineno, line in enumerate(path.read_text().splitlines(), 1)
        if BUCKET_OPERATIONS.search(line)
    ]
    assert found == []
