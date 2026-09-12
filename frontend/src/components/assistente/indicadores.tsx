"use client";

import { useState } from "react";
import { Loader2, Plus, TriangleAlert, X } from "lucide-react";
import {
  AGREGACOES,
  PAPEIS_ACEITOS,
  PERIODOS,
  type Agregacao,
  type Campo,
  type Indicador,
  type IndicadorNovo,
  type Periodo,
} from "@/lib/api";
import Confirmar from "@/components/confirmar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const NENHUM = "__nenhum__";

function Campos({
  campos,
  papeis,
  valor,
  vazio,
  opcional,
  onMudar,
}: {
  campos: Campo[];
  papeis: string[];
  valor: string | null;
  vazio: string;
  opcional?: boolean;
  onMudar: (v: string | null) => void;
}) {
  const opcoes = campos.filter((c) => papeis.includes(c.papel));
  return (
    <Select
      value={valor ?? NENHUM}
      onValueChange={(v) => onMudar(v === NENHUM ? null : v)}
    >
      <SelectTrigger
        size="sm"
        className={
          "w-auto min-w-36" + (valor || opcional ? "" : " border-amber-500")
        }
      >
        <SelectValue placeholder={vazio} />
      </SelectTrigger>
      <SelectContent>
        {opcional && <SelectItem value={NENHUM}>{vazio}</SelectItem>}
        {opcoes.map((c) => (
          <SelectItem key={c.id} value={c.coluna}>
            {c.rotulo ?? c.coluna}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function Frase({
  campos,
  onCriar,
  onCancelar,
}: {
  campos: Campo[];
  onCriar: (novo: IndicadorNovo) => Promise<void>;
  onCancelar: () => void;
}) {
  const [agregacao, setAgregacao] = useState<Agregacao>("soma");
  const [coluna, setColuna] = useState<string | null>(null);
  const [dimensao, setDimensao] = useState<string | null>(null);
  const [periodo, setPeriodo] = useState<Periodo>("sempre");
  const [nome, setNome] = useState("");
  const [salvando, setSalvando] = useState(false);

  const papeis = PAPEIS_ACEITOS[agregacao];
  const rotulo = campos.find((c) => c.coluna === coluna)?.rotulo ?? coluna;
  const sugerido =
    agregacao === "contagem"
      ? "Total de registros"
      : rotulo
        ? `${AGREGACOES[agregacao]} de ${rotulo}`
        : "";
  const falta = papeis.length > 0 && !coluna;

  async function salvar() {
    setSalvando(true);
    try {
      await onCriar({
        nome: nome.trim() || sugerido,
        agregacao,
        coluna: papeis.length ? coluna : null,
        dimensao,
        tempo: campos.find((c) => c.papel === "tempo")?.coluna ?? null,
        periodo,
      });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="bg-muted/40 space-y-3 rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Select
          value={agregacao}
          onValueChange={(v) => setAgregacao(v as Agregacao)}
        >
          <SelectTrigger size="sm" className="w-auto min-w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(AGREGACOES) as Agregacao[]).map((a) => (
              <SelectItem key={a} value={a}>
                {AGREGACOES[a]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {papeis.length > 0 && (
          <>
            <span className="text-muted-foreground">de</span>
            <Campos
              campos={campos}
              papeis={papeis}
              valor={coluna}
              vazio="escolha o campo"
              onMudar={setColuna}
            />
          </>
        )}
        <span className="text-muted-foreground">por</span>
        <Campos
          campos={campos}
          papeis={["dimensao"]}
          valor={dimensao}
          vazio="nada"
          opcional
          onMudar={setDimensao}
        />
        <span className="text-muted-foreground">em</span>
        <Select value={periodo} onValueChange={(v) => setPeriodo(v as Periodo)}>
          <SelectTrigger size="sm" className="w-auto min-w-36">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(PERIODOS) as Periodo[]).map((p) => (
              <SelectItem key={p} value={p}>
                {PERIODOS[p]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-2">
        <Input
          value={nome}
          onChange={(e) => setNome(e.target.value)}
          placeholder={sugerido || "nome do indicador"}
          maxLength={120}
          className="h-8"
        />
        <Button size="sm" variant="ghost" onClick={onCancelar}>
          Cancelar
        </Button>
        <Button size="sm" onClick={salvar} disabled={falta || salvando}>
          {salvando && <Loader2 className="animate-spin" />}
          Adicionar
        </Button>
      </div>
    </div>
  );
}

export default function PassoIndicadores({
  indicadores,
  campos,
  descartados,
  ocupado,
  onTrocarColuna,
  onRemover,
  onCriar,
  onFechar,
  onConcluir,
}: {
  indicadores: Indicador[];
  campos: Campo[];
  descartados: { nome: string; motivo: string }[];
  ocupado: boolean;
  onTrocarColuna: (indicador: Indicador, coluna: string | null) => void;
  onRemover: (indicador: Indicador) => void;
  onCriar: (novo: IndicadorNovo) => Promise<void>;
  onFechar: () => void;
  onConcluir: () => void;
}) {
  const [criando, setCriando] = useState(false);
  const [aRemover, setARemover] = useState<Indicador | null>(null);
  const rotulo = (coluna: string | null) =>
    campos.find((c) => c.coluna === coluna)?.rotulo ?? coluna ?? "";
  const faltando = indicadores.filter(
    (i) => PAPEIS_ACEITOS[i.agregacao].length > 0 && !i.coluna,
  ).length;

  return (
    <>
      <div className="text-muted-foreground my-2 text-sm">
        {ocupado
          ? "Montando os indicadores…"
          : indicadores.length === 0
            ? "Nada por aqui ainda."
            : faltando > 0
              ? `${indicadores.length} ${indicadores.length === 1 ? "indicador" : "indicadores"} · ${faltando} esperando você escolher o campo`
              : `${indicadores.length} ${indicadores.length === 1 ? "indicador definido" : "indicadores, todos com campo definido"}`}
      </div>

      <div className="max-h-96 space-y-2 overflow-y-auto">
        {ocupado ? (
          [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)
        ) : indicadores.length === 0 ? (
          <p className="text-muted-foreground py-8 text-center text-sm">
            Nenhum indicador ainda. Adicione o primeiro abaixo.
          </p>
        ) : (
          indicadores.map((i) => {
            const papeis = PAPEIS_ACEITOS[i.agregacao];
            return (
              <div key={i.id} className="space-y-2 rounded-md border p-3">
                <div className="flex items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{i.nome}</p>
                    <p className="text-muted-foreground text-xs">
                      {AGREGACOES[i.agregacao]}
                      {papeis.length > 0 && ` de ${rotulo(i.coluna) || "…"}`}
                      {i.dimensao && ` por ${rotulo(i.dimensao)}`}
                    </p>
                  </div>
                  {i.origem === "segmento" && (
                    <Badge variant="secondary">ramo</Badge>
                  )}
                  <Button
                    size="icon"
                    variant="ghost"
                    className="size-7"
                    onClick={() => setARemover(i)}
                  >
                    <X className="size-3.5" />
                  </Button>
                </div>
                {papeis.length > 0 && (
                  <Campos
                    campos={campos}
                    papeis={papeis}
                    valor={i.coluna}
                    vazio="escolha o campo"
                    onMudar={(v) => onTrocarColuna(i, v)}
                  />
                )}
              </div>
            );
          })
        )}

        {descartados.length > 0 && (
          <div className="mt-4 space-y-1 rounded-md border border-dashed p-3">
            <p className="text-muted-foreground flex items-center gap-1.5 text-xs">
              <TriangleAlert className="size-3.5" />
              Não dá para calcular com esta tabela
            </p>
            {descartados.map((d) => (
              <p key={d.nome} className="text-muted-foreground text-xs">
                <span className="text-foreground">{d.nome}</span> · {d.motivo}
              </p>
            ))}
          </div>
        )}
      </div>

      {criando ? (
        <Frase
          campos={campos}
          onCriar={async (novo) => {
            await onCriar(novo);
            setCriando(false);
          }}
          onCancelar={() => setCriando(false)}
        />
      ) : (
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => setCriando(true)}
          disabled={ocupado}
        >
          <Plus className="size-4" />
          Adicionar indicador
        </Button>
      )}

      <DialogFooter>
        <Button variant="ghost" onClick={onFechar}>
          Continuar depois
        </Button>
        <Button
          onClick={onConcluir}
          disabled={ocupado || indicadores.length === 0}
        >
          Concluir
        </Button>
      </DialogFooter>

      <Confirmar
        aberto={aRemover !== null}
        titulo={`Remover ${aRemover?.nome}?`}
        descricao="O indicador sai desta conexão. Dá para montar de novo depois, pelo botão de adicionar ou refazendo a proposta."
        acao="Remover"
        onConfirmar={() => {
          if (aRemover) onRemover(aRemover);
          setARemover(null);
        }}
        onFechar={() => setARemover(null)}
      />
    </>
  );
}
