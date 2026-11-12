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
LLM_MODEL = env("LLM_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
LLM_TIMEOUT = float(env("LLM_TIMEOUT", "20"))

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
