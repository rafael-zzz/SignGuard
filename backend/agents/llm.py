"""Cliente LLM via OpenRouter (API compatível com OpenAI). Dono: Rafael.
Sem chave ou com OFFLINE=1 -> os agentes usam só o caminho determinístico (modo regras).

Saída estruturada: a resposta é validada contra um schema Pydantic. Fora do schema -> 1 nova
tentativa; se falhar de novo, devolve None e o agente segue só com regras (docs/03-app-flow.md).

Latência (TRD §7, "LLMs (decoder + judge)"): as chamadas de uma mesma análise dividem um único
orçamento de tempo, LLM_TIMEOUT. O Decodificador usa no máximo DECODER_BUDGET_S e o Juiz fica com
o que sobrar. Quem estoura o tempo cai para as regras: a análise nunca espera o LLM além do orçamento."""
import json
import re
import time

from pydantic import BaseModel, ValidationError

from agents.prompts import response_schema
from api.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, OFFLINE

# Modelos :free nem sempre aceitam json_schema. Se a API recusar o formato, descemos um nível
# (vale para o resto do processo). O schema continua sendo validado aqui de qualquer forma.
_MODES = ("json_schema", "json_object", "text")
_mode = 0
BUDGET_S = LLM_TIMEOUT              # tempo total de LLM por análise (decoder + judge)
DECODER_BUDGET_S = BUDGET_S / 3     # o resumo é curto; a maior parte fica para a explicação do Juiz
_MIN_CALL_S = 1.0                   # com menos que isso não vale abrir a chamada
_COOLDOWN_S = 30.0          # após erro de rede/limite, não insiste: a demo não pode travar
_cooldown_until = 0.0
_MAX_TIMEOUTS = 2           # estouros de tempo seguidos (ex.: decoder e judge da mesma análise) também pausam
_timeouts = 0
_client = None


def available() -> bool:
    return bool(LLM_API_KEY) and not OFFLINE


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        # max_retries=0: quem controla tentativas (e a latência) é chat_structured
        _client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT, max_retries=0)
    return _client


def _extract_json(text: str) -> dict | None:
    for candidate in (text, (re.search(r"\{.*\}", text or "", re.S) or [None])[0]):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except Exception:  # noqa: BLE001
            continue
        if isinstance(data, dict):
            return data
    return None


def _response_format(schema: type[BaseModel]) -> dict:
    mode = _MODES[_mode]
    if mode == "json_schema":
        return {"response_format": {"type": "json_schema", "json_schema": {
            "name": schema.__name__, "strict": True, "schema": response_schema(schema)}}}
    if mode == "json_object":
        return {"response_format": {"type": "json_object"}}
    return {}


def chat_structured(system: str, user: str, schema: type[BaseModel], retries: int = 1,
                    timeout: float | None = None):
    """Devolve (objeto validado | None, erro | None).
    (None, None) = LLM desligado por configuração. `timeout` é quanto esta chamada pode gastar,
    já contando a nova tentativa; nunca passa de BUDGET_S."""
    global _mode, _cooldown_until, _timeouts
    if not available():
        return None, None
    if time.monotonic() < _cooldown_until:
        return None, "LLM em pausa após falha recente; usando regras"

    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    limit = BUDGET_S if timeout is None else min(BUDGET_S, timeout)
    deadline = time.monotonic() + limit
    attempts, problem = 0, "sem resposta"
    while attempts <= retries:
        remaining = deadline - time.monotonic()
        if remaining < _MIN_CALL_S:
            return None, f"LLM sem tempo no orçamento da análise ({BUDGET_S:.0f}s); usando regras"
        try:
            resp = _get_client().with_options(timeout=remaining).chat.completions.create(
                model=LLM_MODEL, messages=messages, temperature=0.1, **_response_format(schema))
            text = resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            if getattr(e, "status_code", None) in (400, 404, 422) and _mode < len(_MODES) - 1:
                _mode += 1          # provedor não aceita este response_format: tenta um mais simples
                continue
            if "timeout" in type(e).__name__.lower():
                _timeouts += 1
                if _timeouts < _MAX_TIMEOUTS:   # lento uma vez: a próxima chamada ainda tenta
                    return None, f"LLM não respondeu em {limit:.1f}s; usando regras"
            _timeouts = 0
            _cooldown_until = time.monotonic() + _COOLDOWN_S
            print(f"[llm] erro: {e}")
            return None, f"LLM indisponível ({type(e).__name__}); usando regras"

        _timeouts = 0
        attempts += 1
        data = _extract_json(text)
        if data is None:
            problem = "a resposta não é um objeto JSON"
        else:
            try:
                return schema.model_validate(data), None
            except ValidationError as e:
                problem = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:3])
        messages += [
            {"role": "assistant", "content": text[:2000]},
            {"role": "user", "content": f"Sua resposta não seguiu o formato ({problem}). "
                                        "Responda SOMENTE com o objeto JSON no formato pedido."},
        ]
    return None, f"LLM fora do schema após {attempts} tentativas ({problem}); usando regras"
