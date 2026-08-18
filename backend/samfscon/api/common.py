"""Helpers shared by the routers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

from fastapi import Depends, Path, Query, Request

from samfscon.auth.deps import client_ip, current_session
from samfscon.auth.session import Session
from samfscon.core.audit import AuditLog, get_audit


class AuditContext:
    """Binds the audit log to the caller behind the current request."""

    def __init__(self, log: AuditLog, session: Session, address: str | None) -> None:
        self.log = log
        self.session = session
        self.address = address

    @contextmanager
    def operation(
        self, action: str, target: str | None = None, **changes: Any
    ) -> Iterator[dict[str, Any]]:
        with self.log.operation(
            action,
            actor=self.session.principal.full,
            target=target,
            session_id=self.session.id,
            client_ip=self.address,
            changes=changes or None,
        ) as record:
            yield record

    def record(self, action: str, target: str | None = None, **extra: Any) -> None:
        self.log.record(
            action=action,
            actor=self.session.principal.full,
            target=target,
            session_id=self.session.id,
            client_ip=self.address,
            extra=extra or None,
        )


def audit_context(request: Request, session: Session = Depends(current_session)) -> AuditContext:
    return AuditContext(get_audit(), session, client_ip(request))


Audit = Annotated[AuditContext, Depends(audit_context)]

# A share name as srvsvc reports it. Samba allows spaces and a good deal of
# punctuation, so the only thing ruled out here is what cannot be a share at
# all: an empty name, and one long enough to be a mistake.
ShareQuery = Annotated[str, Query(min_length=1, max_length=80, description="Share name")]
SharePath = Annotated[str, Path(min_length=1, max_length=80, description="Share name")]

# A path inside a share, share-relative and backslash-separated, the way SMB
# wants it: "Projects\2026\budget.xlsx". The empty string is the share root
# and is valid — it is the path the permissions tab of a share edits.
PathQuery = Annotated[str, Query(max_length=4096, description="Path inside the share")]


def split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or None
