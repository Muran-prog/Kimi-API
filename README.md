Added on 14.07.2025 (Note: there may be changes in the architecture of requests, which may cause the engine to stop working. In case of possible malfunction, I advise you to manually rewrite the logic of replacing requests with fresh ones (through reverse engineering).

---

# Kimi AI Engine

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg?style=flat-square)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

A high-quality, asynchronous, and framework-agnostic Python library for interacting with the Kimi AI API.

This engine is designed for robust and efficient communication with Kimi AI, making it easy to integrate into any commercial or open-source project. It handles session management, authentication, file uploads, and streaming chat responses with a clean, modern `asyncio`-based API.

## ✨ Key Features

*   **Pure Asynchronous:** Built from the ground up with `asyncio` and `curl_cffi` for high performance.
*   **Clean Architecture:** Clear separation of concerns between the `KimiAIEngine` (for session management and file uploads) and the `KimiChat` (for conversations).
*   **Robust Error Handling:** A comprehensive set of custom exceptions (`APIError`, `AuthenticationError`, etc.) for predictable error management.
*   **Typed & Structured Responses:** Uses Python `dataclasses` for API responses, providing a predictable structure and excellent editor support (autocompletion, type checking).
*   **Full Session Configuration:** Easily configure proxies, request timeouts, and browser impersonation settings.
*   **Secure & Graceful Shutdown:** Includes an async context manager (`async with`) to ensure network sessions are always closed properly.
*   **Comprehensive Logging:** Integrated logging helps with debugging and monitoring application behavior.
*   **Multi-Step File Uploads:** A single `upload_file` method abstracts the entire multi-step process of uploading and processing documents and images.

## 📋 Prerequisites

1.  **Python 3.8 or higher.**
2.  An active account on [Kimi.com](https://www.kimi.com/).
3.  A `cookies.txt` file exported from your browser after logging into Kimi.

## ⚙️ Installation

The library depends on `curl_cffi` for its performance and ability to impersonate browser TLS fingerprints.

```bash
pip install curl_cffi
```

## 🔑 Authentication: Getting Your `cookies.txt`

The engine authenticates by using the same cookies as your web browser. You need to export them to a file.

1.  **Log in** to your account on [www.kimi.com](https://www.kimi.com/).
2.  **Use a browser extension** to export your cookies. We recommend:
    *   [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) for Chrome/Edge.
    *   [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) for Firefox.
3.  Click the extension's icon and use the "Export" or "Download" button to save the `cookies.txt` file for the `kimi.com` domain.
4.  **Save the file** in your project's root directory (or another path you can reference) with the name `cookies.txt`.

> **Security Warning:** Your `cookies.txt` file contains sensitive session tokens. **Do not share this file or commit it to version control.** Always add `cookies.txt` to your `.gitignore` file.
>
> ```
> # .gitignore
> cookies.txt
> ```

## 🚀 Usage Examples

### 1. Basic Setup and Sending a Message

This example shows how to initialize the engine, create a new chat, send a message, and print the streamed response chunks.

```python
import asyncio
from KimiAIEngine import KimiAIEngine, KimiException, CompletionChunk

async def main():
    """Main function to run the Kimi AI Engine."""
    try:
        # The engine is best used with an async context manager
        async with KimiAIEngine(cookies_path='cookies.txt') as engine:
            # 1. Create a new chat session on the Kimi backend
            chat = await engine.create_chat(name="My First Chat")
            print(f"Created chat with ID: {chat.chat_id}")

            # 2. Define a prompt
            prompt = "Hello, Kimi! Can you explain the theory of relativity in simple terms?"
            
            # 3. Send the message and stream the response
            print(f"\nUser: {prompt}")
            print("Kimi's Response: ", end="", flush=True)
            
            full_response = ""
            async for event in chat.send_message_stream(prompt=prompt):
                if isinstance(event, CompletionChunk):
                    # Print the text chunk as it arrives
                    print(event.text, end="", flush=True)
                    full_response += event.text
            
            print("\n\n--- End of Stream ---")

    except KimiException as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Managing Conversation History

To have a continuous conversation, you can pass the previous messages as history.

```python
import asyncio
from KimiAIEngine import KimiAIEngine, KimiMessage, CompletionChunk

async def run_conversation():
    async with KimiAIEngine() as engine:
        chat = await engine.create_chat(name="History Demo")
        
        # Keep track of the conversation
        conversation_history = []
        
        # --- First message ---
        prompt1 = "What is the capital of France?"
        print(f"User: {prompt1}")
        print("Kimi: ", end="")
        
        response1 = ""
        async for chunk in chat.send_message_stream(prompt=prompt1):
            if isinstance(chunk, CompletionChunk):
                print(chunk.text, end="")
                response1 += chunk.text
        print("\n")
        
        # Add both user prompt and assistant response to history
        conversation_history.append(KimiMessage(role="user", content=prompt1))
        conversation_history.append(KimiMessage(role="assistant", content=response1))
        
        # --- Second message (with history) ---
        prompt2 = "What about its main attractions?"
        print(f"User: {prompt2}")
        print("Kimi: ", end="")
        
        # Pass the history to maintain context
        async for chunk in chat.send_message_stream(prompt=prompt2, history=conversation_history):
            if isinstance(chunk, CompletionChunk):
                print(chunk.text, end="")
        print("\n")

if __name__ == "__main__":
    asyncio.run(run_conversation())
```

### 3. Uploading and Referencing a File

The engine can upload documents (`.pdf`, `.docx`, `.txt`) or images and reference them in a prompt.

```python
import asyncio
import os
from KimiAIEngine import KimiAIEngine, FileUploadError, CompletionChunk

# Create a dummy file for the example
DUMMY_FILE_PATH = "project_summary.txt"
with open(DUMMY_FILE_PATH, "w") as f:
    f.write("Project Titan is a new initiative to build a next-generation AI using Python and Rust.")

async def analyze_document():
    try:
        async with KimiAIEngine() as engine:
            print(f"Uploading file: {DUMMY_FILE_PATH}...")
            
            # 1. Upload the file
            uploaded_file = await engine.upload_file(file_path=DUMMY_FILE_PATH)
            print(f"File uploaded successfully! File ID: {uploaded_file.id}")

            # 2. Create a chat and reference the file
            chat = await engine.create_chat(name="Document Analysis")
            prompt = "Please summarize the attached document in one sentence."
            
            print(f"\nUser: {prompt}")
            print("Kimi: ", end="")

            # 3. Pass the file ID in the `file_ids` list
            async for chunk in chat.send_message_stream(prompt=prompt, file_ids=[uploaded_file.id]):
                if isinstance(chunk, CompletionChunk):
                    print(chunk.text, end="")
            print("\n")

    except FileUploadError as e:
        print(f"File upload failed: {e}")
    except FileNotFoundError:
        print(f"Error: The file {DUMMY_FILE_PATH} was not found.")
    finally:
        # Clean up the dummy file
        if os.path.exists(DUMMY_FILE_PATH):
            os.remove(DUMMY_FILE_PATH)

if __name__ == "__main__":
    asyncio.run(analyze_document())
```

### 4. Robust Error Handling

Here is how you can catch the custom exceptions raised by the library.

```python
import asyncio
from KimiAIEngine import KimiAIEngine, KimiException, APIError, AuthenticationError

async def handle_errors():
    try:
        # Intentionally use a wrong path for cookies to trigger an error
        async with KimiAIEngine(cookies_path='non_existent_cookies.txt') as engine:
            await engine.create_chat()
            
    except AuthenticationError as e:
        print(f"Caught an Authentication Error: {e}")
        print("Please ensure your 'cookies.txt' file is correct and accessible.")

    except APIError as e:
        print(f"Caught an API Error (Status: {e.status_code}): {e}")
        print(f"Response Body: {e.response_text}")
        
    except KimiException as e:
        # This is the base exception, catching any library-specific error
        print(f"A general Kimi Engine error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(handle_errors())
```

## 📚 API Documentation

### Class `KimiAIEngine`

This is the main class for managing sessions and high-level operations.

*   `__init__(self, cookies_path: str = 'cookies.txt', impersonate: str = "chrome110", timeout: int = 45, proxies: Optional[Dict[str, str]] = None)`
    *   `cookies_path`: Path to your Netscape format `cookies.txt` file.
    *   `impersonate`: The browser to impersonate for the TLS fingerprint (see `curl_cffi` docs). Defaults to `chrome110`.
    *   `timeout`: Default timeout for HTTP requests in seconds.
    *   `proxies`: A dictionary for proxies (e.g., `{'http': '...', 'https': '...'}`).

*   `async def create_chat(self, name: str = "New Chat") -> KimiChat`:
    Creates a new chat session on the Kimi backend and returns a `KimiChat` instance to interact with it.

*   `async def upload_file(self, file_path: str) -> UploadedFile`:
    Handles the entire file upload process and returns an `UploadedFile` dataclass containing the file's ID and metadata.

*   `async def close(self)`:
    Closes the underlying network session. Automatically called when using `async with`.

### Class `KimiChat`

Represents a single conversation and is used to send messages. It should only be created via `engine.create_chat()`.

*   `async def send_message_stream(...) -> AsyncGenerator[...]`:
    Sends a message to the chat and returns an async generator that yields stream events.
    *   **Parameters**:
        *   `prompt` (str): The user's message.
        *   `history` (List[KimiMessage], optional): A list of previous `KimiMessage` objects for context.
        *   `use_search` (bool, optional): Whether to allow Kimi to use web search. Defaults to `True`.
        *   `file_ids` (List[str], optional): A list of file IDs from `upload_file` to reference.
    *   **Yields**:
        *   `CompletionChunk`: A piece of the response text.
        *   `SearchInfo`: Metadata about web searches performed by the AI.
        *   `StatusUpdate`: An event indicating the stream is finished (`'done'`).

### Data Classes

*   `KimiMessage(role: str, content: str)`: Represents a message in the conversation history. `role` is either `"user"` or `"assistant"`.
*   `UploadedFile(id: str, ...)`: Contains metadata about a successfully uploaded file.
*   `StreamEvent(event: str)`: The base class for all streamed events.
    *   `CompletionChunk(text: str)`
    *   `SearchInfo(hallucination: dict, ...)`
    *   `StatusUpdate()`

### Exceptions

*   `KimiException`: Base exception for all library errors.
*   `AuthenticationError`: Raised if `cookies.txt` is missing or invalid.
*   `APIError`: Raised for non-2xx HTTP responses from the Kimi API.
*   `FileUploadError`: Raised if any step of the file upload process fails.

## 📝 Logging

The library uses Python's standard `logging` module. You can configure the logger in your application to control the output level.

```python
import logging

# Set the logging level to INFO to see session initialization messages
logging.basicConfig(level=logging.INFO)

# Or get the specific logger for more granular control
# logger = logging.getLogger('KimiAIEngine')
# logger.setLevel(logging.DEBUG) # Very verbose output for debugging
```

## 🤝 Contributing

Contributions are welcome! Please feel free to fork the repository, make your changes, and submit a pull request.

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Commit your changes (`git commit -am 'Add some feature'`).
4.  Push to the branch (`git push origin feature/your-feature-name`).
5.  Create a new Pull Request.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Disclaimer

This is an unofficial, third-party library and is not affiliated with, endorsed, or sponsored by Moonshot AI or the Kimi AI team. It is a community-driven project intended for research and development purposes.
