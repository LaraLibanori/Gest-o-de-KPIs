"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import {
  Building2,
  Check,
  ChevronsUpDown,
  Database,
  Loader2,
  LogOut,
  Plus,
  Settings,
} from "lucide-react";
import { toast } from "sonner";
import { api, type Organizacao } from "@/lib/api";
import { OrganizacaoProvider } from "./contexto";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

const NAVEGACAO = [
  { href: "/", titulo: "Conexões", icone: Database },
  { href: "/configuracoes", titulo: "Configurações", icone: Settings },
];

export default function Shell({
  email,
  children,
}: {
  email: string;
  children: React.ReactNode;
}) {
  const caminho = usePathname();
  const [organizacoes, setOrganizacoes] = useState<Organizacao[]>([]);
  const [abertaId, setAbertaId] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [nome, setNome] = useState("");
  const [criando, setCriando] = useState(false);
  const [dialogo, setDialogo] = useState(false);

  const recarregar = useCallback(async () => {
    try {
      const lista = await api<Organizacao[]>("/organizacoes");
      setOrganizacoes(lista);
      setAbertaId((atual) =>
        atual && lista.some((o) => o.id === atual) ? atual : (lista[0]?.id ?? null),
      );
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível carregar");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  // O login deixa esse aviso ao criar a conta.
  useEffect(() => {
    if (sessionStorage.getItem("conta-criada") !== "1") return;
    sessionStorage.removeItem("conta-criada");
    toast.success("Conta criada. Bem-vindo ao KPI Builder.");
  }, []);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    if (criando) return;
    setCriando(true);
    try {
      const nova = await api<Organizacao>("/organizacoes", {
        method: "POST",
        body: JSON.stringify({ nome }),
      });
      setOrganizacoes((lista) => [nova, ...lista]);
      setAbertaId(nova.id);
      setNome("");
      setDialogo(false);
      toast.success(`${nova.nome} criada`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "não foi possível criar");
    } finally {
      setCriando(false);
    }
  }

  const aberta = organizacoes.find((o) => o.id === abertaId) ?? null;
  const pagina = NAVEGACAO.find((n) => n.href === caminho);

  return (
    <OrganizacaoProvider value={{ email, organizacoes, aberta, carregando, recarregar }}>
      <SidebarProvider>
        <Sidebar collapsible="icon">
          <SidebarHeader>
            <SidebarMenu>
              <SidebarMenuItem>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <SidebarMenuButton size="lg">
                      <div className="bg-primary text-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                        <Building2 className="size-4" />
                      </div>
                      <div className="grid flex-1 text-left leading-tight">
                        <span className="truncate font-medium">
                          {aberta?.nome ?? (carregando ? "Carregando…" : "KPI Builder")}
                        </span>
                        <span className="text-muted-foreground truncate text-xs">
                          {aberta?.papel ??
                            (carregando ? "\u00a0" : "nenhuma organização")}
                        </span>
                      </div>
                      <ChevronsUpDown className="ml-auto size-4" />
                    </SidebarMenuButton>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent
                    align="start"
                    className="w-(--radix-dropdown-menu-trigger-width) min-w-56"
                  >
                    <DropdownMenuLabel className="text-muted-foreground text-xs">
                      Organizações
                    </DropdownMenuLabel>
                    {organizacoes.map((o) => (
                      <DropdownMenuItem key={o.id} onSelect={() => setAbertaId(o.id)}>
                        <Building2 />
                        <span className="truncate">{o.nome}</span>
                        {o.id === abertaId && <Check className="ml-auto size-4" />}
                      </DropdownMenuItem>
                    ))}
                    {organizacoes.length > 0 && <DropdownMenuSeparator />}
                    <DropdownMenuItem onSelect={() => setDialogo(true)}>
                      <Plus />
                      Nova organização
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarHeader>

          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  {NAVEGACAO.map((item) => (
                    <SidebarMenuItem key={item.href}>
                      <SidebarMenuButton
                        asChild
                        isActive={caminho === item.href}
                        tooltip={item.titulo}
                      >
                        <Link href={item.href}>
                          <item.icone />
                          <span>{item.titulo}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>

          <SidebarFooter>
            <SidebarMenu>
              <SidebarMenuItem>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <SidebarMenuButton size="lg">
                      <Avatar className="size-8 rounded-lg">
                        <AvatarFallback className="rounded-lg text-xs">
                          {email.slice(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <span className="flex-1 truncate text-left text-sm">{email}</span>
                      <ChevronsUpDown className="ml-auto size-4" />
                    </SidebarMenuButton>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent side="top" align="start" className="w-56">
                    <DropdownMenuLabel className="text-muted-foreground truncate text-xs font-normal">
                      {email}
                    </DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild variant="destructive">
                      <form action="/auth/signout" method="post" className="w-full">
                        <button type="submit" className="flex w-full items-center gap-2">
                          <LogOut className="size-4" />
                          Sair
                        </button>
                      </form>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        </Sidebar>

        <SidebarInset>
          <header className="bg-background/80 sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b px-4 backdrop-blur">
            <SidebarTrigger className="-ml-1" />
            <Separator orientation="vertical" className="mr-1 !h-4" />
            <span className="text-muted-foreground truncate text-sm">
              {aberta?.nome ?? "KPI Builder"}
            </span>
            <span className="text-muted-foreground/50 text-sm">/</span>
            <span className="truncate text-sm font-medium">
              {pagina?.titulo ?? "Conexões"}
            </span>
          </header>

          <div className="flex-1">{children}</div>
        </SidebarInset>

        <Dialog open={dialogo} onOpenChange={setDialogo}>
          <DialogContent className="sm:max-w-md">
            <form onSubmit={criar}>
              <DialogHeader>
                <DialogTitle>Nova organização</DialogTitle>
                <DialogDescription>
                  É o espaço que você divide com outras pessoas. Você entra como
                  dono e pode convidar depois.
                </DialogDescription>
              </DialogHeader>
              <Field className="my-6">
                <FieldLabel htmlFor="org-nome">Nome</FieldLabel>
                <Input
                  id="org-nome"
                  placeholder="Minha empresa"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  maxLength={120}
                  required
                  autoFocus
                />
              </Field>
              <DialogFooter>
                <Button type="submit" disabled={criando}>
                  {criando && <Loader2 className="animate-spin" />}
                  Criar
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </SidebarProvider>
    </OrganizacaoProvider>
  );
}
