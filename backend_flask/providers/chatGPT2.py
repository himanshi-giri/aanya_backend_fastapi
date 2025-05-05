import os
from openai import OpenAI
#from dotenv import load_dotenv
from flask import jsonify
from dotenv import load_dotenv
import os
load_dotenv()
OPEN_AI_KEY = os.getenv("OPEN_AI_KEY")
class ChatGPT():

    client = OpenAI(api_key=OPEN_AI_KEY)

    def get_data(_self, system, data):
        #print(data)
        # Extract the user message and conversation history from the request data
        user_message = data["message"]
        history = data["history"]

        # Create a list of message dictionaries for the OpenAI API
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in history]
        # Append the system message from the "system_card.txt" file
        messages.append({"role": "system", "content": system})

        # Call the OpenAI API to generate a response using the GPT-3.5-turbo model
        response = ChatGPT.client.chat.completions.create(model="gpt-3.5-turbo",
        messages=messages,
        # max_tokens=50,
        n=1,
        temperature=1)

        # Extract the generated AI message from the response
        ai_message = response.choices[0].message.content.strip()

        # Return the AI message as a JSON response
        return jsonify(ai_message)
