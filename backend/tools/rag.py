"""Busca de padrões de golpe. Dono: Rafael.
MVP: busca por palavras-chave em data/patterns.json (sem dependências).
Upgrade: trocar search_patterns por Chroma + embeddings (mesma assinatura), conforme cap. 5 do curso."""
import json

from api.config import DATA_DIR

_PATTERNS: list[dict] | None = None


def _load() -> list[dict]:
    global _PATTERNS
    if _PATTERNS is None:
        _PATTERNS = json.loads((DATA_DIR / "patterns.json").read_text(encoding="utf-8"))
    return _PATTERNS


def search_patterns(tags: list[str], k: int = 3) -> list[dict]:
    tags_l = {t.lower() for t in tags}
    scored = []
    for p in _load():
        score = len(tags_l & {t.lower() for t in p["tags"]})
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:k]]
