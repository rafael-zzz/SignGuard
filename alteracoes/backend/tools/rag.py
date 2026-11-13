"""Busca de padrões de golpe (RAG). Dono: Rafael.
Interface (docs/05-backend-schema.md §6): search_patterns(query) -> docs. A assinatura não muda com o backend.

Backends (TRD §2):
- "chroma": os padrões de data/patterns.json ficam indexados em uma coleção Chroma (em memória) e o
  texto livre da consulta (mensagem do usuário/bot) é comparado por embeddings. A semelhança soma
  pontos à busca por tags, então um relato com outras palavras também recupera o padrão certo.
- "memoria": o mesmo cálculo (mesmos embeddings locais, mesma semelhança) sem o Chroma. É o que roda,
  sozinho, se o chromadb não estiver instalado ou falhar ao carregar — o resultado da busca não muda.
- "tags": só tags e palavras-chave (RAG_BACKEND=tags).

Embeddings (RAG_EMBEDDINGS):
- "local" (padrão): vetor calculado aqui, por palavras e trechos de palavras. Não baixa nada, então
  funciona com OFFLINE=1 e sem rede no dia da demo.
- "minilm": modelo all-MiniLM-L6-v2 do próprio Chroma (ONNX). Precisa baixar ~80 MB na primeira vez;
  se não der, cai para "local"."""
import hashlib
import json
import logging
import math
import re
import threading
import unicodedata
from collections import Counter

from api.config import DATA_DIR, OFFLINE, RAG_BACKEND, RAG_EMBEDDINGS

TAG_WEIGHT = 3        # tag que é código de sinal (maiúsculas), ex.: UNLIMITED_APPROVAL
ACTION_WEIGHT = 1     # tag que é ação decodificada, ex.: approve
KEYWORD_CAP = 3       # palavras-chave achadas no texto livre valem 1 cada, até este teto
VECTOR_WEIGHT = 6     # semelhança (0–1) entre o texto livre e o padrão, vezes este peso
MIN_SIMILARITY = 0.25 # abaixo disso a semelhança é ruído e não soma nada
MIN_SCORE = 3         # só a ação (ex.: "transfer") nunca basta para recuperar um padrão
RELATIVE_CUTOFF = 0.6 # descarta padrões muito abaixo do melhor resultado
EMBED_DIM = 512

_PATTERNS: list[dict] | None = None
_LOCK = threading.Lock()
_client = None              # um cliente Chroma por processo (versões 0.x não aceitam recriar)
_collection = None
_embed = None
_memory: dict[str, list[float]] | None = None   # índice sem Chroma: id do padrão -> vetor
_backend: str | None = None   # definido na primeira busca: "chroma", "memoria" ou "tags"


def _load() -> list[dict]:
    global _PATTERNS
    if _PATTERNS is None:
        _PATTERNS = json.loads((DATA_DIR / "patterns.json").read_text(encoding="utf-8"))
    return _PATTERNS


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


# ---------- Embeddings ----------
_STOPWORDS = frozenset(
    "a o as os um uma uns umas de do da dos das em no na nos nas por para pra com sem que se ao aos e ou "
    "mas como mais muito seu sua seus suas meu minha meus minhas este esta esse essa isso isto ele ela "
    "foi ser tem ter esta estao sao pelo pela ate sobre entre quando onde the of to and in is for on".split())


def embed_local(texts: list[str]) -> list[list[float]]:
    """Vetor por palavras e por trechos de 4 letras (pega variações como aprovar/aprovação), com hashing."""
    out = []
    for text in texts:
        feats: Counter = Counter()
        for w in re.findall(r"[a-z0-9]+", _norm(text)):
            if len(w) < 3 or w in _STOPWORDS:
                continue
            feats["w:" + w] += 2
            for i in range(len(w) - 3):
                feats["g:" + w[i:i + 4]] += 1
        vec = [0.0] * EMBED_DIM
        for feat, count in feats.items():
            h = int.from_bytes(hashlib.blake2b(feat.encode(), digest_size=8).digest(), "big")
            vec[h % EMBED_DIM] += (1.0 if (h >> 40) & 1 else -1.0) * (1 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vec))
        out.append([v / norm for v in vec] if norm else vec)
    return out


def _minilm():
    """Embeddings neurais do Chroma. Com OFFLINE=1 só entra se o modelo já estiver em cache (não baixa)."""
    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    model = ONNXMiniLM_L6_V2()
    if OFFLINE:
        from pathlib import Path
        if not (Path(model.DOWNLOAD_PATH) / model.EXTRACTED_FOLDER_NAME / "model.onnx").exists():
            raise RuntimeError("modelo MiniLM não está em cache e OFFLINE=1")
    return lambda texts: [list(map(float, v)) for v in model(texts)]


def _doc_text(p: dict) -> str:
    return f"{p['title']}. {p['description']} {' '.join(p.get('keywords', []))}"


def _init() -> None:
    """Monta o índice na primeira busca. Chroma faltando ou quebrado -> "memoria" (a análise não para)."""
    global _client, _collection, _embed, _backend, _memory
    with _LOCK:
        if _backend is not None:
            return
        if RAG_BACKEND == "tags":
            _backend = "tags"
            return
        patterns = _load()
        texts = [_doc_text(p) for p in patterns]
        try:
            if RAG_BACKEND == "memoria":
                raise RuntimeError("RAG_BACKEND=memoria")
            import chromadb
            from chromadb.config import Settings

            embed, vectors = embed_local, None
            if RAG_EMBEDDINGS == "minilm":
                try:
                    embed = _minilm()
                    vectors = embed(texts)
                except Exception as e:  # noqa: BLE001
                    print(f"[rag] MiniLM indisponível ({type(e).__name__}); usando embeddings locais")
                    embed = embed_local
            logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)   # sem ruído de telemetria
            if _client is None:
                _client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
            coll = _client.get_or_create_collection("padroes_de_golpe", metadata={"hnsw:space": "cosine"},
                                                   embedding_function=None)
            vectors = vectors or embed(texts)
            coll.upsert(ids=[p["id"] for p in patterns], embeddings=vectors, documents=texts)
            _memory = dict(zip((p["id"] for p in patterns), vectors))   # reserva, se uma consulta falhar
            _collection, _embed, _backend = coll, embed, "chroma"
        except Exception as e:  # noqa: BLE001
            if RAG_BACKEND != "memoria":
                print(f"[rag] Chroma indisponível ({type(e).__name__}: {str(e).splitlines()[0][:120]}); "
                      "usando o índice em memória (mesmos embeddings locais)")
            _memory = dict(zip((p["id"] for p in patterns), embed_local(texts)))
            _collection, _embed, _backend = None, embed_local, "memoria"


def backend() -> str:
    """"chroma", "memoria" ou "tags" — qual busca está valendo neste processo."""
    _init()
    return _backend


def _similarities(text: str) -> dict[str, float]:
    """id do padrão -> semelhança (0–1) com o texto livre. Vazio no backend "tags"."""
    global _backend
    _init()
    if _backend == "tags" or not text.strip():
        return {}
    try:
        vector = [float(x) for x in _embed([text])[0]]
    except Exception as e:  # noqa: BLE001
        print(f"[rag] embedding da consulta falhou ({type(e).__name__}); usando só tags nesta busca")
        return {}
    if not any(vector):
        return {}
    if _backend == "chroma":
        try:
            with _LOCK:
                res = _collection.query(query_embeddings=[vector], n_results=len(_load()), include=["distances"])
            return {i: 1.0 - d for i, d in zip(res["ids"][0], res["distances"][0])}
        except Exception as e:  # noqa: BLE001 — ex.: chromadb 0.x consultado de outra thread
            print(f"[rag] consulta ao Chroma falhou ({type(e).__name__}); passando para o índice em memória")
            _backend = "memoria"
    # vetores já normalizados: produto escalar = semelhança de cosseno (mesmo resultado do Chroma)
    return {i: sum(a * b for a, b in zip(vector, doc)) for i, doc in _memory.items()}


# ---------- Busca ----------
def search_patterns(query: str | list[str], k: int = 3) -> list[dict]:
    """`query`: texto livre ou lista de termos (códigos de sinal, ação, contexto da transação).
    Devolve até k padrões {id, title, tags, keywords, description}, do mais para o menos parecido."""
    items = [query] if isinstance(query, str) else [q for q in query if q]
    text = _norm(" ".join(items))
    terms = {_norm(i) for i in items} | set(re.findall(r"[a-z0-9_]+", text))
    free_text = " ".join(i for i in items if " " in i.strip())      # frases; termos soltos são tags
    sims = _similarities(free_text)

    scored = []
    for pos, p in enumerate(_load()):
        score = sum(TAG_WEIGHT if t.isupper() else ACTION_WEIGHT for t in p["tags"] if _norm(t) in terms)
        hits = sum(1 for kw in p.get("keywords", []) if re.search(rf"\b{re.escape(_norm(kw))}\b", text))
        score += min(KEYWORD_CAP, hits)
        sim = sims.get(p["id"], 0.0)
        if sim >= MIN_SIMILARITY:
            score += VECTOR_WEIGHT * sim
        if score >= MIN_SCORE:
            scored.append((-score, pos, p))
    if not scored:
        return []
    scored.sort(key=lambda x: x[:2])
    best = -scored[0][0]
    return [p for s, _, p in scored if -s >= best * RELATIVE_CUTOFF][:k]
