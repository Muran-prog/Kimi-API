# kimiai/chat.py
# -*- coding: utf-8 -*-
"""
Represents a single conversation with the Kimi AI.
"""
import json
import logging
from typing import AsyncGenerator, List, Union

from curl_cffi.requests import AsyncSession, RequestsError

from .exceptions import APIError, KimiException
from .models import CompletionChunk, KimiMessage, SearchInfo, StatusUpdate

logger = logging.getLogger(__name__)

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
