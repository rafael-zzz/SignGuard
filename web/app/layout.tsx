import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SignGuard",
  description: "Agentes de IA que protegem quem assina transações em blockchain",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="container">
          <nav className="nav">
            <span className="brand">SignGuard</span>
            <Link href="/">Analisar</Link>
            <Link href="/agente">Agente-carteira</Link>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
