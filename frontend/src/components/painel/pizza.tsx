"use client";

import type { Quebra } from "@/lib/api";
import { cheio } from "@/lib/numero";

const CORES = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];
const FATIAS = 5;
const R = 42;
const ESPESSURA = 14;
const VOLTA = 2 * Math.PI * R;

// Mais de cinco fatias nenhuma paleta separa: o resto vira "Outros".
function agrupar(linhas: Quebra[]): Quebra[] {
  const ordenado = [...linhas].sort((a, b) => (b.valor ?? 0) - (a.valor ?? 0));
  if (ordenado.length <= FATIAS) return ordenado;
  const resto = ordenado
    .slice(FATIAS - 1)
    .reduce((soma, l) => soma + (l.valor ?? 0), 0);
  return [...ordenado.slice(0, FATIAS - 1), { rotulo: "Outros", valor: resto }];
}

export default function Pizza({ linhas }: { linhas: Quebra[] }) {
  const fatias = agrupar(linhas);
  const total = fatias.reduce((s, l) => s + Math.abs(l.valor ?? 0), 0);
  if (total === 0) return null;

  let percorrido = 0;
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 100 100" className="size-24 shrink-0 -rotate-90">
        {fatias.map((l, i) => {
          const parte = Math.abs(l.valor ?? 0) / total;
          const arco = Math.max(parte * VOLTA - 2, 0);
          const deslocamento = -percorrido * VOLTA;
          percorrido += parte;
          return (
            <circle
              key={l.rotulo}
              cx="50"
              cy="50"
              r={R}
              fill="none"
              stroke={CORES[i % CORES.length]}
              strokeWidth={ESPESSURA}
              strokeDasharray={`${arco} ${VOLTA - arco}`}
              strokeDashoffset={deslocamento}
            >
              <title>{`${l.rotulo}: ${cheio(l.valor ?? 0)}`}</title>
            </circle>
          );
        })}
      </svg>
      <ul className="min-w-0 flex-1 space-y-1.5 text-xs">
        {fatias.map((l, i) => (
          <li key={l.rotulo} className="flex items-center gap-2">
            <span
              className="size-2.5 shrink-0 rounded-sm"
              style={{ background: CORES[i % CORES.length] }}
            />
            <span className="text-muted-foreground truncate">{l.rotulo}</span>
            <span className="text-foreground ml-auto shrink-0 tabular-nums">
              {Math.round((Math.abs(l.valor ?? 0) / total) * 100)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
