"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { LayoutDashboard, Plus } from "lucide-react";
import { toast } from "sonner";
import { api, type Dashboard, type Janela } from "@/lib/api";
import { curto } from "@/lib/numero";
import ControleJanela from "@/components/painel/janela";
import { Cabecalho, Pagina } from "@/components/pagina";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Field,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrganizacao } from "../contexto";

export default function Dashboards() {
  const { aberta } = useOrganizacao();
  const [lista, setLista] = useState<Dashboard[]>([]);
  const [janela, setJanela] = useState<Janela>("30d");
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [aberto, setAberto] = useState(false);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [erroForm, setErroForm] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  const base = aberta ? `/organizacoes/${aberta.id}/dashboards` : null;

  const carregar = useCallback(async () => {
    if (!base) return;
    setCarregando(true);
    try {
      setLista(await api<Dashboard[]>(`${base}?janela=${janela}`));
      setErro(null);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "não foi possível carregar");
    } finally {
      setCarregando(false);
    }
  }, [base, janela]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function criar() {
    if (!base) return;
    setErroForm(null);
    setSalvando(true);
    try {
      await api<Dashboard>(base, {
        method: "POST",
        body: JSON.stringify({ nome, descricao: descricao || null }),
      });
      setNome("");
      setDescricao("");
      setAberto(false);
      await carregar();
      toast.success("dashboard criado");
    } catch (e) {
      setErroForm(e instanceof Error ? e.message : "não foi possível criar");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Pagina largura="normal">
      <Cabecalho
        titulo="Dashboards"
        descricao="Um dashboard junta indicadores de várias conexões em uma tela só."
        acoes={
          <>
            <ControleJanela
              janela={janela}
              desabilitado={lista.length === 0}
              onMudar={setJanela}
            />
            <Dialog open={aberto} onOpenChange={setAberto}>
              <Button size="sm" onClick={() => setAberto(true)}>
                <Plus className="size-4" />
                Novo dashboard
              </Button>
              <DialogContent className="sm:max-w-md">
                <DialogHeader>
                  <DialogTitle>Novo dashboard</DialogTitle>
                  <DialogDescription>
                    Depois é só escolher quais indicadores entram nele.
                  </DialogDescription>
                </DialogHeader>
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="nome">Nome</FieldLabel>
                    <Input
                      id="nome"
                      value={nome}
                      placeholder="Vendas da loja"
                      onChange={(e) => setNome(e.target.value)}
                    />
                  </Field>
                  <Field>
                    <FieldLabel htmlFor="descricao">Descrição</FieldLabel>
                    <Input
                      id="descricao"
                      value={descricao}
                      placeholder="Opcional"
                      onChange={(e) => setDescricao(e.target.value)}
                    />
                  </Field>
                  {erroForm && <FieldError>{erroForm}</FieldError>}
                </FieldGroup>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setAberto(false)}>
                    Cancelar
                  </Button>
                  <Button onClick={criar} disabled={salvando || !nome.trim()}>
                    {salvando ? "Criando..." : "Criar"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      {erro && (
        <p className="text-muted-foreground rounded-lg border border-dashed p-4 text-sm">
          {erro}
        </p>
      )}

      {carregando ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-28 w-full rounded-xl" />
          ))}
        </div>
      ) : !aberta ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <LayoutDashboard />
            </EmptyMedia>
            <EmptyTitle>Crie uma organização primeiro</EmptyTitle>
            <EmptyDescription>
              Dashboards pertencem a uma organização.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : lista.length === 0 ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <LayoutDashboard />
            </EmptyMedia>
            <EmptyTitle>Nenhum dashboard ainda</EmptyTitle>
            <EmptyDescription>
              Monte uma tela com indicadores que hoje estão espalhados por
              conexões diferentes.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button onClick={() => setAberto(true)}>
              <Plus />
              Novo dashboard
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {lista.map((d) => {
            const comValor = d.indicadores.filter(
              (i) => i.valor !== null && i.erro === null,
            );
            return (
              <Card key={d.id}>
                <CardHeader>
                  <CardTitle>
                    <Link href={`/dashboards/${d.id}`}>{d.nome}</Link>
                  </CardTitle>
                  <CardDescription>
                    {d.descricao ??
                      (d.conexoes.length
                        ? `de ${d.conexoes.length} conexão${d.conexoes.length > 1 ? "ões" : ""}`
                        : "sem indicador ainda")}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {d.indicadores.length === 0 ? (
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/dashboards/${d.id}`}>
                        Escolher indicadores
                      </Link>
                    </Button>
                  ) : (
                    <p className="text-muted-foreground text-xs">
                      {d.indicadores.length} indicador
                      {d.indicadores.length > 1 ? "es" : ""} · {comValor.length}{" "}
                      com valor ·{" "}
                      {curto(comValor.reduce((s, i) => s + (i.valor ?? 0), 0))}
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </Pagina>
  );
}
