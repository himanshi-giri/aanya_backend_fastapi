from http import client
import time
import os
import base64
import traceback
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv
from helpers.Utils import Utils
import json 
from google.api_core.exceptions import ResourceExhausted
import markdown

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
#client= genai.Client(api_key=GEMINI_API_KEY)
m23 = genai.list_models()


class GeminiAI:
    """Handles interactions with the Gemini AI API."""

    models = {
        "gemini-1.5-pro": "gemini-1.5-pro"
    }

    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 1024,
        "response_mime_type": "text/plain",
    }

    def normalize_messages(self, messages):
        """Convert 'content' format to 'parts' format."""
        normalized = []
        for msg in messages:
            if "content" in msg:
                parts = []
                for part in msg["content"]:
                    if part.get("type") == "text":
                        parts.append({"text": part["text"]})
                normalized.append({"role": msg["role"], "parts": parts})
            elif "parts" in msg:
                normalized.append(msg)
        return normalized
    
    def denormalize_messages(self, messages):
        """Convert 'parts' format back to 'content' format."""
        denormalized = []
        for msg in messages:
            if "parts" in msg:
                content = [{"type": "text", "text": part["text"]} for part in msg["parts"] if "text" in part]
                denormalized.append({"role": msg["role"], "content": content})
            else:
                denormalized.append(msg)
        return denormalized

    def convert_md_to_html(self, text):
        """Converts Markdown to HTML."""
        return markdown.markdown(text)

    async def get_data_stream(self, system, data):
        # for model in m23:
        #     print(model.name, model.supported_generation_methods)

        try:
            user_message = data.get("message", "").strip()
            history = data.get("history", [])
            temperature = data.get("temperature", 0.7)
            image_file = data.get("image")
            model = data.get("model", "gemini-1.5-pro")
            
            messages = self.normalize_messages(history.copy())
            # messages = history.copy()
            image_content = []

            # print(system)
            # print(messages)

            if system:
                messages.insert(0, {
                    "role": "user",
                    "parts": [{"text": system}]
                })
            if image_file:
                base64_image = await self.encode_image(image_file)
                media_type = self.get_mime_type(image_file.filename)
                image_content.append({
                    "inline_data": {
                        "mime_type": media_type,
                        "data": base64_image
                    }
                })

            if user_message and image_content:
                messages.append({
                    "role": "user",
                    "parts": [{"text": user_message}] + image_content
                })
            elif user_message:
                messages.append({
                    "role": "user",
                    "parts": [{"text": user_message}]
                })
            elif image_content:
                messages.append({
                    "role": "user",
                    "parts": image_content
                })
            #print(model,"model")
            model_instance = genai.GenerativeModel(
                model_name=model,
                generation_config={"temperature": temperature, **self.generation_config}
            )

            response = model_instance.generate_content(messages, stream=True)
            #print(response)
            
            async def stream_generator():
                try:
                    print("stream started")
                   # print(response.iterator)
                    
                    for chunk in response:
                        if hasattr(chunk, "candidates") and chunk.candidates:
                            for candidate in chunk.candidates:
                                if candidate.content and hasattr(candidate.content, "parts"):
                                    for part in candidate.content.parts:
                                        if hasattr(part, "text") and part.text:
                                            text = part.text
                                            print("Streamed text:", text)  # Debugging
                                            yield json.dumps({'text': self.convert_md_to_html(text)})
                                        else:
                                            print("No text in chunk:", chunk)
                                            yield json.dumps({'error': 'Missing text in content'})
                        else:
                                print("No candidates in chunk:", chunk)
                                yield json.dumps({'error': 'Missing candidates in chunk'})
                except ResourceExhausted:
                    time.sleep(6)  # Wait for retry_delay seconds
                    yield "Rate limit exceeded. Please try again later."

                except Exception as e:
                        yield json.dumps({'error': str(e)})

            return stream_generator
            #formatted_response = self.denormalize_messages([{"role": "assistant", "parts": [{"text": response.text}]}])
        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}

    async def encode_image(self, image_file):
        """Convert an image file to Base64 format."""
        image_bytes = await image_file.read()
        return base64.b64encode(image_bytes).decode("utf-8")

    def get_mime_type(self, filename):
        """Detect the correct MIME type based on file extension."""
        ext = filename.split(".")[-1].lower()
        mime_types = {
            "png": "image/png",
            "jpeg": "image/jpeg",
            "jpg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "webp": "image/webp",
        }
        return mime_types.get(ext, "application/octet-stream")

