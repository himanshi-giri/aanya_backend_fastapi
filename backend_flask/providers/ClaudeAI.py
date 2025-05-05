import sys
import base64
import traceback
import anthropic
from certifi import contents
from flask import jsonify
from helpers.Utils import Utils
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock
from dotenv import load_dotenv
import os
from pathlib import Path
import json
import asyncio


load_dotenv()
CLAUDE_API_KEY = os.getenv("CLAUDE_AI_KEY")


class ClaudeAI:
    """Handles interactions with Claude AI API."""

    file_name = "claude_response.json"
    fullResponseHistory = Utils.load_json(file_name, True)

    models = {
        "claude-3-haiku": "claude-3-haiku-20240307",
        "claude-3-5-sonnet": "claude-3-5-sonnet-20240620",
        "claude-3-opus": "claude-3-opus-20240229" 
    }

    client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


    async def get_data_stream(self, system, data):
        """Streams Claude AI responses in chunks."""

        try:
            user_message = data.get("message", "").strip()
            history = data.get("history", [])  
            temperature = data.get("temperature", 0.5)
            image_file = data.get("image")  # Expecting file object
            model = self.models.get(data.get("model"), "claude-3-opus")

            # Prepare message content
            messages = history.copy()
            image_content = []

            if image_file:
                base64_image = await self.encode_image(image_file)
                media_type = self.get_mime_type(image_file.filename)  
                image_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_image
                    }
                })
            if user_message:
                image_content.append({"type": "text", "text": user_message})

            messages.append({"role": "user", "content": image_content})

            print("🔹 Sending request to Claude AI...")  # Debugging
            print("Model:", model)
            #print("Messages:", json.dumps(messages, indent=2))

            # ✅ Streaming Response from Claude AI
            async def stream_generator():
                try:
                    print("⚡ Before Claude API call...")  # ✅ Check before API call
                    try:
                        with self.client.messages.stream(
                            model=model,
                            max_tokens=1024,
                            system=system,
                            messages=messages,
                            temperature=temperature,
                        ) as stream:                       
                            print("Claude AI stream started...")                           
                            for chunk in stream.text_stream:
                                print(chunk)
                                if chunk:
                                        print("Streaming chunk:", chunk)
                                        yield json.dumps({"text": chunk}) + "\n" #json.dumps({"role": "assistant", "content": [{"type": "text", "text": part}]}) + "\n"
                    except Exception as client_error:
                        print(f"Claude Client error: {client_error}")
                        traceback.print_exc()
                        yield json.dumps({"error": str(client_error)}) + "\n"
                except Exception as e:
                    yield json.dumps({"error": str(e)}) + "\n"

            return stream_generator

        except Exception as e:
            traceback.print_exc()
            return json.dumps({"error": str(e)})

    async def get_data(self, system, data):
        
        try:
            user_message = data.get("message", "").strip()
            history = data.get("history", [])  
            temperature = data.get("temperature", 0.5)
            image_file = data.get("image")  # Expecting file object from Flask
            model=data.get('model')
            # Prepare message content
            messages = history.copy()  # Copy history to maintain structure
            image_content=[]
            if image_file:
                # Convert uploaded file to Base64
                base64_image = await self.encode_image(image_file)
                media_type = self.get_mime_type(image_file.filename)  
                image_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64_image
                    }
                })
                print(image_content)
                # image_message = self.get_message_image(base64_image, user_message)
                # messages.append(image_message)
            if user_message:
                image_content.append({"type": "text", "text": user_message})

            # Final message object
            messages.append({"role": "user", "content": image_content})
            #print(self.models.get(data.get("model"),"claude-3-opus" ))
            response = self.client.messages.create(
                model=self.models.get(data.get("model"),"claude-3-opus" ),
                max_tokens=1024,
                system=system,
                messages=messages,
                temperature=temperature,
                
            )

            # Extract AI response content
            ai_response_content = []
            if hasattr(response, "content") and isinstance(response.content, list):
                for block in response.content:
                    if hasattr(block, "text"):
                        ai_response_content.append({"type": "text", "text": block.text})
            
            return {"role": "assistant", "content": ai_response_content}

        except Exception as e:
            traceback.print_exc()
            return {"error": str(e)}
   

    
    async def encode_image(self,image_file):
        """Convert an image file to Base64 format."""
        image_bytes = await image_file.read()
        return base64.b64encode(image_bytes).decode("utf-8")

    def load_prompt_template(self,system):
        with open(system, "r") as file:
            return file.read()
    
    def get_system_prompt(self,role: str,form_data:dict) -> str:
        """Gets the system prompt from a file, optionally including a data key."""
        data_key=form_data.get("data_key")
        if data_key:
            system_prompt_file = Path(f"system-prompts/{role}-{data_key}.txt")
            if system_prompt_file.is_file():
                try:
                    with open(system_prompt_file, "r") as f:
                        return f.read().strip()
                except FileNotFoundError:
                    pass #File was found, but then could not be read.
                except Exception as e:
                    print(f"Error reading system prompt file {system_prompt_file}: {e}")
                    pass #log the error, and continue to the default.

        system_prompt_file = Path(f"system-prompts/{role}.txt")
        template = self.load_prompt_template(system_prompt_file)
        prompt = template.format(
            class_number=form_data.get("class_number"),
            grade=form_data.get("grade"),
            module_outline=form_data.get("module_outline")
        )
        
       # print(prompt) 
        if system_prompt_file.is_file():
            try:
                with open(system_prompt_file, "r") as f:
                    return f.read().strip()
            except FileNotFoundError:
                pass #File was found, but then could not be read.
            except Exception as e:
                print(f"Error reading system prompt file {system_prompt_file}: {e}")
                pass #log the error, and continue to the default.
               
        print(f"Warning: System prompt file not found for role: {role}. Using default prompt.")
        return "You are an AI assistant."
    # async def get_message_image(self,image_file, user_text):
    #     """Prepares a structured message for Claude AI with an image."""
    #     base64_image =await self.encode_image(image_file)  # Await the read operation
    #     print(base64_image,"here")
    #     content = {
    #         "role": "user",
    #         "content": [
    #             {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64_image}},
    #         ],
    #     }

    #     if user_text.strip():  # Ensures empty or whitespace-only text is ignored
    #         content["content"].append({"type": "text", "text": user_text})  # Append text properly

    #     return content

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
        return mime_types.get(ext, "application/octet-stream")  # Default to binary if unknown
