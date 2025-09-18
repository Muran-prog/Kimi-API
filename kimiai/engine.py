# kimiai/engine.py
# -*- coding: utf-8 -*-
"""
The core engine for interacting with the Kimi AI API.
"""
import logging
import os
import random
import string
from http.cookiejar import MozillaCookieJar
from typing import Any, Dict, Optional

from curl_cffi.requests import AsyncSession, Response, RequestsError

from .chat import KimiChat
from .exceptions import (APIError, AuthenticationError, FileUploadError,
                         KimiException)
from .models import UploadedFile

logger = logging.getLogger(__name__)

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

    async def create_chat(self, name: str = "New Chat") -> KimiChat:
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
