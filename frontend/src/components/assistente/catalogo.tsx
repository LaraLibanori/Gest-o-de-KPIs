"use client";

import { ArrowLeft, Hash, Sparkles, Type } from "lucide-react";
import type { Campo, PapelCampo } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const PAPEIS: { valor: PapelCampo; rotulo: string }[] = [
  { valor: "metrica", rotulo: "Métrica" },
  { valor: "dimensao", rotulo: "Dimensão" },
  { valor: "tempo", rotulo: "Tempo" },
  { valor: "ignorar", rotulo: "Ignorar" },
];

const COR: Record<PapelCampo, string> = {
  metrica: "text-chart-1",
  dimensao: "text-chart-2",
  tempo: "text-chart-3",
  ignorar: "text-muted-foreground",
};

const NUMERICA = /^(smallint|integer|bigint|numeric|decimal|real|double|money)/;
const IDENTIFICADOR = /^id$|^id_|_id$/i;

function numerica(c: Campo) {
  return NUMERICA.test(c.tipo);
}

function esquecida(c: Campo) {
  return c.papel === "ignorar" && numerica(c) && !IDENTIFICADOR.test(c.coluna);
}

export default function PassoCatalogo({
  campos,
  tabela,
  ocupado,
  sugerindo,
  rotuloCancelar,
  onVoltar,
  onMudarPapel,
  onFechar,
  onAvancar,
}: {
  campos: Campo[];
  tabela: string | null;
  ocupado: boolean;
  sugerindo: boolean;
  rotuloCancelar: string;
  onVoltar: () => void;
  onMudarPapel: (campo: Campo, papel: PapelCampo) => void;
  onFechar: () => void;
  onAvancar: () => void;
}) {
  const contagem = (papel: PapelCampo) =>
    campos.filter((c) => c.papel === papel).length;

  const metricas = contagem("metrica");
  const dimensoes = contagem("dimensao");
  const tempos = contagem("tempo");
  const semTempo = tempos === 0;
  const numericasSemPapel = campos.filter(esquecida).length;
  const plural = (n: number, um: string, muitos: string) =>
    `${n} ${n === 1 ? um : muitos}`;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <p className="text-sm">
          <span className="font-mono">{tabela}</span>
        </p>
        <ul className="text-muted-foreground flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
          <li className="text-chart-1">
            {plural(metricas, "métrica", "métricas")}
          </li>
          <li className="text-chart-2">
            {plural(dimensoes, "dimensão", "dimensões")}
          </li>
          <li className="text-chart-3">
            {plural(tempos, "coluna de tempo", "colunas de tempo")}
          </li>
          {sugerindo && (
            <li className="flex items-center gap-1">
              <Sparkles className="size-3 animate-pulse" />
              sugerindo nomes
            </li>
          )}
        </ul>
      </div>

      {semTempo && !ocupado && (
        <p className="rounded-lg border border-dashed p-3 text-xs">
          Nenhuma coluna de data. Sem ela o filtro de período não funciona, mas
          o resto do painel continua valendo.
        </p>
      )}

      {numericasSemPapel > 0 && !ocupado && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3">
          <p className="text-xs">
            {numericasSemPapel} coluna{numericasSemPapel === 1 ? "" : "s"}{" "}
            numérica{numericasSemPapel === 1 ? "" : "s"}{" "}
            {numericasSemPapel === 1 ? "está ignorada" : "estão ignoradas"}.
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              campos
                .filter(esquecida)
                .forEach((c) => onMudarPapel(c, "metrica"))
            }
          >
            <Hash className="size-4" />
            Virar métrica
          </Button>
        </div>
      )}

      {ocupado ? (
        <div className="space-y-1.5">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      ) : campos.length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">
          A tabela não tem colunas visíveis para esse usuário.
        </p>
      ) : (
        <ul className="max-h-80 divide-y overflow-y-auto rounded-lg border">
          {campos.map((c) => (
            <li key={c.id} className="flex items-center gap-3 p-2.5">
              {numerica(c) ? (
                <Hash className="text-chart-1 size-4 shrink-0" />
              ) : (
                <Type className="text-chart-2 size-4 shrink-0" />
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm">
                  {c.rotulo ?? <span className="font-mono">{c.coluna}</span>}
                </p>
                <p className="text-muted-foreground truncate text-xs">
                  {c.rotulo && <span className="font-mono">{c.coluna} · </span>}
                  {c.tipo}
                  {c.cardinalidade !== null &&
                    ` · ${c.cardinalidade.toLocaleString("pt-BR")} valores`}
                </p>
              </div>
              {!c.confirmado && <Badge variant="outline">sugerido</Badge>}
              <Select
                value={c.papel}
                onValueChange={(v) => onMudarPapel(c, v as PapelCampo)}
              >
                <SelectTrigger
                  className={cn("w-32", COR[c.papel])}
                  size="sm"
                  aria-label={`Papel de ${c.rotulo ?? c.coluna}`}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAPEIS.map((p) => (
                    <SelectItem key={p.valor} value={p.valor}>
                      {p.rotulo}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center gap-2 border-t pt-4">
        <Button variant="ghost" onClick={onVoltar}>
          <ArrowLeft className="size-4" />
          Voltar
        </Button>
        <Button variant="ghost" onClick={onFechar}>
          {rotuloCancelar}
        </Button>
        <div className="flex-1" />
        <Button
          onClick={onAvancar}
          disabled={ocupado || sugerindo || campos.length === 0}
        >
          Confirmar e montar indicadores
        </Button>
      </div>
    </div>
  );
}
