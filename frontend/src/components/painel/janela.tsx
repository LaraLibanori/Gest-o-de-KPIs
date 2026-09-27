"use client";

import { JANELAS, type Janela } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ControleJanela({
  janela,
  onMudar,
  desabilitado,
}: {
  janela: Janela;
  onMudar: (j: Janela) => void;
  desabilitado: boolean;
}) {
  if (desabilitado) return null;
  return (
    <div
      role="radiogroup"
      aria-label="Período"
      className="bg-muted/50 inline-flex items-center gap-0.5 rounded-lg p-0.5"
    >
      {JANELAS.map((j) => (
        <button
          key={j.valor}
          role="radio"
          aria-checked={janela === j.valor}
          onClick={() => onMudar(j.valor)}
          className={cn(
            "focus-visible:ring-ring/50 rounded-md px-2.5 py-1 text-xs font-medium transition-colors outline-none focus-visible:ring-2",
            janela === j.valor
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {j.rotulo}
        </button>
      ))}
    </div>
  );
}
