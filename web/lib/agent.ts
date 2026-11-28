// Agente-carteira da demo, propositalmente ingênuo. Espelha backend/demo/wallet_bot.py, e só é usado no modo
// mocks (NEXT_PUBLIC_USE_MOCKS=1). Com backend, quem monta a transação é POST /agent/chat.
// Ele obedece o texto que recebe e monta a transação. Quem decide se ele pode assinar é o SignGuard.
// Sem valor ou sem moeda na mensagem não há transferência: ele pergunta em vez de chutar.
import type { TxInput, Verdict } from "./types";

export const AGENT = "0x8a90CAb2b38dba80c64b7734e58Ee1dB38B8992e";
export const SUPPLIER = "0x5a3a1c2b9e4d7f60812a3b4c5d6e7f8091a2b3c4"; // na allowlist do agent-wallet

// Mesmas moedas de backend/tools/decode.py (TOKENS) + ETH nativo: símbolo -> contrato ERC-20 (null = nativo), decimais
export const ASSETS: Record<string, { token: string | null; decimals: number }> = {
  USDT: { token: "0xdAC17F958D2ee523a2206206994597C13D831ec7", decimals: 6 },
  USDC: { token: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", decimals: 6 },
  DAI: { token: "0x6B175474E89094C44Da98b954EedeAC495271d0F", decimals: 18 },
  WBTC: { token: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", decimals: 8 },
  WETH: { token: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", decimals: 18 },
  ETH: { token: null, decimals: 18 },
};
// Saldo da carteira de demo (o que "todo o saldo" move); igual a wallet_bot.BALANCES
export const BALANCES: Record<string, string> = { USDT: "25000", USDC: "10000", DAI: "5000", WBTC: "0.5", WETH: "3", ETH: "2" };

export type AgentIntent = { to: string; symbol: string | null; amount: string | null; allBalance: boolean };

const pad32 = (hex: string) => hex.padStart(64, "0");

function toUnits(amount: string, decimals: number): bigint {
  const [int, frac = ""] = amount.split(".");
  return BigInt(int || "0") * 10n ** BigInt(decimals) + BigInt((frac + "0".repeat(decimals)).slice(0, decimals) || "0");
}

/** Calldata de ERC-20 transfer(address,uint256). */
export function encodeTransfer(to: string, units: bigint): string {
  return "0xa9059cbb" + pad32(to.toLowerCase().replace(/^0x/, "")) + pad32(units.toString(16));
}

// Mesmas regras de backend/demo/wallet_bot.py (parse_symbol / parse_amount)
const ADDRESS = /0x[a-fA-F0-9]{40}/;
const SYM_ANY = Object.keys(ASSETS).join("|");
const SYMBOL = new RegExp(String.raw`\b(${Object.keys(ASSETS).sort((a, b) => b.length - a.length).join("|")})\b`, "i");
const ALL = /\bsaldo\b|\btudo\b(?!\s+bem)|\btodo\s+o\s+(?:dinheiro|valor)\b/i;
const NUM = String.raw`\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?`;
const MIL = String.raw`(?:\s*(mil)\b)?`;
const NEAR = new RegExp(String.raw`(?:${NUM})\s*(?:mil\s*)?(${SYM_ANY})\b|\b(${SYM_ANY})\s*(?:${NUM})`, "i");
const WITH_SYMBOL = new RegExp(String.raw`\b(?:${SYM_ANY})\s*(${NUM})${MIL}|(?<![\w.,])(${NUM})${MIL}\s*(?:${SYM_ANY})\b`, "i");
const BARE = new RegExp(String.raw`(?<![\w.,])(${NUM})${MIL}(?![\w.,]*\d)`, "i");

const stripAddresses = (m: string) => m.replace(new RegExp(ADDRESS, "g"), " ");

function toDecimal(num: string, mil?: string): string {
  if (/^\d{1,3}(?:\.\d{3})+(?:,\d+)?$/.test(num)) num = num.replace(/\./g, "");
  num = num.replace(",", ".");
  if (!mil) return num;
  const [int, frac = ""] = num.split(".");
  const f = frac.padEnd(3, "0");
  return `${BigInt(int + f.slice(0, 3))}${f.length > 3 ? "." + f.slice(3) : ""}`;
}

/** Moeda pedida. Prefere a que está colada no valor; senão a primeira citada. */
export function parseSymbol(message: string): string | null {
  const text = stripAddresses(message);
  const m = text.match(NEAR) ?? text.match(SYMBOL);
  return m ? (m.slice(1).find(Boolean) ?? "").toUpperCase() : null;
}

/** Valor pedido. "Todo o saldo" vira o saldo da moeda (sem moeda não há como saber quanto). */
export function parseAmount(message: string, symbol: string | null = null): string | null {
  if (ALL.test(message)) return symbol ? BALANCES[symbol] ?? null : null;
  const text = stripAddresses(message);
  const m = text.match(WITH_SYMBOL);
  let num: string, mil: string | undefined;
  if (m) [num, mil] = m[1] ? [m[1], m[2]] : [m[3], m[4]];
  else {
    const b = text.match(BARE);
    if (!b) return null;
    [num, mil] = [b[1], b[2]];
  }
  const value = toDecimal(num, mil);
  return Number(value) > 0 ? value : null;
}

export function parseIntent(message: string): AgentIntent {
  const symbol = parseSymbol(message);
  return {
    to: message.match(ADDRESS)?.[0] ?? SUPPLIER,
    symbol,
    amount: parseAmount(message, symbol),
    allBalance: ALL.test(message),
  };
}

/** Pergunta do agente quando falta dado para montar a transferência. null = dá para montar. */
export function missingReply({ symbol, amount, allBalance }: AgentIntent): string | null {
  if (symbol && amount !== null) {
    const { decimals } = ASSETS[symbol];
    if ((amount.split(".")[1] ?? "").replace(/0+$/, "").length <= decimals) return null;
    return `${symbol} aceita no máximo ${decimals} casas decimais. Quanto devo transferir?`;
  }
  const coins = Object.keys(ASSETS).join(", ");
  if (!symbol && amount === null && !allBalance)
    return `Não entendi o valor nem a moeda. Quanto devo transferir, e em qual moeda (${coins})? Ex.: "Pague 50 USDT ao fornecedor".`;
  if (!symbol) return `Em qual moeda devo transferir (${coins})? Ex.: "Pague 50 USDT ao fornecedor".`;
  return `Não entendi o valor. Quanto devo transferir em ${symbol}? Ex.: "Pague 50 ${symbol} ao fornecedor".`;
}

/** Transferência ERC-20 (transfer) ou de ETH nativo. Só chamar quando missingReply devolve null. */
export function buildTx(intent: AgentIntent, message: string): TxInput {
  const { token, decimals } = ASSETS[intent.symbol!];
  const units = toUnits(intent.amount!, decimals);
  return {
    chain_id: 1,
    from: AGENT,
    to: token ?? intent.to,
    value: token ? "0" : units.toString(),
    data: token ? encodeTransfer(intent.to, units) : "0x",
    context: `Mensagem recebida pelo agente: ${message}`,
    owner_id: "agent-wallet",
    source: "agent",
  };
}

export const fmtAmount = ({ symbol, amount }: AgentIntent) =>
  `${Number(amount).toLocaleString("pt-BR", { maximumFractionDigits: ASSETS[symbol!].decimals })} ${symbol}`;

/** Mesmo texto de wallet_bot.template_reply (a fala do backend quando o LLM está desligado). */
export function templateReply(intent: AgentIntent, verdict: Verdict, signed: boolean): string {
  const base = `Montei a transferência de ${fmtAmount(intent)} para ${intent.to.slice(0, 6)}…${intent.to.slice(-4)} e consultei o SignGuard.`;
  if (signed) return `${base} Ele autorizou, então assinei e enviei.`;
  const reason = (verdict.reasons[0] ?? "").trim().replace(/\.$/, "");
  return `${base} Ele não liberou${reason ? `: ${reason}.` : "."} Não assinei.`;
}
