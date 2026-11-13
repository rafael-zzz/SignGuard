"""Cliente LLM via OpenRouter (API compatível com OpenAI). Dono: Rafael.
Sem chave ou com OFFLINE=1 -> os agentes usam só o caminho determinístico (modo regras).

Saída estruturada: a resposta é validada contra um schema Pydantic. Fora do schema -> 1 nova
tentativa; se falhar de novo, devolve None e o agente segue só com regras (docs/03-app-flow.md).

O LLM está fora do caminho da decisão (docs/07 §5): só o nó `explain` chama este cliente, depois que
o veredito já foi fechado em código. Latência (TRD §7): uma chamada por análise, com teto LLM_TIMEOUT
(4 s). Estourou -> vale o texto do template; o veredito é o mesmo."""
import json
import re
import threading
import time

from pydantic import BaseModel, ValidationError

from agents.prompts import response_schema
from api.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, OFFLINE

# Modelos :free nem sempre aceitam json_schema. Se a API recusar o formato, descemos um nível
# (vale para o resto do processo). O schema continua sendo validado aqui de qualquer forma.
_MODES = ("json_schema", "json_object", "text")
_mode = 0
# LLM_MODEL aceita uma lista separada por vírgula. Modelos :free somem sem aviso: se o provedor
# disser que o modelo não existe mais, passamos para o próximo e ficamos nele.
MODELS = [m.strip() for m in (LLM_MODEL or "").split(",") if m.strip()]
_model = 0
_MODEL_GONE = re.compile(r"unavailable|not a valid model|no longer available|deprecated|does not exist|"
                         r"model not found|no endpoints found for", re.I)
BUDGET_S = LLM_TIMEOUT              # teto de LLM por análise (uma chamada: a explicação)
_MIN_CALL_S = 1.0                   # com menos que isso não vale abrir a chamada
_COOLDOWN_S = 30.0          # após erro de rede/limite, não insiste: a demo não pode travar
_cooldown_until = 0.0
_MAX_TIMEOUTS = 2           # estouros de tempo seguidos também pausam
_timeouts = 0
_client = None


def available() -> bool:
    return bool(LLM_API_KEY) and bool(MODELS) and not OFFLINE


def current_model() -> str | None:
    return MODELS[_model] if MODELS else None


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
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__, "strict": True, "schema": response_schema(schema),
                },
            },
            "extra_body": {"provider": {"require_parameters": True}},
        }
    if mode == "json_object":
        return {"response_format": {"type": "json_object"}}
    return {}


_last = threading.local()


def last_error() -> str | None:
    """Motivo da última falha de chat_json nesta thread (None = sem falha)."""
    return getattr(_last, "error", None)


def _fail(reason: str) -> None:
    _last.error = reason
    return None


def chat_json(system: str, user, schema: type[BaseModel] | None = None, timeout: float | None = None):
    """Uma chamada ao modelo. Devolve o objeto JSON da resposta; se a resposta não for um objeto JSON,
    devolve o texto cru (quem chama trata como fora do schema). None = sem resposta: LLM desligado
    (last_error() é None) ou falha tratada de rede/limite/tempo (last_error() diz qual).
    `user`: texto ou lista de mensagens. Nada aqui é confiável: quem valida é chat_structured."""
    global _mode, _model, _cooldown_until, _timeouts
    _last.error = None
    if not available():
        return None
    if time.monotonic() < _cooldown_until:
        return _fail("LLM em pausa após falha recente; usando regras")

    limit = BUDGET_S if timeout is None else min(BUDGET_S, timeout)
    messages = [{"role": "system", "content": system}]
    messages += [{"role": "user", "content": user}] if isinstance(user, str) else list(user)
    deadline = time.monotonic() + limit
    start_mode = _mode
    while True:
        remaining = deadline - time.monotonic()
        if remaining < _MIN_CALL_S:
            return _fail(f"LLM sem tempo no orçamento da análise ({BUDGET_S:.0f}s); usando regras")
        try:
            resp = _get_client().with_options(timeout=remaining).chat.completions.create(
                model=MODELS[_model], messages=messages, temperature=0.1,
                **(_response_format(schema) if schema is not None else {}))
            text = resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            status = getattr(e, "status_code", None)
            if status in (400, 404, 422):
                gone = _MODEL_GONE.search(str(e))
                if not gone and schema is not None and _mode < len(_MODES) - 1:
                    _mode += 1          # provedor não aceita este response_format: tenta um mais simples
                    continue
                _mode = start_mode      # o problema não era o formato: desfaz a descida
                if _model < len(MODELS) - 1:
                    print(f"[llm] modelo {MODELS[_model]} recusado ({status}); usando {MODELS[_model + 1]}")
                    _model += 1
                    continue
                _model = 0
                _cooldown_until = time.monotonic() + _COOLDOWN_S
                print(f"[llm] erro: {e}")
                return _fail(f"LLM recusou a requisição ({status}); confira LLM_MODEL: {str(e)[:160]}")
            if "timeout" in type(e).__name__.lower():
                _timeouts += 1
                if _timeouts < _MAX_TIMEOUTS:   # lento uma vez: a próxima chamada ainda tenta
                    return _fail(f"LLM não respondeu em {limit:.1f}s; usando regras")
            _timeouts = 0
            _cooldown_until = time.monotonic() + _COOLDOWN_S
            print(f"[llm] erro: {e}")
            return _fail(f"LLM indisponível ({type(e).__name__}); usando regras")
        _timeouts = 0
        data = _extract_json(text)
        return data if data is not None else text


def chat_structured(system: str, user: str, schema: type[BaseModel], retries: int = 1,
                    timeout: float | None = None):
    """Devolve (objeto validado | None, erro | None). (None, None) = LLM desligado por configuração.
    Tudo que o modelo devolve passa pelo schema; fora dele -> 1 nova tentativa -> regras.
    `timeout` é quanto esta chamada pode gastar, já contando a nova tentativa; nunca passa de BUDGET_S."""
    limit = BUDGET_S if timeout is None else min(BUDGET_S, timeout)
    deadline = time.monotonic() + limit
    messages = [{"role": "user", "content": user}]
    attempts, problem = 0, "sem resposta"
    while attempts <= retries:
        data = chat_json(system, user if attempts == 0 else messages, schema, deadline - time.monotonic())
        if data is None:
            return None, last_error()
        attempts += 1
        if isinstance(data, dict):
            try:
                return schema.model_validate(data), None
            except ValidationError as e:
                problem = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:3])
        else:
            problem = "a resposta não é um objeto JSON"
        said = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
        messages += [
            {"role": "assistant", "content": said[:2000]},
            {"role": "user", "content": f"Sua resposta não seguiu o formato ({problem}). "
                                        "Responda SOMENTE com o objeto JSON no formato pedido."},
        ]
    return None, f"LLM fora do schema após {attempts} tentativas ({problem}); usando regras"
