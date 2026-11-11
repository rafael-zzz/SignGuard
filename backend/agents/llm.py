"""Cliente LLM via OpenRouter (compatível com a API da OpenAI). Dono: Rafael.
Sem chave ou com OFFLINE=1 -> retorna None e os agentes usam o caminho determinístico."""
import json
import re

from api.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, OFFLINE

_client = None


def available() -> bool:
    return bool(LLM_API_KEY) and not OFFLINE


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT)
    return _client


def _extract_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        m = re.search(r"\{.*\}", text or "", re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                return None
    return None


def chat_json(system: str, user: str, retries: int = 1) -> dict | None:
    """Chama o modelo pedindo JSON. Modelos :free nem sempre respeitam response_format,
    por isso também extraímos o JSON do texto."""
    if not available():
        return None
    for _ in range(retries + 1):
        try:
            resp = _get_client().chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            data = _extract_json(resp.choices[0].message.content or "")
            if data is not None:
                return data
        except Exception as e:  # noqa: BLE001
            print(f"[llm] erro: {e}")
    return None
