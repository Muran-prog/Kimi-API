# -*- coding: utf-8 -*-
"""
KimiAIEngine: A high-quality, asynchronous library for interacting with the Kimi AI API.

This module provides a robust, reusable, and framework-agnostic engine 
for communicating with Kimi AI, designed for easy integration into any 
commercial or open-source project.

Features:
- Pure asynchronous design using asyncio and curl_cffi.
- Clean separation of concerns (Engine vs. Chat).
- Robust error handling with custom exceptions.
- Structured, typed responses (dataclasses) instead of raw dictionaries.
- Comprehensive logging for debugging and monitoring.
- Full configuration of session parameters (cookies, proxies, timeout).
- Async context manager for safe session handling.
- Detailed docstrings and type hinting for excellent developer experience.

Example usage is provided at the end of the file.
"""
import asyncio
import json
import logging
import os
import random
import string
from dataclasses import dataclass, field
from http.cookiejar import MozillaCookieJar
from typing import Any, Dict, List, Optional, AsyncGenerator, Union

from curl_cffi.requests import AsyncSession, Response, RequestsError

# --- Setup logging ---
# The library gets its own logger. The user of the library can configure
# the logging level and handlers for their specific application.
logger = logging.getLogger(__name__)

# --- Custom Exceptions for Robust Error Handling ---

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

# --- Data Structures for Typed and Predictable API Responses ---

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

# --- Core Engine and Chat Classes ---

class KimiAIEngine:
    """
    An asynchronous engine for creating chats and managing files with the Kimi API.

    This class handles session management, authentication, and high-level operations
    like creating new chat sessions and uploading files. It is designed to be
    instantiated once and reused.
    """

    def __init__(
        self,
        cookies_path: str = 'cookies.txt',
        impersonate: str = "chrome110",
        timeout: int = 45,
        proxies: Optional[Dict[str, str]] = None
    ):
        """
        Initializes the Kimi AI Engine.

        Args:
            cookies_path (str): Path to the Netscape format cookies file.
            impersonate (str): The browser to impersonate for TLS fingerprinting.
            timeout (int): Default timeout for HTTP requests in seconds.
            proxies (Optional[Dict[str, str]]): Proxies dictionary for the session.
        """
        self.base_url = "https://www.kimi.com/api"
        self.cookies_path = cookies_path
        self._impersonate = impersonate
        self._timeout = timeout
        self._proxies = proxies or {}
        self.session: Optional[AsyncSession] = None
        self._is_initialized = False

    async def _initialize_session(self) -> None:
        """Creates and configures the asynchronous HTTP session."""
        if self._is_initialized:
            return

        logger.info("Initializing KimiAIEngine session.")
        device_id = str(random.randint(10**18, 10**19 - 1))
        session_id = str(random.randint(10**18, 10**19 - 1))
        traffic_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
            'Content-Type': 'application/json',
            'Origin': 'https://www.kimi.com',
            'Referer': 'https://www.kimi.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'X-Language': 'en-US',
            'X-Msh-Platform': 'web',
            'x-msh-device-id': device_id,
            'x-msh-session-id': session_id,
            'x-traffic-id': traffic_id,
        }
        
        self.session = AsyncSession(
            impersonate=self._impersonate,
            timeout=self._timeout,
            proxies=self._proxies,
            headers=headers
        )

        self._load_cookies()
        logger.info("Session initialized successfully.")
        self._is_initialized = True

    def _load_cookies(self):
        """
        Loads cookies and extracts the authorization token.

        Raises:
            AuthenticationError: If the cookie file is not found or the 'kimi-auth'
                                 token is missing within the cookies.
        """
        if not os.path.exists(self.cookies_path):
            raise AuthenticationError(f"Cookie file not found at: {self.cookies_path}")

        try:
            cookie_jar = MozillaCookieJar(self.cookies_path)
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            self.session.cookies.update(cookie_jar)
            
            auth_token = self.session.cookies.get('kimi-auth')
            if not auth_token:
                raise AuthenticationError("Authentication token 'kimi-auth' not found in cookies file.")
            
            self.session.headers['Authorization'] = f"Bearer {auth_token}"
            logger.info("Authorization token loaded and set successfully.")
        except Exception as e:
            raise AuthenticationError(f"Failed to load or process cookies: {e}") from e

    async def _make_request(self, method: str, url: str, **kwargs: Any) -> Response:
        """
        A robust wrapper for making HTTP requests.

        Args:
            method (str): HTTP method (e.g., "GET", "POST").
            url (str): The full URL for the request.
            **kwargs: Additional arguments for the request (json, data, etc.).

        Returns:
            Response: The response object from curl_cffi.

        Raises:
            APIError: If the server responds with a non-2xx status code.
            KimiException: For other network or request-related errors.
        """
        if not self.session:
            await self._initialize_session()
        
        try:
            response = await self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except RequestsError as e:
            status_code = e.response.status_code if e.response else 0
            response_text = e.response.text if e.response else "No response"
            logger.error(f"API request to {url} failed with status {status_code}. Response: {response_text}", exc_info=True)
            raise APIError(f"API request failed: {e}", status_code, response_text) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during request to {url}: {e}", exc_info=True)
            raise KimiException(f"An unexpected error occurred: {e}") from e

    async def create_chat(self, name: str = "New Chat") -> 'KimiChat':
        """
        Creates a new chat session on the Kimi backend.

        Args:
            name (str): The name for the new chat session.

        Returns:
            KimiChat: An object representing the newly created chat.
        """
        logger.info(f"Creating a new chat named '{name}'.")
        payload = {
            "name": name, 
            "born_from": "home", 
            "kimiplus_id": "kimi",
            "is_example": False, 
            "source": "web", 
            "tags": []
        }
        response = await self._make_request("POST", f"{self.base_url}/chat", json=payload)
        chat_id = response.json().get('id')
        logger.info(f"Successfully created chat with ID: {chat_id}")
        return KimiChat(chat_id, self.session, self.base_url)

    async def upload_file(self, file_path: str) -> UploadedFile:
        """
        Uploads a file to Kimi for use in chats.

        This method handles the entire multi-step upload process:
        1. Get a pre-signed URL.
        2. Upload the file content to the URL.
        3. Register the file with the Kimi API.
        4. Wait for the file to be processed.

        Args:
            file_path (str): The local path to the file to upload.

        Returns:
            UploadedFile: A dataclass with information about the uploaded file.

        Raises:
            FileUploadError: If any step of the upload process fails.
            FileNotFoundError: If the specified file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found at path: {file_path}")

        file_name = os.path.basename(file_path)
        file_ext = file_name.split('.')[-1].lower()
        file_type = 'image' if file_ext in ['png', 'jpg', 'jpeg', 'webp', 'gif'] else 'file'
        logger.info(f"Starting upload for file '{file_name}' (type: {file_type}).")

        try:
            # 1. Get pre-signed URL
            pre_sign_data = (await self._make_request(
                "POST", f"{self.base_url}/pre-sign-url", 
                json={"name": file_name, "action": file_type}
            )).json()
            logger.debug(f"Received pre-signed URL for '{file_name}'.")

            # 2. Upload file content
            with open(file_path, 'rb') as f:
                upload_response = await self.session.put(pre_sign_data['url'], data=f.read())
                upload_response.raise_for_status()
            logger.debug(f"File content for '{file_name}' uploaded to storage.")

            # 3. Register file with Kimi API
            file_api_payload = {
                "name": file_name,
                "object_name": pre_sign_data['object_name'],
                "type": file_type,
                "file_id": pre_sign_data.get('file_id', '')
            }
            file_data = (await self._make_request(
                "POST", f"{self.base_url}/file", json=file_api_payload
            )).json()
            logger.debug(f"File '{file_name}' registered with API. File ID: {file_data['id']}")

            # 4. Wait for processing (if it's a document)
            if file_type == 'file':
                logger.info(f"Waiting for document '{file_name}' to be parsed by Kimi...")
                parse_resp = await self.session.post(
                    f"{self.base_url}/file/parse_process", json={"ids": [file_data['id']]}
                )
                parse_resp.raise_for_status()
                # Simplified check for completion; a more robust solution might need a timeout
                if '"status":"parsed"' in parse_resp.text:
                   logger.info(f"File '{file_name}' has been successfully parsed.")
                else:
                   logger.warning(f"Could not confirm immediate parsing for '{file_name}'. May need time.")

            uploaded_file = UploadedFile(
                id=file_data['id'],
                name=file_data['name'],
                object_name=file_data['object_name'],
                file_type=file_data['type'],
                meta=file_data.get('meta', {})
            )
            logger.info(f"File '{file_name}' successfully uploaded with ID: {uploaded_file.id}")
            return uploaded_file
            
        except Exception as e:
            logger.error(f"File upload failed for '{file_path}'. Error: {e}", exc_info=True)
            raise FileUploadError(f"Failed to upload file '{file_path}': {e}") from e

    async def close(self) -> None:
        """Closes the underlying HTTP session. Essential for graceful shutdown."""
        if self.session:
            await self.session.close()
            self.session = None
            self._is_initialized = False
            logger.info("KimiAIEngine session closed.")

    async def __aenter__(self) -> 'KimiAIEngine':
        await self._initialize_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


class KimiChat:
    """
    Represents a single conversation with Kimi AI.

    This class should be instantiated via `KimiAIEngine.create_chat()`.
    It holds the state of a specific chat (its ID) and provides the method
    to send messages and stream the response.
    """
    def __init__(self, chat_id: str, session: AsyncSession, base_url: str):
        """
        Initializes a KimiChat instance. Not meant to be called directly.

        Args:
            chat_id (str): The unique identifier for this chat.
            session (AsyncSession): The shared session from KimiAIEngine.
            base_url (str): The base API URL.
        """
        self.chat_id = chat_id
        self._session = session
        self._base_url = base_url

    async def send_message_stream(
        self, 
        prompt: str, 
        history: List[KimiMessage] = None,
        use_search: bool = True, 
        file_ids: List[str] = None
    ) -> AsyncGenerator[Union[CompletionChunk, SearchInfo, StatusUpdate], None]:
        """
        Sends a message to the chat and streams the response event by event.

        Args:
            prompt (str): The user's message/prompt.
            history (List[KimiMessage], optional): A list of previous messages in the
                conversation for context. Defaults to None.
            use_search (bool, optional): Whether to allow Kimi to use web search.
                Defaults to True.
            file_ids (List[str], optional): A list of file IDs (from `upload_file`)
                to reference in the prompt. Defaults to None.

        Yields:
            An asynchronous generator of stream events, which can be instances of
            `CompletionChunk`, `SearchInfo`, or `StatusUpdate`.
        """
        url = f"{self._base_url}/chat/{self.chat_id}/completion/stream"
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "history": [vars(msg) for msg in history] if history else [],
            "kimiplus_id": "kimi",
            "model": "k2",
            "use_search": use_search,
            "refs": file_ids or [],
            "extend": {"sidebar": True},
            "scene_labels": [],
            "use_deep_research": False,
            "use_semantic_memory": False
        }
        logger.info(f"Sending stream request to chat {self.chat_id} with use_search={use_search}.")
        logger.debug(f"Request payload: {payload}")

        try:
            response = await self._session.post(url, json=payload, stream=True)
            response.raise_for_status()

            async for line_bytes in response.aiter_lines():
                line = line_bytes.decode('utf-8').strip()
                if not line.startswith('data:'):
                    continue
                
                data_str = line[5:].strip()
                if not data_str:
                    continue

                try:
                    data = json.loads(data_str)
                    event_type = data.get('event')

                    if event_type == 'cmpl':
                        yield CompletionChunk(event='cmpl', text=data.get('text', ''))
                    elif event_type == 'search_info':
                        yield SearchInfo(
                            event='search_info',
                            hallucination=data.get('hallucination', {}),
                            search_type=data.get('search_type', '')
                        )
                    elif event_type == 'status':
                        yield StatusUpdate(event='status')
                    # Other events can be added here if discovered
                        
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON from stream line: {data_str}")
                    continue
        except RequestsError as e:
            status = e.response.status_code if e.response else 0
            text = e.response.text if e.response else "No response"
            raise APIError(f"Stream API request failed: {e}", status, text) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during stream processing: {e}", exc_info=True)
            raise KimiException(f"Stream processing failed: {e}") from e
