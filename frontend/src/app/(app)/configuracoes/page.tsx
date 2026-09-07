"use client";

import { useState } from "react";
import { Building2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useOrganizacao } from "../contexto";
import Pessoas from "../pessoas";
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
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Item, ItemContent, ItemDescription, ItemTitle } from "@/components/ui/item";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const data = (iso: string) =>
  new Date(iso).toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

export default function Configuracoes() {
  const { email, aberta, carregando, recarregar } = useOrganizacao();
  const [apagando, setApagando] = useState(false);

  async function apagar() {
    if (!aberta) return;
    try {
      await api<void>(`/organizacoes/${aberta.id}`, { method: "DELETE" });
      toast.success(`${aberta.nome} apagada`);
      await recarregar();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível apagar");
    } finally {
      setApagando(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl p-4 md:p-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Configurações</h1>
        <p className="text-muted-foreground mt-1 text-sm">
          Quem participa desta organização e o que fazer com ela.
        </p>
      </div>

      {carregando ? (
        <Skeleton className="h-64 w-full" />
      ) : !aberta ? (
        <Empty className="border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Building2 />
            </EmptyMedia>
            <EmptyTitle>Nenhuma organização selecionada</EmptyTitle>
            <EmptyDescription>
              Crie uma pelo seletor no topo da barra lateral.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <Tabs defaultValue="pessoas">
          <TabsList>
            <TabsTrigger value="pessoas">Pessoas</TabsTrigger>
            <TabsTrigger value="organizacao">Organização</TabsTrigger>
          </TabsList>

          <TabsContent value="pessoas" className="mt-6">
            <Pessoas organizacao={aberta} meuEmail={email} />
          </TabsContent>

          <TabsContent value="organizacao" className="mt-6 flex flex-col gap-6">
            <Card>
              <CardHeader>
                <CardTitle>{aberta.nome}</CardTitle>
                <CardDescription>criada em {data(aberta.criada_em)}</CardDescription>
                <CardAction>
                  <Badge variant={aberta.papel === "dono" ? "default" : "secondary"}>
                    seu papel: {aberta.papel}
                  </Badge>
                </CardAction>
              </CardHeader>
            </Card>

            {aberta.papel === "dono" && (
              <Card className="border-destructive/40">
                <CardHeader>
                  <CardTitle className="text-destructive">Zona de risco</CardTitle>
                  <CardDescription>
                    Ações daqui não têm volta.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Item variant="outline">
                    <ItemContent>
                      <ItemTitle>Apagar organização</ItemTitle>
                      <ItemDescription>
                        Remove a organização, seus membros, convites e conexões.
                      </ItemDescription>
                    </ItemContent>
                    <Button variant="destructive" onClick={() => setApagando(true)}>
                      <Trash2 />
                      Apagar
                    </Button>
                  </Item>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      )}

      <AlertDialog open={apagando} onOpenChange={setApagando}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Apagar {aberta?.nome}?</AlertDialogTitle>
            <AlertDialogDescription>
              A organização, seus membros, convites e conexões são removidos. Não
              dá para desfazer.
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
