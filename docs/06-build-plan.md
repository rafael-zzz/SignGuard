# 06 — Build Plan · SignGuard

## Papéis
| Papel | Responsável | Foco |
|---|---|---|
| A — Agentes | **Rafael** | LangGraph, prompts, Juiz, RAG, defesa contra prompt injection, seção "fluxo do agente" do README |
| B — Backend/Tools | **Dávila** | FastAPI, Anvil, decode, Etherscan, SQLite, fixtures, bot-carteira |
| C — Front | **Caio** | Telas Analisar, Resultado, Agente-carteira; slides do pitch |
| D — Contrato + Pitch | **Davi** | `SignGuardRegistry`, deploy Sepolia, `/attest` on-chain, BMC, roteiro e apresentação do pitch |

**Regra de paralelismo:** `05-backend-schema.md` é o contrato entre todos. Fechar `TxInput` e `Verdict` hoje de manhã; cada um codifica contra mocks; integração quinta à tarde.

## Qua 11/11 — Fundação
- [ ] Todos: inscrição individual no AVA + curso (chave da edição Nordeste)
- [ ] Davi: repo + estrutura de pastas + `.env.example`
- [ ] Caio: telas Analisar + Resultado com JSON mockado (sem esperar a API)
- [x] Dávila: Anvil fork rodando; `simulate_tx` e `decode_calldata` para ERC-20 `approve/transfer`
- [x] Dávila: 4 fixtures de demo (03-app-flow)
- [x] Rafael: grafo LangGraph com nós stub retornando JSON fixo — superado: o grafo já roda com os nós reais; resposta fixa para o time vem de `OFFLINE=1` + fixtures.
- [ ] Davi: `SignGuardRegistry` + teste Foundry + deploy Sepolia
- [ ] Davi: preencher casos reais no PRD; rascunho do BMC

## Qui 12/11 — Integração
- [ ] Rafael: decoder e judge com LLM real + saída estruturada; regras de piso em código — implementado e testado contra servidor local; **falta rodar com a chave do OpenRouter**.
- [x] Dávila: `contract_info`, `check_blocklist`, endpoints `/analyze` e `/attest`
- [x] Rafael: RAG com 10–20 padrões de golpe (approve phishing, drainer, address poisoning, Bybit/Safe) — 16 padrões, busca no Chroma com queda para tags.
- [ ] Caio: telas ligadas à API + tela Agente-carteira
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

## Sex 13/11 — Dia do hackathon
| Horário | Atividade |
|---|---|
| 08h00 | Credenciamento, setup, checar `.env` e Wi-Fi (hotspot reserva) |
| até 10h | Corrigir bugs do ensaio; cache dos cenários (`OFFLINE=1`) |
| 10h–12h | P1: tela de Políticas, Forense mock ou `PolicyGuard` (escolher 1) |
| 12h–13h | Mentoria: validar pitch e BMC |
| 13h–14h30 | Polimento da UI, README, prints/GIF |
| 14h30–15h | Ensaio do pitch (3 min cronometrado) |
| **15h00** | Submeter tudo (margem de 30 min) |
| 15h30 | 🔒 Congelamento |

## Lista de corte (se atrasar, corta nessa ordem)
1. Forense
2. `PolicyGuard` on-chain
3. Tela de Políticas (usa JSON fixo)
4. RAG (Ameaças só com regras + Etherscan)
5. Simulação real (usa fixtures)

**Nunca cortar:** veredito explicado em PT-BR, cenário de prompt injection, atestado on-chain.

## Roteiro do pitch (3 min)
1. **0:00–0:30** Dor: Bybit US$ 1,5 bi por blind signing + golpe real no Brasil.
2. **0:30–0:50** Solução: camada de agentes antes da assinatura; IA só veta.
3. **0:50–2:10** Demo: approve malicioso bloqueado → agente manipulado bloqueado → atestado no explorer.
4. **2:10–2:40** Negócio: B2B via API para exchanges/fintechs/PSAVs + reputação pública on-chain.
5. **2:40–3:00** Próximos passos e pedido.

## Checklist de entrega
- [ ] Protótipo (demo ao vivo + vídeo)
- [ ] BMC atualizado
- [ ] Pitch 3 min
- [ ] README: inputs, lógica dos agentes, outputs, como rodar, endereço do contrato
