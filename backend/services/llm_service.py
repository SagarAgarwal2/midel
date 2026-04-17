import json
import os
import re
from typing import Any

import requests


class GroqClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.url = "https://api.groq.com/openai/v1/chat/completions"

    def _fallback_extract(self, text: str) -> list[dict[str, Any]]:
        records = []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines:
            parts = [part.strip() for part in re.split(r"[,;|]", line)]
            if len(parts) < 3:
                continue
            supplier = parts[0]
            product = parts[1]
            delay = re.findall(r"\d+", line)
            delay_days = int(delay[0]) if delay else 0
            lowered = line.lower()
            risk_level = "High" if delay_days > 7 else "Medium" if delay_days > 3 else "Low"
            issue = "logistics disruption"
            if "quality" in lowered:
                issue = "quality issue"
            elif "port" in lowered:
                issue = "port congestion"
            records.append(
                {
                    "supplier": supplier,
                    "product": product,
                    "delay_days": delay_days,
                    "issue": issue,
                    "risk_level": risk_level,
                }
            )
        return records

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            return "No GROQ_API_KEY configured. Set it in backend/.env."
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = requests.post(self.url, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def extract_structured_json(self, raw_text: str) -> list[dict[str, Any]]:
        prompt = (
            "Extract structured supply chain data from this text and return JSON. "
            "Return ONLY a JSON array with objects having keys: supplier, product, delay_days, issue, risk_level."
        )
        try:
            content = self.chat(
                "You are a supply chain data extraction assistant.",
                f"{prompt}\n\nTEXT:\n{raw_text}",
            )
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            payload = json_match.group(0) if json_match else content
            parsed = json.loads(payload)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return self._fallback_extract(raw_text)
        return self._fallback_extract(raw_text)
