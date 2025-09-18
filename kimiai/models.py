# kimiai/models.py
# -*- coding: utf-8 -*-
"""
Data models for the KimiAIEngine library.

This module provides typed, structured classes for representing API objects
like messages, files, and stream events, ensuring predictable and easy-to-use
data structures instead of raw dictionaries.
"""
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass(frozen=True)
class KimiMessage:
    """Represents a message in a chat conversation history."""
    role: str  # "user" or "assistant"
    content: str

@dataclass(frozen=True)
class UploadedFile:
    """Represents a successfully uploaded file and its metadata."""
    id: str
    name: str
    object_name: str
    file_type: str
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class StreamEvent:
    """Base class for events received from the completion stream."""
    event: str

@dataclass(frozen=True)
class CompletionChunk(StreamEvent):
    """A chunk of the generated text message."""
    text: str

@dataclass(frozen=True)
class SearchInfo(StreamEvent):
    """Contains information related to the web search results."""
    hallucination: Dict[str, Any]
    search_type: str

@dataclass(frozen=True)
class StatusUpdate(StreamEvent):
    """Represents a status update from the stream (e.g., 'done')."""
    pass
