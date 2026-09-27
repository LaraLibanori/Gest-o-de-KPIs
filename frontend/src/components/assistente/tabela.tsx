"use client";

import { Check, Database, Layers, Sheet, Table2 } from "lucide-react";
import type { Relacao } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const ICONE = { tabela: Table2, view: Sheet, "view materializada": Database };

const TODOS = "\0todos";

export default function PassoTabela({
  relacoes,
  esquemas,
  esquema,
  escolhida,
  ocupado,
  rotuloCancelar,
  onEscolher,
  onEsquema,
  onFechar,
}: {
  relacoes: Relacao[];
  esquemas: string[];
  esquema: string | null;
  escolhida: string | null;
  ocupado: boolean;
  rotuloCancelar: string;
  onEscolher: (r: Relacao) => void;
  onEsquema: (esquema: string | null) => void;
  onFechar: () => void;
}) {
  return (
    <>
      {esquemas.length > 1 && (
        <div className="mb-4 flex items-center gap-3">
          <span className="text-muted-foreground flex items-center gap-1.5 text-sm">
            <Layers className="size-4" />
            Schema
          </span>
          <Select
            value={esquema ?? TODOS}
            onValueChange={(v) => onEsquema(v === TODOS ? null : v)}
            disabled={ocupado}
          >
            <SelectTrigger className="w-full font-mono" size="sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {esquemas.map((e) => (
                <SelectItem key={e} value={e} className="font-mono">
                  {e}
                </SelectItem>
              ))}
              <SelectItem value={TODOS}>Todos os schemas</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

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
            return (
              <button
                key={r.nome}
                onClick={() => onEscolher(r)}
                className="hover:bg-accent flex w-full items-center gap-3 rounded-md border p-3 text-left transition-colors"
              >
                <Icone className="text-muted-foreground size-4 shrink-0" />
                <span className="flex-1 truncate font-mono text-sm">
                  {r.nome}
                </span>
                <Badge variant="outline">{r.tipo}</Badge>
                {escolhida === r.nome && (
                  <Check className="text-primary size-4" />
                )}
              </button>
            );
          })
        )}
      </div>
      <p className="text-muted-foreground text-xs">
        View materializada costuma responder mais rápido que view comum.
      </p>
      <DialogFooter>
        <Button variant="ghost" onClick={onFechar}>
          {rotuloCancelar}
        </Button>
      </DialogFooter>
    </>
  );
}
