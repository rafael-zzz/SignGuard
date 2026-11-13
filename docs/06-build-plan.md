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
- [x] Rafael: grafo LangGraph com nós stub retornando JSON fixo
- [x] Davi: `SignGuardRegistry` + teste Foundry + deploy Sepolia ([`0x1652…059B`](https://sepolia.etherscan.io/address/0x1652D6a7bbE1980df629322B5b2D7c3AA902059B#code), atestado testado ponta a ponta)
- [ ] Davi: preencher casos reais no PRD; rascunho do BMC

## Qui 12/11 — Integração
- [ ] Rafael: decoder e judge com LLM real + saída estruturada; regras de piso em código. Versão base na `main`; versão do Rafael (`feat/agents`) aguardando PR.
- [x] Dávila: `contract_info`, `check_blocklist`, endpoints `/analyze` e `/attest`
- [ ] Rafael: RAG com 10–20 padrões de golpe (approve phishing, drainer, address poisoning, Bybit/Safe). A `main` tem 8; `feat/agents` tem 16, aguardando PR.
- [x] Caio: telas ligadas à API + tela Agente-carteira (PR #1)
- [ ] Dávila + Rafael: `wallet_bot.py` + cenário de prompt injection — parte de Dávila implementada e testada; validação conjunta pendente.
- [ ] Davi: pitch v1 + BMC · Rafael: README (inputs → lógica → outputs) · Caio: slides
- [ ] **Noite:** ensaio ponta a ponta dos 4 cenários + gravar vídeo de backup


## Sex 13/11 — Dia do hackathon (replanejado após o feedback do jurado)
Detalhes, motivos e código de referência em **[07-alinhamento-jurado.md](07-alinhamento-jurado.md)**.

**Passo 0:** Rafael faz o merge da `feat/agents` → `main` antes de qualquer outra coisa.

- [ ] Davi: pedir a chave do Jev (TypeSafe AI) ao jurado e colocar `TYPESAFE_API_KEY` no `.env`
- [ ] Rafael: merge `feat/agents` → `main`
- [ ] Rafael: `judge.py` — LLM não altera veredito nem risco; BLOCK só por regra
- [ ] Rafael: `decoder.py` — remover a chamada de LLM (fica o template)
- [ ] Dávila: `timings_ms` por nó + campo no `Verdict`
- [ ] Dávila: testes de propriedade (determinismo, invariância ao contexto, teto do probabilístico, LLM não rebaixa)
- [ ] Dávila: `backend/eval/dataset.jsonl` (30–40 casos) + `scripts/eval.py` (matriz, falso-PERMITIR = 0, p50/p95)
- [ ] Davi: README — envelope de garantia + "o que não garantimos"
- [ ] Davi: slides "o probabilístico só filtra, o determinístico decide" + evidências (números do eval)
- [ ] Rafael (P1): `tools/jev.py` + sinais `PROMPT_INJECTION` / `INTENT_MISMATCH` / `CLASSIFIER_UNAVAILABLE` (teto ALERTAR)
- [ ] Dávila (P1): gravar respostas do Jev em `offline.jev` nas fixtures; rodar o eval com o Jev e fixar os limiares
- [ ] Davi (P1): UI com selo REGRA / CLASSIFICADOR por motivo + tempo da análise

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
