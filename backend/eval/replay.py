"""Replay isolado de entradas offline; não altera agentes nem metadados originais."""
from copy import deepcopy


def replay_inputs(row):
    tx, offline = deepcopy(row['tx']), deepcopy(row['offline'])
    # Tempo registrado é evidência histórica, nunca tempo medido no replay.
    if isinstance(offline.get('jev'), dict):
        offline['jev'].pop('latency_ms', None)
    return tx, offline


def provenance(row, classifier, live=False):
    if not classifier or classifier.get('status') != 'ok':
        return 'unavailable'
    if 'jev' in row['offline']:
        return row['offline'].get('jev_provenance', 'recorded_unverified')
    return 'live' if live else 'synthetic'
