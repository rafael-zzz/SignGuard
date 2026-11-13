# Design System — extraído das referências ("Bank Smarter")

## 1. Conceito
- **Monocromático de alto contraste**: preto absoluto (marca, onboarding, header) + branco puro (conteúdo, folhas/sheets).
- **Camadas**: fundo escuro com textura granulada → "sheet" branca sobe por cima com cantos grandes. Hierarquia vem de camadas, não de cor.
- **Cor só para significado**: verde = entrada/sucesso; vermelho só no pin do mapa. Valores negativos ficam em **preto** (não vermelho).
- **Editorial + utilitário**: título serifado fino no onboarding; resto em sans-serif geométrica, limpa.
- Sem divisórias, sem sombras pesadas: espaço em branco separa os grupos.

## 2. Cores

### Escuras (superfícies de marca)
| Token | Hex | Uso |
|---|---|---|
| `ink-1000` | `#000000` | Fundo onboarding, tab bar |
| `ink-950` | `#0A0A0A` | Fundo do app / header |
| `ink-900` | `#141414` | Superfície elevada escura (mapa) |
| `ink-850` | `#1C1C1E` | Botões pill no header |
| `ink-border` | `rgba(255,255,255,0.14)` | Borda de botões no escuro |
| `on-dark` | `#FFFFFF` | Texto primário no escuro |
| `on-dark-muted` | `#8A8A8E` | Texto de apoio no escuro |
| `on-dark-subtle` | `#5C5C60` | Ícones inativos (tab bar) |

### Claras (conteúdo)
| Token | Hex | Uso |
|---|---|---|
| `paper` | `#FFFFFF` | Sheets, modais |
| `paper-100` | `#F4F4F5` | Botão fechar, fundo de logos |
| `paper-border` | `#E7E7EA` | Borda dos action tiles |
| `text-primary` | `#0A0A0A` | Títulos, valores |
| `text-secondary` | `#6E6E73` | Labels de detalhe |
| `text-tertiary` | `#A1A1A6` | Categoria, datas, seções ("YESTERDAY") |
| `handle` | `#D4D4D8` | Alça da bottom sheet |

### Semânticas
| Token | Hex | Uso |
|---|---|---|
| `positive` | `#22B55A` | Entrada (+$50.00), assinatura válida |
| `negative` | `#E5484D` | Pin do mapa → no seu projeto: assinatura inválida |
| `warning` | `#F5A524` | (sugerido) pendente / em verificação |

## 3. Tipografia
- **Display (serifa fina)**: Instrument Serif 400 — ou alternativa paga: PP Editorial New Light.
- **UI**: Manrope (400/500/600/700). Alternativa: Inter / Geist.
- **Mono (sugerido p/ hashes)**: JetBrains Mono / Geist Mono.

| Estilo | Fonte | Tamanho/Linha | Peso | Tracking | Exemplo |
|---|---|---|---|---|---|
| `display` | Serif | 36/40 | 400 | -0.02em | "Bank Smarter." |
| `balance` | Manrope | 32/36 | 500 | -0.03em | $4,923.82 |
| `amount-lg` | Manrope | 28/32 | 600 | -0.03em | -$15.99 |
| `title` | Manrope | 18/24 | 600 | -0.01em | Transactions |
| `heading` | Manrope | 16/22 | 600 | -0.01em | Details |
| `body` | Manrope | 14/20 | 500 | 0 | Starbucks / -$5.75 |
| `body-sm` | Manrope | 13/18 | 400–600 | 0 | linhas de detalhe |
| `caption` | Manrope | 12/16 | 400 | 0 | Food & Drink, datas |
| `overline` | Manrope | 10/14 | 600 | 0.08em, UPPERCASE | YESTERDAY |
| `micro` | Manrope | 11/14 | 500 | 0 | Split the Bill |

Valores usam `font-variant-numeric: tabular-nums`.

## 4. Espaçamento, raios, bordas, sombras
- **Grid base 4px**. Escala: 4, 8, 12, 16, 20, 24, 32, 40.
- Padding lateral das telas: **16px** (sheet) / **20px** (onboarding).
- Linha de transação: 10–12px vertical, gap ícone→texto 12px.
- Entre grupos de data: 16px; overline → 1ª linha: 8px.

| Raio | Valor | Uso |
|---|---|---|
| `sm` | 8px | mapa, chips |
| `md` | 12px | action tiles, card de mapa |
| `lg` | 16px | cards |
| `sheet` | 28px | topo da bottom sheet / modal |
| `full` | 9999px | pills, CTA, avatar, logos, tab bar |

- Bordas: 1px sempre (`ink-border` no escuro, `paper-border` no claro).
- Sombras: quase nenhuma. Sheet: `0 -8px 24px rgba(0,0,0,0.25)`. Tab bar: `0 8px 24px rgba(0,0,0,0.3)`.

## 5. Textura (assinatura visual)
- Ruído granulado (grain) em: header escuro (opacidade ~6–8%) e formas da hero (alto contraste, tipo granito).
- Hero: 3–4 retângulos rotacionados (~-35°), preenchidos com noise branco/cinza sobre preto, sobrepostos em cascata, um "fio" fino separando.
- Implementação: SVG `feTurbulence` (ver `globals.css` → `.grain`, `.grain-strong`).

## 6. Componentes

**CTA pill (escuro)** — altura 52px, largura total, raio full, borda 1px `ink-border`, fundo transparente, texto 14/500 branco à esquerda (padding 20px), seta → à direita.

**Pill secundário (header)** — altura 32px, padding 12px, fundo `ink-850`, borda `ink-border`, ícone 14px + texto 12/500. Ex.: "+ Top Up", "↗ Send Money".

**Header do usuário** — avatar 28px + nome 14/500 + chevron 14px; ícone de busca 20px à direita.

**Bottom sheet** — fundo `paper`, raio 28px só no topo, alça 36×4px `handle` centralizada a 8px do topo; título + ícone de filtro.

**Transaction row** — logo circular 36px (fundo `paper-100` ou cor da marca) | coluna nome (body) + categoria (caption tertiary) | valor alinhado à direita (body, tabular). Sem divisórias.

**Tab bar flutuante** — pill preta ~112×40px, centralizada a 16px do rodapé, 3 ícones 18px; ativo branco, inativos `on-dark-subtle`.

**Modal de detalhe** — sheet branca cheia; botão fechar 28px círculo `paper-100` com X 14px; logo 40px + nome (title) + categoria; valor `amount-lg`; data caption.

**Action tile** — 3 em linha, gap 8px, altura ~64px, raio 12, borda `paper-border`, ícone 16px em cima + texto `micro` embaixo, centralizados.

**Detail row** — label `body-sm` `text-secondary` à esquerda; valor `body-sm` 600 `text-primary` à direita; 10px vertical entre linhas.

**Map card** — raio 12, mapa em tema escuro, pin `negative`; legenda (endereço) caption tertiary 8px abaixo.

## 7. Adaptação para o seu projeto (verificação de assinaturas)
| Referência | No seu app |
|---|---|
| Saldo $4,923.82 | Nº de transações verificadas / score de confiança |
| Top Up / Send Money | "Verificar tx" / "Conectar carteira" |
| Lista de transações | Lista de tx analisadas pelos agentes |
| Logo do merchant | Ícone da chain (ETH, SOL, ADA, ICP) |
| Valor +/- | Badge de status: Válida (verde), Inválida (vermelho), Em análise (âmbar) |
| Split / Repeat / Save | "Reanalisar" / "Ver no explorer" / "Exportar laudo" |
| Transaction number | Hash em mono, truncado: `0x8a3f…92c1` com botão copiar |
| Mapa | Timeline dos agentes (assinatura → chave pública → nonce → veredito) no mesmo card escuro |

Regra: mantenha o verde/vermelho **só** no status. Todo o resto preto/branco.

## 8. Setup Next.js (App Router + Tailwind v4)
```tsx
// app/layout.tsx
import { Instrument_Serif, Manrope, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const serif = Instrument_Serif({ subsets: ["latin"], weight: "400", variable: "--font-instrument-serif" });
const sans = Manrope({ subsets: ["latin"], variable: "--font-manrope" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${serif.variable} ${sans.variable} ${mono.variable}`}>
      <body className="bg-ink-950 font-sans text-on-dark antialiased">{children}</body>
    </html>
  );
}
```
Dependências: `npm i lucide-react clsx`.
