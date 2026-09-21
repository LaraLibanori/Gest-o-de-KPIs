"use client";

import { TriangleAlert } from "lucide-react";
import {
  FRASES,
  PERIODOS,
  type IndicadorCalculado,
  type Periodo,
} from "@/lib/api";
import { cheio, curto } from "@/lib/numero";
import Barras from "@/components/painel/barras";
import Linha from "@/components/painel/linha";
import Pizza from "@/components/painel/pizza";
import Tabela from "@/components/painel/tabela";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Cartao({
  indicador,
  rotulo,
}: {
  indicador: IndicadorCalculado;
  rotulo: (coluna: string | null) => string;
}) {
  const periodo: Periodo | null = indicador.periodo;
  const legenda = [
    FRASES[indicador.agregacao](rotulo(indicador.coluna)),
    indicador.dimensao ? `por ${rotulo(indicador.dimensao)}` : null,
    periodo && periodo !== "sempre" ? PERIODOS[periodo] : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card>
      <CardHeader>
        <CardTitle>{indicador.nome}</CardTitle>
        <CardDescription className="truncate">{legenda}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {indicador.erro ? (
          <p className="text-muted-foreground flex items-start gap-1.5 text-sm">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" />
            {indicador.erro}
          </p>
        ) : (
          <p
            className="text-3xl font-semibold tabular-nums"
            title={
              indicador.valor === null ? undefined : cheio(indicador.valor)
            }
          >
            {indicador.valor === null ? "—" : curto(indicador.valor)}
          </p>
        )}
        {indicador.linhas.length > 0 &&
          (indicador.grafico === "linha" ? (
            <Linha linhas={indicador.linhas} />
          ) : indicador.grafico === "pizza" ? (
            <Pizza linhas={indicador.linhas} />
          ) : indicador.grafico === "tabela" ? (
            <Tabela linhas={indicador.linhas} />
          ) : (
            <Barras linhas={indicador.linhas} />
          ))}
      </CardContent>
    </Card>
  );
}
