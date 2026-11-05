"use client";

import type { Dimensao, IndicadorCalculado, Janela } from "@/lib/api";
import { metaPorPonto } from "@/lib/meta";
import { ehDinheiro } from "@/lib/numero";
import Composicao from "@/components/painel/composicao";
import Evolucao from "@/components/painel/evolucao";
import Mudancas from "@/components/painel/mudancas";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const SEM_ZERO = new Set(["media", "minimo", "maximo"]);
const SOMAVEIS = new Set(["soma", "contagem", "distintos"]);
export const APARAR = new Set(["90d", "12m", "tudo"]);
const BALDES: Record<string, string> = {
  "7d": "por dia, últimos 7 dias",
  "30d": "por dia, últimos 30 dias",
  "90d": "por semana, últimos 90 dias",
  "12m": "por mês, últimos 12 meses",
  tudo: "por mês, todo o período",
};

export default function Destaque({
  indicador,
  base,
  dimensoes,
  janela,
  rotuloDe,
  carregandoSerie = false,
  origem,
  acao,
}: {
  indicador: IndicadorCalculado;
  base: string;
  dimensoes: Dimensao[] | null;
  janela: string;
  rotuloDe: (coluna: string | null) => string;
  carregandoSerie?: boolean;
  origem?: string;
  acao?: React.ReactNode;
}) {
  const forma = indicador.grafico;
  const moeda = ehDinheiro(indicador);
  const comGrafico = forma === "linha" || forma === "numero";

  const evolucao = (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">
          {indicador.nome}
          {origem && (
            <span className="text-muted-foreground font-normal">
              {" "}
              · {origem}
            </span>
          )}
        </CardTitle>
        <CardDescription>{BALDES[janela] ?? ""}</CardDescription>
        {acao && comGrafico && <CardAction>{acao}</CardAction>}
      </CardHeader>
      <CardContent>
        <Evolucao
          pontos={indicador.serie}
          rotulo={indicador.nome}
          total={SOMAVEIS.has(indicador.agregacao) ? indicador.valor : null}
          zero={!SEM_ZERO.has(indicador.agregacao)}
          carregando={carregandoSerie}
          moeda={moeda}
          aparar={APARAR.has(janela)}
          meta={metaPorPonto(
            indicador.meta,
            indicador.agregacao,
            janela as Janela,
          )}
        />
      </CardContent>
    </Card>
  );

  const composicao = (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Divisão de {indicador.nome}</CardTitle>
        <CardDescription>Clique numa linha para ver o detalhe.</CardDescription>
        {acao && !comGrafico && <CardAction>{acao}</CardAction>}
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

  const graficos =
    forma === "linha" ? (
      evolucao
    ) : forma === "numero" ? (
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        {evolucao}
        {composicao}
      </div>
    ) : (
      <div className="max-w-2xl">{composicao}</div>
    );

  return (
    <div className="space-y-4">
      <Mudancas base={base} indicador={indicador} janela={janela as Janela} />
      {graficos}
    </div>
  );
}
