# 06 — Build Plan · SignGuard

## Papéis
| Papel | Responsável | Foco |
|---|---|---|
| A — Agentes | **Rafael** | LangGraph, prompts, Juiz, RAG, defesa contra prompt injection, README "fluxo do agente" · **hoje:** Jev no Ameaças, LLM fora da decisão (ver [07](07-alinhamento-jurado.md)) |
| B — Backend/Evidências | **Dávila** | FastAPI, Anvil, decode, Etherscan, SQLite, fixtures, bot-carteira · **hoje:** latência por nó, eval, testes de propriedade |
| C+D — Front, Contrato e Pitch | **Davi** | Assume o front do Caio (que saiu do time em 13/11) + `SignGuardRegistry`, BMC, pitch |

**Regra de paralelismo:** `05-backend-schema.md` é o contrato entre todos. Fechar `TxInput` e `Verdict` hoje de manhã; cada um codifica contra mocks; integração quinta à tarde.

## Qua 11/11 — Fundação
- [ ] Todos: inscrição individual no AVA + curso (chave da edição Nordeste)
- [x] Davi: repo + estrutura de pastas + `.env.example`
- [x] Caio: telas Analisar + Resultado com JSON mockado (sem esperar a API)
- [x] Dávila: Anvil fork rodando; `simulate_tx` e `decode_calldata` para ERC-20 `approve/transfer`
- [x] Dávila: 4 fixtures de demo (03-app-flow)
- [x] Rafael: grafo LangGraph com nós stub retornando JSON fixo — superado: o grafo já roda com os nós reais; resposta fixa para o time vem de `OFFLINE=1` + fixtures.
- [x] Davi: `SignGuardRegistry` + teste Foundry + deploy Sepolia ([`0x1652…059B`](https://sepolia.etherscan.io/address/0x1652D6a7bbE1980df629322B5b2D7c3AA902059B#code), atestado testado ponta a ponta)
- [ ] Davi: preencher casos reais no PRD; rascunho do BMC

## Qui 12/11 — Integração
- [ ] Rafael: decoder e judge com LLM real + saída estruturada; regras de piso em código — implementado e testado contra servidor local; **falta rodar com a chave do OpenRouter**.
- [x] Dávila: `contract_info`, `check_blocklist`, endpoints `/analyze` e `/attest`
- [x] Rafael: RAG com 10–20 padrões de golpe (approve phishing, drainer, address poisoning, Bybit/Safe) — 16 padrões, busca no Chroma com queda para tags.
- [x] Caio: telas ligadas à API + tela Agente-carteira (PR #1)
- [x] Dávila + Rafael: `wallet_bot.py` + cenário de prompt injection — integrado e validado ponta a ponta contra a API (pagamento normal permitido, injeção bloqueada).
- [ ] Davi: pitch v1 + BMC · Rafael: README (inputs → lógica → outputs) ✅ · Caio: slides
- [ ] **Noite:** ensaio ponta a ponta dos 4 cenários + gravar vídeo de backup

### Entregue — papel A (Agentes), atualizado em 12/11
Verificação: `pytest -q` em `backend/` (200 testes: agentes, backend, segurança e os 4 cenários), sem LLM, RPC nem Etherscan.
Os 18 requisitos de integração marcados `dependency_rafael` em `tests/test_security.py` passam e voltaram para a execução padrão.

| Item | Onde | Situação |
|---|---|---|
| Grafo `decoder → (threat ∥ policy) → judge` | `agents/graph.py` | ✅ entregue |
| Decodificador: fatos por código, LLM só reescreve o resumo | `agents/decoder.py` | ✅ entregue |
| Ameaças: sinais com peso + evidências do que foi consultado | `agents/threat.py` | ✅ entregue |
| Política determinística (5 regras do schema §4) | `agents/policy.py` | ✅ entregue |
| Juiz: regras do TRD §4 em código; LLM só sobe o risco | `agents/judge.py` | ✅ entregue |
| Saída estruturada: schema, 1 nova tentativa, queda para regras | `agents/llm.py`, `agents/prompts.py` | ✅ entregue |
| Orçamento de 6 s de LLM por análise (TRD §7) | `agents/llm.py` (`LLM_TIMEOUT`) | ✅ entregue |
| Defesa contra prompt injection (5 itens do TRD §5) | `agents/prompts.py`, `agents/threat.py`, `demo/wallet_bot.py` | ✅ entregue |
| RAG: 16 padrões, Chroma + embeddings, queda para tags | `tools/rag.py`, `data/patterns.json` | ✅ entregue — embeddings locais por padrão |
| Agente Forense (mock) + `POST /forensic` | `agents/forensic.py`, `tools/trace.py` | ✅ entregue — rota simulada, `mocked: true` |
| Bot-carteira integrado ao backend com autenticação | `demo/wallet_bot.py` | ✅ entregue |
| Seção "fluxo do agente" do README | `README.md` | ✅ entregue |
| Script para conferir o LLM real nos 4 cenários | `scripts/check_llm.py` | ✅ entregue — ainda não executado com rede |

Requisitos de integração (Dávila, `dependency_rafael`) atendidos em 12/11:
- Função não identificada tem piso de ALERTAR, mesmo com score abaixo de 40.
- Saída crua do LLM (`llm.chat_json`) sempre passa pelo schema; texto que manda assinar é descartado quando o veredito não é PERMITIR.
- Idade mínima do contrato vale para todo contrato envolvido, inclusive os conhecidos; contrato com idade não confirmada viola a política.
- Token sem preço ou sem decimais conhecidos: o limite em USD não pode ser conferido → ALERTAR via `policy.warnings[]` (alterado em 13/11; antes era violação → BLOQUEAR).
- Em swap, a allowlist cobre também a carteira que recebe a saída, quando não é o remetente.
- `allowed_hours` é conferido em UTC.
- ETH enviado direto a um contrato vira ação `unknown` (nunca PERMITIR).
- Blocklist cobre o caminho do swap, o token e a origem do `transferFrom`.
- `increaseAllowance` viola a política de permissões ilimitadas (o valor final não é conhecido).

Pendente no papel A:
- **LLM real**: nenhuma chamada foi feita a um modelo do OpenRouter (o ambiente de desenvolvimento usado não alcança a rede). Rodar `python -m scripts.check_llm` em `backend/` com o `.env` preenchido: confere aceitação do `json_schema`, tempo dentro dos 6 s e o texto gerado.
- **Embeddings neurais** (`RAG_EMBEDDINGS=minilm`): caminho implementado, não executado (exige download de ~80 MB).
- **Simulação real**: os agentes não foram exercitados contra o Anvil; só com fixtures.
- **Tela Forense** no front: o endpoint e o cliente (`getForensic`) existem, a tela não.

Efeitos a conhecer antes da demo:
- Com RPC configurado e **sem** `ETHERSCAN_API_KEY`, o contrato é reconhecido mas a idade não; com `min_contract_age_days > 0` isso bloqueia a transação. Preencher a chave ou usar fixtures.
- Horário permitido é UTC: `[8, 22]` equivale a 5h–19h em Recife.

## Sex 13/11 — Dia do hackathon (replanejado após o feedback do jurado)
Detalhes, motivos e código de referência em **[07-alinhamento-jurado.md](07-alinhamento-jurado.md)**.

**Passo 0:** Rafael faz o merge da `feat/agents` → `main` antes de qualquer outra coisa.

- [x] Davi: pedir a chave do Jev (TypeSafe AI) ao jurado e colocar `TYPESAFE_API_KEY` no `.env` — dispensado: o Jev roda pelo OpenRouter com a `OPENROUTER_API_KEY`
- [ ] Rafael: merge `feat/agents` → `main` — feito na branch `feat/jev-implentation` (conflitos resolvidos); falta o PR para a `main`
- [x] Rafael: `judge.py` — LLM não altera veredito nem risco; BLOCK só por regra (o LLM virou o nó `explain`, depois do veredito)
- [x] Rafael: `decoder.py` — remover a chamada de LLM (fica o template)
- [x] Dávila: `timings_ms` por nó + campo no `Verdict` (+ `latency_ms` no `/health`)
- [x] Dávila: testes de propriedade (determinismo, invariância ao contexto, teto do probabilístico, LLM não rebaixa) — `tests/test_properties.py`
- [x] Dávila: `backend/eval/dataset.jsonl` (60 casos) + `backend/scripts/eval.py` (matriz, falso-PERMITIR = 0, p50/p95) — rodar com `python -m scripts.eval`
- [x] Davi: README — envelope de garantia + "o que não garantimos" + números do eval offline
- [ ] Davi: slides "o probabilístico só filtra, o determinístico decide" + evidências (números do eval)
- [x] Rafael (P1): `tools/jev.py` + sinais `PROMPT_INJECTION` / `INTENT_MISMATCH` / `CLASSIFIER_UNAVAILABLE` (teto ALERTAR) — testado com respostas simuladas; Jev real chamado pelo OpenRouter (`/api/v1/systemone`, modelo `typesafe/jev-1.14`) com a `OPENROUTER_API_KEY`; eval ao vivo (60 casos): 60/60, recall e precisão de injeção 100%, decisão p50 530 ms
- [ ] Dávila (P1): gravar respostas do Jev em `offline.jev` nas fixtures (`python -m scripts.eval --live --record-jev`) — pendente. Eval com o Jev rodou (`eval/results-live-jev.json`) e o limiar de injeção foi fixado em 0,90
- [x] Davi (P1): UI com selo REGRA / CLASSIFICADOR por motivo + tempo da análise

| Horário | Atividade |
|---|---|
| até 10h30 | Passo 0 + P0 de cada um |
| 10h30–12h | P1 (Jev, fixtures offline, selos na UI) |
| 12h–13h | Mentoria: validar a narrativa "probabilístico filtra, determinístico decide" |
| 13h–14h | Rodar o eval final, colocar os números nos slides, README |
| 14h–14h30 | Ensaio ponta a ponta dos 4 cenários + vídeo de backup |
| 14h30–15h | Ensaio do pitch (3 min cronometrado) |
| **15h00** | Submeter tudo (margem de 30 min) |
| 15h30 | 🔒 Congelamento |

## Lista de corte (se atrasar, corta nessa ordem)
1. Forense
2. `PolicyGuard` on-chain
3. Tela de Políticas (usa JSON fixo)
4. Pergunta de categoria de golpe no Jev (P2)
5. Selos REGRA/CLASSIFICADOR na UI (mostrar no JSON)
6. Simulação real (usa fixtures)

**Nunca cortar:** BLOCK só por regra, números do eval, latência medida, veredito explicado em PT-BR, cenário de prompt injection, atestado on-chain.

## Roteiro do pitch (3 min)
1. **0:00–0:30** Dor: Bybit US$ 1,5 bi por blind signing + golpe real no Brasil.
2. **0:30–0:50** Solução: camada antes da assinatura. O probabilístico (Jev) só filtra e o determinístico decide. A IA nunca move fundos.
3. **0:50–1:50** Demo: approve malicioso bloqueado por regra → agente manipulado barrado (selo CLASSIFICADOR 0,9x + regra de limite) → atestado no explorer.
4. **1:50–2:20** Por que confiar: escopo garantido, falso-PERMITIR = 0 no eval, mesma tx → mesmo veredito, decisão em X ms.
5. **2:20–2:45** Negócio: B2B via API para exchanges/fintechs/PSAVs + reputação pública on-chain.
6. **2:45–3:00** Próximos passos e pedido.

## Checklist de entrega
- [ ] Protótipo (demo ao vivo + vídeo)
- [ ] BMC atualizado
- [ ] Pitch 3 min
- [ ] README: inputs, lógica dos agentes, outputs, como rodar, endereço do contrato
- [ ] README: envelope de garantia, limites, números do eval e latência
