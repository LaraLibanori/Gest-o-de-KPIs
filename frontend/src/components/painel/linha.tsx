"use client";

import type { Quebra } from "@/lib/api";
import { cheio } from "@/lib/numero";

const L = 300;
const A = 80;
// Meio traco de folga nas bordas, senao o stroke pinta fora do cartao.
const FOLGA = 2;

export default function Linha({ linhas }: { linhas: Quebra[] }) {
  const cheios = linhas.filter((l) => l.valor !== null);
  if (cheios.length < 2) return null;

  // Sem base zero: numero longe de zero deixaria a tendencia achatada.
  const valores = cheios.map((l) => l.valor as number);
  const maior = Math.max(...valores);
  const menor = Math.min(...valores);
  const faixa = maior - menor || Math.abs(maior) || 1;
  const x = (i: number) => FOLGA + (i / (linhas.length - 1)) * (L - FOLGA * 2);
  const y = (v: number) => FOLGA + (1 - (v - menor) / faixa) * (A - FOLGA * 2);
  // Vazio virou buraco, nao zero: o traco quebra e recomeca.
  const trechos: [number, number][][] = [];
  let corrente: [number, number][] = [];
  linhas.forEach((l, i) => {
    if (l.valor === null) {
      if (corrente.length) trechos.push(corrente);
      corrente = [];
      return;
    }
    corrente.push([x(i), y(l.valor)]);
  });
  if (corrente.length) trechos.push(corrente);

  return (
    <div className="space-y-1">
      <svg
        viewBox={`0 0 ${L} ${A}`}
        className="h-20 w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Série de ${linhas.length} pontos`}
      >
        {trechos.map(([primeiro, ...resto]) =>
          // Ponto sozinho entre dois vazios: polyline de um ponto nao desenha nada.
          resto.length ? (
            <polyline
              key={String(primeiro)}
              points={[primeiro, ...resto].map((p) => p.join(",")).join(" ")}
              className="stroke-chart-1"
              fill="none"
              strokeWidth={2}
              vectorEffect="non-scaling-stroke"
              strokeLinejoin="round"
            />
          ) : (
            <circle
              key={String(primeiro)}
              cx={primeiro[0]}
              cy={primeiro[1]}
              r={2}
              className="fill-chart-1"
            />
          ),
        )}
        {cheios.map((l) => (
          <circle
            key={l.rotulo}
            cx={x(linhas.indexOf(l))}
            cy={y(l.valor as number)}
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
