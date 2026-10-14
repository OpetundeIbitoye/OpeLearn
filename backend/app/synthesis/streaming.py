"""Typed server-sent event framing."""

import json
from typing import Any, Literal

FrameType = Literal["token", "citation", "sources", "done", "error"]


def sse_frame(frame_type: FrameType, data: dict[str, Any]) -> str:
    return f"event: {frame_type}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"
