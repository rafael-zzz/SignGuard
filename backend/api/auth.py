"""Credenciais por proprietário para o MVP; sem bypass implícito no modo offline."""
import json
import os
import secrets
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer = HTTPBearer(auto_error=False)


def configured_keys() -> dict[str, str]:
    try:
        keys = json.loads(os.getenv("SIGNGUARD_API_KEYS", "{}"))
        if not isinstance(keys, dict) or any(
            not isinstance(owner, str) or not owner or not isinstance(key, str) or len(key) < 32
            for owner, key in keys.items()
        ) or len(set(keys.values())) != len(keys):
            raise ValueError
        return keys
    except (ValueError, TypeError):
        raise HTTPException(503, "configuração de autenticação inválida") from None


def current_owner(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> str:
    keys = configured_keys()
    if not keys:
        raise HTTPException(503, "autenticação não configurada")
    if credentials:
        for owner, key in keys.items():
            if secrets.compare_digest(credentials.credentials.encode(), key.encode()):
                return owner
    raise HTTPException(401, "credencial ausente ou inválida", headers={"WWW-Authenticate": "Bearer"})


Owner = Annotated[str, Depends(current_owner)]


def require_owner(requested: str, authenticated: str) -> None:
    if requested != authenticated:
        raise HTTPException(403, "proprietário não autorizado")
