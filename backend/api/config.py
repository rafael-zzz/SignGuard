import os
import math
from pathlib import Path

try:
    from dotenv import load_dotenv  # opcional
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]          # backend/
DATA_DIR = ROOT / "data"
FIXTURES_DIR = ROOT / "demo" / "fixtures"


def env(name: str, default: str | None = None) -> str | None:
    v = os.getenv(name)
    return v if v not in (None, "") else default


OFFLINE = env("OFFLINE", "0") == "1"

# LLM via OpenRouter (API compatível com OpenAI)
LLM_API_KEY = env("OPENROUTER_API_KEY")
LLM_BASE_URL = env("LLM_BASE_URL", "https://openrouter.ai/api/v1")
# Um modelo ou vários separados por vírgula: se o primeiro deixar de existir (os :free mudam), usa o próximo.
LLM_MODEL = env("LLM_MODEL", "google/gemma-4-26b-a4b-it")
# O LLM só redige a explicação, depois que o veredito já foi decidido em código (docs/07 §5).
# Teto da chamada de explicação: no máximo 4 s, mesmo que o .env peça mais. Estourou -> texto do template.
LLM_TIMEOUT = min(float(env("LLM_TIMEOUT", "4")), 4.0)

# Classificador Jev (TypeSafe AI): probabilidade calibrada para o texto do contexto (docs/07 §4).
# Sem chave -> fica desligado e vale só o regex. A versão é fixada: entra no relatório atestado.
TYPESAFE_API_KEY = env("TYPESAFE_API_KEY")
JEV_MODEL = env("JEV_MODEL", "jev-1.14.0")
JEV_TIMEOUT = float(env("JEV_TIMEOUT", "2"))
# Por onde chamar o Jev. É o mesmo modelo e a mesma API System One nos dois caminhos:
#   typesafe   = api.typesafe.ai com TYPESAFE_API_KEY (modelo JEV_MODEL)
#   openrouter = openrouter.ai/api/v1/systemone com a OPENROUTER_API_KEY (modelo JEV_OPENROUTER_MODEL)
#   off        = só regex
# Padrão (auto): typesafe se houver chave; senão openrouter se houver chave; senão off.
JEV_BACKEND = (env("JEV_BACKEND", "auto") or "auto").lower()
# Versão fixada. Não use `~typesafe/jev-latest` nem `typesafe/jev-router` (este é um roteador de LLM de chat).
JEV_OPENROUTER_MODEL = env("JEV_OPENROUTER_MODEL", "typesafe/jev-1.14")
if JEV_OPENROUTER_MODEL == "typesafe/jev-router":   # valor de um .env antigo: não é o classificador
    print("[config] JEV_OPENROUTER_MODEL=typesafe/jev-router é um roteador de chat, não o Jev; usando typesafe/jev-1.14")
    JEV_OPENROUTER_MODEL = "typesafe/jev-1.14"

# RAG (padrões de golpe): "chroma" (cai para "tags" se o chromadb faltar ou falhar) ou "tags"
RAG_BACKEND = env("RAG_BACKEND", "chroma")
RAG_EMBEDDINGS = env("RAG_EMBEDDINGS", "local")     # "local" (sem download) ou "minilm" (modelo ONNX do Chroma)

# Blockchain
MAINNET_RPC_URL = env("MAINNET_RPC_URL")            # ou http://127.0.0.1:8545 (anvil --fork-url ...)
SEPOLIA_RPC_URL = env("SEPOLIA_RPC_URL")
ETHERSCAN_API_KEY = env("ETHERSCAN_API_KEY")
ATTESTER_PRIVATE_KEY = env("ATTESTER_PRIVATE_KEY")
REGISTRY_ADDRESS = env("REGISTRY_ADDRESS")
SEPOLIA_EXPLORER = env("SEPOLIA_EXPLORER", "https://sepolia.etherscan.io")

# Preço fixo para a demo (sem oráculo)
ETH_USD = float(env("ETH_USD", "3000"))
if not math.isfinite(ETH_USD) or ETH_USD <= 0:
    raise ValueError("ETH_USD deve ser positivo e finito")

DB_PATH = env("DB_PATH", str(DATA_DIR / "signguard.db"))
