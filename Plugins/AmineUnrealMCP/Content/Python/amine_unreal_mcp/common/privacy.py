"""Conservative redaction for tool outputs; never transform write arguments."""
import re

SENSITIVE_KEY = re.compile(r"password|passwd|secret|api[_ -]?key|(?:access|refresh|auth)[_ -]?token|authorization|credential", re.I)
ASSIGNMENT = re.compile(r"\b(password|passwd|secret|api[_ -]?key|(?:access|refresh|auth)[_ -]?token|authorization)\b(\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;]+)", re.I)
BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.I)
KEY = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")


def redact(value):
    if isinstance(value, dict):
        return {key: "[REDACTED]" if SENSITIVE_KEY.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        value = BEARER.sub("Bearer [REDACTED]", value)
        value = ASSIGNMENT.sub(lambda match: match[1] + match[2] + "[REDACTED]", value)
        return KEY.sub("[REDACTED]", value)
    return value
