import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KPI Builder",
  description:
    "Conecte seu banco de dados e monte seus próprios dashboards de indicadores, sem precisar programar.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
