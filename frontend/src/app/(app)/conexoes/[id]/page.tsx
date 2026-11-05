"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ChartNoAxesColumn,
  DatabaseZap,
  Info,
  RefreshCw,
  TriangleAlert,
} from "lucide-react";
import {
  api,
  JANELAS,
  type Campo,
  type Conexao,
  type IndicadorCalculado,
  type Janela,
  type Painel,
} from "@/lib/api";
import { humano } from "@/lib/rotulo";
import CamposCalculados from "@/components/painel/campos";
import Destaque, { APARAR } from "@/components/painel/destaque";
import DefinirMeta from "@/components/painel/meta";
import { metaDaJanela } from "@/lib/meta";
import ControleJanela from "@/components/painel/janela";
import Tile, { colunas } from "@/components/painel/tile";
import { Cabecalho, Pagina } from "@/components/pagina";
import { Button } from "@/components/ui/button";
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { paineis } from "@/lib/paineis";
import { cn } from "@/lib/utils";
import { useOrganizacao } from "../../contexto";

const JANELA_INICIAL: Janela = "30d";

// Cache do navegador: o custo esta na ida ao banco do cliente, nao no tamanho da resposta.
const FRESCO = 60_000;

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
  const [naoAchou, setNaoAchou] = useState(false);
  const pedido = useRef(0);
  const pintou = useRef(false);
  const contexto = useRef(false);

  const base = aberta ? `/organizacoes/${aberta.id}/conexoes` : null;

  const rotulo = useCallback(
    (coluna: string | null) => {
      if (!coluna) return "registros";
      const achado = campos.find((c) => c.coluna === coluna);
      return achado?.rotulo ?? humano(coluna);
    },
    [campos],
  );

  useEffect(() => {
    contexto.current = false;
    pintou.current = false;
    setSelecionado(null);
    setNaoAchou(false);
  }, [id]);

  const buscar = useCallback(
    async (alvo: Janela, forcar = false) => {
      if (!base) return;
      const meu = ++pedido.current;
      const chave = `${id}:${alvo}`;
      const guardado = paineis.get(chave);

      if (guardado && !forcar) {
        setPainel(guardado.completo ?? guardado.rapido);
        setCarregando(false);
        setCarregandoSerie(!guardado.completo);
        pintou.current = true;
        if (guardado.completo && Date.now() - guardado.em < FRESCO) return;
      } else {
        setCarregando(true);
        setCarregandoSerie(false);
        pintou.current = false;
      }

      try {
        if (!contexto.current || forcar) {
          const [lista, catalogo] = await Promise.all([
            api<Conexao[]>(base),
            api<Campo[]>(`${base}/${id}/catalogo`).catch((e: unknown) => e),
          ]);
          const achada = lista.find((c) => c.id === id);
          if (!achada) {
            setNaoAchou(true);
            return;
          }
          if (!Array.isArray(catalogo)) throw catalogo;
          contexto.current = true;
          setConexao(achada);
          setCampos(catalogo);
        }

        if (!guardado || forcar) {
          const rapido = await api<Painel>(
            `${base}/${id}/painel?janela=${alvo}&serie=0`,
          );
          if (meu !== pedido.current) return;
          setPainel(rapido);
          setErro(null);
          pintou.current = true;
          setCarregando(false);
          setCarregandoSerie(true);
          paineis.set(chave, { rapido, em: Date.now() });
        }

        const completo = await api<Painel>(
          `${base}/${id}/painel?janela=${alvo}`,
        );
        if (meu !== pedido.current) return;
        setPainel(completo);
        const anterior = paineis.get(chave);
        paineis.set(chave, {
          rapido: anterior?.rapido ?? completo,
          completo,
          em: Date.now(),
        });
      } catch (e) {
        if (meu !== pedido.current) return;
        if (pintou.current) {
          setErro(
            e instanceof Error
              ? `os números estão acima, mas a série falhou: ${e.message}`
              : "os números estão acima, mas a série falhou",
          );
        } else {
          setErro(
            e instanceof Error
              ? `Não foi possível carregar o painel: ${e.message}`
              : "Não foi possível carregar o painel.",
          );
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- troca de janela chama buscar direto
  }, [carregandoOrg, buscar]);

  useEffect(() => setSelecionado(null), [janela]);

  const todos = useMemo(() => painel?.indicadores ?? [], [painel]);
  const indicadores = useMemo(
    () => todos.filter((i) => i.erro === null && i.valor !== null),
    [todos],
  );
  const comFalha = useMemo(() => todos.filter((i) => i.erro !== null), [todos]);
  const vazio =
    janela !== "tudo" &&
    todos.length > 0 &&
    todos.every((i) => i.erro === null && !i.valor);

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

  if (naoAchou)
    return (
      <Pagina largura="largo">
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <DatabaseZap />
            </EmptyMedia>
            <EmptyTitle>Conexão não encontrada</EmptyTitle>
            <EmptyDescription>
              Ela pode ter sido apagada ou pertencer a outra organização.
            </EmptyDescription>
          </EmptyHeader>
          <Button asChild size="sm">
            <Link href="/">Ver conexões</Link>
          </Button>
        </Empty>
      </Pagina>
    );

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
              "Indicadores calculados a partir da tabela fato"
            )}
            {" · "}
            {painel?.janela === "tudo"
              ? "todo o período"
              : `últimos ${rotuloJanela}`}
          </>
        }
        acoes={
          <>
            {base && (
              <CamposCalculados
                base={`${base}/${id}`}
                colunas={campos}
                aoMudar={() => {
                  paineis.clear();
                  buscar(janela, true);
                }}
              />
            )}
            <ControleJanela
              janela={janela}
              desabilitado={!painel?.janelavel}
              onMudar={(j) => {
                setJanela(j);
                buscar(j);
              }}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => buscar(janela, true)}
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
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertDescription>{erro ?? painel?.erro}</AlertDescription>
        </Alert>
      )}

      {vazio && !carregando && (
        <Alert>
          <Info />
          <AlertDescription className="flex flex-wrap items-center gap-x-3 gap-y-2">
            Não há registros nos últimos {rotuloJanela}. Os dados podem ser mais
            antigos.
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setJanela("tudo");
                buscar("tudo");
              }}
            >
              Ver todo o período
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {!!painel?.avisos?.length && (
        <div className="space-y-2">
          {painel.avisos.map((a) => (
            <Alert key={a}>
              <Info />
              <AlertDescription>{a}</AlertDescription>
            </Alert>
          ))}
        </div>
      )}

      {carregando && !painel ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-36 w-full rounded-xl" />
          ))}
        </div>
      ) : !painel ? null : todos.length === 0 ? (
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
              <Alert>
                <Info />
                <AlertDescription>
                  Nenhum dos {todos.length} indicadores deste painel pôde ser
                  calculado. O erro de cada um está no cartão acima.
                </AlertDescription>
              </Alert>
            )}

          <div
            className={cn("grid items-stretch gap-4", colunas(todos.length))}
          >
            {todos.map((i) => (
              <Tile
                key={i.id}
                indicador={i}
                janela={rotuloJanela}
                selecionado={destaque?.id === i.id}
                aparar={APARAR.has(janela)}
                alvo={metaDaJanela(i.meta, i.agregacao, janela)}
                onSelecionar={() => setSelecionado(i.id)}
              />
            ))}
          </div>

          {destaque && base && (
            <Destaque
              indicador={destaque}
              base={`${base}/${id}`}
              dimensoes={painel?.dimensoes ?? []}
              janela={janela}
              rotuloDe={rotulo}
              carregandoSerie={carregandoSerie}
              acao={
                aberta?.papel === "dono" ? (
                  <DefinirMeta
                    base={`${base}/${id}`}
                    indicador={destaque}
                    onSalvo={(meta) => {
                      paineis.clear();
                      setPainel(
                        (p) =>
                          p && {
                            ...p,
                            indicadores: p.indicadores.map((i) =>
                              i.id === destaque.id ? { ...i, meta } : i,
                            ),
                          },
                      );
                    }}
                  />
                ) : undefined
              }
            />
          )}
        </>
      )}
    </Pagina>
  );
}
