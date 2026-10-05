"use client";

import type { Dimensao, IndicadorCalculado } from "@/lib/api";
import Composicao from "@/components/painel/composicao";
import Evolucao from "@/components/painel/evolucao";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const SEM_ZERO = new Set(["media", "minimo", "maximo"]);
const SOMAVEIS = new Set(["soma", "contagem", "distintos"]);

export default function Destaque({
  indicador,
  base,
  dimensoes,
  janela,
  rotuloDe,
  carregandoSerie = false,
  origem,
}: {
  indicador: IndicadorCalculado;
  base: string;
  dimensoes: Dimensao[];
  janela: string;
  rotuloDe: (coluna: string | null) => string;
  carregandoSerie?: boolean;
  origem?: string;
}) {
  const forma = indicador.grafico;
  const variacao =
    indicador.variacao === null
      ? "sem período anterior"
      : `variação de ${indicador.variacao.toFixed(1).replace(".", ",")}%`;

  const evolucao = (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{indicador.nome}</CardTitle>
        <CardDescription>
          {[origem, variacao].filter(Boolean).join(" · ")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Evolucao
          pontos={indicador.serie}
          rotulo={indicador.nome}
          total={SOMAVEIS.has(indicador.agregacao) ? indicador.valor : null}
          zero={!SEM_ZERO.has(indicador.agregacao)}
          carregando={carregandoSerie}
        />
        <p className="text-muted-foreground mt-2 text-xs">
          Passe o mouse ou use as setas do teclado para ver o valor de cada
          período.
        </p>
      </CardContent>
    </Card>
  );

  const composicao = (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Composição</CardTitle>
        <CardDescription>
          Como {indicador.nome.toLowerCase()} se reparte
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Composicao
          key={indicador.id}
          base={base}
          indicador={indicador}
          dimensoes={dimensoes}
          janela={janela}
          rotuloDe={rotuloDe}
          forma={forma === "pizza" || forma === "tabela" ? forma : "barra"}
        />
      </CardContent>
    </Card>
  );

  if (forma === "linha") return evolucao;
  if (forma === "numero")
    return (
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        {evolucao}
        {composicao}
      </div>
    );
  return <div className="max-w-2xl">{composicao}</div>;
}
