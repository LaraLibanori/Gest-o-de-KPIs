"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { LayoutDashboard, Plus } from "lucide-react";
import { toast } from "sonner";
import { api, type Dashboard, type Janela } from "@/lib/api";
import ControleJanela from "@/components/painel/janela";
import { Cabecalho, Pagina } from "@/components/pagina";
import { Alert, AlertDescription } from "@/components/ui/alert";
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

  const pedido = useRef(0);

  const base = aberta ? `/organizacoes/${aberta.id}/dashboards` : null;

  const carregar = useCallback(async () => {
    if (!base) {
      setCarregando(false);
      return;
    }
    const meu = ++pedido.current;
    setCarregando(true);
    try {
      const nova = await api<Dashboard[]>(`${base}?janela=${janela}`);
      if (meu !== pedido.current) return;
      setLista(nova);
      setErro(null);
    } catch (e) {
      if (meu !== pedido.current) return;
      setErro(e instanceof Error ? e.message : "não foi possível carregar");
    } finally {
      if (meu === pedido.current) setCarregando(false);
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
                <form
                  className="space-y-4"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (nome.trim() && !salvando) criar();
                  }}
                >
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
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setAberto(false)}
                    >
                      Cancelar
                    </Button>
                    <Button type="submit" disabled={salvando || !nome.trim()}>
                      {salvando ? "Criando..." : "Criar"}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </>
        }
      />

      {erro && (
        <Alert variant="destructive">
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
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
                        ? `de ${d.conexoes.length} ${d.conexoes.length > 1 ? "conexões" : "conexão"}`
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
                      com valor
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
