"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  XAxis,
  YAxis,
} from "recharts";
import type { Quebra } from "@/lib/api";
import { cheio, eixo } from "@/lib/numero";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";

export default function Evolucao({
  pontos,
  rotulo,
  total,
  zero = true,
  carregando = false,
  moeda = false,
  aparar = false,
  meta = null,
}: {
  pontos: Quebra[];
  rotulo: string;
  total: number | null;
  zero?: boolean;
  carregando?: boolean;
  moeda?: boolean;
  aparar?: boolean;
  meta?: number | null;
}) {
  const todos = pontos.filter((p) => p.valor !== null);
  const cortar = aparar && todos.length > 4;
  const validos = cortar ? todos.slice(1, -1) : todos;
  const mensal =
    validos.length > 2 && validos.every((p) => p.rotulo.endsWith("-01"));
  const rotuloDe = mensal ? rotuloMes : rotuloDia;
  const comAnterior = validos.some((p) => p.anterior != null);

  if (validos.length < 2)
    return carregando ? (
      <Skeleton className="h-72 w-full" />
    ) : (
      <div className="text-muted-foreground flex h-72 items-center justify-center text-sm">
        Sem série temporal para desenhar
      </div>
    );

  return (
    <div>
      {comAnterior && (
        <div className="text-muted-foreground mb-2 flex flex-wrap items-center gap-4 text-xs">
          <span className="inline-flex items-center gap-1.5">
            <span className="bg-chart-1 h-0.5 w-4 rounded" />
            Período atual
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="border-muted-foreground w-4 border-t-2 border-dashed" />
            Mesmo período antes
          </span>
        </div>
      )}
      <ChartContainer
        config={{
          valor: {
            label: comAnterior ? "Período atual" : rotulo,
            color: "var(--chart-1)",
          },
          anterior: {
            label: "Mesmo período antes",
            color: "var(--muted-foreground)",
          },
        }}
        className="aspect-auto h-72 w-full"
      >
        <ComposedChart data={validos} margin={{ left: 4, right: 12, top: 8 }}>
          <CartesianGrid vertical={false} strokeDasharray="3 4" />
          <XAxis
            dataKey="rotulo"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            minTickGap={48}
            tickFormatter={rotuloDe}
          />
          <YAxis
            width={moeda ? 72 : 52}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => eixo(v, moeda)}
            domain={zero ? [0, "auto"] : ["auto", "auto"]}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(v) => rotuloDe(String(v))}
                formatter={(v, nome) => (
                  <span className="flex w-full justify-between gap-4">
                    <span className="text-muted-foreground">
                      {nome === "anterior"
                        ? "Mesmo período antes"
                        : comAnterior
                          ? "Período atual"
                          : rotulo}
                    </span>
                    <span className="font-medium tabular-nums">
                      {cheio(Number(v), moeda)}
                    </span>
                  </span>
                )}
                hideIndicator={!comAnterior}
              />
            }
          />
          <Area
            dataKey="valor"
            type="monotone"
            stroke="var(--color-valor)"
            fill="var(--color-valor)"
            fillOpacity={0.15}
            strokeWidth={2}
            isAnimationActive={false}
          />
          {meta !== null && (
            <ReferenceLine
              y={meta}
              stroke="var(--color-amber-500)"
              strokeDasharray="6 4"
              strokeWidth={1.5}
              ifOverflow="extendDomain"
              label={{
                value: `meta ${eixo(meta, moeda)}`,
                position: "insideTopRight",
                fill: "var(--color-amber-500)",
                fontSize: 11,
              }}
            />
          )}
          {comAnterior && (
            <Line
              dataKey="anterior"
              type="monotone"
              stroke="var(--color-anterior)"
              strokeOpacity={0.7}
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ChartContainer>

      {cortar && (
        <p className="text-muted-foreground mt-1 text-xs">
          O primeiro e o último período estão incompletos e ficam fora do
          gráfico.
        </p>
      )}
      {total !== null && (
        <p className="text-muted-foreground mt-1 text-xs">
          Total no período:{" "}
          <span className="text-foreground font-medium tabular-nums">
            {cheio(total, moeda)}
          </span>
        </p>
      )}
    </div>
  );
}

function rotuloDia(iso: string): string {
  const data = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}

function rotuloMes(iso: string): string {
  const data = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleDateString("pt-BR", { month: "short", year: "numeric" });
}
