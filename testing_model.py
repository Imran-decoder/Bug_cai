import os
from openai import OpenAI

token = "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"
endpoint = "https://models.github.ai/inference"
model = "gpt-4o-mini"

client = OpenAI(
    base_url=endpoint,
    api_key=token,

)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "What is the capital of France?",
        }
    ],
    model=model
)

print(response.choices[0].message.content)