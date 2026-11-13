"""Validação sem reescrever rótulos ou metadados do conjunto de avaliação."""
import json
from pathlib import Path

LABELS = ('ALLOW', 'WARN', 'BLOCK')


def load_dataset(path):
    rows, seen = [], set()
    for number, line in enumerate(Path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
        try:
            row = json.loads(line)
            required = {'id', 'expected', 'tx_malicious', 'injection', 'mismatch', 'why', 'tx', 'offline'}
            if not isinstance(row, dict) or not required <= row.keys():
                raise ValueError('campos obrigatórios ausentes')
            if not isinstance(row['id'], str) or not row['id'] or row['id'] in seen:
                raise ValueError('ID inválido ou duplicado')
            if row['expected'] not in LABELS:
                raise ValueError('rótulo inválido')
            for key in ('tx_malicious', 'injection'):
                if type(row[key]) is not bool:
                    raise ValueError(f'{key} deve ser booleano')
            if row['mismatch'] is not None and type(row['mismatch']) is not bool:
                raise ValueError('mismatch deve ser booleano ou null (intenção ambígua)')
            if not isinstance(row['why'], str) or not isinstance(row['tx'], dict):
                raise ValueError('why/tx inválido')
            if not {'from', 'to', 'data', 'value', 'owner_id', 'chain_id'} <= row['tx'].keys():
                raise ValueError('transação incompleta')
            off = row['offline']
            if not isinstance(off, dict) or type(off.get('simulation_ok')) is not bool or not isinstance(off.get('contract_info'), dict):
                raise ValueError('offline inconsistente')
            for info in off['contract_info'].values():
                if any(type(info.get(k)) is not bool for k in ('is_contract', 'verified')) or not isinstance(info.get('age_days'), (int, float)) or info['age_days'] < 0:
                    raise ValueError('contract_info inconsistente')
            seen.add(row['id'])
            rows.append(row)
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError(f'{path}:{number}: {exc}') from exc
    if not rows:
        raise ValueError('dataset vazio')
    return rows
