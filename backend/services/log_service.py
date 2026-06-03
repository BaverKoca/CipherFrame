"""Database-backed server logging helpers for Cipher Frame."""

from backend.models.server_log import LogLevel, ServerLog


def create_server_log(session, *, level: LogLevel, event_type: str, message: str, actor_user_id: int | None = None, ip_address: str | None = None) -> ServerLog:
    """Persist a structured server log entry."""

    log_entry = ServerLog(
        level=level,
        event_type=event_type,
        message=message,
        actor_user_id=actor_user_id,
        ip_address=ip_address,
    )
    session.add(log_entry)
    session.commit()
    session.refresh(log_entry)
    return log_entry