import sys
import base64
import httpx
from dotenv import load_dotenv
import os
load_dotenv()
CLAUDE_AI_KEY = os.getenv("CLAUDE_AI_KEY")

sys.path.append(r"../")

import anthropic
from flask import jsonify
import traceback
from helpers.Utils import Utils
from anthropic.types.text_block import TextBlock
from anthropic.types.tool_use_block import ToolUseBlock


class ClaudeAI2:

    file_name = "claud_response-2024-07-23.json"
    fullResponseHistory = Utils.load_json(file_name, True)  # list()
    #file_name = "claud_response-2024-07-23.json"
    #fullResponseHistory = Utils.load_json(file_name, True)  # list()

    dummy_assistant = {
        "role": "assistant",
        "content": "reading",
    }

    models = {
        "claude-3-haiku": "claude-3-haiku-20240307",
        "claude-3-5-sonnet": "claude-3-5-sonnet-20240620",
        "claude-3-opus": "claude-3-opus-20240229" 
    }
    

    client = anthropic.Anthropic(
        api_key=CLAUDE_AI_KEY
    )
    # client = None

    # def __init__(self, claude_key):
    # if ClaudeAI.client is not None:
    #    ClaudeAI.client = anthropic.Anthropic(api_key=claude_key)

    def get_data(_self, system, data):
        # print(data)
        user_message = data["message"]
        history = data["history"]
        prompt_temprature = 0.5
        if "temperature" in data:
            prompt_temprature = data["temperature"]
        ai_message = ""
        # Create a prompt and call the API
        if data["filePath"] != "":
            msg = _self.get_message_image(data)
            # history.append(_self.dummy_assistant)
            # history.append(msg)
            history[-1] = msg
        try:
            message = ClaudeAI2.client.messages.create(
                model=_self.models[data["ai_model"]],
                max_tokens=1024,
                system=system,
                # messages=[{"role": "user", "content": user_message}],
                messages=history,
                temperature=prompt_temprature,
            )
            # print(message.content)
            print(message)
            ClaudeAI2.fullResponseHistory.append(message.to_dict())
            Utils.save_json(_self.file_name, ClaudeAI2.fullResponseHistory)
            #print(message)
            #ClaudeAI2.fullResponseHistory.append(message.to_dict())
            #Utils.save_json(_self.file_name, ClaudeAI2.fullResponseHistory)
            # text_block  = (TextBlock) (message.content[0])
            # ai_message = text_block.text
            # ai_message = message.content[0]['text'].strip()
            for response_content in message.content:
                print("handling", response_content.type)
                if response_content.type == "text":
                    # ai_message += message.content[0].text.strip()
                    ai_message += _self.handle_text(
                        response_content
                    )  # message.content[0].text.strip()

                if response_content.type == "tool_use":
                    print("tool use")
                    ai_message += _self.handle_tool_use(response_content)
            return jsonify(ai_message)

        except Exception as e:
            # print(e)
            a = sys.exc_info()
            e1 = "".join(traceback.format_exception(*a))
            print(e1)
            ai_message = str(e)
            return jsonify(ai_message)

    def get_message_image(_self, data):
        image_url = data["filePath"]
        image_media_type = _self.get_mime_type(image_url)  # "image/jpeg"
        # Read local file
        with open(image_url, "rb") as file:
            img_file = file.read()

        # image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
        image_data = base64.b64encode(img_file).decode("utf-8")

        msg = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": data["message"]},
            ],
        }
        print(msg)
        return msg

    def get_mime_type(_self, img_url: str):
        mime_type = "image/jpeg"
        if img_url.endswith("png"):
            mime_type = "image/png"
        if img_url.endswith("gif"):
            mime_type = "image/gif"
        if img_url.endswith("bmp"):
            mime_type = "image/bmp"

        return mime_type

    def handle_tool_use(_self, response: ToolUseBlock):
        rval = f"{response.id} - {response.name} - {response.input}"
        print(response)
        return rval

    def handle_text(_self, response: TextBlock):
        rval = f"{response.text}"
        s = response.to_json(indent=5)
        print(s)
        return rval
