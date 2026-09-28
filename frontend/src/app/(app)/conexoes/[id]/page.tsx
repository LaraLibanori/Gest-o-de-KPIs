"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { ChartNoAxesColumn, RefreshCw, TriangleAlert } from "lucide-react";
import {
  api,
  JANELAS,
  type Campo,
  type Conexao,
  type IndicadorCalculado,
  type Janela,
  type Painel,
} from "@/lib/api";
import { falhar } from "@/lib/erros";
import { humano } from "@/lib/rotulo";
import Composicao from "@/components/painel/composicao";
import ControleJanela from "@/components/painel/janela";
import Evolucao from "@/components/painel/evolucao";
import Tile from "@/components/painel/tile";
import { Cabecalho, Pagina } from "@/components/pagina";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrganizacao } from "../../contexto";

const JANELA_INICIAL: Janela = "30d";
const SEM_ZERO = new Set(["media", "minimo", "maximo"]);
const SOMAVEIS = new Set(["soma", "contagem", "distintos"]);

export default function PainelDaConexao() {
  const { id } = useParams<{ id: string }>();
  const busca = useSearchParams();
  const { aberta, carregando: carregandoOrg } = useOrganizacao();
  const [conexao, setConexao] = useState<Conexao | null>(null);
  const [painel, setPainel] = useState<Painel | null>(null);
  const [campos, setCampos] = useState<Campo[]>([]);
  const [janela, setJanela] = useState<Janela>(() => {
    const pedida = busca.get("j");
    return JANELAS.some((j) => j.valor === pedida)
      ? (pedida as Janela)
      : JANELA_INICIAL;
  });
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [carregandoSerie, setCarregandoSerie] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const pedido = useRef(0);
  const pintou = useRef(false);

  const base = aberta ? `/organizacoes/${aberta.id}/conexoes` : null;

  const rotulo = useCallback(
    (coluna: string | null) => {
      if (!coluna) return "registros";
      const achado = campos.find((c) => c.coluna === coluna);
      return achado?.rotulo ?? humano(coluna);
    },
    [campos],
  );

  const buscar = useCallback(
    async (alvo: Janela) => {
      if (!base) return;
      const meu = ++pedido.current;
      setCarregando(true);
      setCarregandoSerie(false);
      pintou.current = false;
      try {
        const [lista, catalogo, rapido] = await Promise.all([
          api<Conexao[]>(base),
          api<Campo[]>(`${base}/${id}/catalogo`),
          api<Painel>(`${base}/${id}/painel?janela=${alvo}&serie=0`),
        ]);
        if (meu !== pedido.current) return;
        setConexao(lista.find((c) => c.id === id) ?? null);
        setCampos(catalogo);
        setPainel(rapido);
        setErro(null);
        pintou.current = true;
        setCarregando(false);
        setCarregandoSerie(true);

        const completo = await api<Painel>(
          `${base}/${id}/painel?janela=${alvo}`,
        );
        if (meu !== pedido.current) return;
        setPainel(completo);
      } catch (e) {
        if (meu !== pedido.current) return;
        if (pintou.current) {
          setErro(
            e instanceof Error
              ? `os números estão acima, mas a série falhou: ${e.message}`
              : "os números estão acima, mas a série falhou",
          );
        } else {
          setErro(e instanceof Error ? e.message : "não foi possível carregar");
          falhar(e, "não foi possível carregar o painel");
        }
      } finally {
        if (meu === pedido.current) {
          setCarregando(false);
          setCarregandoSerie(false);
        }
      }
    },
    [base, id],
  );

  useEffect(() => {
    if (!carregandoOrg) buscar(janela);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carregandoOrg, buscar]);

  const todos = useMemo(() => painel?.indicadores ?? [], [painel]);
  const indicadores = useMemo(
    () => todos.filter((i) => i.erro === null && i.valor !== null),
    [todos],
  );
  const comFalha = useMemo(() => todos.filter((i) => i.erro !== null), [todos]);

  const destaque: IndicadorCalculado | null = useMemo(() => {
    const achado = indicadores.find((i) => i.id === selecionado);
    return achado ?? indicadores[0] ?? null;
  }, [indicadores, selecionado]);

  const rotuloJanela =
    {
      "7d": "7 dias",
      "30d": "30 dias",
      "90d": "90 dias",
      "12m": "12 meses",
      tudo: "",
    }[janela] ?? "";

  return (
    <Pagina largura="largo">
      <Cabecalho
        titulo={conexao?.nome ?? "Painel"}
        voltar={{ href: "/", rotulo: "Conexões" }}
        descricao={
          <>
            {painel?.tabela ? (
              <span className="font-mono">{painel.tabela}</span>
            ) : (
              "Os indicadores calculados a partir da tabela fato."
            )}
            {painel?.tabela && " · "}
            {painel?.janela === "tudo"
              ? "todo o período"
              : `últimos ${rotuloJanela}`}
          </>
        }
        acoes={
          <>
            <ControleJanela
              janela={janela}
              desabilitado={!painel?.janelavel}
              onMudar={(j) => {
                setJanela(j);
                setSelecionado(null);
                buscar(j);
              }}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => buscar(janela)}
              disabled={carregando}
              aria-label="Atualizar"
            >
              <RefreshCw className={carregando ? "animate-spin" : undefined} />
              Atualizar
            </Button>
          </>
        }
      />

      {(erro ?? painel?.erro) && (
        <p className="text-muted-foreground flex items-start gap-2 rounded-lg border border-dashed p-4 text-sm">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          {erro ?? painel?.erro}
        </p>
      )}

      {carregando && !painel ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-36 w-full rounded-xl" />
          ))}
        </div>
      ) : erro ? null : todos.length === 0 ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <ChartNoAxesColumn />
            </EmptyMedia>
            <EmptyTitle>Nenhum indicador ainda</EmptyTitle>
            <EmptyDescription>
              Volte para as conexões e use{" "}
              <span className="text-foreground">Revisar campos</span> para
              montar os indicadores desta conexão.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <>
          {comFalha.length === indicadores.length &&
            indicadores.length === 0 && (
              <p className="text-muted-foreground rounded-lg border border-dashed p-4 text-sm">
                Nenhum dos {todos.length} indicadores deste painel pôde ser
                calculado. O erro de cada um está no cartão acima.
              </p>
            )}

          <div className="grid items-stretch gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {todos.map((i) => (
              <Tile
                key={i.id}
                indicador={i}
                janela={rotuloJanela}
                selecionado={destaque?.id === i.id}
                onSelecionar={() => setSelecionado(i.id)}
              />
            ))}
          </div>

          {destaque && base && (
            <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
              <section className="bg-card text-card-foreground rounded-xl border p-4">
                <header className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                  <h2 className="text-sm font-medium">{destaque.nome}</h2>
                  <p className="text-muted-foreground text-xs">
                    {rotulo(destaque.coluna)} ·{" "}
                    {destaque.variacao === null
                      ? "sem período anterior"
                      : `variação de ${destaque.variacao.toFixed(1).replace(".", ",")}%`}
                  </p>
                </header>
                <Evolucao
                  pontos={destaque.serie}
                  rotulo={destaque.nome}
                  total={
                    SOMAVEIS.has(destaque.agregacao) ? destaque.valor : null
                  }
                  zero={!SEM_ZERO.has(destaque.agregacao)}
                  carregando={carregandoSerie}
                />
                <p className="text-muted-foreground mt-2 text-xs">
                  Passe o mouse ou use as setas do teclado para ver o valor de
                  cada período.
                </p>
              </section>

              <section className="bg-card text-card-foreground rounded-xl border p-4">
                <header className="mb-3">
                  <h2 className="text-sm font-medium">Composição</h2>
                  <p className="text-muted-foreground text-xs">
                    Como {destaque.nome.toLowerCase()} se reparte
                  </p>
                </header>
                <Composicao
                  base={`${base}/${id}`}
                  indicador={destaque}
                  dimensoes={painel?.dimensoes ?? []}
                  janela={janela}
                  rotuloDe={rotulo}
                />
              </section>
            </div>
          )}
        </>
      )}
    </Pagina>
  );
}
