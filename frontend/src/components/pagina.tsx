"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

const LARGURAS = {
  estreito: "max-w-4xl",
  normal: "max-w-6xl",
  largo: "max-w-7xl",
} as const;

export type Largura = keyof typeof LARGURAS;

export function Pagina({
  largura = "normal",
  children,
}: {
  largura?: Largura;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "mx-auto flex w-full flex-col gap-6 px-4 py-6 md:px-8 md:py-8",
        LARGURAS[largura],
      )}
    >
      {children}
    </div>
  );
}

export function Cabecalho({
  titulo,
  descricao,
  voltar,
  acoes,
  children,
  className,
}: {
  titulo: string;
  descricao?: React.ReactNode;
  voltar?: { href: string; rotulo: string };
  acoes?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap items-start justify-between gap-4", className)}>
      <div className="min-w-0">
        {voltar && (
          <Link
            href={voltar.href}
            className="text-muted-foreground hover:text-foreground -ml-2 mb-1 inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-sm transition-colors"
          >
            {voltar.rotulo}
          </Link>
        )}
        <h1 className="truncate text-2xl font-semibold tracking-tight">{titulo}</h1>
        {descricao && (
          <p className="text-muted-foreground mt-1 text-sm">{descricao}</p>
        )}
      </div>
      {acoes && <div className="flex shrink-0 items-center gap-2">{acoes}</div>}
      {children}
    </div>
  );
}
