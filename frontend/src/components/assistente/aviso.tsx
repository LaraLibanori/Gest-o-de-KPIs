"use client";

import { CircleCheck, TriangleAlert } from "lucide-react";
import { cn } from "@/lib/utils";

export type Recado = {
  tipo: "erro" | "ok";
  titulo: string;
  texto?: string;
  dica?: string;
};

export function RecadoAlerta({ recado }: { recado: Recado | null }) {
  if (!recado) return null;
  const erro = recado.tipo === "erro";
  return (
    <div
      role={erro ? "alert" : "status"}
      className={cn(
        "flex items-start gap-2.5 rounded-lg border p-3 text-sm",
        erro
          ? "border-destructive/40 bg-destructive/10"
          : "border-primary/30 bg-primary/5",
      )}
    >
      {erro ? (
        <TriangleAlert className="text-destructive mt-0.5 size-4 shrink-0" />
      ) : (
        <CircleCheck className="text-primary mt-0.5 size-4 shrink-0" />
      )}
      <div className="min-w-0">
        <p className={cn("font-medium", erro && "text-destructive")}>
          {recado.titulo}
        </p>
        {recado.texto && (
          <p className="text-muted-foreground mt-0.5 break-words">
            {recado.texto}
          </p>
        )}
        {recado.dica && (
          <p className="text-muted-foreground mt-1 text-xs">{recado.dica}</p>
        )}
      </div>
    </div>
  );
}

export function Escala({
  itens,
}: {
  itens: { valor: string; rotulo: string }[];
}) {
  if (itens.length === 0) return null;
  return (
    <dl className="grid grid-cols-3 divide-x rounded-lg border">
      {itens.map((i) => (
        <div key={i.rotulo} className="px-3 py-2.5 text-center">
          <dd className="text-foreground text-base font-semibold tabular-nums">
            {i.valor}
          </dd>
          <dt className="text-muted-foreground text-xs">{i.rotulo}</dt>
        </div>
      ))}
    </dl>
  );
}
