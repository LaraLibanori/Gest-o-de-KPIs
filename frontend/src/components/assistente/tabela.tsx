"use client";

import { useMemo, useState } from "react";
import {
  ArrowLeft,
  Check,
  Database,
  Layers,
  Search,
  Sheet,
  Table2,
} from "lucide-react";
import type { Relacao } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  podeVoltar,
  onEscolher,
  onEsquema,
  onVoltar,
  onFechar,
}: {
  relacoes: Relacao[];
  esquemas: string[];
  esquema: string | null;
  escolhida: string | null;
  ocupado: boolean;
  rotuloCancelar: string;
  podeVoltar: boolean;
  onEscolher: (r: Relacao) => void;
  onEsquema: (esquema: string | null) => void;
  onVoltar: () => void;
  onFechar: () => void;
}) {
  const [busca, setBusca] = useState("");

  const filtradas = useMemo(() => {
    const alvo = busca.trim().toLowerCase();
    if (!alvo) return relacoes;
    return relacoes.filter((r) => r.nome.toLowerCase().includes(alvo));
  }, [relacoes, busca]);

  return (
    <div className="space-y-4">
      {esquemas.length > 1 && (
        <div className="flex items-center gap-3">
          <span className="text-muted-foreground flex shrink-0 items-center gap-1.5 text-sm">
            <Layers className="size-4" />
            Schema
          </span>
          <Select
            value={esquema ?? TODOS}
            onValueChange={(v) => onEsquema(v === TODOS ? null : v)}
            disabled={ocupado}
          >
            <SelectTrigger className="flex-1 font-mono" size="sm">
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

      {!ocupado && relacoes.length > 8 && (
        <div className="relative">
          <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" />
          <Input
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="filtrar por nome"
            className="pl-9"
          />
        </div>
      )}

      {ocupado ? (
        <div className="space-y-1.5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-13 w-full rounded-lg" />
          ))}
        </div>
      ) : relacoes.length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">
          Nenhuma tabela visível para esse usuário.
        </p>
      ) : filtradas.length === 0 ? (
        <p className="text-muted-foreground py-10 text-center text-sm">
          Nada com esse nome. Tente parte do nome, sem o schema.
        </p>
      ) : (
        <ul className="max-h-72 space-y-1 overflow-y-auto">
          {filtradas.map((r) => {
            const Icone = ICONE[r.tipo];
            const ativo = escolhida === r.nome;
            return (
              <li key={r.nome}>
                <button
                  onClick={() => onEscolher(r)}
                  className={
                    "flex w-full items-center gap-3 rounded-lg border p-3 text-left transition-colors " +
                    (ativo
                      ? "border-primary bg-primary/5"
                      : "hover:bg-accent hover:border-foreground/20")
                  }
                >
                  <Icone className="text-muted-foreground size-4 shrink-0" />
                  <span className="flex-1 truncate font-mono text-sm">
                    {r.nome}
                  </span>
                  <Badge variant="outline">{r.tipo}</Badge>
                  {ativo && <Check className="text-primary size-4 shrink-0" />}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <p className="text-muted-foreground text-xs">
        Escolha a tabela que guarda os registros do dia a dia. View
        materializada costuma responder mais rápido que view comum.
      </p>

      <div className="flex items-center gap-2 border-t pt-4">
        {podeVoltar && (
          <Button variant="ghost" onClick={onVoltar}>
            <ArrowLeft className="size-4" />
            Voltar
          </Button>
        )}
        <Button variant="ghost" onClick={onFechar}>
          {rotuloCancelar}
        </Button>
        <div className="flex-1" />
        <span className="text-muted-foreground text-xs">
          {ocupado
            ? "lendo…"
            : `${filtradas.length} de ${relacoes.length} tabela${relacoes.length === 1 ? "" : "s"}`}
        </span>
      </div>
    </div>
  );
}
