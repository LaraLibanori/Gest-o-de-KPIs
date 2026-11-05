"use client";

import { useState } from "react";
import { Target } from "lucide-react";
import { toast } from "sonner";
import { api, type IndicadorCalculado } from "@/lib/api";
import { falhar } from "@/lib/erros";
import { acumula } from "@/lib/meta";
import { curto, ehDinheiro, subirEBom } from "@/lib/numero";
import Confirmar from "@/components/confirmar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export default function DefinirMeta({
  base,
  indicador,
  onSalvo,
}: {
  base: string;
  indicador: IndicadorCalculado;
  onSalvo: (meta: number | null) => void;
}) {
  const [aberto, setAberto] = useState(false);
  const [texto, setTexto] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [removendo, setRemovendo] = useState(false);
  const moeda = ehDinheiro(indicador);
  const atual = indicador.meta;

  function abrir(sim: boolean) {
    setAberto(sim);
    if (sim) setTexto(atual === null ? "" : String(atual));
  }

  async function salvar(meta: number | null) {
    setSalvando(true);
    try {
      await api(`${base}/indicadores/${indicador.id}`, {
        method: "PATCH",
        body: JSON.stringify({ meta }),
      });
      onSalvo(meta);
      setAberto(false);
      toast.success(meta === null ? "Meta removida." : "Meta salva.");
    } catch (e) {
      falhar(e, "não foi possível salvar a meta");
    } finally {
      setSalvando(false);
    }
  }

  const numero = Number(texto.replace(",", "."));
  const valida = texto.trim() !== "" && Number.isFinite(numero) && numero >= 0;

  return (
    <>
      <Confirmar
        aberto={removendo}
        titulo="Remover a meta?"
        descricao={`${indicador.nome} deixa de mostrar se a meta foi atingida. Dá para definir outra depois.`}
        acao="Remover"
        onConfirmar={() => salvar(null)}
        onFechar={() => setRemovendo(false)}
      />
      <Dialog open={aberto} onOpenChange={abrir}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <Target className="size-4" />
            {atual === null ? "Definir meta" : `Meta: ${curto(atual, moeda)}`}
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Meta de {indicador.nome}</DialogTitle>
            <DialogDescription>
              {acumula(indicador.agregacao)
                ? "Quanto você espera em 30 dias. Em 7 dias, 90 dias e 12 meses a meta é ajustada na mesma proporção."
                : "O valor esperado. Vale igual em qualquer período, porque não se soma com o tempo."}
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (valida) salvar(numero);
            }}
          >
            <Field>
              <FieldLabel htmlFor="meta">
                {moeda ? "Meta em reais" : "Meta"}
              </FieldLabel>
              <Input
                id="meta"
                type="number"
                inputMode="decimal"
                min={0}
                step="any"
                autoFocus
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
              />
              {!subirEBom(indicador) && (
                <FieldDescription>
                  Neste indicador, ficar abaixo da meta é bom.
                </FieldDescription>
              )}
            </Field>
            <DialogFooter className="mt-6">
              {atual !== null && (
                <Button
                  type="button"
                  variant="ghost"
                  className="sm:mr-auto"
                  disabled={salvando}
                  onClick={() => setRemovendo(true)}
                >
                  Remover meta
                </Button>
              )}
              <Button
                type="button"
                variant="outline"
                onClick={() => setAberto(false)}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={!valida || salvando}>
                {salvando ? "Salvando…" : "Salvar"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}
