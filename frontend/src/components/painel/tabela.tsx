"use client";

import type { Quebra } from "@/lib/api";
import { cheio, curto } from "@/lib/numero";

export default function Tabela({ linhas }: { linhas: Quebra[] }) {
  const total = linhas.reduce((s, l) => s + Math.abs(l.valor ?? 0), 0);

  return (
    <div className="max-h-56 overflow-y-auto">
      <table className="w-full text-xs">
        <tbody>
          {linhas.map((l) => (
            <tr key={l.rotulo} className="border-b last:border-0">
              <td className="text-muted-foreground truncate py-1.5 pr-2">
                {l.rotulo}
              </td>
              <td
                className="py-1.5 text-right tabular-nums"
                title={l.valor === null ? undefined : cheio(l.valor)}
              >
                {l.valor === null ? "—" : curto(l.valor)}
              </td>
              <td className="text-muted-foreground w-12 py-1.5 text-right tabular-nums">
                {total === 0
                  ? "—"
                  : `${Math.round((Math.abs(l.valor ?? 0) / total) * 100)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
