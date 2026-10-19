import os

from dotenv import load_dotenv
from groq import Groq


load_dotenv()


api_key = os.getenv("GROQ_API_KEY")


if not api_key:

    print("GROQ_API_KEY not found in .env")

    exit()


client = Groq(
    api_key=api_key
)


response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": "Reply with exactly: API connection successful"
        }
    ]
)


print(
    response.choices[0].message.content
)