"""Tests for event -> frontend-dict serialization."""

from __future__ import annotations

import json

import pytest

from yt_downloader.events import Cancelled, Failed, Finished, LogMessage, Progress, Stage
from yt_downloader.webui.serialization import event_to_dict


def test_log_message():
    assert event_to_dict(LogMessage("hi", "warning")) == {
        "type": "log",
        "text": "hi",
        "level": "warning",
    }


def test_stage():
    assert event_to_dict(Stage("Downloading...")) == {"type": "stage", "text": "Downloading..."}


def test_progress():
    assert event_to_dict(Progress(0.5, speed=1000.0, eta=12)) == {
        "type": "progress",
        "fraction": 0.5,
        "speed": 1000.0,
        "eta": 12,
    }


def test_progress_unknown_total():
    assert event_to_dict(Progress(None))["fraction"] is None


def test_finished():
    assert event_to_dict(Finished()) == {"type": "finished", "outputDir": None}


def test_finished_with_output_dir():
    assert event_to_dict(Finished(output_dir="/a/b")) == {
        "type": "finished",
        "outputDir": "/a/b",
    }


def test_failed():
    assert event_to_dict(Failed("boom")) == {"type": "failed", "message": "boom"}


def test_cancelled():
    assert event_to_dict(Cancelled()) == {"type": "cancelled"}


def test_unknown_event_raises():
    with pytest.raises(TypeError):
        event_to_dict(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "event",
    [
        LogMessage("x"),
        Stage("y"),
        Progress(0.1, 2.0, 3),
        Progress(None),
        Finished(),
        Finished("/a/b"),
        Failed("z"),
        Cancelled(),
    ],
)
def test_every_event_is_json_serializable(event):
    json.dumps(event_to_dict(event))
