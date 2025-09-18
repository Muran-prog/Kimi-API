# example.py
# -*- coding: utf-8 -*-
"""
Example usage of the refactored KimiAIEngine library.
"""
import asyncio
import logging
import os

# Import classes directly from the kimiai package thanks to the __init__.py setup
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

    # Ensure you have a 'cookies.txt' file in the same directory
    if not os.path.exists('cookies.txt'):
        print("Error: 'cookies.txt' not found. Please create this file with your Kimi session cookies.")
        return

    try:
        # The engine is an async context manager for safe session handling
        async with KimiAIEngine(cookies_path='cookies.txt') as engine:
            # 1. Create a new chat
            print("Creating a new chat...")
            chat = await engine.create_chat(name="My First API Chat")
            print(f"Chat created with ID: {chat.chat_id}")

            # 2. (Optional) Upload a file
            # Create a dummy file for upload demonstration
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
                print("Proceeding without the file context.")
            finally:
                os.remove(dummy_file_path) # Clean up the dummy file

            # 3. Send a message and stream the response
            print(f"\nSending prompt: '{prompt}'")
            print("Streaming response from Kimi:")
            print("-" * 30)

            full_response = ""
            # The async for loop handles the stream of events
            async for event in chat.send_message_stream(prompt, file_ids=file_ids):
                if isinstance(event, CompletionChunk):
                    print(event.text, end="", flush=True)
                    full_response += event.text
                elif isinstance(event, SearchInfo):
                    print(f"\n[Kimi is searching: {event.search_type}]")
                elif isinstance(event, StatusUpdate):
                    # This event often signals the end of the stream
                    pass

            print("\n" + "-" * 30)
            print("\nFull response received.")

    except AuthenticationError as e:
        print(f"\nERROR: Authentication failed: {e}")
    except APIError as e:
        print(f"\nERROR: An API error occurred: {e}")
        print(f"Response body: {e.response_text}")
    except KimiException as e:
        print(f"\nERROR: An unexpected library error occurred: {e}")
    except Exception as e:
        print(f"\nERROR: A general error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
