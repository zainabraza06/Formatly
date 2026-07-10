"""Live events emitted during execution. Streamed over WebSocket so the UI can
animate every operation (highlight nodes one by one, fade deletions, etc.)."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventName(str, Enum):
    BATCH_STARTED = "batch_started"
    BATCH_FINISHED = "batch_finished"
    BATCH_FAILED = "batch_failed"

    SELECTION_STARTED = "selection_started"
    SELECTION_ITEM = "selection_item"
    SELECTION_FINISHED = "selection_finished"

    FORMAT_STARTED = "format_started"
    FORMAT_PROGRESS = "format_progress"
    FORMAT_FINISHED = "format_finished"

    DELETE_STARTED = "delete_started"
    DELETE_ITEM = "delete_item"
    DELETE_FINISHED = "delete_finished"

    INSERT_STARTED = "insert_started"
    INSERT_ITEM = "insert_item"
    INSERT_FINISHED = "insert_finished"

    MOVE_STARTED = "move_started"
    MOVE_ITEM = "move_item"
    MOVE_FINISHED = "move_finished"

    REPLACE_STARTED = "replace_started"
    REPLACE_ITEM = "replace_item"
    REPLACE_FINISHED = "replace_finished"

    ACTION_ERROR = "action_error"


class Event(BaseModel):
    name: EventName
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_message(self) -> dict[str, Any]:
        return {"event": self.name.value, "payload": self.payload}
