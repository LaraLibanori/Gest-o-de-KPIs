"use client";

import { CircleCheck, TriangleAlert } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

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
    <Alert variant={erro ? "destructive" : "default"}>
      {erro ? <TriangleAlert /> : <CircleCheck />}
      <AlertTitle>{recado.titulo}</AlertTitle>
      {(recado.texto || recado.dica) && (
        <AlertDescription>
          {recado.texto}
          {recado.dica && <span className="block text-xs">{recado.dica}</span>}
        </AlertDescription>
      )}
    </Alert>
  );
}
