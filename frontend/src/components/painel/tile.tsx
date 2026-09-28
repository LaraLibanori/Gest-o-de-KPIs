"use client";

import { ArrowDownRight, ArrowUpRight, Minus, TriangleAlert } from "lucide-react";
import { FRASES, type IndicadorCalculado } from "@/lib/api";
import { cheio, curto } from "@/lib/numero";
import { humano, variacao } from "@/lib/rotulo";
import Sparkline from "@/components/painel/sparkline";
import { cn } from "@/lib/utils";

function Delta({ valor }: { valor: number | null }) {
  if (valor === null || !Number.isFinite(valor)) {
    return (
      <span className="text-muted-foreground inline-flex items-center gap-1 text-xs">
        <Minus className="size-3" />
        {valor === null ? "sem comparação" : "—"}
      </span>
    );
  }
  if (valor === 0) {
    return (
      <span className="text-muted-foreground inline-flex items-center gap-1 text-xs">
        <Minus className="size-3" />
        estável
      </span>
    );
  }
  const subiu = valor > 0;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-0.5 text-xs font-medium tabular-nums",
        subiu ? "text-emerald-500" : "text-rose-500",
      )}
    >
      {subiu ? (
        <ArrowUpRight className="size-3.5" />
      ) : (
        <ArrowDownRight className="size-3.5" />
      )}
      {variacao(valor)}
    </span>
  );
}

export default function Tile({
  indicador,
  janela,
  selecionado,
  onSelecionar,
}: {
  indicador: IndicadorCalculado;
  janela: string;
  selecionado: boolean;
  onSelecionar: () => void;
}) {
  const rotulo = humano(indicador.coluna ?? "");
  const conta = FRASES[indicador.agregacao](rotulo);

  return (
    <button
      onClick={onSelecionar}
      aria-pressed={selecionado}
      className={cn(
        "group bg-card text-card-foreground relative flex flex-col gap-3 overflow-hidden rounded-xl border p-4 text-left transition-all",
        "hover:border-primary/40 focus-visible:ring-ring/50 outline-none focus-visible:ring-2",
        selecionado && "border-primary/60 ring-primary/20 ring-2",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="truncate text-sm font-medium">{indicador.nome}</p>
        {selecionado && <span className="bg-primary size-1.5 shrink-0 rounded-full" />}
      </div>

      {indicador.erro ? (
        <p className="text-muted-foreground flex items-start gap-1.5 text-xs">
          <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
          {indicador.erro}
        </p>
      ) : (
        <div className="flex flex-col gap-1">
          <p
            className="text-3xl leading-none font-semibold tabular-nums"
            title={indicador.valor === null ? undefined : cheio(indicador.valor)}
          >
            {indicador.valor === null ? "—" : curto(indicador.valor)}
          </p>
          <div className="flex items-center gap-2">
            <Delta valor={indicador.variacao} />
            {janela && (
              <span className="text-muted-foreground truncate text-xs">
                vs {janela}
              </span>
            )}
          </div>
        </div>
      )}

      {!indicador.erro && indicador.serie.length > 1 && (
        <Sparkline pontos={indicador.serie} className="-mx-1 h-9 w-[calc(100%+0.5rem)]" />
      )}

      <p
        className="text-muted-foreground truncate text-xs"
        title={`${conta} · ${indicador.nome}`}
      >
        {conta}
      </p>
    </button>
  );
}
