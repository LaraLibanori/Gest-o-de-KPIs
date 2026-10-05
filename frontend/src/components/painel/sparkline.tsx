"use client";

import { Area, AreaChart, YAxis } from "recharts";
import type { Quebra } from "@/lib/api";
import { ChartContainer } from "@/components/ui/chart";

export default function Sparkline({
  pontos,
  className = "h-10 w-full",
}: {
  pontos: Quebra[];
  className?: string;
}) {
  const validos = pontos.filter((p) => p.valor !== null);
  if (validos.length < 2) return <div className={className} aria-hidden />;

  const subiu =
    (validos[validos.length - 1].valor as number) >=
    (validos[0].valor as number);
  const cor = subiu ? "var(--chart-1)" : "var(--chart-4)";

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
