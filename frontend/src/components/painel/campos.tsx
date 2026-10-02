"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, Conflito, type Campo } from "@/lib/api";
import Confirmar from "@/components/confirmar";
import { Badge } from "@/components/ui/badge";
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
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Dados = {
  nome: string;
  rotulo: string;
  formula: string;
  papel: "metrica" | "dimensao";
};

const VAZIO: Dados = { nome: "", rotulo: "", formula: "", papel: "metrica" };

export default function CamposCalculados({
  base,
  colunas,
}: {
  base: string;
  colunas: Campo[];
}) {
  const [aberto, setAberto] = useState(false);
  const [lista, setLista] = useState<Campo[]>([]);
  const [dados, setDados] = useState<Dados>(VAZIO);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [confirmando, setConfirmando] = useState<Campo | null>(null);

  const numericas = colunas
    .filter((c) => !c.formula && /int|num|real|double|money/i.test(c.tipo))
    .map((c) => c.coluna);

  const carregar = useCallback(async () => {
    try {
      setLista(await api<Campo[]>(`${base}/campos`));
    } catch {
      setLista([]);
    }
  }, [base]);

  useEffect(() => {
    if (aberto) carregar();
  }, [aberto, carregar]);

  async function salvar() {
    setErro(null);
    setSalvando(true);
    try {
      await api<Campo>(`${base}/campos`, {
        method: "POST",
        body: JSON.stringify(dados),
      });
      setDados(VAZIO);
      await carregar();
      toast.success("campo criado");
    } catch (e) {
      setErro(e instanceof Error ? e.message : "não foi possível criar");
    } finally {
      setSalvando(false);
    }
  }

  async function apagar(campo: Campo, forcar = false) {
    setConfirmando(null);
    try {
      await api(`${base}/campos/${campo.id}${forcar ? "?forcar=1" : ""}`, {
        method: "DELETE",
      });
      await carregar();
      toast.success("campo apagado");
    } catch (e) {
      // 409 significa que indicador depende do campo: perguntar antes de quebrar.
      if (e instanceof Conflito) {
        setConfirmando(campo);
        return;
      }
      toast.error(e instanceof Error ? e.message : "não foi possível apagar");
    }
  }

  return (
    <Dialog open={aberto} onOpenChange={setAberto}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <Plus className="size-4" />
          Campo calculado
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Campos calculados</DialogTitle>
          <DialogDescription>
            Uma conta feita sobre as colunas que já existem. Exemplo:{" "}
            <span className="font-mono text-xs">
              (valor_total - custo_total) / valor_total * 100
            </span>
          </DialogDescription>
        </DialogHeader>

        {lista.length > 0 && (
          <ul className="divide-border divide-y rounded-md border">
            {lista.map((c) => (
              <li key={c.id} className="flex items-center gap-2 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">
                    {c.rotulo ?? c.coluna}
                  </p>
                  <p className="text-muted-foreground truncate font-mono text-xs">
                    {c.formula}
                  </p>
                </div>
                {!!c.em_uso && (
                  <Badge variant="secondary" className="shrink-0">
                    {c.em_uso} em uso
                  </Badge>
                )}
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={`Apagar ${c.rotulo ?? c.coluna}`}
                  onClick={() => apagar(c)}
                >
                  <Trash2 className="size-4" />
                </Button>
              </li>
            ))}
          </ul>
        )}

        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="nome">Nome</FieldLabel>
            <Input
              id="nome"
              value={dados.nome}
              placeholder="margem"
              onChange={(e) =>
                setDados({ ...dados, nome: e.target.value.toLowerCase() })
              }
            />
            <FieldDescription>
              Sem espaço, em minúsculo. É por esse nome que o indicador aponta.
            </FieldDescription>
          </Field>

          <Field>
            <FieldLabel htmlFor="rotulo">Nome para a tela</FieldLabel>
            <Input
              id="rotulo"
              value={dados.rotulo}
              placeholder="Margem"
              onChange={(e) => setDados({ ...dados, rotulo: e.target.value })}
            />
          </Field>

          <Field>
            <FieldLabel htmlFor="formula">Fórmula</FieldLabel>
            <Input
              id="formula"
              className="font-mono"
              value={dados.formula}
              placeholder="valor_total - custo_total"
              onChange={(e) => setDados({ ...dados, formula: e.target.value })}
            />
            <FieldDescription>
              Só operações e as funções abs, round, ceil, floor, sqrt, power,
              coalesce, nullif, least e greatest.
            </FieldDescription>
          </Field>

          <Field>
            <FieldLabel htmlFor="papel">Serve para</FieldLabel>
            <Select
              value={dados.papel}
              onValueChange={(v) =>
                setDados({ ...dados, papel: v as "metrica" | "dimensao" })
              }
            >
              <SelectTrigger id="papel" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="metrica">Somar, média, contagem</SelectItem>
                <SelectItem value="dimensao">Quebrar o painel</SelectItem>
              </SelectContent>
            </Select>
          </Field>

          {erro && <FieldError>{erro}</FieldError>}
        </FieldGroup>

        {numericas.length > 0 && (
          <p className="text-muted-foreground text-xs">
            Colunas numéricas desta tabela:{" "}
            <span className="font-mono">{numericas.join(", ")}</span>
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setAberto(false)}>
            Fechar
          </Button>
          <Button
            onClick={salvar}
            disabled={
              salvando ||
              !dados.nome.trim() ||
              !dados.rotulo.trim() ||
              !dados.formula.trim()
            }
          >
            {salvando ? "Criando..." : "Criar campo"}
          </Button>
        </DialogFooter>
      </DialogContent>

      <Confirmar
        aberto={confirmando !== null}
        titulo="Apagar mesmo assim?"
        descricao={
          confirmando && (confirmando.em_uso ?? 0) > 0
            ? `${confirmando.em_uso} indicador${confirmando.em_uso === 1 ? "" : "es"} usa este campo e vai parar de funcionar.`
            : "Este campo calculado será apagado."
        }
        acao="Apagar assim mesmo"
        fecharAoConfirmar={false}
        onConfirmar={() => confirmando && apagar(confirmando, true)}
        onFechar={() => setConfirmando(null)}
      />
    </Dialog>
  );
}
