"""Rastreio de fundos pós-incidente (Agente Forense). Dono: Rafael.
Interface (docs/05-backend-schema.md §6): trace_funds(tx_hash) -> hops. Fonte no MVP: mock.

A rota é SIMULADA: os endereços e valores são derivados do próprio hash, então o mesmo hash
sempre gera o mesmo relatório, mas nada aqui foi lido da blockchain. O rastreio real
(Etherscan / cross-chain) está no roadmap (PRD §5) e entra trocando o corpo desta função."""
import re

from eth_utils import keccak

from tools.decode import fmt_br

TX_HASH = re.compile(r"^0x[0-9a-fA-F]{64}$")


def _derive(seed: bytes, label: str) -> bytes:
    return keccak(seed + label.encode())


def trace_funds(tx_hash: str) -> list[dict]:
    """Saltos {step, from, from_label, to, to_label, token, amount, tx_hash, minutes_after}, em ordem."""
    if not isinstance(tx_hash, str) or not TX_HASH.match(tx_hash):
        raise ValueError("tx_hash inválido: esperado 0x seguido de 64 caracteres hexadecimais")
    seed = bytes.fromhex(tx_hash[2:])

    def addr(label: str) -> str:
        return "0x" + _derive(seed, label)[-20:].hex()

    total = 1_000 + int.from_bytes(_derive(seed, "valor")[:4], "big") % 49_000     # 1.000 a 49.999 USDT
    part_a = total * 6 // 10
    part_b = total - part_a
    victim, scammer = addr("vitima"), addr("golpista")
    mule_a, mule_b = addr("intermediaria-a"), addr("intermediaria-b")
    route = [
        (victim, "Carteira da vítima", scammer, "Endereço do golpista", total, tx_hash, 0),
        (scammer, "Endereço do golpista", mule_a, "Carteira intermediária A", part_a, None, 4),
        (scammer, "Endereço do golpista", mule_b, "Carteira intermediária B", part_b, None, 6),
        (mule_a, "Carteira intermediária A", addr("exchange"), "Depósito em exchange centralizada", part_a, None, 31),
        (mule_b, "Carteira intermediária B", addr("bridge"), "Ponte para outra rede (bridge)", part_b, None, 47),
    ]
    return [
        {"step": i, "from": src, "from_label": src_label, "to": dst, "to_label": dst_label,
         "token": "USDT", "amount": fmt_br(amount, 2),
         "tx_hash": h or "0x" + _derive(seed, f"salto-{i}").hex(), "minutes_after": minutes}
        for i, (src, src_label, dst, dst_label, amount, h, minutes) in enumerate(route, start=1)
    ]
