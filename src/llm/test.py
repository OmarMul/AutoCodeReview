import asyncio
from src.llm.groq_client import GroqClient

async def test():
    client = GroqClient()

    response = await client.generate(
        messages=[
            {"role": "user", "content": "Say hello"}
        ]
    )

    print(response["choices"][0]["message"]["content"])

asyncio.run(test())
