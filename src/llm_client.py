import os
import json
import logging
from typing import Any, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LLMClient:
    """
    LLM Client wrapper supporting OpenRouter, OpenAI, and Gemini API endpoints.
    Provides structured completion (JSON mode / extraction).
    """
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.5-9b")

        self.client = None
        if self.api_key and not self.api_key.startswith("sk-or-v1-your_") and not self.api_key.startswith("your_"):
            try:
                from openai import OpenAI
                if os.getenv("OPENROUTER_API_KEY"):
                    self.client = OpenAI(
                        base_url=self.base_url,
                        api_key=self.api_key,
                        timeout=10.0,
                        default_headers={
                            "HTTP-Referer": "https://github.com/VinUni-AI20k/K4-Day9-Multi-Agent-A2A",
                            "X-Title": "E-Commerce Dispute Multi-Agent Pipeline"
                        }
                    )
                else:
                    self.client = OpenAI(api_key=self.api_key, timeout=10.0)

            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI/OpenRouter client: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Optional[Dict[str, Any]]:
        """
        Generate a structured JSON output from LLM.
        Returns parsed dictionary or None if LLM is unavailable or fails.
        """
        if not self.client:
            return None

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt + "\nIMPORTANT: Return ONLY valid JSON matching the exact schema requested. Do not include markdown code fences or explanatory text outside the JSON."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            if not content:
                return None

            content_clean = content.strip()
            if content_clean.startswith("```"):
                lines = content_clean.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content_clean = "\n".join(lines).strip()

            return json.loads(content_clean)
        except Exception as e:
            logger.warning(f"LLM API Call Exception: {e}")
            return None
