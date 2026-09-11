"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CircleCheck,
  CircleSlash,
  Database,
  Loader2,
  MoreHorizontal,
  Plus,
  RefreshCw,
  Table2,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { api, type Conexao, type Verificacao } from "@/lib/api";
import { useOrganizacao } from "./contexto";
import Assistente from "./assistente";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
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
  const [assistente, setAssistente] = useState<{ ativo: boolean; alvo: Conexao | null }>(
    { ativo: false, alvo: null },
  );
  const [verificando, setVerificando] = useState<string | null>(null);
  const [apagando, setApagando] = useState<Conexao | null>(null);

  const souDono = aberta?.papel === "dono";

  const carregar = useCallback(async (organizacaoId: string) => {
    setCarregando(true);
    try {
      setConexoes(await api<Conexao[]>(`/organizacoes/${organizacaoId}/conexoes`));
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível carregar");
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
        toast.success(`${conexao.nome} respondeu. ${r.relacoes.length} tabelas.`);
      else toast.error(r.erro ?? "o banco não respondeu");
      carregar(aberta.id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível verificar");
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
      setConexoes((lista) => lista.filter((c) => c.id !== apagando.id));
      toast.success(`${apagando.nome} removida`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível apagar");
    } finally {
      setApagando(null);
    }
  }

  function fecharAssistente(mudou: boolean) {
    setAssistente({ ativo: false, alvo: null });
    if (mudou && aberta) carregar(aberta.id);
  }

  const ocupado = carregandoOrg || carregando;

  return (
    <div className="mx-auto w-full max-w-6xl p-4 md:p-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Conexões</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Os bancos PostgreSQL de onde os indicadores são calculados.
          </p>
        </div>
        {souDono && conexoes.length > 0 && (
          <Button onClick={() => setAssistente({ ativo: true, alvo: null })}>
            <Plus />
            Nova conexão
          </Button>
        )}
      </div>

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
        <Empty className="border-dashed py-16">
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
              <Button onClick={() => setAssistente({ ativo: true, alvo: null })}>
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
                    <Button
                      size="sm"
                      onClick={() => setAssistente({ ativo: true, alvo: c })}
                    >
                      Continuar
                    </Button>
                  ) : (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => verificar(c)}
                      disabled={verificando === c.id}
                    >
                      {verificando === c.id ? (
                        <Loader2 className="animate-spin" />
                      ) : (
                        <RefreshCw />
                      )}
                      Verificar
                    </Button>
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
                        <DropdownMenuItem
                          onSelect={() => setAssistente({ ativo: true, alvo: c })}
                        >
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
          onFechar={fecharAssistente}
        />
      )}

      <AlertDialog open={apagando !== null} onOpenChange={(o) => !o && setApagando(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Apagar {apagando?.nome}?</AlertDialogTitle>
            <AlertDialogDescription>
              A credencial guardada é descartada. O banco da empresa não é
              alterado, mas os indicadores que dependem dessa conexão param.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction onClick={apagar}>Apagar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
