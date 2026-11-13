"""Congela respostas de ferramentas apenas no avaliador, sem alterar os agentes.

A primeira execução observa as ferramentas existentes. As seguintes reproduzem
exatamente essas respostas, inclusive None/erro do Jev. Não são chamadas reais.
O relógio da política também é fixado para as execuções pareadas.
"""
import json
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from unittest.mock import patch


class ToolReplay:
    def __init__(self):
        self.answers = {}
        self.replaying = False
        self._lock = Lock()
        self._stack = ExitStack()

    def _wrap(self, name, fn):
        def call(*args, **kwargs):
            key = (name, json.dumps([args, kwargs], sort_keys=True, ensure_ascii=False))
            if self.replaying:
                if key not in self.answers:
                    raise RuntimeError(f"replay sem resposta capturada: {name}")
                return deepcopy(self.answers[key])
            result = fn(*args, **kwargs)
            with self._lock:
                self.answers[key] = deepcopy(result)
            return result
        return call

    def __enter__(self):
        from agents import decoder, policy, threat
        from tools import jev

        frozen = datetime.now(timezone.utc)

        class Clock:
            @classmethod
            def now(cls, tz=None):
                return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)

        self._stack.enter_context(patch.object(policy, "datetime", Clock))
        for module, attr in [(decoder, "decode_calldata"), (decoder, "simulate_tx"),
                             (decoder, "contract_info"), (threat, "contract_info"),
                             (threat.db, "check_blocklist"), (threat, "search_patterns"),
                             (jev, "classify")]:
            name = f"{module.__name__}.{attr}"
            self._stack.enter_context(patch.object(module, attr, self._wrap(name, getattr(module, attr))))
        return self

    def __exit__(self, *exc):
        return self._stack.__exit__(*exc)
