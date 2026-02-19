import asyncio
import time
from src.utils.logger import get_logger
from typing import Optional, Dict, Any, AsyncGenerator

import httpx
from httpx import Response
from dotenv import load_dotenv
import os

load_dotenv()

class TokenBucket:
    def __init__(self, rate: int, per:float):
        """
        rate = number of tokens allowed
        per = seconds window
        """
        self.rate = rate
        self.per = per
        self.allowance = rate
        self.last_check = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, tokens: int = 1):
        async with self.lock:
            current = time.monotonic()
            elapsed = current - self.last_check
            self.last_check = current

            self.allowance += elapsed * (self.rate / self.per)
            if self.allowance > self.rate:
                self.allowance = self.rate

            if self.allowance < tokens:
                wait_time = (tokens - self.allowance) * (self.per / self.rate)
                await asyncio.sleep(wait_time)
                self.allowance = 0
            else:
                self.allowance -= tokens

class GroqClient:
    BASE_URL = os.getenv("GROQ_BASE_URL")
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.timeout = float(os.getenv("TIMEOUT", 30.0))
        
        self.client = httpx.AsyncClient(timeout=self.timeout)

        self.request_bucket = TokenBucket(rate=30, per=60)
        self.token_bucket = TokenBucket(rate=14400, per=60)
        self.logger = get_logger("groq_client")

    async def _retry_request(self, func, max_retries=3):
        delay=1
        for attempt in range(max_retries):
            try:
                return await func()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    self.logger.warning("Rate limit exceeded, retrying...")
                else:
                    raise
            except Exception as e:
                self.logger.error(f"Unexpected Error: {e}")
            
            await asyncio.sleep(delay)
            delay *= 2
        
        raise Exception("Max retries exceeded")

    async def generate(
        self,
        messages: list,
        model: str = "llama-3.3-70b-versatile",
        max_tokens = 1000,
        stream: bool = False,
    )->Dict[Any, str]:

        await self.request_bucket.consume(1)
        estimated_tokens = sum(len(m["content"]) for m in messages) // 4
        await self.token_bucket.consume(estimated_tokens)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        async def request_func():
            response = await self.client.post(
                self.BASE_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response
        
        response: Response = await self._retry_request(request_func)
        
        data = response.json()
        usage = data.get("usage", {})
        self.logger.info(f"Token usage: {usage}")

        return data
    
    async def generate_stream(
        self,
        messages: list,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 1000,
    ) -> AsyncGenerator[str, None]:

        await self.request_bucket.consume(1)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with self.client.stream(
            "POST",
            self.BASE_URL,
            headers=headers,
            json=payload,
        ) as response:

            async for chunk in response.aiter_text():
                yield chunk
