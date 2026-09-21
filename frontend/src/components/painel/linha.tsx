"use client";

import type { Quebra } from "@/lib/api";
import { cheio } from "@/lib/numero";

const L = 300;
const A = 80;
// Meio traco de folga nas bordas, senao o stroke pinta fora do cartao.
const FOLGA = 2;

export default function Linha({ linhas }: { linhas: Quebra[] }) {
  const pontos = linhas.map((l) => l.valor ?? 0);
  if (pontos.length < 2) return null;

  const maior = Math.max(...pontos);
  const menor = Math.min(...pontos, 0);
  const faixa = maior - menor || 1;
  const x = (i: number) => FOLGA + (i / (pontos.length - 1)) * (L - FOLGA * 2);
  const y = (v: number) => FOLGA + (1 - (v - menor) / faixa) * (A - FOLGA * 2);
  const traco = pontos.map((v, i) => `${x(i)},${y(v)}`).join(" ");

  return (
    <div className="space-y-1">
      <svg
        viewBox={`0 0 ${L} ${A}`}
        className="h-20 w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Série de ${linhas.length} pontos`}
      >
        <polygon
          points={`${FOLGA},${A} ${traco} ${L - FOLGA},${A}`}
          className="fill-chart-1 opacity-10"
        />
        <polyline
          points={traco}
          className="stroke-chart-1"
          fill="none"
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
          strokeLinejoin="round"
        />
        {linhas.map((l, i) => (
          <circle
            key={l.rotulo}
            cx={x(i)}
            cy={y(pontos[i])}
            r={6}
            fill="transparent"
          >
            <title>{`${l.rotulo}: ${l.valor === null ? "—" : cheio(l.valor)}`}</title>
          </circle>
        ))}
      </svg>
      <div className="text-muted-foreground flex justify-between text-xs">
        <span>{linhas[0].rotulo}</span>
        <span>{linhas[linhas.length - 1].rotulo}</span>
      </div>
    </div>
  );
}
