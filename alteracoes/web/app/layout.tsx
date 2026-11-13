import type { Metadata } from "next";
import { Instrument_Serif, Manrope, JetBrains_Mono } from "next/font/google";
import AppNav from "@/components/AppNav";
import "./globals.css";

const serif = Instrument_Serif({ subsets: ["latin"], weight: "400", variable: "--font-instrument-serif" });
const sans = Manrope({ subsets: ["latin"], variable: "--font-manrope" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains-mono" });

export const metadata: Metadata = {
  title: "SignGuard",
  description: "Agentes de IA que protegem quem assina transações em blockchain",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${serif.variable} ${sans.variable} ${mono.variable}`}>
      <body className="bg-ink-950 font-sans text-on-dark antialiased">
        <div className="grain min-h-screen overflow-x-clip">
          <div className="mx-auto max-w-4xl px-4 sm:px-5">
            <AppNav />
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
