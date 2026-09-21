"use client";

import type { Quebra } from "@/lib/api";
import { cheio, curto } from "@/lib/numero";

export default function Barras({ linhas }: { linhas: Quebra[] }) {
  const maior = Math.max(...linhas.map((l) => Math.abs(l.valor ?? 0)), 1);

  return (
    <div className="space-y-2.5">
      {linhas.map((l) => (
        <div key={l.rotulo} className="space-y-1">
          <div className="flex items-baseline justify-between gap-3 text-xs">
            <span className="text-muted-foreground truncate">{l.rotulo}</span>
            <span
              className="text-foreground shrink-0 tabular-nums"
              title={l.valor === null ? undefined : cheio(l.valor)}
            >
              {l.valor === null ? "—" : curto(l.valor)}
            </span>
          </div>
          <div className="bg-muted h-2 overflow-hidden rounded-sm">
            <div
              className="bg-chart-1 h-full rounded-r-sm"
              style={{
                width: `${Math.max(2, (Math.abs(l.valor ?? 0) / maior) * 100)}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
