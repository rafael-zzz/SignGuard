# 04 — Design Brief · SignGuard

## Objetivo
Em 5 segundos, qualquer pessoa entende **o que a transação faz** e **se deve assinar**.

## Princípios
1. Veredito primeiro, detalhes depois.
2. Linguagem humana, sem jargão ("permissão ilimitada", não "approve MAX_UINT256").
3. Toda afirmação com evidência clicável.
4. Transmitir confiança e segurança, não medo.

## Telas (MVP)
**1. Analisar**
- Campo para colar transação (to / data / value / from) ou link.
- Botões de exemplo: "Golpe de approve", "Swap legítimo", "Endereço suspeito", "Agente manipulado".
- CTA: **Analisar antes de assinar**.

**2. Resultado**
- Selo grande: 🟢 PERMITIR / 🟡 ALERTAR / 🔴 BLOQUEAR + score 0–100.
- Frase-resumo em PT-BR (output do Decodificador).
- Cards por agente (Decodificador, Ameaças, Política) com status e evidências.
- "Mudanças de saldo" simuladas (antes → depois).
- Botão **Registrar atestado on-chain** → link do explorer.

**3. Políticas**
- Toggles e campos: limite por transação, allowlist, horário, bloquear approve ilimitado.

**4. Agente-carteira (demo)**
- Chat do bot à esquerda, painel SignGuard à direita mostrando o bloqueio em tempo real.

**5. Forense (opcional)**
- Hash → relatório em markdown + botão copiar.

## Identidade visual
Fonte da verdade: **[design-system.md](design-system.md)** (tokens em `web/app/globals.css`, componentes base em `web/components/ui.tsx`).
- Nome: **SignGuard**. Ícone: escudo.
- Monocromático de alto contraste: header preto com grain (`ink-950`) + "sheet" branca (`paper`) subindo por cima com raio 28px.
- Cor **só no status**: verde `#22B55A` (Permitir), âmbar `#F5A524` (Alertar), vermelho `#E5484D` (Bloquear). Todo o resto preto/branco; saídas de saldo em preto, não vermelho.
- Tipografia: Instrument Serif (títulos display), Manrope (UI), JetBrains Mono (endereços/hashes).
- Endereços sempre truncados `0x1234…abcd` com copiar.

## Tom de voz
Direto e calmo. Ex.: "Esta transação dá ao contrato X permissão para gastar **todos** os seus USDT. O contrato foi criado há 2 horas e não é verificado. **Não assine.**"

## Para o pitch
- Print da tela Resultado com BLOQUEAR.
- GIF do Fluxo 3 (prompt injection bloqueado).
