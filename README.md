# Kimi AI Unofficial Python API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-unofficial-red)]()

A high-quality, asynchronous, and unofficial Python library for interacting with the Kimi AI API. This library provides a robust, reusable, and framework-agnostic engine for communicating with Kimi AI (from Moonshot AI), designed for easy integration into any project.

The entire project is built with a clean, modular architecture, focusing on readability, maintainability, and a great developer experience.

**Repository:** [https://github.com/Muran-prog/Kimi-API.git](https://github.com/Muran-prog/Kimi-API.git)

---

### Disclaimer

This is an unofficial library and is **not affiliated with, endorsed, or sponsored by Moonshot AI (Kimi AI's parent company) in any way.** It is a reverse-engineered client that interacts with Kimi's internal web API. The API is undocumented and may change at any time without notice, which could cause this library to break. Use this software at your own risk. The developers are not responsible for any issues, damages, or account actions that may result from its use.

---

### ⚠️ Important Notice

> **Added on 14.07.2025:** Note: there may be changes in the architecture of requests, which may cause the engine to stop working. In case of possible malfunction, I advise you to manually rewrite the logic of replacing requests with fresh ones (through reverse engineering).

---

## ✅ Key Features

-   **Pure Asynchronous:** Built from the ground up with `asyncio` and `curl_cffi` for high performance and non-blocking I/O.
-   **Clean Modular Architecture:** Code is logically separated into modules for exceptions, data models, the core engine, and chat handling.
-   **Robust Error Handling:** A clear hierarchy of custom exceptions for predictable error management.
-   **Typed & Structured Responses:** Uses Python `dataclasses` for API responses, providing type safety and autocompletion instead of raw dictionaries.
-   **Full File Upload Support:** A complete, multi-step implementation for uploading documents and images to be used as context in conversations.
-   **Streaming Completions:** Efficiently handle long responses by processing them chunk-by-chunk as they arrive.
-   **Full Session Configuration:** Easily configure cookies, proxies, and timeouts.
-   **Safe Session Management:** Uses an async context manager (`async with`) for guaranteed session cleanup.
-   **Excellent Developer Experience:** Detailed docstrings and full type hinting for a smooth development process.

## ⚙️ Installation

This library is not on PyPI. You can install it directly from GitHub.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Muran-prog/Kimi-API.git
    cd Kimi-API
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install the required dependencies:**
    You'll need `curl_cffi` for its ability to impersonate browser TLS fingerprints, which is crucial for avoiding blocks.
    ```bash
    pip install curl_cffi
    ```

## 🔑 Authentication: Getting Your `cookies.txt`

The library authenticates by using your browser's session cookies. You need to export them into a `cookies.txt` file in the Netscape format.

1.  Log in to your account on [www.kimi.com](https://www.kimi.com) in your web browser (e.g., Chrome, Firefox).
2.  Install a browser extension that can export cookies in the Netscape format. A recommended extension for Chrome is **"Get cookies.txt LOCALLY"**.
3.  With the Kimi AI website open, click the extension's icon and export the cookies.
4.  Save the downloaded file as `cookies.txt` in the root directory of this project.

**Important:** Your `cookies.txt` file must contain the `kimi-auth` cookie for the library to work.

## 🚀 Quick Start Example

The following example demonstrates how to initialize the engine, create a chat, upload a file, and stream a response.

```python
# example.py
import asyncio
import logging
import os

# Import classes directly from the kimiai package
from kimiai import (APIError, AuthenticationError, CompletionChunk,
                    FileUploadError, KimiAIEngine, KimiException, SearchInfo,
                    StatusUpdate)


async def main():
    """Demonstrates the core functionality of the KimiAIEngine."""
    # Configure logging to see the library's output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if not os.path.exists('cookies.txt'):
        print("Error: 'cookies.txt' not found.")
        return

    try:
        # The engine is an async context manager for safe session handling
        async with KimiAIEngine(cookies_path='cookies.txt') as engine:
            # 1. Create a new chat
            print("Creating a new chat...")
            chat = await engine.create_chat(name="My First API Chat")
            print(f"Chat created with ID: {chat.chat_id}")

            # 2. (Optional) Upload a file for context
            dummy_file_path = "sample_document.txt"
            with open(dummy_file_path, "w", encoding="utf-8") as f:
                f.write("This is a test document to be analyzed by Kimi AI.")

            print(f"\nUploading file: {dummy_file_path}...")
            file_ids = []
            prompt = "Hello, Kimi! Can you tell me a joke about programming?"
            try:
                uploaded_file = await engine.upload_file(dummy_file_path)
                print(f"File uploaded successfully! ID: {uploaded_file.id}")
                file_ids.append(uploaded_file.id)
                prompt = "Please summarize the content of the document I've just uploaded."
            except FileUploadError as e:
                print(f"File upload failed: {e}")
            finally:
                os.remove(dummy_file_path) # Clean up

            # 3. Send a message and stream the response
            print(f"\nSending prompt: '{prompt}'")
            print("Streaming response from Kimi:")
            print("-" * 30)

            full_response = ""
            async for event in chat.send_message_stream(prompt, file_ids=file_ids):
                if isinstance(event, CompletionChunk):
                    print(event.text, end="", flush=True)
                    full_response += event.text
                elif isinstance(event, SearchInfo):
                    print(f"\n[Kimi is searching: {event.search_type}]")
                # Handle other event types if needed

            print("\n" + "-" * 30)
            print("\nFull response received.")

    except AuthenticationError as e:
        print(f"\nERROR: Authentication failed: {e}")
    except APIError as e:
        print(f"\nERROR: An API error occurred: {e}")
    except KimiException as e:
        print(f"\nERROR: An unexpected library error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🏛️ Project Structure

The codebase is organized into a clean, modular structure within the `kimiai/` package directory:

```
kimiai/
├── __init__.py      # Makes the directory a package and exposes public classes.
├── engine.py        # Contains the main KimiAIEngine for session management and top-level actions.
├── chat.py          # Contains the KimiChat class for handling individual conversations.
├── models.py        # Defines all dataclasses for structured API responses (e.g., UploadedFile, CompletionChunk).
└── exceptions.py    # Defines all custom exceptions for clear error handling.

example.py           # A script demonstrating how to use the library.
```

## 🤝 Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to improve the code, please feel free to:

1.  Open an issue to discuss the change.
2.  Fork the repository and create a new branch.
3.  Make your changes and submit a pull request.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
