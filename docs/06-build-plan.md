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
- [ ] Rafael: grafo LangGraph com nós stub retornando JSON fixo
- [ ] Davi: `SignGuardRegistry` + teste Foundry + deploy Sepolia
- [ ] Davi: preencher casos reais no PRD; rascunho do BMC

## Qui 12/11 — Integração
- [ ] Rafael: decoder e judge com LLM real + saída estruturada; regras de piso em código
- [x] Dávila: `contract_info`, `check_blocklist`, endpoints `/analyze` e `/attest`
- [ ] Rafael: RAG com 10–20 padrões de golpe (approve phishing, drainer, address poisoning, Bybit/Safe)
- [ ] Caio: telas ligadas à API + tela Agente-carteira
- [ ] Dávila + Rafael: `wallet_bot.py` + cenário de prompt injection — parte de Dávila implementada e testada; validação conjunta pendente.
- [ ] Davi: pitch v1 + BMC · Rafael: README (inputs → lógica → outputs) · Caio: slides
- [ ] **Noite:** ensaio ponta a ponta dos 4 cenários + gravar vídeo de backup


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
