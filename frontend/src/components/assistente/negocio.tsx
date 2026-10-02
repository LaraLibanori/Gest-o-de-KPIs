"use client";

import { ArrowLeft, Loader2 } from "lucide-react";
import type { Segmento } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

export default function PassoNegocio({
  negocio,
  setNegocio,
  segmento,
  setSegmento,
  segmentos,
  ocupado,
  rotuloCancelar,
  onEnviar,
  onVoltar,
  onCancelar,
}: {
  negocio: string;
  setNegocio: (v: string) => void;
  segmento: string;
  setSegmento: (v: string) => void;
  segmentos: Segmento[];
  ocupado: boolean;
  rotuloCancelar: string;
  onEnviar: (e: React.FormEvent) => void;
  onVoltar: () => void;
  onCancelar: () => void;
}) {
  return (
    <form onSubmit={onEnviar} className="space-y-6">
      <FieldGroup className="gap-5">
        <Field>
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
        <Field>
          <FieldLabel htmlFor="segmento">Ramo</FieldLabel>
          <Select value={segmento} onValueChange={setSegmento}>
            <SelectTrigger id="segmento" className="w-full">
              <SelectValue placeholder="escolha o ramo" />
            </SelectTrigger>
            <SelectContent>
              {segmentos.map((s) => (
                <SelectItem key={s.chave} value={s.chave}>
                  {s.nome}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldDescription>
            É o ramo que define quais indicadores são sugeridos.
          </FieldDescription>
        </Field>
      </FieldGroup>
      <div className="flex items-center gap-2 border-t pt-4">
        <Button type="button" variant="ghost" onClick={onVoltar}>
          <ArrowLeft className="size-4" />
          Voltar
        </Button>
        <Button type="button" variant="ghost" onClick={onCancelar}>
          {rotuloCancelar}
        </Button>
        <div className="flex-1" />
        <Button type="submit" disabled={ocupado}>
          {ocupado && <Loader2 className="animate-spin" />}
          Ler os campos
        </Button>
      </div>
    </form>
  );
}
