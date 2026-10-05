"use client";

import { JANELAS, type Janela } from "@/lib/api";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function ControleJanela({
  janela,
  onMudar,
  desabilitado,
}: {
  janela: Janela;
  onMudar: (j: Janela) => void;
  desabilitado: boolean;
}) {
  if (desabilitado) return null;
  return (
    <Tabs
      value={janela}
      activationMode="manual"
      onValueChange={(v) => onMudar(v as Janela)}
    >
      <TabsList aria-label="Período">
        {JANELAS.map((j) => (
          <TabsTrigger key={j.valor} value={j.valor}>
            {j.rotulo}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
