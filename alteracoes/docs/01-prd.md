# 01 — PRD · SignGuard

> Agentes de IA que protegem quem assina transações em blockchain — pessoas ou outros agentes de IA.
> Hackathon AKCIT Camp Nordeste · 13/11/2026 · CESAR School · congelamento 15h30

## 1. Problema
- **Blind signing:** em 2025 a Bybit perdeu ~US$ 1,5 bi porque os signatários aprovaram uma transação que não conseguiam ler.
- **Golpes no varejo BR:** contratos falsos, `approve` ilimitado de tokens, sites clonados.
- **Regulação:** com os PSAVs regulados pelo Banco Central, exchanges e fintechs precisam provar diligência sobre transações.
- **Risco novo:** agentes de IA com carteira própria podem ser manipulados por prompt injection e esvaziar fundos.
- **Casos reais:** _[preencher com 1–2 casos da comunidade Bybit / faculdade]_

## 2. Solução
Camada entre quem assina e a blockchain. Antes da assinatura, um time de agentes analisa a transação e devolve um veredito **PERMITIR / ALERTAR / BLOQUEAR** com explicação em português. O veredito é registrado on-chain como atestado auditável. A IA **só pode vetar, nunca mover fundos**.

## 3. Público
| Segmento | Dor | Como usa |
|---|---|---|
| Usuário cripto (B2C) | Não entende o que assina | Cola a transação / link e recebe explicação |
| Exchanges, fintechs, PSAVs (B2B) | Diligência, multisig, compliance | API/SDK antes de assinar + trilha de auditoria |
| Agentes de IA com carteira | Prompt injection | Chamam a API antes de assinar; veto obrigatório |

## 4. Agentes
| Agente | Faz | No MVP |
|---|---|---|
| Decodificador | Simula a tx e explica em PT-BR o efeito real | ✅ |
| Ameaças | Checa contrato/endereços: idade, verificação, blocklist, padrões de exploit (RAG) | ✅ |
| Política | Aplica regras (limite, allowlist, horário) de forma determinística | ✅ |
| Juiz | Consolida evidências em veredito + score de risco | ✅ |
| Forense | Rastreia fundos pós-incidente e gera relatório | 🟡 demo/mock |

## 5. Escopo do MVP
**Dentro**
- Entrada: transação EVM bruta (to, data, value, from) ou exemplo pré-carregado.
- Simulação em fork da mainnet + decodificação de calldata.
- Explicação em PT-BR + score 0–100 + veredito.
- Políticas configuráveis (JSON) aplicadas em código.
- Atestado on-chain em testnet (`SignGuardRegistry`).
- Demo de agente-carteira sofrendo prompt injection e sendo bloqueado.

**Fora (roadmap)**
- Extensão de navegador / integração com Safe Guard.
- Multichain real e rastreio cross-chain completo.
- Base rotulada de golpes brasileiros.
- `PolicyGuard` on-chain completo (P1 se sobrar tempo).

## 6. Histórias de usuário
1. Como usuário, colo uma transação e entendo em 1 frase o que ela faz.
2. Como usuário, sou alertado quando dou permissão ilimitada a um contrato recém-criado.
3. Como empresa, defino limites e allowlist e qualquer violação é bloqueada.
4. Como agente de IA, consulto o SignGuard antes de assinar e sou impedido mesmo se meu prompt foi manipulado.
5. Como auditor, consulto on-chain o veredito dado a uma transação.

## 7. Requisitos não funcionais
- Latência alvo: < 15 s por análise (demo).
- Dados da transação **nunca** são tratados como instrução pelos LLMs.
- Política decidida por código, não por LLM.
- Toda decisão com evidências rastreáveis (o que cada agente viu).

## 8. Métricas de sucesso (hackathon)
- 3 de 3 cenários de demo com veredito correto.
- Ataque de prompt injection bloqueado ao vivo.
- Atestado visível no explorer da testnet.
- Entregáveis submetidos antes de 15h30.

## 9. Riscos e gaps
- Falsos positivos e latência.
- Ausência de dados rotulados de golpes brasileiros.
- Segurança dos próprios agentes contra prompt injection.
- Validação B2B com exchanges/fintechs.

## 10. Entregáveis AKCIT
1. Protótipo funcional (demo ao vivo + vídeo de backup)
2. BMC atualizado
3. Pitch de 3 min
4. README com fluxo do agente (inputs → lógica → outputs)
