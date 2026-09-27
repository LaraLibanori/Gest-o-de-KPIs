"use client";

import type { Quebra } from "@/lib/api";

// Sparkline e contexto, nao leitura: o numero vive no tile e o desenho aqui
// serve para o olho pegar a direcao antes mesmo de ler.
export default function Sparkline({
  pontos,
  className = "h-10 w-full",
}: {
  pontos: Quebra[];
  className?: string;
}) {
  const valores = pontos
    .map((p) => p.valor)
    .filter((v): v is number => v !== null);
  if (valores.length < 2) return <div className={className} aria-hidden />;

  const menor = Math.min(...valores);
  const faixa = Math.max(...valores) - menor || Math.abs(Math.max(...valores)) || 1;
  const ultimo = valores[valores.length - 1];
  const primeiro = valores[0];
  const subiu = ultimo >= primeiro;

  const L = 100;
  const A = 32;
  const x = (i: number) => (i / (valores.length - 1)) * L;
  const y = (v: number) => A - 2 - ((v - menor) / faixa) * (A - 4);

  const linha = valores.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  const area = `0,${A} ${linha} ${L},${A}`;
  const cor = subiu ? "var(--color-chart-1)" : "var(--color-chart-4)";

  return (
    <svg
      viewBox={`0 0 ${L} ${A}`}
      className={className}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polygon points={area} fill={cor} opacity={0.14} />
      <polyline
        points={linha}
        fill="none"
        stroke={cor}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
