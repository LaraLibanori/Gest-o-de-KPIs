"use client";

import { Sparkles } from "lucide-react";
import type { Campo, PapelCampo } from "@/lib/api";
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

const PAPEIS: { valor: PapelCampo; rotulo: string }[] = [
  { valor: "metrica", rotulo: "Métrica" },
  { valor: "dimensao", rotulo: "Dimensão" },
  { valor: "tempo", rotulo: "Tempo" },
  { valor: "ignorar", rotulo: "Ignorar" },
];

export default function PassoCatalogo({
  campos,
  tabela,
  ocupado,
  sugerindo,
  onMudarPapel,
  onFechar,
  onAvancar,
}: {
  campos: Campo[];
  tabela: string | null;
  ocupado: boolean;
  sugerindo: boolean;
  onMudarPapel: (campo: Campo, papel: PapelCampo) => void;
  onFechar: () => void;
  onAvancar: () => void;
}) {
  const contagem = (papel: PapelCampo) =>
    campos.filter((c) => c.papel === papel).length;

  return (
    <>
      <div className="text-muted-foreground my-2 text-sm">
        {ocupado ? (
          "Lendo a tabela…"
        ) : (
          <>
            <span className="font-mono">{tabela}</span> · {contagem("metrica")}{" "}
            métricas, {contagem("dimensao")} dimensões, {contagem("tempo")} de
            tempo
            {sugerindo && (
              <span className="ml-2 inline-flex items-center gap-1">
                <Sparkles className="size-3 animate-pulse" />
                sugerindo nomes
              </span>
            )}
          </>
        )}
      </div>
      <div className="max-h-96 space-y-1 overflow-y-auto">
        {ocupado
          ? [0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-11 w-full" />
            ))
          : campos.map((c) => (
              <div
                key={c.id}
                className="flex items-center gap-3 rounded-md border p-2 pl-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm">
                    {c.rotulo ?? <span className="font-mono">{c.coluna}</span>}
                  </p>
                  <p className="text-muted-foreground truncate text-xs">
                    {c.rotulo && (
                      <span className="font-mono">{c.coluna} · </span>
                    )}
                    {c.tipo}
                    {c.cardinalidade !== null &&
                      ` · ${c.cardinalidade.toLocaleString("pt-BR")} valores`}
                  </p>
                </div>
                <Select
                  value={c.papel}
                  onValueChange={(v) => onMudarPapel(c, v as PapelCampo)}
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
        <Button variant="ghost" onClick={onFechar}>
          Continuar depois
        </Button>
        <Button onClick={onAvancar} disabled={ocupado || campos.length === 0}>
          Montar indicadores
        </Button>
      </DialogFooter>
    </>
  );
}
