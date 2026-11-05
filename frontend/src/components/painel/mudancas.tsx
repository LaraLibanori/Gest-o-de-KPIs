"use client";

import { useEffect, useState } from "react";
import { ArrowDownRight, ArrowUpRight, Sparkles } from "lucide-react";
import {
  api,
  type Fator,
  type IndicadorCalculado,
  type Janela,
  type Mudancas as Dados,
} from "@/lib/api";
import { curto, eixo, ehDinheiro } from "@/lib/numero";
import { variacao } from "@/lib/rotulo";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

const PERIODOS: Record<Janela, string> = {
  "7d": "7 dias",
  "30d": "30 dias",
  "90d": "90 dias",
  "12m": "12 meses",
  tudo: "",
};

const guardados = new Map<string, Dados | null>();
const resumos = new Map<string, string>();

function Lista({
  titulo,
  fatores,
  moeda,
  sobe,
  bom,
}: {
  titulo: string;
  fatores: Fator[];
  moeda: boolean;
  sobe: boolean;
  bom: boolean;
}) {
  if (fatores.length === 0) return null;
  const Icone = sobe ? ArrowUpRight : ArrowDownRight;
  return (
    <div className="space-y-2">
      <p className="text-muted-foreground text-xs">{titulo}</p>
      <ul className="space-y-1.5">
        {fatores.map((f) => {
          const valor = moeda
            ? eixo(Math.abs(f.diferenca), true)
            : curto(Math.abs(f.diferenca));
          return (
            <li
              key={`${f.dimensao}:${f.grupo}`}
              className="flex items-center justify-between gap-3 text-sm"
            >
              <span className="min-w-0 truncate">
                {f.grupo}
                <span className="text-muted-foreground">
                  {" "}
                  · {f.rotulo_dimensao}
                </span>
              </span>
              <span
                className={cn(
                  "inline-flex shrink-0 items-center gap-0.5 font-medium tabular-nums",
                  sobe === bom ? "text-emerald-500" : "text-rose-500",
                )}
              >
                <Icone className="size-3.5" />
                {sobe ? "+" : "−"}
                {valor}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function Mudancas({
  base,
  indicador,
  janela,
}: {
  base: string;
  indicador: IndicadorCalculado;
  janela: Janela;
}) {
  const chave = `${base}:${indicador.id}:${janela}`;
  const ativo = janela !== "tudo" && !!indicador.tempo;
  const [dados, setDados] = useState<{
    chave: string;
    valor: Dados | null;
  } | null>(() =>
    guardados.has(chave) ? { chave, valor: guardados.get(chave)! } : null,
  );
  const [texto, setTexto] = useState<{ chave: string; valor: string } | null>(
    () => (resumos.has(chave) ? { chave, valor: resumos.get(chave)! } : null),
  );
  const [escrevendo, setEscrevendo] = useState(false);
  const [falhou, setFalhou] = useState<string | null>(null);

  useEffect(() => {
    if (!ativo || guardados.has(chave)) return;
    let vivo = true;
    api<Dados>(`${base}/mudancas?indicador=${indicador.id}&janela=${janela}`)
      .catch(() => null)
      .then((r) => {
        guardados.set(chave, r);
        if (vivo) setDados({ chave, valor: r });
      });
    return () => {
      vivo = false;
    };
  }, [ativo, base, chave, indicador.id, janela]);

  if (!ativo) return null;

  const atual =
    dados?.chave === chave
      ? dados
      : guardados.has(chave)
        ? { chave, valor: guardados.get(chave) ?? null }
        : null;
  const mudou = atual?.valor ?? null;
  const resumo =
    texto?.chave === chave ? texto.valor : (resumos.get(chave) ?? null);
  const moeda = ehDinheiro(indicador);
  const periodo = PERIODOS[janela];

  if (
    atual &&
    (!mudou || (mudou.subiram.length === 0 && mudou.cairam.length === 0))
  )
    return null;

  async function explicar() {
    if (!mudou || escrevendo) return;
    setEscrevendo(true);
    setFalhou(null);
    try {
      const r = await api<{ texto: string | null }>(
        `${base}/mudancas/resumo?indicador=${indicador.id}`,
        {
          method: "POST",
          llm: true,
          body: JSON.stringify({ ...mudou, dinheiro: moeda }),
        },
      );
      if (!r.texto) throw new Error();
      resumos.set(chave, r.texto);
      setTexto({ chave, valor: r.texto });
    } catch (e) {
      setFalhou(
        e instanceof Error && e.message.includes("limite")
          ? e.message
          : "A IA não respondeu agora. Os números acima continuam valendo.",
      );
    } finally {
      setEscrevendo(false);
    }
  }

  const sentido =
    mudou?.variacao == null
      ? null
      : mudou.variacao > 0
        ? "subiu"
        : mudou.variacao < 0
          ? "caiu"
          : "ficou estável";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">O que mudou</CardTitle>
        <CardDescription>
          {!mudou ? (
            <Skeleton className="mt-1 h-4 w-72" />
          ) : sentido ? (
            <>
              {indicador.nome} {sentido}{" "}
              <span
                className={cn(
                  "font-medium",
                  (mudou.variacao ?? 0) !== 0 &&
                    ((mudou.variacao ?? 0) > 0 === mudou.subir_e_bom
                      ? "text-emerald-500"
                      : "text-rose-500"),
                )}
              >
                {variacao(mudou.variacao)}
              </span>{" "}
              em relação aos {periodo} anteriores. Veja quem mais pesou.
            </>
          ) : (
            `Quem mais pesou em ${indicador.nome.toLowerCase()} nos últimos ${periodo}.`
          )}
        </CardDescription>
        {mudou && (
          <CardAction>
            <Button
              variant="outline"
              size="sm"
              onClick={explicar}
              disabled={escrevendo || !!resumo}
            >
              <Sparkles
                className={cn("size-4", escrevendo && "animate-pulse")}
              />
              {escrevendo ? "Escrevendo…" : "Explicar com IA"}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {!mudou ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {[0, 1].map((i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="h-5 w-full" />
                <Skeleton className="h-5 w-full" />
              </div>
            ))}
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2">
            <Lista
              titulo="Puxaram para cima"
              fatores={mudou.subiram}
              moeda={moeda}
              sobe
              bom={mudou.subir_e_bom}
            />
            <Lista
              titulo="Puxaram para baixo"
              fatores={mudou.cairam}
              moeda={moeda}
              sobe={false}
              bom={mudou.subir_e_bom}
            />
          </div>
        )}

        {escrevendo && (
          <div className="bg-muted/40 space-y-2 rounded-lg p-3">
            <p className="text-muted-foreground text-xs">
              A IA está lendo os números. Pode levar até um minuto.
            </p>
            <Skeleton className="h-3.5 w-full" />
            <Skeleton className="h-3.5 w-11/12" />
            <Skeleton className="h-3.5 w-2/3" />
          </div>
        )}
        {resumo && (
          <div className="bg-muted/40 animate-in fade-in rounded-lg p-3">
            <p className="text-sm leading-relaxed">{resumo}</p>
            <p className="text-muted-foreground mt-2 flex items-center gap-1 text-xs">
              <Sparkles className="size-3" />
              Escrito pela IA a partir dos números acima.
            </p>
          </div>
        )}
        {falhou && <p className="text-muted-foreground text-xs">{falhou}</p>}
      </CardContent>
    </Card>
  );
}
