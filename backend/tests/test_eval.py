from pathlib import Path
import json
import pytest
from eval.dataset import load_dataset
from eval.replay import replay_inputs
from scripts.eval import prf

DATASET = Path(__file__).parents[1] / 'eval/dataset.jsonl'


def test_sixty_cases():
    assert len(load_dataset(DATASET)) == 60


@pytest.mark.parametrize('field,value', [('expected', 'INVALID'), ('injection', 1)])
def test_invalid(tmp_path, field, value):
    row = load_dataset(DATASET)[0]
    row[field] = value
    path = tmp_path / 'data.jsonl'
    path.write_text(json.dumps(row), encoding='utf-8')
    with pytest.raises(ValueError):
        load_dataset(path)


def test_duplicate(tmp_path):
    row = load_dataset(DATASET)[0]
    path = tmp_path / 'data.jsonl'
    path.write_text((json.dumps(row) + '\n') * 2, encoding='utf-8')
    with pytest.raises(ValueError):
        load_dataset(path)


def test_utf8(tmp_path):
    path = tmp_path / 'data.jsonl'
    path.write_bytes(b'\xef\xbb\xbf' + DATASET.read_bytes().replace(b'\n', b'\r\n'))
    assert load_dataset(path) == load_dataset(DATASET)


def test_metrics():
    result = prf([(True, True), (False, True), (True, False)])
    assert result['precision'] == result['recall'] == .5


def test_replay_copy():
    row = load_dataset(DATASET)[0]
    row['offline']['jev'] = {'model': 'test', 'latency_ms': 123}
    tx, offline = replay_inputs(row)
    assert offline['jev'] == {'model': 'test'}
    assert row['offline']['jev']['latency_ms'] == 123
    assert tx == row['tx']
