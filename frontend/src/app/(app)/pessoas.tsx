"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, MailPlus, MoreHorizontal, UserRoundX, X } from "lucide-react";
import { toast } from "sonner";
import { api, type Convite, type Membro, type Organizacao } from "@/lib/api";
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
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
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Empty, EmptyDescription, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item";
import { Skeleton } from "@/components/ui/skeleton";

type Alvo = { titulo: string; descricao: string; acao: () => Promise<void> };

function iniciais(texto: string) {
  return texto.slice(0, 2).toUpperCase();
}

export default function Pessoas({
  organizacao,
  meuEmail,
}: {
  organizacao: Organizacao;
  meuEmail: string;
}) {
  const [membros, setMembros] = useState<Membro[]>([]);
  const [convites, setConvites] = useState<Convite[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [email, setEmail] = useState("");
  const [convidando, setConvidando] = useState(false);
  const [aberto, setAberto] = useState(false);
  const [alvo, setAlvo] = useState<Alvo | null>(null);

  const souDono = organizacao.papel === "dono";

  const carregar = useCallback(async (id: string) => {
    setCarregando(true);
    try {
      const [m, c] = await Promise.all([
        api<Membro[]>(`/organizacoes/${id}/membros`),
        api<Convite[]>(`/organizacoes/${id}/convites`),
      ]);
      setMembros(m);
      setConvites(c);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível carregar");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar(organizacao.id);
  }, [organizacao.id, carregar]);

  async function convidar(e: React.FormEvent) {
    e.preventDefault();
    if (convidando) return;
    setConvidando(true);
    try {
      const convite = await api<Convite>(`/organizacoes/${organizacao.id}/convites`, {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      toast.success(
        convite.situacao === "membro"
          ? `${convite.email} entrou na organização`
          : `Convite guardado. ${convite.email} entra assim que criar a conta.`,
      );
      setEmail("");
      setAberto(false);
      carregar(organizacao.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "não foi possível convidar");
    } finally {
      setConvidando(false);
    }
  }

  function pedirRemocao(membro: Membro) {
    const sou = membro.email === meuEmail;
    setAlvo({
      titulo: sou ? "Sair da organização?" : `Remover ${membro.email}?`,
      descricao: sou
        ? "Você perde o acesso a esta organização e precisa de um novo convite para voltar."
        : "Essa pessoa perde o acesso imediatamente. Dá para convidar de novo depois.",
      acao: async () => {
        await api<void>(`/organizacoes/${organizacao.id}/membros/${membro.usuario_id}`, {
          method: "DELETE",
        });
        setMembros((lista) => lista.filter((m) => m.usuario_id !== membro.usuario_id));
        toast.success(sou ? "Você saiu da organização" : "Pessoa removida");
      },
    });
  }

  function pedirCancelamento(convite: Convite) {
    setAlvo({
      titulo: `Cancelar o convite de ${convite.email}?`,
      descricao: "O convite deixa de valer. Você pode enviar outro quando quiser.",
      acao: async () => {
        await api<void>(`/organizacoes/${organizacao.id}/convites/${convite.id}`, {
          method: "DELETE",
        });
        setConvites((lista) => lista.filter((c) => c.id !== convite.id));
        toast.success("Convite cancelado");
      },
    });
  }

  async function confirmar() {
    if (!alvo) return;
    try {
      await alvo.acao();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível concluir");
    } finally {
      setAlvo(null);
    }
  }

  const total = membros.length;
  const resumo =
    total === 1 ? "1 pessoa" : `${total} pessoas`;

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Pessoas</CardTitle>
          <CardDescription>
            {carregando
              ? "Carregando…"
              : convites.length > 0
                ? `${resumo} · ${convites.length} convite${convites.length > 1 ? "s" : ""} pendente${convites.length > 1 ? "s" : ""}`
                : resumo}
          </CardDescription>
          {souDono && (
            <CardAction>
              <Dialog open={aberto} onOpenChange={setAberto}>
                <DialogTrigger asChild>
                  <Button size="sm">
                    <MailPlus />
                    Convidar
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <form onSubmit={convidar}>
                    <DialogHeader>
                      <DialogTitle>Convidar para {organizacao.nome}</DialogTitle>
                      <DialogDescription>
                        Quem já tem conta entra na hora. Quem não tem, entra assim
                        que se cadastrar com esse e-mail.
                      </DialogDescription>
                    </DialogHeader>
                    <Field className="my-6">
                      <FieldLabel htmlFor="convidado">E-mail</FieldLabel>
                      <Input
                        id="convidado"
                        type="email"
                        placeholder="pessoa@empresa.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                      />
                      <FieldDescription>
                        A pessoa entra como membro e não pode convidar outras.
                      </FieldDescription>
                    </Field>
                    <DialogFooter>
                      <Button type="submit" disabled={convidando}>
                        {convidando && <Loader2 className="animate-spin" />}
                        Enviar convite
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </CardAction>
          )}
        </CardHeader>

        <CardContent>
          {carregando ? (
            <div className="flex flex-col gap-4">
              {[0, 1].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <Skeleton className="size-8 rounded-full" />
                  <Skeleton className="h-4 w-48" />
                </div>
              ))}
            </div>
          ) : (
            <ItemGroup className="gap-1">
              {membros.map((m) => (
                <Item key={m.usuario_id} size="sm">
                  <ItemMedia>
                    <Avatar className="size-8">
                      <AvatarFallback>{iniciais(m.email)}</AvatarFallback>
                    </Avatar>
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>
                      {m.nome ?? m.email}
                      {m.email === meuEmail && (
                        <span className="text-muted-foreground font-normal">
                          {" "}
                          (você)
                        </span>
                      )}
                    </ItemTitle>
                    {m.nome && <ItemDescription>{m.email}</ItemDescription>}
                  </ItemContent>
                  <ItemActions className="gap-2">
                    <Badge variant={m.papel === "dono" ? "default" : "secondary"}>
                      {m.papel}
                    </Badge>
                    {(souDono || m.email === meuEmail) && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-8"
                            aria-label={`Ações de ${m.email}`}
                          >
                            <MoreHorizontal />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            variant="destructive"
                            onSelect={() => pedirRemocao(m)}
                          >
                            <UserRoundX />
                            {m.email === meuEmail ? "Sair da organização" : "Remover"}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </ItemActions>
                </Item>
              ))}

              {convites.map((c) => (
                <Item key={c.id} size="sm" className="opacity-80">
                  <ItemMedia>
                    <Avatar className="size-8">
                      <AvatarFallback className="bg-transparent border border-dashed">
                        {iniciais(c.email)}
                      </AvatarFallback>
                    </Avatar>
                  </ItemMedia>
                  <ItemContent>
                    <ItemTitle>{c.email}</ItemTitle>
                    <ItemDescription>ainda não criou a conta</ItemDescription>
                  </ItemContent>
                  <ItemActions className="gap-2">
                    <Badge variant="outline">convite pendente</Badge>
                    {souDono && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        aria-label={`Cancelar convite de ${c.email}`}
                        onClick={() => pedirCancelamento(c)}
                      >
                        <X />
                      </Button>
                    )}
                  </ItemActions>
                </Item>
              ))}

              {membros.length === 0 && convites.length === 0 && (
                <Empty className="border-0">
                  <EmptyMedia variant="icon">
                    <MailPlus />
                  </EmptyMedia>
                  <EmptyTitle>Ninguém por aqui ainda</EmptyTitle>
                  <EmptyDescription>
                    Convide alguém pelo e-mail para dividir esta organização.
                  </EmptyDescription>
                </Empty>
              )}
            </ItemGroup>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={alvo !== null} onOpenChange={(o) => !o && setAlvo(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{alvo?.titulo}</AlertDialogTitle>
            <AlertDialogDescription>{alvo?.descricao}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction onClick={confirmar}>Confirmar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
