"""Testes isolados: nunca usam o banco de desenvolvimento nem serviços externos."""
import os
import tempfile
from pathlib import Path

import pytest

# Antes de importar config/agents, inclusive durante a coleta dos testes existentes.
_TEST_DB = tempfile.TemporaryDirectory(prefix="signguard-tests-")
os.environ["OFFLINE"] = "1"
os.environ["SIGNGUARD_DEMO_MODE"] = "0"
os.environ["DB_PATH"] = str(Path(_TEST_DB.name) / "tests.db")

os.environ["SIGNGUARD_API_KEYS"] = '{"default":"default-test-key-0000000000000000","agent-wallet":"agent-test-key-000000000000000000","company":"company-test-key-0000000000000000"}'


@pytest.fixture(scope="session", autouse=True)
def initialize_rag_on_session_thread():
    """Mantém vivo o SQLite em memória do Chroma durante toda a suíte.

    Chroma 0.x guarda conexões por thread e referências fracas no pool. Se a
    primeira conexão nasce num worker descartável do LangGraph, o banco pode
    desaparecer após a coleta de lixo (no such table: collections). Inicializar
    no thread da sessão mantém a conexão; não substitui o RAG nem seus testes.
    """
    from tools import rag
    rag.backend()
