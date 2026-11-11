"""Testes isolados: nunca usam o banco de desenvolvimento nem serviços externos."""
import os
import tempfile
from pathlib import Path

# Antes de importar config/agents, inclusive durante a coleta dos testes existentes.
_TEST_DB = tempfile.TemporaryDirectory(prefix="signguard-tests-")
os.environ["OFFLINE"] = "1"
os.environ["DB_PATH"] = str(Path(_TEST_DB.name) / "tests.db")
