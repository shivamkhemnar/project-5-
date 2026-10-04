import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "AlphaQuant AI — Quant Terminal", description: "Forecasting + anomaly detection terminal" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0B0E14] text-slate-100 antialiased">{children}</body>
    </html>
  );
}
