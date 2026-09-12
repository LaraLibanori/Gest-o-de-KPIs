"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import {
  api,
  type Campo,
  type Conexao,
  type Indicador,
  type IndicadorNovo,
  type PapelCampo,
  type Proposta,
  type Relacao,
  type Segmento,
  type Sugestao,
  type Verificacao,
} from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import PassoCatalogo from "@/components/assistente/catalogo";
import PassoCredenciais, { VAZIO } from "@/components/assistente/credenciais";
import PassoIndicadores from "@/components/assistente/indicadores";
import PassoNegocio from "@/components/assistente/negocio";
import PassoTabela from "@/components/assistente/tabela";

type Etapa = "credenciais" | "tabela" | "negocio" | "catalogo" | "indicadores";

const ETAPAS: { id: Etapa; titulo: string; descricao: string }[] = [
  {
    id: "credenciais",
    titulo: "Acesso ao banco",
    descricao: "A senha é guardada cifrada e nunca volta para a tela.",
  },
  {
    id: "tabela",
    titulo: "Tabela fato",
    descricao: "A tabela que consolida os registros do dia a dia.",
  },
  {
    id: "negocio",
    titulo: "Seu negócio",
    descricao: "Ajuda a plataforma a nomear os campos e sugerir indicadores.",
  },
  {
    id: "catalogo",
    titulo: "Campos",
    descricao: "Confira o que a plataforma entendeu de cada coluna.",
  },
  {
    id: "indicadores",
    titulo: "Indicadores",
    descricao: "Confirme de qual campo cada indicador é calculado.",
  },
];

const LARGAS: Etapa[] = ["catalogo", "indicadores"];

export default function Assistente({
  organizacaoId,
  conexao,
  aberto,
  onFechar,
}: {
  organizacaoId: string;
  conexao: Conexao | null;
  aberto: boolean;
  onFechar: (mudou: boolean) => void;
}) {
  const [etapa, setEtapa] = useState<Etapa>("credenciais");
  const [atual, setAtual] = useState<Conexao | null>(null);
  const [form, setForm] = useState(VAZIO);
  const [relacoes, setRelacoes] = useState<Relacao[]>([]);
  const [negocio, setNegocio] = useState("");
  const [segmento, setSegmento] = useState("");
  const [segmentos, setSegmentos] = useState<Segmento[]>([]);
  const [campos, setCampos] = useState<Campo[]>([]);
  const [indicadores, setIndicadores] = useState<Indicador[]>([]);
  const [descartados, setDescartados] = useState<Proposta["descartados"]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [sugerindo, setSugerindo] = useState(false);
  const [mudou, setMudou] = useState(false);

  const base = `/organizacoes/${organizacaoId}/conexoes`;

  const falhar = (e: unknown) =>
    toast.error(e instanceof Error ? e.message : "não foi possível concluir");

  const buscarRelacoes = useCallback(
    async (id: string) => {
      const r = await api<Verificacao>(`${base}/${id}/verificar`, {
        method: "POST",
      });
      if (!r.ok) throw new Error(r.erro ?? "o banco não respondeu");
      setRelacoes(r.relacoes);
    },
    [base],
  );

  useEffect(() => {
    if (!aberto) return;
    api<Segmento[]>("/segmentos")
      .then(setSegmentos)
      .catch(() => {});
  }, [aberto]);

  // Retoma de onde a pessoa parou, ou começa do zero.
  useEffect(() => {
    if (!aberto) return;
    setMudou(false);
    setDescartados([]);
    if (!conexao) {
      setEtapa("credenciais");
      setAtual(null);
      setForm(VAZIO);
      setRelacoes([]);
      setNegocio("");
      setSegmento("");
      setCampos([]);
      setIndicadores([]);
      return;
    }
    setAtual(conexao);
    setNegocio(conexao.descricao_negocio ?? "");
    setSegmento(conexao.segmento ?? "");
    const retomar = conexao.etapa === "pronta" ? "indicadores" : conexao.etapa;
    setEtapa(retomar);
    setOcupado(true);
    (async () => {
      try {
        if (retomar === "tabela") await buscarRelacoes(conexao.id);
        if (retomar === "catalogo")
          setCampos(await api<Campo[]>(`${base}/${conexao.id}/catalogo`));
        if (retomar === "indicadores") {
          setCampos(await api<Campo[]>(`${base}/${conexao.id}/catalogo`));
          setIndicadores(
            await api<Indicador[]>(`${base}/${conexao.id}/indicadores`),
          );
        }
      } catch (e) {
        falhar(e);
      } finally {
        setOcupado(false);
      }
    })();
  }, [aberto, conexao, base, buscarRelacoes]);

  async function salvarCredenciais(e: React.FormEvent) {
    e.preventDefault();
    if (ocupado) return;
    setOcupado(true);
    try {
      const nova = await api<Conexao>(base, {
        method: "POST",
        body: JSON.stringify({ ...form, porta: Number(form.porta) }),
      });
      setAtual(nova);
      setMudou(true);
      await buscarRelacoes(nova.id);
      setEtapa("tabela");
    } catch (err) {
      falhar(err);
    } finally {
      setOcupado(false);
    }
  }

  async function escolherTabela(relacao: Relacao) {
    if (!atual || ocupado) return;
    setOcupado(true);
    try {
      setAtual(
        await api<Conexao>(`${base}/${atual.id}`, {
          method: "PATCH",
          body: JSON.stringify({
            tabela_fato: relacao.nome,
            tabela_tipo: relacao.tipo,
            etapa: "negocio",
          }),
        }),
      );
      setEtapa("negocio");
    } catch (e) {
      falhar(e);
    } finally {
      setOcupado(false);
    }
  }

  const sugerir = useCallback(
    async (id: string) => {
      setSugerindo(true);
      try {
        const r = await api<Sugestao>(`${base}/${id}/catalogo/rotulos`, {
          method: "POST",
        });
        if (r.aplicadas > 0) setCampos(r.campos);
      } catch {
        // sem sugestao o catalogo por regra continua valendo
      } finally {
        setSugerindo(false);
      }
    },
    [base],
  );

  async function salvarNegocio(e: React.FormEvent) {
    e.preventDefault();
    if (!atual || ocupado) return;
    setOcupado(true);
    try {
      await api<Conexao>(`${base}/${atual.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          descricao_negocio: negocio,
          segmento: segmento || null,
          etapa: "catalogo",
        }),
      });
      setCampos(
        await api<Campo[]>(`${base}/${atual.id}/catalogo`, { method: "POST" }),
      );
      setEtapa("catalogo");
      sugerir(atual.id);
    } catch (err) {
      falhar(err);
    } finally {
      setOcupado(false);
    }
  }

  async function mudarPapel(campo: Campo, papel: PapelCampo) {
    if (!atual) return;
    setCampos((lista) =>
      lista.map((c) =>
        c.id === campo.id ? { ...c, papel, confirmado: true } : c,
      ),
    );
    try {
      await api<Campo>(`${base}/${atual.id}/catalogo/${campo.id}`, {
        method: "PATCH",
        body: JSON.stringify({ papel, confirmado: true }),
      });
    } catch (e) {
      falhar(e);
    }
  }

  async function montarIndicadores() {
    if (!atual || ocupado) return;
    setEtapa("indicadores");
    setOcupado(true);
    try {
      const p = await api<Proposta>(`${base}/${atual.id}/indicadores/propor`, {
        method: "POST",
      });
      setIndicadores(p.indicadores);
      setDescartados(p.descartados);
      setMudou(true);
    } catch (e) {
      falhar(e);
    } finally {
      setOcupado(false);
    }
  }

  async function trocarColuna(indicador: Indicador, coluna: string | null) {
    if (!atual) return;
    setIndicadores((lista) =>
      lista.map((i) => (i.id === indicador.id ? { ...i, coluna } : i)),
    );
    try {
      await api<Indicador>(`${base}/${atual.id}/indicadores/${indicador.id}`, {
        method: "PATCH",
        body: JSON.stringify({ coluna, confirmado: true }),
      });
    } catch (e) {
      falhar(e);
      setIndicadores((lista) =>
        lista.map((i) => (i.id === indicador.id ? indicador : i)),
      );
    }
  }

  async function removerIndicador(indicador: Indicador) {
    if (!atual) return;
    setIndicadores((lista) => lista.filter((i) => i.id !== indicador.id));
    try {
      await api<void>(`${base}/${atual.id}/indicadores/${indicador.id}`, {
        method: "DELETE",
      });
    } catch (e) {
      falhar(e);
    }
  }

  async function criarIndicador(novo: IndicadorNovo) {
    if (!atual) return;
    try {
      const criado = await api<Indicador>(`${base}/${atual.id}/indicadores`, {
        method: "POST",
        body: JSON.stringify(novo),
      });
      setIndicadores((lista) => [...lista, criado]);
    } catch (e) {
      falhar(e);
    }
  }

  async function concluir() {
    if (!atual || ocupado) return;
    setOcupado(true);
    try {
      await api<Conexao>(`${base}/${atual.id}`, {
        method: "PATCH",
        body: JSON.stringify({ etapa: "pronta" }),
      });
      toast.success(`${atual.nome} está pronta.`);
      onFechar(true);
    } catch (e) {
      falhar(e);
    } finally {
      setOcupado(false);
    }
  }

  const indice = Math.max(
    0,
    ETAPAS.findIndex((e) => e.id === etapa),
  );
  const passo = ETAPAS[indice];

  return (
    <Dialog open={aberto} onOpenChange={(o) => !o && onFechar(mudou)}>
      <DialogContent
        className={LARGAS.includes(etapa) ? "sm:max-w-2xl" : "sm:max-w-lg"}
        showCloseButton={false}
      >
        <DialogHeader>
          <div className="text-muted-foreground mb-1 flex items-center gap-1.5 text-xs">
            {ETAPAS.map((e, i) => (
              <span
                key={e.id}
                className={
                  "h-1 flex-1 rounded-full " +
                  (i <= indice ? "bg-primary" : "bg-muted")
                }
              />
            ))}
          </div>
          <DialogTitle>{passo.titulo}</DialogTitle>
          <DialogDescription>
            Etapa {indice + 1} de {ETAPAS.length} · {passo.descricao}
          </DialogDescription>
        </DialogHeader>

        {etapa === "credenciais" && (
          <PassoCredenciais
            form={form}
            setForm={setForm}
            ocupado={ocupado}
            onEnviar={salvarCredenciais}
            onCancelar={() => onFechar(mudou)}
          />
        )}

        {etapa === "tabela" && (
          <PassoTabela
            relacoes={relacoes}
            escolhida={atual?.tabela_fato ?? null}
            ocupado={ocupado}
            onEscolher={escolherTabela}
            onFechar={() => onFechar(mudou)}
          />
        )}

        {etapa === "negocio" && (
          <PassoNegocio
            negocio={negocio}
            setNegocio={setNegocio}
            segmento={segmento}
            setSegmento={setSegmento}
            segmentos={segmentos}
            ocupado={ocupado}
            onEnviar={salvarNegocio}
            onVoltar={() => setEtapa("tabela")}
          />
        )}

        {etapa === "catalogo" && (
          <PassoCatalogo
            campos={campos}
            tabela={atual?.tabela_fato ?? null}
            ocupado={ocupado}
            sugerindo={sugerindo}
            onMudarPapel={mudarPapel}
            onFechar={() => onFechar(mudou)}
            onAvancar={montarIndicadores}
          />
        )}

        {etapa === "indicadores" && (
          <PassoIndicadores
            indicadores={indicadores}
            campos={campos}
            descartados={descartados}
            ocupado={ocupado}
            onTrocarColuna={trocarColuna}
            onRemover={removerIndicador}
            onCriar={criarIndicador}
            onFechar={() => onFechar(mudou)}
            onConcluir={concluir}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
