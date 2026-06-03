"""WebSocket schemas for Cipher Frame real-time chat."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OnlineUserItem(BaseModel):
    """Connected user metadata returned by the online users endpoint."""

    user_id: int
    username: str
    connection_time: datetime
    last_activity: datetime

    model_config = ConfigDict(from_attributes=True)
