"""Confere o LLM real nos 4 cenários: python -m scripts.check_llm (dentro de backend/).
Usa as fixtures (simulação e reputação fixas), então só o LLM depende de rede.
O LLM só escreve a explicação: mostra, por cenário, se o texto veio do modelo, o tempo da decisão
(sem LLM) e o da explicação, e por que caiu para o template."""
import json

from agents import llm
from agents.graph import run
from api import db
from api.config import FIXTURES_DIR, OFFLINE


def main() -> None:
    if OFFLINE or not llm.available():
        raise SystemExit("Defina OFFLINE=0 e OPENROUTER_API_KEY no .env da raiz.")
    db.init_db()
    print(f"modelos (em ordem): {', '.join(llm.MODELS)} · teto da explicação: {llm.BUDGET_S:.0f}s\n")
    used = wrong = 0
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        fx = json.loads(path.read_text(encoding="utf-8"))
        llm._cooldown_until = 0.0            # cada cenário tenta de novo, mesmo se o anterior falhou
        state = run(fx["tx"], db.DEFAULT_POLICIES[fx["tx"]["owner_id"]], fx["offline"])
        v = state["verdict"]
        ok = v["verdict"] == fx["expected"]
        used += v["llm_used"]
        wrong += not ok
        print(f"{'✅' if ok else '❌'} {fx['id']}: {v['verdict']} (esperado {fx['expected']}) · risco {v['risk_score']} · "
              f"texto: {'IA' if v['llm_used'] else 'template'} · decisão {v['timings_ms']['decision']} ms · "
              f"explicação {v['timings_ms']['explain']} ms")
        print(f"   resumo: {v['decoded']['summary_ptbr']}")
        print(f"   explicação: {v['explanation_ptbr']}")
        for e in state["errors"]:
            print(f"   ⚠️  {e}")
        print()
    print(f"{used}/4 cenários com texto do LLM · modelo em uso: {llm.current_model()} · "
          f"formato aceito pelo provedor: {llm._MODES[llm._mode]}")
    if wrong:
        raise SystemExit(f"{wrong} cenário(s) com veredito diferente do esperado")
    if not used:
        raise SystemExit("O LLM não foi usado em nenhum cenário: veja os avisos acima (tempo, limite ou formato).")


if __name__ == "__main__":
    main()
