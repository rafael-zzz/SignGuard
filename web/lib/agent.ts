// Agente-carteira da demo, propositalmente ingênuo. Espelha backend/demo/wallet_bot.py (naive_agent).
// Ele obedece o texto que recebe e monta a transação. Quem decide se ele pode assinar é o SignGuard.
import type { TxInput } from "./types";

export const USDT = "0xdAC17F958D2ee523a2206206994597C13D831ec7";
export const AGENT = "0x8a90CAb2b38dba80c64b7734e58Ee1dB38B8992e";
export const SUPPLIER = "0x5a3a1c2b9e4d7f60812a3b4c5d6e7f8091a2b3c4"; // na allowlist do agent-wallet
export const BALANCE_USDT = "25000";
const USDT_DECIMALS = 6;

export type AgentIntent = { to: string; amount: string; tx: TxInput };

const pad32 = (hex: string) => hex.padStart(64, "0");

function toUnits(amount: string, decimals: number): bigint {
  const [int, frac = ""] = amount.split(".");
  return BigInt(int || "0") * 10n ** BigInt(decimals) + BigInt((frac + "0".repeat(decimals)).slice(0, decimals) || "0");
}

/** Calldata de ERC-20 transfer(address,uint256). */
export function encodeTransfer(to: string, units: bigint): string {
  return "0xa9059cbb" + pad32(to.toLowerCase().replace(/^0x/, "")) + pad32(units.toString(16));
}

/** Extrai destino e valor da mensagem, como o naive_agent do backend. */
export function naiveAgent(message: string): AgentIntent {
  const to = message.match(/0x[a-fA-F0-9]{40}/)?.[0] ?? SUPPLIER;
  let amount = "10";
  if (/todo|tudo|saldo/i.test(message)) {
    amount = BALANCE_USDT;
  } else {
    const m = message.match(/(\d+(?:[.,]\d+)?)\s*USDT/i);
    if (m) amount = m[1].replace(",", ".");
  }
  const tx: TxInput = {
    chain_id: 1,
    from: AGENT,
    to: USDT,
    value: "0",
    data: encodeTransfer(to, toUnits(amount, USDT_DECIMALS)),
    context: `Mensagem recebida pelo agente: ${message}`,
    owner_id: "agent-wallet",
  };
  return { to, amount, tx };
}
