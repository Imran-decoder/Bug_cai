# import os
# from openai import OpenAI
#
# token = "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"
# endpoint = "https://models.github.ai/inference"
# model = "gpt-4o"
#
# client = OpenAI(
#     base_url=endpoint,
#     api_key=token,
#
# )
#
# response = client.chat.completions.create(
#     messages=[
#         {
#             "role": "system",
#             "content": "You are a helpful assistant.",
#         },
#         {
#             "role": "user",
#             "content": "What is the capital of France?",
#         }
#     ],
#     model=model
# )
#
# print(response.choices[0].message.content)


# /////////
# import os
# from azure.ai.inference import ChatCompletionsClient
# from azure.ai.inference.models import SystemMessage, UserMessage
# from azure.core.credentials import AzureKeyCredential
#
# endpoint = "https://models.github.ai/inference"
# model = "meta/Llama-4-Scout-17B-16E-Instruct"
token = "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"
#
# client = ChatCompletionsClient(
#     endpoint=endpoint,
#     credential=AzureKeyCredential(token),
# )
#
# response = client.complete(
#     messages=[
#         SystemMessage("You are a helpful assistant."),
#         UserMessage("What is the capital of France?"),
#     ],
#     temperature=1.0,
#     top_p=1.0,
#     max_tokens=1000,
#     model=model
# )
#
# print(response.choices[0].message.content)

import os
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = "https://models.github.ai/inference"
model = "xai/grok-3"
# token = os.environ["GITHUB_TOKEN"]

client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token),
)

response = client.complete(
    messages=[
        SystemMessage("You are a helpful assistant."),
        UserMessage("What is the capital of France?"),
    ],
    temperature=1.0,
    top_p=1.0,
    model=model
)

print(response.choices[0].message.content)

