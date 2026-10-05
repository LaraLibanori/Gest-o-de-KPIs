"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  CircleCheck,
  CircleSlash,
  Database,
  Loader2,
  MoreHorizontal,
  Pencil,
  Plus,
  RefreshCw,
  Table2,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { falhar } from "@/lib/erros";
import { api, type Conexao, type Verificacao } from "@/lib/api";
import { useOrganizacao } from "./contexto";
import Assistente from "./assistente";
import { Badge } from "@/components/ui/badge";
import Confirmar from "@/components/confirmar";
import { Cabecalho, Pagina } from "@/components/pagina";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { paineis } from "@/lib/paineis";

function quando(iso: string | null) {
  if (!iso) return "nunca verificada";
  const dias = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (dias === 0) return "verificada hoje";
  if (dias === 1) return "verificada ontem";
  return `verificada há ${dias} dias`;
}

function Situacao({ conexao }: { conexao: Conexao }) {
  if (conexao.etapa !== "pronta")
    return <Badge variant="outline">configuração incompleta</Badge>;
  if (conexao.verificacao_erro)
    return (
      <Badge variant="destructive">
        <CircleSlash />
        sem resposta
      </Badge>
    );
  return (
    <Badge variant="secondary">
      <CircleCheck />
      conectada
    </Badge>
  );
}

export default function Conexoes() {
  const { aberta, carregando: carregandoOrg } = useOrganizacao();
  const [conexoes, setConexoes] = useState<Conexao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [assistente, setAssistente] = useState<{
    ativo: boolean;
    alvo: Conexao | null;
    editar: boolean;
  }>({ ativo: false, alvo: null, editar: false });
  const [verificando, setVerificando] = useState<string | null>(null);
  const [apagando, setApagando] = useState<Conexao | null>(null);

  const souDono = aberta?.papel === "dono";

  const carregar = useCallback(async (organizacaoId: string) => {
    setCarregando(true);
    try {
      setConexoes(
        await api<Conexao[]>(`/organizacoes/${organizacaoId}/conexoes`),
      );
    } catch (e) {
      falhar(e, "não foi possível carregar");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    if (aberta) carregar(aberta.id);
    else if (!carregandoOrg) setCarregando(false);
  }, [aberta, carregandoOrg, carregar]);

  async function verificar(conexao: Conexao) {
    if (!aberta) return;
    setVerificando(conexao.id);
    try {
      const r = await api<Verificacao>(
        `/organizacoes/${aberta.id}/conexoes/${conexao.id}/verificar`,
        { method: "POST" },
      );
      if (r.ok)
        toast.success(
          `${conexao.nome} respondeu. ${r.relacoes.length} tabelas.`,
        );
      else toast.error(r.erro ?? "o banco não respondeu");
      carregar(aberta.id);
    } catch (e) {
      falhar(e, "não foi possível verificar");
    } finally {
      setVerificando(null);
    }
  }

  async function apagar() {
    if (!aberta || !apagando) return;
    try {
      await api<void>(`/organizacoes/${aberta.id}/conexoes/${apagando.id}`, {
        method: "DELETE",
      });
      paineis.clear();
      setConexoes((lista) => lista.filter((c) => c.id !== apagando.id));
      toast.success(`${apagando.nome} removida`);
    } catch (e) {
      falhar(e, "não foi possível apagar");
    } finally {
      setApagando(null);
    }
  }

  function fecharAssistente(mudou: boolean) {
    setAssistente({ ativo: false, alvo: null, editar: false });
    if (!mudou) return;
    paineis.clear();
    if (aberta) carregar(aberta.id);
  }

  const abrir = (alvo: Conexao | null, editar = false) =>
    setAssistente({ ativo: true, alvo, editar });

  const ocupado = carregandoOrg || carregando;

  return (
    <Pagina>
      <Cabecalho
        titulo="Conexões"
        descricao="Os bancos PostgreSQL de onde os indicadores são calculados."
        acoes={
          souDono && conexoes.length > 0 ? (
            <Button onClick={() => abrir(null)}>
              <Plus />
              Nova conexão
            </Button>
          ) : null
        }
      />

      {ocupado ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardFooter>
                <Skeleton className="h-4 w-24" />
              </CardFooter>
            </Card>
          ))}
        </div>
      ) : !aberta ? (
        <Empty className="border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Database />
            </EmptyMedia>
            <EmptyTitle>Crie uma organização primeiro</EmptyTitle>
            <EmptyDescription>
              As conexões pertencem a uma organização. Use o seletor no topo da
              barra lateral para criar a sua.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : conexoes.length === 0 ? (
        <Empty className="border-dashed py-10">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Database />
            </EmptyMedia>
            <EmptyTitle>Conecte seu primeiro banco</EmptyTitle>
            <EmptyDescription>
              Aponte para o PostgreSQL da empresa e escolha a tabela fato. A
              partir dela a plataforma sugere quais campos viram métrica e quais
              viram dimensão.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            {souDono ? (
              <Button onClick={() => abrir(null)}>
                <Plus />
                Adicionar conexão
              </Button>
            ) : (
              <p className="text-muted-foreground text-sm">
                Só o dono da organização pode adicionar conexões.
              </p>
            )}
          </EmptyContent>
        </Empty>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {conexoes.map((c) => (
            <Card key={c.id} className="gap-4">
              <CardHeader>
                <CardTitle className="truncate">{c.nome}</CardTitle>
                <CardDescription className="font-mono text-xs break-all">
                  {c.usuario}@{c.host}:{c.porta}/{c.banco}
                  {c.esquema ? ` · ${c.esquema}` : ""}
                </CardDescription>
              </CardHeader>

              <CardContent className="flex flex-wrap items-center gap-2">
                <Situacao conexao={c} />
                {c.tabela_fato ? (
                  <Badge variant="outline" className="font-mono">
                    <Table2 />
                    {c.tabela_fato}
                  </Badge>
                ) : (
                  <Badge variant="outline">sem tabela fato</Badge>
                )}
              </CardContent>

              <CardFooter className="justify-between">
                <span className="text-muted-foreground text-xs">
                  {quando(c.verificada_em)}
                </span>
                <div className="flex items-center gap-1">
                  {souDono && c.etapa !== "pronta" ? (
                    <Button size="sm" onClick={() => abrir(c)}>
                      Continuar
                    </Button>
                  ) : (
                    <>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={() => verificar(c)}
                        disabled={verificando === c.id}
                        aria-label={`Verificar ${c.nome}`}
                      >
                        {verificando === c.id ? (
                          <Loader2 className="animate-spin" />
                        ) : (
                          <RefreshCw />
                        )}
                      </Button>
                      <Button size="sm" asChild>
                        <Link href={`/conexoes/${c.id}`}>Ver painel</Link>
                      </Button>
                    </>
                  )}
                  {souDono && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8"
                          aria-label={`Ações de ${c.nome}`}
                        >
                          <MoreHorizontal />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => abrir(c, true)}>
                          <Pencil />
                          Editar conexão
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => abrir(c)}>
                          <Table2 />
                          Revisar campos
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          variant="destructive"
                          onSelect={() => setApagando(c)}
                        >
                          <Trash2 />
                          Apagar conexão
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {aberta && (
        <Assistente
          organizacaoId={aberta.id}
          conexao={assistente.alvo}
          aberto={assistente.ativo}
          editar={assistente.editar}
          onFechar={fecharAssistente}
        />
      )}

      <Confirmar
        aberto={apagando !== null}
        titulo={`Apagar ${apagando?.nome ?? "a conexão"}?`}
        descricao="A credencial guardada é descartada. O banco da empresa não é alterado, mas os indicadores que dependem dessa conexão param."
        onConfirmar={apagar}
        onFechar={() => setApagando(null)}
      />
    </Pagina>
  );
}
