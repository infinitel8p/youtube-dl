"""Turn core `events.py` dataclasses into JSON-serializable dicts for the frontend.

Pure and UI-free, so it can be unit-tested. Each dict carries a ``type`` discriminator
the Svelte app switches on.
"""

from __future__ import annotations

from ..events import Cancelled, Event, Failed, Finished, LogMessage, Progress, Stage


def event_to_dict(event: Event) -> dict:
    """Serialize one event. Raises TypeError on an unknown event type."""
    if isinstance(event, LogMessage):
        return {"type": "log", "text": event.text, "level": event.level}
    if isinstance(event, Stage):
        return {"type": "stage", "text": event.text}
    if isinstance(event, Progress):
        return {
            "type": "progress",
            "fraction": event.fraction,
            "speed": event.speed,
            "eta": event.eta,
        }
    if isinstance(event, Finished):
        return {"type": "finished", "outputDir": event.output_dir}
    if isinstance(event, Failed):
        return {"type": "failed", "message": event.message}
    if isinstance(event, Cancelled):
        return {"type": "cancelled"}
    raise TypeError(f"Unknown event type: {event!r}")
