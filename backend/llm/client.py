"""
Unified LLM client — switch between a locally-run Ollama model and the Groq API
without changing any agent code. Controlled via env vars (see .env.example).

Usage:
    from backend.llm.client import LLMClient
    llm = LLMClient()                      # reads LLM_PROVIDER from env (default: groq)
    llm = LLMClient(provider="local")      # force local Ollama
    llm = LLMClient(provider="groq")       # force Groq
"""

import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env into the environment so os.getenv() picks it up


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()

        if self.provider == "local":
            self.model = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
            self.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        elif self.provider == "groq":
            self.model = model or os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
            self.base_url = "https://api.groq.com/openai/v1"

            # Collect all Groq API keys from the environment.
            # Supports GROQ_API_KEY (primary) plus any number of additional
            # keys named GROQ_API_KEY_1, GROQ_API_KEY_2, ... GROQ_API_KEY_N.
            # Add new keys to .env only — never hardcode values in source.
            #
            # Example .env:
            #   GROQ_API_KEY=gsk_...primary...
            #   GROQ_API_KEY_1=gsk_...account2...
            #   GROQ_API_KEY_2=gsk_...account3...
            keys = []
            primary = os.getenv("GROQ_API_KEY")
            if primary:
                keys.append(primary)
            i = 1
            while True:
                k = os.getenv(f"GROQ_API_KEY_{i}")
                if not k:
                    break
                keys.append(k)
                i += 1

            if not keys:
                raise ValueError(
                    "No Groq API key found. Set GROQ_API_KEY (and optionally "
                    "GROQ_API_KEY_1, GROQ_API_KEY_2, ...) in your .env file."
                )

            self._api_keys = keys          # full list for rotation
            self._key_index = 0            # which key we're currently using
            print(f"[LLMClient] Groq provider — {len(keys)} API key(s) loaded.")

        else:
            raise ValueError(f"Unknown provider '{self.provider}'. Use 'local' or 'groq'.")

    @property
    def api_key(self) -> str:
        """Current active Groq API key."""
        return self._api_keys[self._key_index]

    def _rotate_key(self):
        """Advance to the next key in round-robin order."""
        self._key_index = (self._key_index + 1) % len(self._api_keys)
        print(
            f"[LLMClient] Rotated to API key slot {self._key_index + 1} "
            f"of {len(self._api_keys)}."
        )

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        """Returns the raw text content of the model's reply."""
        if self.provider == "local":
            return self._generate_ollama(system_prompt, user_prompt, temperature, json_mode)
        return self._generate_groq(system_prompt, user_prompt, temperature, json_mode)

    def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        retries: int = 1,
    ) -> dict:
        """Calls generate() in JSON mode and parses the result. If parsing fails,
        retries up to `retries` more times with an added reminder, before giving
        up and returning a dict flagged with _parse_error so callers can detect
        and count these instead of silently mis-scoring an evaluation."""
        prompt = user_prompt
        last_raw = None

        for attempt in range(retries + 1):
            raw = self.generate(system_prompt, prompt, temperature=temperature, json_mode=True)
            last_raw = raw
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                prompt = (
                    user_prompt
                    + "\n\nYour previous response was not valid JSON. "
                    + "Respond with ONLY valid JSON, no other text, no markdown fences."
                )

        return {"_raw": last_raw, "_parse_error": True}

    # ---- Ollama (local) ----
    def _generate_ollama(self, system_prompt, user_prompt, temperature, json_mode):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_mode:
            payload["format"] = "json"

        resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    # ---- Groq (OpenAI-compatible API) ----
    def _generate_groq(self, system_prompt, user_prompt, temperature, json_mode):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Retry on two independent failure modes:
        #   1. HTTP 429 (rate limit) — rotate key, then back off if all keys exhausted
        #   2. Network errors (RemoteDisconnected, ConnectionError, Timeout) —
        #      Groq sometimes drops the TCP connection under load; wait 5s and retry
        #      on the same key (rotating doesn't help for network drops).
        total_attempts = len(self._api_keys) + 3  # key rotations + backoff retries
        backoff = 10  # seconds for rate-limit back-off
        backoff_phase = False  # True once we've exhausted all key rotations
        resp = None

        for attempt in range(total_attempts):
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            try:
                resp = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60,
                )
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as net_err:
                # Transient network drop — wait briefly and retry
                wait = 5 * (attempt + 1)  # 5s, 10s, 15s …
                print(
                    f"[LLMClient] Network error on attempt {attempt + 1}: "
                    f"{net_err.__class__.__name__}. Retrying in {wait}s..."
                )
                time.sleep(wait)
                continue  # retry same key — network drops aren't key-specific

            if resp.status_code == 429:
                pass  # handled below in the 429 block
            elif resp.status_code == 400:
                # Groq returns 400 json_validate_failed when the model emits an
                # empty string under json_mode — this is a transient model failure,
                # not a bad prompt. Retry on a different key after a short wait.
                err = resp.json().get("error", {})
                if err.get("code") == "json_validate_failed":
                    wait = 5 * (attempt + 1)
                    print(
                        f"[LLMClient] json_validate_failed on attempt {attempt + 1} "
                        f"(key slot {self._key_index + 1}). Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                    self._rotate_key()
                    continue
                else:
                    break  # genuine bad-request — surface it below
            else:
                break  # success or other non-retryable error — handle below

            # HTTP 429 handling
            if not backoff_phase and (attempt + 1) < len(self._api_keys):
                # Still have unused keys — rotate immediately, no sleep
                self._rotate_key()
            else:
                # All keys tried, or already in back-off phase
                backoff_phase = True
                retry_after = int(resp.headers.get("Retry-After", backoff))
                wait = max(retry_after, backoff)
                print(
                    f"[LLMClient] All keys rate-limited. "
                    f"Waiting {wait}s before retry (back-off attempt "
                    f"{attempt - len(self._api_keys) + 2})..."
                )
                time.sleep(wait)
                backoff = min(backoff * 2, 60)  # cap at 60s
                self._rotate_key()  # keep rotating even during back-off

        if resp is None:
            raise requests.exceptions.ConnectionError(
                f"Groq API unreachable after {total_attempts} attempts (all network errors)."
            )
        if not resp.ok:
            # Include response body so 400/429/etc. are immediately diagnosable
            raise requests.HTTPError(
                f"{resp.status_code} from Groq API (key slot {self._key_index + 1}): "
                f"{resp.text[:400]}",
                response=resp,
            )
        return resp.json()["choices"][0]["message"]["content"]
