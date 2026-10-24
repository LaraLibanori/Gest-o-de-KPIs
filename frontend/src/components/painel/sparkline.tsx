"use client";

import { Area, AreaChart, YAxis } from "recharts";
import type { Quebra } from "@/lib/api";
import { ChartContainer } from "@/components/ui/chart";

export default function Sparkline({
  pontos,
  className = "h-10 w-full",
  aparar = false,
}: {
  pontos: Quebra[];
  className?: string;
  aparar?: boolean;
}) {
  const todos = pontos.filter((p) => p.valor !== null);
  const validos = aparar && todos.length > 4 ? todos.slice(1, -1) : todos;
  if (validos.length < 2) return <div className={className} aria-hidden />;

  const cor = "var(--chart-1)";

  return (
    <ChartContainer
      config={{ valor: { color: cor } }}
      className={`aspect-auto ${className}`}
      aria-hidden
    >
      <AreaChart
        data={validos}
        margin={{ top: 2, bottom: 2, left: 0, right: 0 }}
      >
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <Area
          dataKey="valor"
          type="monotone"
          stroke="var(--color-valor)"
          fill="var(--color-valor)"
          fillOpacity={0.14}
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ChartContainer>
  );
}
