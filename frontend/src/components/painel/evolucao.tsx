"use client";

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
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
}: {
  pontos: Quebra[];
  rotulo: string;
  total: number | null;
  zero?: boolean;
  carregando?: boolean;
  moeda?: boolean;
  aparar?: boolean;
}) {
  const todos = pontos.filter((p) => p.valor !== null);
  const cortar = aparar && todos.length > 4;
  const validos = cortar ? todos.slice(1, -1) : todos;
  const mensal =
    validos.length > 2 && validos.every((p) => p.rotulo.endsWith("-01"));
  const rotuloDe = mensal ? rotuloMes : rotuloDia;

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
      <ChartContainer
        config={{ valor: { label: rotulo, color: "var(--chart-1)" } }}
        className="aspect-auto h-72 w-full"
      >
        <AreaChart data={validos} margin={{ left: 4, right: 12, top: 8 }}>
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
                formatter={(v) => cheio(Number(v), moeda)}
                hideIndicator
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
        </AreaChart>
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
