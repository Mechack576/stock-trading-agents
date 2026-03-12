import hashlib
import uuid


def make_trace_id(name: str) -> str:
    """Generate a deterministic trace ID based on a name string.

    Uses a SHA-256 hash of the name to produce a consistent UUID-formatted trace ID,
    so the same trader always maps to the same trace group in the tracing UI.

    Args:
        name: A string identifier (e.g. trader name) to derive the trace ID from.

    Returns:
        A UUID-formatted string to use as the trace_id.
    """
    hash_bytes = hashlib.sha256(name.encode()).digest()[:16]
    return str(uuid.UUID(bytes=hash_bytes))
