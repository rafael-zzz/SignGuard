"""Testes isolados: nunca usam o banco de desenvolvimento nem serviços externos."""
import os
import tempfile
from pathlib import Path

# Antes de importar config/agents, inclusive durante a coleta dos testes existentes.
_TEST_DB = tempfile.TemporaryDirectory(prefix="signguard-tests-")
os.environ["OFFLINE"] = "1"
os.environ["DB_PATH"] = str(Path(_TEST_DB.name) / "tests.db")

os.environ["SIGNGUARD_API_KEYS"] = '{"default":"default-test-key-0000000000000000","agent-wallet":"agent-test-key-000000000000000000","company":"company-test-key-0000000000000000"}'
