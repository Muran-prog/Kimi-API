# kimiai/exceptions.py
# -*- coding: utf-8 -*-
"""
Custom exceptions for the KimiAIEngine library.

This module defines a clear hierarchy of exceptions to allow for robust
and specific error handling by the library's users.
"""

class KimiException(Exception):
    """Base exception class for all Kimi Engine errors."""
    pass

class AuthenticationError(KimiException):
    """Raised when authentication fails, e.g., missing or invalid cookies."""
    pass

class APIError(KimiException):
    """Raised when the Kimi API returns a non-2xx HTTP status code."""
    def __init__(self, message: str, status_code: int, response_text: str):
        super().__init__(f"{message} (Status: {status_code})")
        self.status_code = status_code
        self.response_text = response_text

class FileUploadError(KimiException):
    """Raised when a file upload fails at any stage."""
    pass
