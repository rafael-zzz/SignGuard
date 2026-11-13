from agents.graph import _timed, percentile


def test_percentiles():
    assert percentile(list(range(1, 101)), 50) == 50
    assert percentile(list(range(1, 101)), 95) == 95
    assert percentile([], 50) == 0


def test_elapsed_decision(monkeypatch):
    ticks = iter([10., 10.025])
    monkeypatch.setattr('agents.graph.time.perf_counter', lambda: next(ticks))
    out = _timed('judge', lambda state: {})({'t0': 9.9, 'timings': {'threat': 80, 'policy': 80}})
    assert out['timings'] == {'judge': 25, 'decision': 125}
