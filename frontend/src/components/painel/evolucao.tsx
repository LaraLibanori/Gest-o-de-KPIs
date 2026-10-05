"use client";

import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from "recharts";
import type { Quebra } from "@/lib/api";
import { cheio, curto } from "@/lib/numero";
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
}: {
  pontos: Quebra[];
  rotulo: string;
  total: number | null;
  zero?: boolean;
  carregando?: boolean;
}) {
  const validos = pontos.filter((p) => p.valor !== null);

  if (validos.length < 2)
    return carregando ? (
      <Skeleton className="h-60 w-full" />
    ) : (
      <div className="text-muted-foreground flex h-60 items-center justify-center text-sm">
        Sem série temporal para desenhar
      </div>
    );

  return (
    <div>
      <ChartContainer
        config={{ valor: { label: rotulo, color: "var(--chart-1)" } }}
        className="aspect-auto h-60 w-full"
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
            width={48}
            tickLine={false}
            axisLine={false}
            tickFormatter={curto}
            domain={zero ? [0, "auto"] : ["auto", "auto"]}
          />
          <ChartTooltip
            content={
              <ChartTooltipContent
                labelFormatter={(v) => rotuloDe(String(v))}
                formatter={(v) => cheio(Number(v))}
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

      {total !== null && (
        <p className="text-muted-foreground mt-1 text-xs">
          Total no período:{" "}
          <span className="text-foreground font-medium tabular-nums">
            {cheio(total)}
          </span>
        </p>
      )}
    </div>
  );
}

function rotuloDe(iso: string): string {
  const data = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}
