"""
hitl_guard.py — Human-In-The-Loop safety guard for generated SQL.

# INTERN NOTE: HITL (Human-In-The-Loop) guard explained
# LLMs can occasionally generate data-mutating SQL (INSERT/UPDATE/DELETE/DROP)
# even when asked read-only questions. Silently executing such statements
# against a production database would be catastrophic.
# The HITL guard intercepts any SQL before execution and flags write operations
# for explicit human approval. The frontend shows an ApprovalModal, and the
# user must type "CONFIRM" before the statement is actually run.
# This creates a mandatory human checkpoint — the LLM can suggest writes but
# a human must authorise them. Pure SELECT queries pass through automatically.
# In production, approval events should be logged with the approver's identity.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Patterns that indicate a potentially destructive or mutating SQL statement
_DANGEROUS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bINSERT\b", re.IGNORECASE), "INSERT statement detected — would modify data"),
    (re.compile(r"\bUPDATE\b", re.IGNORECASE), "UPDATE statement detected — would modify data"),
    (re.compile(r"\bDELETE\b", re.IGNORECASE), "DELETE statement detected — would remove data"),
    (re.compile(r"\bDROP\b", re.IGNORECASE), "DROP statement detected — would destroy a table or database"),
    (re.compile(r"\bTRUNCATE\b", re.IGNORECASE), "TRUNCATE statement detected — would erase all rows"),
    (re.compile(r"\bALTER\b", re.IGNORECASE), "ALTER statement detected — would modify schema"),
    (re.compile(r"\bCREATE\b", re.IGNORECASE), "CREATE statement detected — would modify schema"),
    (re.compile(r"\bGRANT\b", re.IGNORECASE), "GRANT statement detected — would change permissions"),
    (re.compile(r"\bREVOKE\b", re.IGNORECASE), "REVOKE statement detected — would change permissions"),
    (re.compile(r";\s*--", re.IGNORECASE), "Possible SQL injection comment terminator detected"),
]


def check_sql(sql: str) -> dict:
    """
    Inspect *sql* for dangerous or write operations.

    Returns:
        {"requires_approval": True,  "reason": "<human-readable explanation>"}
        {"requires_approval": False}

    Never raises — returns a safe default if sql is empty or None.
    """
    if not sql or not sql.strip():
        return {"requires_approval": False}

    for pattern, reason in _DANGEROUS_PATTERNS:
        if pattern.search(sql):
            logger.warning("HITL guard flagged SQL. Reason: %s", reason)
            return {"requires_approval": True, "reason": reason}

    return {"requires_approval": False}
