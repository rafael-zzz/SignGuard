"""Testes herméticos: sem LLM, RPC nem Etherscan, e com um banco temporário (não mexe em data/signguard.db)."""
import os
import tempfile

os.environ["OFFLINE"] = "1"
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="signguard-test-"), "signguard.db")
