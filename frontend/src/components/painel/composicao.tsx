"use client";

import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  api,
  type Composicao,
  type Dimensao,
  type IndicadorCalculado,
} from "@/lib/api";
import { cheio, curto } from "@/lib/numero";
import { cn } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const NIVEIS = new Set(["media", "minimo", "maximo"]);

export default function Composicao({
  base,
  indicador,
  dimensoes,
  janela,
  rotuloDe,
}: {
  base: string;
  indicador: IndicadorCalculado;
  dimensoes: Dimensao[];
  janela: string;
  rotuloDe: (coluna: string | null) => string;
}) {
  const [coluna, setColuna] = useState<string>(dimensoes[0]?.coluna ?? "");
  const [dados, setDados] = useState<Composicao | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);

  useEffect(() => {
    if (!coluna || indicador.id === undefined) return;
    let vivo = true;
    setCarregando(true);
    setErro(null);
    setAberto(null);
    api<Composicao>(
      `${base}/composicao?indicador=${indicador.id}&dimensao=${encodeURIComponent(coluna)}&janela=${janela}`,
    )
      .then((r) => {
        if (vivo) setDados(r);
      })
      .catch((e) => {
        if (vivo) {
          setDados(null);
          setErro(e instanceof Error ? e.message : "não foi possível ler");
        }
      })
      .finally(() => {
        if (vivo) setCarregando(false);
      });
    return () => {
      vivo = false;
    };
  }, [base, coluna, indicador.id, janela]);

  const somavel = !NIVEIS.has(indicador.agregacao);
  const pontos = (dados?.pontos ?? []).filter((p) => p.valor !== null);
  const maior = Math.max(...pontos.map((p) => p.valor as number), 0);
  const total = pontos.reduce((s, p) => s + (p.valor as number), 0);

  if (dimensoes.length === 0)
    return (
      <p className="text-muted-foreground text-sm">
        Esta tabela não tem coluna de texto para quebrar.
      </p>
    );

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Select value={coluna} onValueChange={setColuna}>
          <SelectTrigger size="sm" className="flex-1">
            <SelectValue placeholder="escolha a divisão" />
          </SelectTrigger>
          <SelectContent>
            {dimensoes.map((d) => (
              <SelectItem key={d.coluna} value={d.coluna}>
                {rotuloDe(d.coluna)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <ChevronDown className="text-muted-foreground size-4 shrink-0" />
      </div>

      {erro && <p className="text-muted-foreground text-sm">{erro}</p>}

      {carregando && !dados ? (
        <div className="space-y-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-7 w-full" />
          ))}
        </div>
      ) : pontos.length === 0 ? (
        <p className="text-muted-foreground py-6 text-center text-sm">
          Sem dados neste período
        </p>
      ) : (
        <ul className="space-y-1.5">
          {pontos.map((p) => {
            const valor = p.valor as number;
            const fatia = maior > 0 ? (valor / maior) * 100 : 0;
            const doTotal = total > 0 ? (valor / total) * 100 : 0;
            const escolhido = aberto === p.rotulo;
            return (
              <li key={p.rotulo}>
                <button
                  type="button"
                  aria-expanded={escolhido}
                  onClick={() => setAberto(escolhido ? null : p.rotulo)}
                  className={cn(
                    "grid w-full grid-cols-[minmax(0,7rem)_1fr_auto] items-center gap-3 rounded-md px-1 py-1 text-left transition-colors hover:bg-accent/50",
                    escolhido && "bg-accent/60",
                  )}
                >
                  <span className="truncate text-sm">{p.rotulo}</span>
                  <span className="bg-muted h-2 overflow-hidden rounded-full">
                    <span
                      className="bg-chart-1 block h-full rounded-full transition-[width] duration-500"
                      style={{ width: `${fatia}%` }}
                    />
                  </span>
                  <span className="text-muted-foreground w-20 text-right text-xs tabular-nums">
                    {curto(valor)}
                    <span className="ml-1 opacity-70">
                      {doTotal.toFixed(0)}%
                    </span>
                  </span>
                </button>
                {escolhido && (
                  <dl className="text-muted-foreground animate-in fade-in grid grid-cols-3 gap-2 px-1 pt-1.5 pb-1 text-xs">
                    <div>
                      <dt>Valor</dt>
                      <dd className="text-foreground tabular-nums">
                        {cheio(valor)}
                      </dd>
                    </div>
                    <div>
                      <dt>Do total</dt>
                      <dd className="text-foreground tabular-nums">
                        {doTotal.toFixed(1).replace(".", ",")}%
                      </dd>
                    </div>
                    <div>
                      <dt>Da maior</dt>
                      <dd className="text-foreground tabular-nums">
                        {fatia.toFixed(1).replace(".", ",")}%
                      </dd>
                    </div>
                  </dl>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {dados && pontos.length > 0 && somavel && (
        <p className="text-muted-foreground text-xs">
          Top {pontos.length}
          {dados.total !== null && <> · {cheio(dados.total)} no período</>}
        </p>
      )}
    </div>
  );
}
