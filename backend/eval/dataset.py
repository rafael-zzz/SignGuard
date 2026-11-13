"""Validação e categorias do dataset; nunca usa previsões para definir rótulos."""
import json
from pathlib import Path

from api.models import TxInput

DATASET = Path(__file__).with_name("dataset.jsonl")


def categories(row: dict) -> list[str]:
    """Categorias sobrepostas, definidas pelo caso de entrada, não pelo resultado."""
    base, _, context = row["id"].partition("__")
    tags = [base]
    if base.startswith("approve"):
        tags += ["approve", "spenders_diferentes"]
        if row["tx_malicious"]:
            tags.append("approve_malicioso")
    if base.startswith("transfer") or base.startswith("agente"):
        tags.append("variacao_de_valor")
    if base == "swap-legitimo":
        tags.append("swap_legitimo")
    if "blocklist" in base:
        tags.append("blocklist")
    if "fora-do-escopo" in base:
        tags.append("funcao_desconhecida")
    if "simulacao" in base:
        tags.append("falha_de_simulacao")
    if row["tx"].get("context"):
        tags.append("contexto_malicioso" if row["injection"] else "contexto_sem_injecao")
    if context.startswith("benigno"):
        tags.append("contexto_benigno")
    if row["injection"]:
        tags.append("prompt_injection")
    # A nota de auditoria e a alegação de aprovação anterior são conteúdo de
    # terceiros usado para dispensar a verificação (injeção indireta/disfarçada).
    if context in {"injecao-disfarcada", "ja-aprovado"}:
        tags.append("prompt_injection_indireto")
    if context == "conversa-longa":
        tags.append("contexto_longo")
    return sorted(set(tags))


def load_dataset(path: Path = DATASET) -> list[dict]:
    rows, ids = [], set()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row["id"], str) or not row["id"] or row["id"] in ids:
                raise ValueError("id vazio ou duplicado")
            if row["expected"] not in {"ALLOW", "WARN", "BLOCK"}:
                raise ValueError("expected inválido")
            if any(type(row[k]) is not bool for k in ("injection", "tx_malicious")):
                raise ValueError("rótulos injection/tx_malicious devem ser booleanos")
            if not isinstance(row["why"], str) or not row["why"].strip():
                raise ValueError("justificativa de segurança ausente")
            tx = TxInput.model_validate(row["tx"])
            if tx.chain_id != 1 or (row["injection"] and not tx.context):
                raise ValueError("rede fora do escopo ou injeção sem contexto")
            offline = row["offline"]
            if not isinstance(offline, dict) or not isinstance(offline.get("contract_info"), dict):
                raise ValueError("estado simulado ausente")
            if "simulation_ok" not in offline or not any(offline["simulation_ok"] is x for x in (True, False, None)):
                raise ValueError("simulation_ok deve ser true, false ou null")
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
        ids.add(row["id"])
        rows.append(row)
    if not 30 <= len(rows) <= 40:
        raise ValueError(f"dataset deve conter 30–40 casos; encontrados {len(rows)}")
    return rows
