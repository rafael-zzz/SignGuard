"use client";
// Mantido por compatibilidade: delega para o Hash do design system.
import { Hash, shortHash } from "./ui";

export const short = shortHash;

export default function AddressChip({ address }: { address?: string | null }) {
  return <Hash value={address} />;
}
