"""Busca de padrões de golpe (RAG). Dono: Rafael.
Interface (docs/05-backend-schema.md §6): search_patterns(query) -> docs.
MVP (TRD §2): busca por tags e palavras-chave em data/patterns.json, sem dependências e sem rede.
Upgrade: trocar o corpo de search_patterns por Chroma + embeddings mantendo a assinatura."""
import json
import re
import unicodedata

from api.config import DATA_DIR

TAG_WEIGHT = 3        # tag que é código de sinal (maiúsculas), ex.: UNLIMITED_APPROVAL
ACTION_WEIGHT = 1     # tag que é ação decodificada, ex.: approve
KEYWORD_CAP = 3       # palavras-chave achadas no texto livre valem 1 cada, até este teto
MIN_SCORE = 3         # só a ação (ex.: "transfer") nunca basta para recuperar um padrão
RELATIVE_CUTOFF = 0.6 # descarta padrões muito abaixo do melhor resultado

_PATTERNS: list[dict] | None = None


def _load() -> list[dict]:
    global _PATTERNS
    if _PATTERNS is None:
        _PATTERNS = json.loads((DATA_DIR / "patterns.json").read_text(encoding="utf-8"))
    return _PATTERNS


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def search_patterns(query: str | list[str], k: int = 3) -> list[dict]:
    """`query`: texto livre ou lista de termos (códigos de sinal, ação, contexto da transação).
    Devolve até k padrões {id, title, tags, keywords, description}, do mais para o menos parecido."""
    items = [query] if isinstance(query, str) else [q for q in query if q]
    text = _norm(" ".join(items))
    terms = {_norm(i) for i in items} | set(re.findall(r"[a-z0-9_]+", text))

    scored = []
    for pos, p in enumerate(_load()):
        score = sum(TAG_WEIGHT if t.isupper() else ACTION_WEIGHT for t in p["tags"] if _norm(t) in terms)
        hits = sum(1 for kw in p.get("keywords", []) if re.search(rf"\b{re.escape(_norm(kw))}\b", text))
        score += min(KEYWORD_CAP, hits)
        if score >= MIN_SCORE:
            scored.append((-score, pos, p))
    if not scored:
        return []
    scored.sort(key=lambda x: x[:2])
    best = -scored[0][0]
    return [p for s, _, p in scored if -s >= best * RELATIVE_CUTOFF][:k]
