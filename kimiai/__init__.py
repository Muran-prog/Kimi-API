# kimiai/__init__.py
# -*- coding: utf-8 -*-
"""
KimiAIEngine: A high-quality, asynchronous library for interacting with the Kimi AI API.

This package provides a robust, reusable, and framework-agnostic engine
for communicating with Kimi AI, designed for easy integration into any
commercial or open-source project.
"""
import logging

from .chat import KimiChat
from .engine import KimiAIEngine
from .exceptions import (APIError, AuthenticationError, FileUploadError,
                         KimiException)
from .models import (CompletionChunk, KimiMessage, SearchInfo, StatusUpdate,
                     StreamEvent, UploadedFile)

# Set up a null handler for the library's logger. This prevents log messages
# from appearing in the console unless the user of the library configures logging.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "KimiAIEngine",
    "KimiChat",
    "KimiException",
    "AuthenticationError",
    "APIError",
    "FileUploadError",
    "KimiMessage",
    "UploadedFile",
    "StreamEvent",
    "CompletionChunk",
    "SearchInfo",
    "StatusUpdate",
]

__version__ = "1.0.0"
