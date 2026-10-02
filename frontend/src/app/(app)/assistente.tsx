"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { falhar, textoDe } from "@/lib/erros";
import {
  api,
  Conflito,
  type Campo,
  type Conexao,
  type Grafico,
  type Indicador,
  type IndicadorNovo,
  type PapelCampo,
  type Proposta,
  type Relacao,
  type Segmento,
  type SugestaoGrafico,
  type Sugestao,
  type Verificacao,
} from "@/lib/api";
import Confirmar from "@/components/confirmar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { RecadoAlerta } from "@/components/assistente/aviso";
import PassoCatalogo from "@/components/assistente/catalogo";
import PassoCredenciais, {
  de as credenciaisDe,
  VAZIO,
  type Aviso,
} from "@/components/assistente/credenciais";
import PassoIndicadores from "@/components/assistente/indicadores";
import PassoNegocio from "@/components/assistente/negocio";
import PassoTabela from "@/components/assistente/tabela";
import Trilha from "@/components/assistente/trilha";

type Etapa = "credenciais" | "tabela" | "negocio" | "catalogo" | "indicadores";

const ETAPAS: {
  id: Etapa;
  curto: string;
  titulo: string;
  descricao: string;
}[] = [
  {
    id: "credenciais",
    curto: "Acesso",
    titulo: "Conectar ao banco",
    descricao: "A senha é guardada cifrada e nunca volta para a tela.",
  },
  {
    id: "tabela",
    curto: "Tabela",
    titulo: "Escolher a tabela fato",
    descricao: "A tabela que guarda os registros do dia a dia.",
  },
  {
    id: "negocio",
    curto: "Contexto",
    titulo: "Sobre o seu negócio",
    descricao: "Ajuda a nomear os campos e sugerir os indicadores.",
  },
  {
    id: "catalogo",
    curto: "Campos",
    titulo: "O que cada coluna é",
    descricao: "Confira o que a plataforma entendeu. Dá para corrigir.",
  },
  {
    id: "indicadores",
    curto: "Indicadores",
    titulo: "O que será calculado",
    descricao: "Confirme de qual campo cada indicador sai.",
  },
];

export default function Assistente({
  organizacaoId,
  conexao,
  aberto,
  editar,
  onFechar,
}: {
  organizacaoId: string;
  conexao: Conexao | null;
  aberto: boolean;
  editar: boolean;
  onFechar: (mudou: boolean) => void;
}) {
  const [etapa, setEtapa] = useState<Etapa>("credenciais");
  const [visitados, setVisitados] = useState<number[]>([0]);
  const [atual, setAtual] = useState<Conexao | null>(null);
  const [form, setForm] = useState(VAZIO);
  const [relacoes, setRelacoes] = useState<Relacao[]>([]);
  const [esquemas, setEsquemas] = useState<string[]>([]);
  const [esquema, setEsquema] = useState<string | null>(null);
  const [negocio, setNegocio] = useState("");
  const [segmento, setSegmento] = useState("");
  const [segmentos, setSegmentos] = useState<Segmento[]>([]);
  const [campos, setCampos] = useState<Campo[]>([]);
  const [indicadores, setIndicadores] = useState<Indicador[]>([]);
  const [descartados, setDescartados] = useState<Proposta["descartados"]>([]);
  const [ocupado, setOcupado] = useState(false);
  const [sugerindo, setSugerindo] = useState(false);
  const [mudou, setMudou] = useState(false);
  const [criada, setCriada] = useState(false);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [testando, setTestando] = useState(false);
  const [descartando, setDescartando] = useState(false);
  const [conflito, setConflito] = useState<{
    nome: string;
    texto: string;
  } | null>(null);
  const descartandoAgora = useRef(false);

  function irPara(alvo: Etapa) {
    setEtapa(alvo);
    setVisitados((antes) =>
      antes.includes(ETAPAS.findIndex((e) => e.id === alvo))
        ? antes
        : [...antes, ETAPAS.findIndex((e) => e.id === alvo)],
    );
  }

  const base = `/organizacoes/${organizacaoId}/conexoes`;

  const buscarRelacoes = useCallback(
    async (id: string, alvo?: string | null) => {
      const busca = alvo ? `?esquema=${encodeURIComponent(alvo)}` : "";
      const r = await api<Verificacao>(`${base}/${id}/verificar${busca}`, {
        method: "POST",
      });
      if (!r.ok) throw new Error(r.erro ?? "o banco não respondeu");
      setRelacoes(r.relacoes);
      setEsquemas(r.esquemas);
    },
    [base],
  );

  async function descartar(id: string): Promise<boolean> {
    try {
      await api<void>(`${base}/${id}`, { method: "DELETE" });
      return true;
    } catch {
      toast.error(
        "não foi possível apagar o rascunho, a conexão continua salva",
      );
      return false;
    }
  }

  useEffect(() => {
    if (!aberto) return;
    api<Segmento[]>("/segmentos")
      .then(setSegmentos)
      .catch(() => {});
  }, [aberto]);

  const abertoAntes = useRef(false);
  useEffect(() => {
    const abriu = aberto && !abertoAntes.current;
    abertoAntes.current = aberto;
    if (!abriu) return;
    setMudou(false);
    setCriada(false);
    setAviso(null);
    setVisitados([0]);
    setTestando(false);
    setDescartando(false);
    setConflito(null);
    setDescartados([]);
    if (!conexao) {
      setEtapa("credenciais");
      setAtual(null);
      setForm(VAZIO);
      setRelacoes([]);
      setEsquemas([]);
      setEsquema(null);
      setNegocio("");
      setSegmento("");
      setCampos([]);
      setIndicadores([]);
      return;
    }
    setAtual(conexao);
    setEsquema(conexao.esquema ?? null);
    setForm(credenciaisDe(conexao));
    if (editar) {
      setEtapa("credenciais");
      return;
    }
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
  }, [aberto, conexao, base, buscarRelacoes, editar]);

  async function testar() {
    if (testando || ocupado) return;
    if (atual && !form.senha) return;
    setTestando(true);
    setAviso(null);
    try {
      const r = await api<Verificacao>(`${base}/provar`, {
        method: "POST",
        body: JSON.stringify({ ...form, porta: Number(form.porta) }),
      });
      if (!r.ok) {
        setAviso({
          tipo: "erro",
          titulo: "Não foi possível conectar",
          texto: r.erro ?? "o banco não respondeu",
        });
        return;
      }
      setEsquemas(r.esquemas);
      setAviso({
        tipo: "okto",
        titulo: "Conexão funciona",
        texto: `${r.relacoes.length} tabela${r.relacoes.length === 1 ? "" : "s"} em ${r.esquemas.length} schema${r.esquemas.length === 1 ? "" : "s"}.`,
      });
    } catch (err) {
      setAviso({
        tipo: "erro",
        titulo: "Não foi possível testar",
        texto: textoDe(err, "não foi possível conectar ao banco"),
      });
    } finally {
      setTestando(false);
    }
  }

  async function trocarEsquema(alvo: string | null) {
    if (!atual || ocupado) return;
    setEsquema(alvo);
    setOcupado(true);
    try {
      await buscarRelacoes(atual.id, alvo);
    } catch (err) {
      falhar(err);
    } finally {
      setOcupado(false);
    }
  }

  async function salvarCredenciais(e: React.FormEvent) {
    e.preventDefault();
    if (ocupado) return;
    setAviso(null);
    setOcupado(true);
    const corpo = {
      ...form,
      porta: Number(form.porta),
      esquema: form.esquema.trim() || null,
    };
    let nova: Conexao | null = null;
    try {
      const edicao = atual !== null;
      nova = await api<Conexao>(edicao ? `${base}/${atual!.id}` : base, {
        method: edicao ? "PATCH" : "POST",
        body: JSON.stringify(corpo),
      });
      await buscarRelacoes(nova.id, nova.esquema);
      setCriada(!edicao);
      setAtual(nova);
      setForm(credenciaisDe(nova));
      setMudou(true);
      if (edicao)
        toast.success("Conexão atualizada. Confira as tabelas abaixo.");
      irPara("tabela");
    } catch (err) {
      if (!atual && nova) await descartar(nova.id);
      setAviso({
        tipo: "erro",
        titulo: "Não foi possível conectar",
        texto: textoDe(err, "não foi possível conectar ao banco"),
      });
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
      irPara("negocio");
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
          llm: true,
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
      irPara("catalogo");
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
      setCampos((lista) => lista.map((c) => (c.id === campo.id ? campo : c)));
    }
  }

  async function montarIndicadores() {
    if (!atual || ocupado) return;
    irPara("indicadores");
    setOcupado(true);
    try {
      const p = await api<Proposta>(`${base}/${atual.id}/indicadores/propor`, {
        method: "POST",
      });
      setIndicadores(p.indicadores);
      setDescartados(p.descartados);
      setMudou(true);
      sugerirGraficos(atual.id);
    } catch (e) {
      falhar(e);
    } finally {
      setOcupado(false);
    }
  }

  // Sugestao de forma: se a llm nao responder, a escolhida por regra continua.
  const sugerirGraficos = useCallback(
    async (id: string) => {
      try {
        const r = await api<SugestaoGrafico>(
          `${base}/${id}/indicadores/graficos`,
          {
            method: "POST",
            llm: true,
          },
        );
        if (r.aplicadas === 0) return;
        // So a forma volta da sugestao: o resto pode ter mudado nesse meio tempo.
        const formas = new Map(r.indicadores.map((i) => [i.id, i.grafico]));
        setIndicadores((lista) =>
          lista.map((i) =>
            formas.has(i.id) ? { ...i, grafico: formas.get(i.id)! } : i,
          ),
        );
      } catch {
        // sem sugestao a forma por regra continua valendo
      }
    },
    [base],
  );

  async function trocarGrafico(indicador: Indicador, grafico: Grafico) {
    if (!atual) return;
    setIndicadores((lista) =>
      lista.map((i) => (i.id === indicador.id ? { ...i, grafico } : i)),
    );
    try {
      await api<Indicador>(`${base}/${atual.id}/indicadores/${indicador.id}`, {
        method: "PATCH",
        body: JSON.stringify({ grafico }),
      });
    } catch (e) {
      falhar(e);
      setIndicadores((lista) =>
        lista.map((i) => (i.id === indicador.id ? indicador : i)),
      );
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

  async function removerIndicador(indicador: Indicador, forcar = false) {
    if (!atual) return;
    const antes = indicadores;
    setIndicadores((lista) => lista.filter((i) => i.id !== indicador.id));
    try {
      await api<void>(
        `${base}/${atual.id}/indicadores/${indicador.id}${forcar ? "?forcar=1" : ""}`,
        { method: "DELETE" },
      );
    } catch (e) {
      setIndicadores(antes);
      if (e instanceof Conflito) {
        setConflito({ nome: indicador.nome, texto: e.message });
        return;
      }
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

  function pedirFechar() {
    if (!criada) {
      onFechar(mudou);
      return;
    }
    setDescartando(true);
  }

  const reeditando = editar && atual?.etapa === "pronta";

  async function sairDescartando() {
    if (descartandoAgora.current) return;
    descartandoAgora.current = true;
    setOcupado(true);
    const ok = !atual || (await descartar(atual.id));
    setOcupado(false);
    descartandoAgora.current = false;
    if (!ok) return;
    setDescartando(false);
    onFechar(true);
  }

  const indice = Math.max(
    0,
    ETAPAS.findIndex((e) => e.id === etapa),
  );
  const passo = ETAPAS[indice];
  const rotuloCancelar = criada ? "Cancelar" : "Fechar";

  return (
    <>
      <Dialog open={aberto} onOpenChange={(o) => !o && pedirFechar()}>
        <DialogContent
          className="max-h-[85vh] grid-rows-[auto_1fr] gap-0 overflow-hidden p-0 sm:max-w-3xl"
          showCloseButton={false}
        >
          <div className="border-b px-6 pt-5 pb-4">
            <Trilha
              itens={ETAPAS}
              indice={indice}
              visited={visitados}
              onIr={(i) => irPara(ETAPAS[i].id)}
            />

            <div className="mt-5 flex items-start justify-between gap-4">
              <div className="min-w-0">
                <DialogTitle className="text-lg">{passo.titulo}</DialogTitle>
                <DialogDescription className="mt-0.5">
                  {passo.descricao}
                </DialogDescription>
              </div>
              <span className="text-muted-foreground shrink-0 text-xs">
                Etapa {indice + 1} de {ETAPAS.length}
              </span>
            </div>
          </div>

          <div className="min-h-0 space-y-4 overflow-y-auto px-6 py-5">
            {reeditando && (
              <p className="text-muted-foreground rounded-lg border border-dashed p-3 text-xs">
                Você está reeditando uma conexão já pronta. Se seguir até o fim,
                ela continua pronta e com os mesmos indicadores.
              </p>
            )}

            <RecadoAlerta
              recado={
                aviso
                  ? {
                      tipo: aviso.tipo === "okto" ? "ok" : "erro",
                      titulo: aviso.titulo,
                      texto: aviso.texto,
                    }
                  : null
              }
            />

            {etapa === "credenciais" && (
              <PassoCredenciais
                form={form}
                setForm={setForm}
                ocupado={ocupado}
                testando={testando}
                editando={atual !== null}
                podeTestar={!atual || form.senha.trim().length > 0}
                onTestar={testar}
                onEnviar={salvarCredenciais}
                onCancelar={pedirFechar}
              />
            )}

            {etapa === "tabela" && (
              <PassoTabela
                relacoes={relacoes}
                esquemas={esquemas}
                esquema={esquema}
                escolhida={atual?.tabela_fato ?? null}
                ocupado={ocupado}
                rotuloCancelar={rotuloCancelar}
                podeVoltar={atual !== null}
                onVoltar={() => irPara("credenciais")}
                onEscolher={escolherTabela}
                onEsquema={trocarEsquema}
                onFechar={pedirFechar}
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
                rotuloCancelar={rotuloCancelar}
                onEnviar={salvarNegocio}
                onVoltar={() => irPara("tabela")}
                onCancelar={pedirFechar}
              />
            )}

            {etapa === "catalogo" && (
              <PassoCatalogo
                campos={campos}
                tabela={atual?.tabela_fato ?? null}
                ocupado={ocupado}
                sugerindo={sugerindo}
                rotuloCancelar={rotuloCancelar}
                onVoltar={() => irPara("negocio")}
                onMudarPapel={mudarPapel}
                onFechar={pedirFechar}
                onAvancar={montarIndicadores}
              />
            )}

            {etapa === "indicadores" && (
              <PassoIndicadores
                indicadores={indicadores}
                campos={campos}
                descartados={descartados}
                ocupado={ocupado}
                rotuloCancelar={rotuloCancelar}
                onVoltar={() => irPara("catalogo")}
                onTrocarColuna={trocarColuna}
                onTrocarGrafico={trocarGrafico}
                onRemover={removerIndicador}
                conflito={conflito}
                onFecharConflito={() => setConflito(null)}
                onCriar={criarIndicador}
                onFechar={pedirFechar}
                onConcluir={concluir}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Confirmar
        aberto={descartando}
        titulo="Descartar esta conexão?"
        descricao={`A conexão ${atual?.nome ?? ""} e o que foi configurado até agora serão apagados. O banco da empresa não é alterado.`}
        acao="Descartar"
        fecharAoConfirmar={false}
        onConfirmar={sairDescartando}
        onFechar={() => setDescartando(false)}
      />
    </>
  );
}
