# chat/llms/openai_client.py

import os
from openai import OpenAI

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def chat(self, messages, stream_callback=None):
        response_text = ""
        stream = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            stream=True,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            response_text += delta
            if stream_callback:
                stream_callback(delta)

        return response_text
