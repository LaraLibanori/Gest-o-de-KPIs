"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  ChartNoAxesColumn,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import { api, type Campo, type Conexao, type Painel } from "@/lib/api";
import { falhar } from "@/lib/erros";
import Cartao from "@/components/painel/cartao";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrganizacao } from "../../contexto";

export default function PainelDaConexao() {
  const { id } = useParams<{ id: string }>();
  const { aberta, carregando: carregandoOrg } = useOrganizacao();
  const [conexao, setConexao] = useState<Conexao | null>(null);
  const [painel, setPainel] = useState<Painel | null>(null);
  const [campos, setCampos] = useState<Campo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const base = aberta ? `/organizacoes/${aberta.id}/conexoes` : null;

  const buscar = useCallback(async () => {
    if (!base) return;
    setCarregando(true);
    try {
      const [lista, catalogo, dados] = await Promise.all([
        api<Conexao[]>(base),
        api<Campo[]>(`${base}/${id}/catalogo`),
        api<Painel>(`${base}/${id}/painel`),
      ]);
      setConexao(lista.find((c) => c.id === id) ?? null);
      setCampos(catalogo);
      setPainel(dados);
      setErro(null);
    } catch (e) {
      // Sem isso a falha viraria o estado vazio, que diz outra coisa.
      setErro(e instanceof Error ? e.message : "não foi possível carregar");
      falhar(e, "não foi possível carregar o painel");
    } finally {
      setCarregando(false);
    }
  }, [base, id]);

  useEffect(() => {
    if (!carregandoOrg) buscar();
  }, [carregandoOrg, buscar]);

  const rotulo = (coluna: string | null) =>
    campos.find((c) => c.coluna === coluna)?.rotulo ?? coluna ?? "";

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Button variant="ghost" size="sm" className="-ml-2 mb-1" asChild>
            <Link href="/">
              <ArrowLeft />
              Conexões
            </Link>
          </Button>
          <h1 className="truncate text-2xl font-semibold">
            {conexao?.nome ?? "Painel"}
          </h1>
          <p className="text-muted-foreground truncate text-sm">
            {painel?.tabela ? (
              <span className="font-mono">{painel.tabela}</span>
            ) : (
              "Os indicadores calculados a partir da tabela fato."
            )}
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={buscar}
          disabled={carregando}
          aria-label="Atualizar"
        >
          <RefreshCw className={carregando ? "animate-spin" : undefined} />
          Atualizar
        </Button>
      </div>

      {(erro ?? painel?.erro) && (
        <p className="text-muted-foreground flex items-start gap-2 rounded-lg border border-dashed p-4 text-sm">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          {erro ?? painel?.erro}
        </p>
      )}

      {carregando ? (
        <div className="grid items-start gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      ) : erro ? null : painel && painel.indicadores.length > 0 ? (
        <div className="grid items-start gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {painel.indicadores.map((i) => (
            <Cartao key={i.id} indicador={i} rotulo={rotulo} />
          ))}
        </div>
      ) : (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ChartNoAxesColumn />
            </EmptyMedia>
            <EmptyTitle>Nenhum indicador ainda</EmptyTitle>
            <EmptyDescription>
              Volte para as conexões e use{" "}
              <span className="text-foreground">Revisar campos</span> para
              montar os indicadores desta conexão.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}
    </div>
  );
}
