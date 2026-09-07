import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import "./globals.css";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "KPI Builder",
  description:
    "Conecte seu banco de dados e monte seus próprios dashboards de indicadores, sem precisar programar.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="pt-BR"
      className={cn("dark font-sans", geist.variable, geistMono.variable)}
      suppressHydrationWarning
    >
      <body className="antialiased">
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster position="bottom-right" theme="dark" />
      </body>
    </html>
  );
}
