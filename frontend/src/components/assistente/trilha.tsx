"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export type ItemTrilha = { id: string; curto: string; titulo: string };

export default function Trilha({
  itens,
  indice,
  visited,
  onIr,
}: {
  itens: ItemTrilha[];
  indice: number;
  visited: number[];
  onIr: (i: number) => void;
}) {
  return (
    <nav aria-label="Etapas" className="w-full">
      <ol className="flex items-start gap-1">
        {itens.map((item, i) => {
          const feito = visited.includes(i) && i !== indice;
          const atual = i === indice;
          const podeIr = i <= indice || visited.includes(i);
          const Icone = feito ? Check : null;

          return (
            <li key={item.id} className="flex min-w-0 flex-1 flex-col gap-1.5">
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => podeIr && onIr(i)}
                  disabled={!podeIr}
                  aria-current={atual ? "step" : undefined}
                  className={cn(
                    "flex size-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium transition-colors",
                    atual &&
                      "border-primary bg-primary text-primary-foreground",
                    feito && "border-primary/40 bg-primary/10 text-primary",
                    !atual && !feito && "bg-muted text-muted-foreground",
                    podeIr && !atual && "hover:border-foreground/40",
                  )}
                >
                  {Icone ? <Icone className="size-3.5" /> : i + 1}
                </button>
                {i < itens.length - 1 && (
                  <span
                    className={cn(
                      "h-px flex-1 transition-colors",
                      i < indice ? "bg-primary/50" : "bg-border",
                    )}
                  />
                )}
              </div>

              <button
                type="button"
                onClick={() => podeIr && onIr(i)}
                disabled={!podeIr}
                className={cn(
                  "truncate text-left text-xs transition-colors",
                  atual
                    ? "text-foreground font-medium"
                    : feito
                      ? "text-muted-foreground hover:text-foreground"
                      : "text-muted-foreground/50",
                  podeIr && !atual && "cursor-pointer",
                )}
              >
                {item.curto}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
