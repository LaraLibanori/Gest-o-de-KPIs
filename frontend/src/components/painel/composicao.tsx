"use client";

import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Cell, Pie, PieChart } from "recharts";
import {
  api,
  type Composicao,
  type Quebra,
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
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const NIVEIS = new Set(["media", "minimo", "maximo"]);

function Pizza({
  pontos,
  total,
  nome,
}: {
  pontos: Quebra[];
  total: number;
  nome: string;
}) {
  const fatias = pontos.filter((p) => (p.valor ?? 0) > 0);
  const cor = (i: number) => `var(--chart-${(i % 5) + 1})`;
  return (
    <div className="space-y-3">
      <ChartContainer
        config={{ valor: { label: nome } }}
        className="mx-auto aspect-square max-h-56"
      >
        <PieChart>
          <ChartTooltip
            content={<ChartTooltipContent nameKey="rotulo" hideLabel />}
          />
          <Pie
            data={fatias}
            dataKey="valor"
            nameKey="rotulo"
            innerRadius={50}
            strokeWidth={2}
            isAnimationActive={false}
          >
            {fatias.map((p, i) => (
              <Cell key={p.rotulo} fill={cor(i)} />
            ))}
          </Pie>
        </PieChart>
      </ChartContainer>
      <ul className="grid gap-1 text-xs">
        {fatias.map((p, i) => (
          <li key={p.rotulo} className="flex items-center gap-2">
            <span
              className="size-2.5 shrink-0 rounded-sm"
              style={{ background: cor(i) }}
            />
            <span className="truncate">{p.rotulo}</span>
            <span className="text-muted-foreground ml-auto tabular-nums">
              {curto(p.valor as number)}
              {total > 0 &&
                ` · ${(((p.valor as number) / total) * 100).toFixed(0)}%`}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Tabela({ pontos, total }: { pontos: Quebra[]; total: number }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Grupo</TableHead>
          <TableHead className="text-right">Valor</TableHead>
          {total > 0 && <TableHead className="text-right">Do total</TableHead>}
        </TableRow>
      </TableHeader>
      <TableBody>
        {pontos.map((p) => (
          <TableRow key={p.rotulo}>
            <TableCell className="max-w-40 truncate">{p.rotulo}</TableCell>
            <TableCell className="text-right tabular-nums">
              {cheio(p.valor as number)}
            </TableCell>
            {total > 0 && (
              <TableCell className="text-muted-foreground text-right tabular-nums">
                {(((p.valor as number) / total) * 100)
                  .toFixed(1)
                  .replace(".", ",")}
                %
              </TableCell>
            )}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export type Forma = "barra" | "pizza" | "tabela";

export default function Composicao({
  base,
  indicador,
  dimensoes,
  janela,
  rotuloDe,
  forma = "barra",
}: {
  base: string;
  indicador: IndicadorCalculado;
  dimensoes: Dimensao[];
  janela: string;
  rotuloDe: (coluna: string | null) => string;
  forma?: Forma;
}) {
  const [escolhida, setColuna] = useState<string>("");
  const preferida =
    dimensoes.find((d) => d.coluna === indicador.dimensao) ?? dimensoes[0];
  const coluna = dimensoes.some((d) => d.coluna === escolhida)
    ? escolhida
    : (preferida?.coluna ?? "");
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
    setDados(null);
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
  const total = somavel ? (dados?.total ?? 0) : 0;

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
      ) : forma === "pizza" ? (
        <Pizza pontos={pontos} total={total} nome={indicador.nome} />
      ) : forma === "tabela" ? (
        <Tabela pontos={pontos} total={total} />
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
                  <Progress
                    value={fatia}
                    className="h-2 [&>[data-slot=progress-indicator]]:bg-chart-1 [&>[data-slot=progress-indicator]]:transition-[transform] [&>[data-slot=progress-indicator]]:duration-500"
                  />
                  <span className="text-muted-foreground w-20 text-right text-xs tabular-nums">
                    {curto(valor)}
                    {total > 0 && (
                      <span className="ml-1 opacity-70">
                        {doTotal.toFixed(0)}%
                      </span>
                    )}
                  </span>
                </button>
                {escolhido && (
                  <dl
                    className={cn(
                      "text-muted-foreground animate-in fade-in grid gap-2 px-1 pt-1.5 pb-1 text-xs",
                      total > 0 ? "grid-cols-3" : "grid-cols-2",
                    )}
                  >
                    <div>
                      <dt>Valor</dt>
                      <dd className="text-foreground tabular-nums">
                        {cheio(valor)}
                      </dd>
                    </div>
                    {total > 0 && (
                      <div>
                        <dt>Do total</dt>
                        <dd className="text-foreground tabular-nums">
                          {doTotal.toFixed(1).replace(".", ",")}%
                        </dd>
                      </div>
                    )}
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
          {total > 0 && <> · {cheio(total)} no período</>}
        </p>
      )}
    </div>
  );
}
