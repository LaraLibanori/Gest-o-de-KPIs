"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Database, Loader2, Sheet, Table2 } from "lucide-react";
import { toast } from "sonner";
import {
  api,
  type Campo,
  type Conexao,
  type PapelCampo,
  type Relacao,
  type Verificacao,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

type Etapa = "credenciais" | "tabela" | "negocio" | "catalogo";

const ETAPAS: { id: Etapa; titulo: string; descricao: string }[] = [
  {
    id: "credenciais",
    titulo: "Acesso ao banco",
    descricao: "A senha é guardada cifrada e nunca volta para a tela.",
  },
  {
    id: "tabela",
    titulo: "Tabela fato",
    descricao: "A tabela que consolida os registros do dia a dia.",
  },
  {
    id: "negocio",
    titulo: "Seu negócio",
    descricao: "Ajuda a plataforma a nomear os campos.",
  },
  {
    id: "catalogo",
    titulo: "Campos",
    descricao: "Confira o que a plataforma entendeu de cada coluna.",
  },
];

const PAPEIS: { valor: PapelCampo; rotulo: string }[] = [
  { valor: "metrica", rotulo: "Métrica" },
  { valor: "dimensao", rotulo: "Dimensão" },
  { valor: "tempo", rotulo: "Tempo" },
  { valor: "ignorar", rotulo: "Ignorar" },
];

const VAZIO = {
  nome: "",
  host: "",
  porta: "5432",
  banco: "",
  usuario: "",
  senha: "",
};

const ICONE = { tabela: Table2, view: Sheet, "view materializada": Database };

export default function Assistente({
  organizacaoId,
  conexao,
  aberto,
  onFechar,
}: {
  organizacaoId: string;
  conexao: Conexao | null;
  aberto: boolean;
  onFechar: (mudou: boolean) => void;
}) {
  const [etapa, setEtapa] = useState<Etapa>("credenciais");
  const [atual, setAtual] = useState<Conexao | null>(null);
  const [form, setForm] = useState(VAZIO);
  const [relacoes, setRelacoes] = useState<Relacao[]>([]);
  const [negocio, setNegocio] = useState("");
  const [campos, setCampos] = useState<Campo[]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [mudou, setMudou] = useState(false);

  const base = `/organizacoes/${organizacaoId}/conexoes`;

  const falhar = (e: unknown) =>
    toast.error(e instanceof Error ? e.message : "não foi possível concluir");

  const buscarRelacoes = useCallback(
    async (id: string) => {
      const r = await api<Verificacao>(`${base}/${id}/verificar`, { method: "POST" });
      if (!r.ok) throw new Error(r.erro ?? "o banco não respondeu");
      setRelacoes(r.relacoes);
    },
    [base],
  );

  // Retoma de onde a pessoa parou, ou começa do zero.
  useEffect(() => {
    if (!aberto) return;
    setMudou(false);
    if (!conexao) {
      setEtapa("credenciais");
      setAtual(null);
      setForm(VAZIO);
      setRelacoes([]);
      setNegocio("");
      setCampos([]);
      return;
    }
    setAtual(conexao);
    setNegocio(conexao.descricao_negocio ?? "");
    const retomar = conexao.etapa === "pronta" ? "catalogo" : conexao.etapa;
    setEtapa(retomar);
    setOcupado(true);
    (async () => {
      try {
        if (retomar === "tabela") await buscarRelacoes(conexao.id);
        if (retomar === "catalogo")
          setCampos(await api<Campo[]>(`${base}/${conexao.id}/catalogo`));
      } catch (e) {
        falhar(e);
      } finally {
        setOcupado(false);
      }
    })();
  }, [aberto, conexao, base, buscarRelacoes]);

  async function salvarCredenciais(e: React.FormEvent) {
    e.preventDefault();
    if (ocupado) return;
    setOcupado(true);
    try {
      const nova = await api<Conexao>(base, {
        method: "POST",
        body: JSON.stringify({ ...form, porta: Number(form.porta) }),
      });
      setAtual(nova);
      setMudou(true);
      await buscarRelacoes(nova.id);
      setEtapa("tabela");
    } catch (err) {
      falhar(err);
    } finally {
      setOcupado(false);
    }
  }

  async function escolherTabela(relacao: Relacao) {
    if (!atual || ocupado) return;
    setOcupado(true);
    try {
      setAtual(
        await api<Conexao>(`${base}/${atual.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            tabela_fato: relacao.nome,
            tabela_tipo: relacao.tipo,
            etapa: "negocio",
          }),
        }),
      );
      setEtapa("negocio");
    } catch (e) {
      falhar(e);
    } finally {
      setOcupado(false);
    }
  }

  async function salvarNegocio(e: React.FormEvent) {
    e.preventDefault();
    if (!atual || ocupado) return;
    setOcupado(true);
    try {
      await api<Conexao>(`${base}/${atual.id}`, {
        method: "PATCH",
        body: JSON.stringify({ descricao_negocio: negocio, etapa: "catalogo" }),
      });
      setCampos(await api<Campo[]>(`${base}/${atual.id}/catalogo`, { method: "POST" }));
      setEtapa("catalogo");
    } catch (err) {
      falhar(err);
    } finally {
      setOcupado(false);
    }
  }

  async function mudarPapel(campo: Campo, papel: PapelCampo) {
    if (!atual) return;
    setCampos((lista) =>
      lista.map((c) => (c.id === campo.id ? { ...c, papel, confirmado: true } : c)),
    );
    try {
      await api<Campo>(`${base}/${atual.id}/catalogo/${campo.id}`, {
        method: "PATCH",
        body: JSON.stringify({ papel, confirmado: true }),
      });
    } catch (e) {
      falhar(e);
    }
  }

  async function concluir() {
    if (!atual || ocupado) return;
    setOcupado(true);
    try {
      await api<Conexao>(`${base}/${atual.id}`, {
        method: "PATCH",
        body: JSON.stringify({ etapa: "pronta" }),
      });
      toast.success(`${atual.nome} pronta para montar indicadores.`);
      onFechar(true);
    } catch (e) {
      falhar(e);
    } finally {
      setOcupado(false);
    }
  }

  const indice = ETAPAS.findIndex((e) => e.id === etapa);
  const passo = ETAPAS[indice];
  const contagem = (papel: PapelCampo) =>
    campos.filter((c) => c.papel === papel).length;

  return (
    <Dialog open={aberto} onOpenChange={(o) => !o && onFechar(mudou)}>
      <DialogContent
        className={etapa === "catalogo" ? "sm:max-w-2xl" : "sm:max-w-lg"}
        showCloseButton={false}
      >
        <DialogHeader>
          <div className="text-muted-foreground mb-1 flex items-center gap-1.5 text-xs">
            {ETAPAS.map((e, i) => (
              <span
                key={e.id}
                className={
                  "h-1 flex-1 rounded-full " +
                  (i <= indice ? "bg-primary" : "bg-muted")
                }
              />
            ))}
          </div>
          <DialogTitle>{passo.titulo}</DialogTitle>
          <DialogDescription>
            Etapa {indice + 1} de {ETAPAS.length} · {passo.descricao}
          </DialogDescription>
        </DialogHeader>

        {etapa === "credenciais" && (
          <form onSubmit={salvarCredenciais}>
            <FieldGroup className="my-6">
              <Field>
                <FieldLabel htmlFor="nome">Nome</FieldLabel>
                <Input
                  id="nome"
                  placeholder="Produção"
                  value={form.nome}
                  onChange={(e) => setForm({ ...form, nome: e.target.value })}
                  maxLength={120}
                  required
                  autoFocus
                />
              </Field>
              <div className="grid grid-cols-[1fr_100px] gap-4">
                <Field>
                  <FieldLabel htmlFor="host">Host</FieldLabel>
                  <Input
                    id="host"
                    placeholder="db.empresa.com"
                    value={form.host}
                    onChange={(e) => setForm({ ...form, host: e.target.value })}
                    required
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="porta">Porta</FieldLabel>
                  <Input
                    id="porta"
                    type="number"
                    value={form.porta}
                    onChange={(e) => setForm({ ...form, porta: e.target.value })}
                    required
                  />
                </Field>
              </div>
              <Field>
                <FieldLabel htmlFor="banco">Banco</FieldLabel>
                <Input
                  id="banco"
                  placeholder="postgres"
                  value={form.banco}
                  onChange={(e) => setForm({ ...form, banco: e.target.value })}
                  required
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field>
                  <FieldLabel htmlFor="usuario">Usuário</FieldLabel>
                  <Input
                    id="usuario"
                    autoComplete="off"
                    value={form.usuario}
                    onChange={(e) => setForm({ ...form, usuario: e.target.value })}
                    required
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="senha">Senha</FieldLabel>
                  <Input
                    id="senha"
                    type="password"
                    autoComplete="new-password"
                    value={form.senha}
                    onChange={(e) => setForm({ ...form, senha: e.target.value })}
                    required
                  />
                </Field>
              </div>
              <FieldDescription>
                Um usuário só de leitura basta, e é mais seguro.
              </FieldDescription>
            </FieldGroup>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => onFechar(mudou)}>
                Cancelar
              </Button>
              <Button type="submit" disabled={ocupado}>
                {ocupado && <Loader2 className="animate-spin" />}
                Conectar
              </Button>
            </DialogFooter>
          </form>
        )}

        {etapa === "tabela" && (
          <>
            <div className="my-4 max-h-80 space-y-1 overflow-y-auto">
              {ocupado ? (
                [0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full" />)
              ) : relacoes.length === 0 ? (
                <p className="text-muted-foreground py-8 text-center text-sm">
                  Nenhuma tabela visível para esse usuário.
                </p>
              ) : (
                relacoes.map((r) => {
                  const Icone = ICONE[r.tipo];
                  const escolhida = atual?.tabela_fato === r.nome;
                  return (
                    <button
                      key={r.nome}
                      onClick={() => escolherTabela(r)}
                      className="hover:bg-accent flex w-full items-center gap-3 rounded-md border p-3 text-left transition-colors"
                    >
                      <Icone className="text-muted-foreground size-4 shrink-0" />
                      <span className="flex-1 truncate font-mono text-sm">
                        {r.nome}
                      </span>
                      <Badge variant="outline">{r.tipo}</Badge>
                      {escolhida && <Check className="text-primary size-4" />}
                    </button>
                  );
                })
              )}
            </div>
            <p className="text-muted-foreground text-xs">
              View materializada costuma responder mais rápido que view comum.
            </p>
            <DialogFooter>
              <Button variant="ghost" onClick={() => onFechar(mudou)}>
                Continuar depois
              </Button>
            </DialogFooter>
          </>
        )}

        {etapa === "negocio" && (
          <form onSubmit={salvarNegocio}>
            <Field className="my-6">
              <FieldLabel htmlFor="negocio">O que sua empresa faz?</FieldLabel>
              <Textarea
                id="negocio"
                placeholder="loja de material de construção com entrega própria"
                value={negocio}
                onChange={(e) => setNegocio(e.target.value)}
                maxLength={500}
                rows={3}
                autoFocus
              />
              <FieldDescription>
                Uma frase basta. Nenhum dado da tabela sai do seu banco.
              </FieldDescription>
            </Field>
            <DialogFooter>
              <Button type="button" variant="ghost" onClick={() => setEtapa("tabela")}>
                Voltar
              </Button>
              <Button type="submit" disabled={ocupado}>
                {ocupado && <Loader2 className="animate-spin" />}
                Ler os campos
              </Button>
            </DialogFooter>
          </form>
        )}

        {etapa === "catalogo" && (
          <>
            <div className="text-muted-foreground my-2 text-sm">
              {ocupado ? (
                "Lendo a tabela…"
              ) : (
                <>
                  <span className="font-mono">{atual?.tabela_fato}</span> ·{" "}
                  {contagem("metrica")} métricas, {contagem("dimensao")} dimensões,{" "}
                  {contagem("tempo")} de tempo
                </>
              )}
            </div>
            <div className="max-h-96 space-y-1 overflow-y-auto">
              {ocupado
                ? [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-11 w-full" />)
                : campos.map((c) => (
                    <div
                      key={c.id}
                      className="flex items-center gap-3 rounded-md border p-2 pl-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-mono text-sm">{c.coluna}</p>
                        <p className="text-muted-foreground text-xs">
                          {c.tipo}
                          {c.cardinalidade !== null &&
                            ` · ${c.cardinalidade.toLocaleString("pt-BR")} valores`}
                        </p>
                      </div>
                      <Select
                        value={c.papel}
                        onValueChange={(v) => mudarPapel(c, v as PapelCampo)}
                      >
                        <SelectTrigger className="w-36" size="sm">
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
                    </div>
                  ))}
            </div>
            <DialogFooter>
              <Button variant="ghost" onClick={() => onFechar(mudou)}>
                Continuar depois
              </Button>
              <Button onClick={concluir} disabled={ocupado || campos.length === 0}>
                Concluir
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
