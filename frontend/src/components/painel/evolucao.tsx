"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { Quebra } from "@/lib/api";
import { cheio, curto } from "@/lib/numero";
import { cn } from "@/lib/utils";

const L = 720;
const A = 240;
const MARGEM = { topo: 16, direita: 16, base: 28, esquerda: 52 };
const INTERNO_L = L - MARGEM.esquerda - MARGEM.direita;
const INTERNO_A = A - MARGEM.topo - MARGEM.base;

// Soma, contagem e distintos sao quantidades absolutas: comecar em zero e o que
// nao deixa a linha parecer maior do que e. Media, minimo e maximo sao um
// nivel, e zero so achata a leitura.
function escala(valores: number[], zero: boolean) {
  const maior = Math.max(...valores);
  const menor = zero ? Math.min(0, ...valores) : Math.min(...valores);
  const bruto = Math.max(...valores) - Math.min(0, ...valores) || Math.abs(maior) || 1;
  const folga = bruto * 0.12;
  const topo = maior + (maior > 0 ? folga : 0);
  const piso = zero
    ? Math.min(0, menor - folga)
    : Math.min(menor - folga, maior * 0.8);
  const y = (v: number) =>
    MARGEM.topo + (1 - (v - piso) / (topo - piso || 1)) * INTERNO_A;
  const tiques: { v: number; y: number }[] = [];
  const passos = 4;
  for (let i = 0; i <= passos; i++) {
    const v = piso + ((topo - piso) * i) / passos;
    tiques.push({ v, y: y(v) });
  }
  return { y, tiques, base: piso };
}

export default function Evolucao({
  pontos,
  rotulo,
  total,
  zero = true,
}: {
  pontos: Quebra[];
  rotulo: string;
  total: number | null;
  zero?: boolean;
}) {
  const [ativo, setAtivo] = useState<number | null>(null);
  const caixa = useRef<HTMLDivElement>(null);

  // n e a posicao depois do filtro: o indice original pula com os nulos e
  // empurra os pontos seguintes para fora do grafico.
  const validos = useMemo(
    () => pontos.filter((p) => p.valor !== null).map((p, n) => ({ ...p, n })),
    [pontos],
  );

  const { y, tiques, base } = useMemo(
    () => escala(validos.map((p) => p.valor as number), zero),
    [validos, zero],
  );

  const x = useCallback(
    (n: number) =>
      MARGEM.esquerda +
      (validos.length < 2 ? INTERNO_L / 2 : (n / (validos.length - 1)) * INTERNO_L),
    [validos.length],
  );

  const traco = useMemo(
    () =>
      validos
        .map((p) => `${p.n === 0 ? "M" : "L"}${x(p.n)},${y(p.valor as number)}`)
        .join(" "),
    [validos, x, y],
  );

  const area = useMemo(() => {
    if (validos.length < 2) return "";
    const primeiro = validos[0];
    const ultimo = validos[validos.length - 1];
    return `${traco} L${x(ultimo.n)},${y(base)} L${x(primeiro.n)},${y(base)} Z`;
  }, [validos, traco, x, y, base]);

  // O ponteiro vira indice pelo mais proximo, e nao por proporcao do pixel: o
  // eixo temporal nao e uniforme quando o balde muda de granularidade.
  const mover = useCallback(
    (clientX: number) => {
      const caixa_ = caixa.current?.getBoundingClientRect();
      if (!caixa_ || validos.length === 0) return;
      const px = ((clientX - caixa_.left) / caixa_.width) * L;
      let melhor = 0;
      let menor = Infinity;
      validos.forEach((p) => {
        const d = Math.abs(x(p.n) - px);
        if (d < menor) {
          menor = d;
          melhor = p.n;
        }
      });
      setAtivo(melhor);
    },
    [caixa, validos, x],
  );

  const teclado = useCallback(
    (e: React.KeyboardEvent) => {
      if (validos.length === 0) return;
      const salto = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
      if (salto === 0 && e.key !== "Home" && e.key !== "End") return;
      e.preventDefault();
      setAtivo((atual) => {
        if (e.key === "Home") return 0;
        if (e.key === "End") return validos.length - 1;
        const base_ = atual === null ? validos.length - 1 : atual;
        return Math.max(0, Math.min(validos.length - 1, base_ + salto));
      });
    },
    [validos.length],
  );

  if (validos.length < 2)
    return (
      <div className="text-muted-foreground flex h-60 items-center justify-center text-sm">
        Sem série temporal para desenhar
      </div>
    );

  const ponto = ativo === null ? null : validos[ativo];
  const anterior = ativo !== null && ativo > 0 ? validos[ativo - 1].valor : null;
  const mudanca =
    ponto && anterior !== null && anterior !== 0
      ? (((ponto.valor as number) - anterior) / Math.abs(anterior)) * 100
      : null;

  return (
    <div ref={caixa} className="relative">
      <svg
        viewBox={`0 0 ${L} ${A}`}
        className="h-60 w-full touch-none focus-visible:ring-ring/50 rounded-sm focus-visible:ring-2 focus-visible:outline-none"
        role="application"
        aria-label={`${rotulo} ao longo do tempo. Use as setas para percorrer os períodos.`}
        tabIndex={0}
        onPointerMove={(e) => mover(e.clientX)}
        onPointerDown={(e) => mover(e.clientX)}
        onPointerLeave={() => setAtivo(null)}
        onKeyDown={teclado}
        onBlur={() => setAtivo(null)}
      >
        <defs>
          <linearGradient id="preenche" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.34} />
            <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0.02} />
          </linearGradient>
        </defs>

        {tiques.map((t, i) => (
          <g key={i}>
            <line
              x1={MARGEM.esquerda}
              x2={L - MARGEM.direita}
              y1={t.y}
              y2={t.y}
              stroke="var(--color-border)"
              strokeDasharray={i === 0 ? undefined : "3 4"}
              opacity={0.6}
            />
            <text
              x={MARGEM.esquerda - 8}
              y={t.y + 4}
              textAnchor="end"
              className="fill-muted-foreground text-[10px]"
            >
              {curto(t.v)}
            </text>
          </g>
        ))}

        {area && <path d={area} fill="url(#preenche)" />}
        <path
          d={traco}
          fill="none"
          stroke="var(--color-chart-1)"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {ponto && (
          <g>
            <line
              x1={x(ponto.n)}
              x2={x(ponto.n)}
              y1={MARGEM.topo}
              y2={A - MARGEM.base}
              stroke="var(--color-chart-1)"
              strokeWidth={1}
              strokeDasharray="3 3"
              opacity={0.7}
            />
            <circle
              cx={x(ponto.n)}
              cy={y(ponto.valor as number)}
              r={5}
              fill="var(--color-chart-1)"
              stroke="var(--color-background)"
              strokeWidth={2}
            />
          </g>
        )}

        <text
          x={MARGEM.esquerda}
          y={A - 8}
          className="fill-muted-foreground text-[10px]"
        >
          {rotuloDe(pontos[0]?.rotulo)}
        </text>
        <text
          x={L - MARGEM.direita}
          y={A - 8}
          textAnchor="end"
          className="fill-muted-foreground text-[10px]"
        >
          {rotuloDe(pontos[pontos.length - 1]?.rotulo)}
        </text>
      </svg>

      {ponto && (
        <div
          className={cn(
            "bg-popover text-popover-foreground pointer-events-none absolute top-2 z-10 w-44 rounded-lg border p-2.5 shadow-lg",
            (ativo ?? 0) > validos.length / 2 ? "left-2" : "right-2",
          )}
        >
          <p className="text-muted-foreground text-[11px]">
            {rotuloDe(ponto.rotulo)}
          </p>
          <p className="mt-0.5 text-lg leading-none font-semibold tabular-nums">
            {curto(ponto.valor as number)}
          </p>
          <p className="text-muted-foreground mt-1 text-[11px] tabular-nums">
            {cheio(ponto.valor as number)}
            {mudanca !== null && (
              <span
                className={cn(
                  "ml-1 font-medium",
                  mudanca >= 0 ? "text-emerald-500" : "text-rose-500",
                )}
              >
                {mudanca >= 0 ? "+" : ""}
                {mudanca.toFixed(1).replace(".", ",")}%
              </span>
            )}
          </p>
        </div>
      )}

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

// 2026-09-01 vira 01/set, que cabe no eixo e ainda diz o mes.
function rotuloDe(iso: string | undefined): string {
  if (!iso) return "";
  const data = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(data.getTime())) return iso;
  return data.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
}
