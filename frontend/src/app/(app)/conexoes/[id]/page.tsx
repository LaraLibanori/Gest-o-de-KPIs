"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  ChartNoAxesColumn,
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
import { falhar } from "@/lib/erros";
import { humano } from "@/lib/rotulo";
import CamposCalculados from "@/components/painel/campos";
import Destaque from "@/components/painel/destaque";
import ControleJanela from "@/components/painel/janela";
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
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { paineis } from "@/lib/paineis";
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

  // Trocar de conexao nao remonta a tela, entao o contexto precisa ser zerado.
  useEffect(() => {
    contexto.current = false;
    pintou.current = false;
    setSelecionado(null);
  }, [id]);

  const buscar = useCallback(
    async (alvo: Janela, forcar = false) => {
      if (!base) return;
      const meu = ++pedido.current;
      const chave = `${id}:${alvo}`;
      const guardado = paineis.get(chave);

      // Mostra o que tem sem esperar e revalida por tras, sem piscar a tela.
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
        // Atualizar recarrega o catalogo: coluna nova no banco precisa aparecer.
        if (!contexto.current || forcar) {
          const [lista, catalogo] = await Promise.all([
            api<Conexao[]>(base),
            api<Campo[]>(`${base}/${id}/catalogo`),
          ]);
          contexto.current = true;
          setConexao(lista.find((c) => c.id === id) ?? null);
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- troca de janela chama buscar direto
  }, [carregandoOrg, buscar]);

  // Indicador marcado nao sobrevive a troca de periodo.
  useEffect(() => setSelecionado(null), [janela]);

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
            <Destaque
              indicador={destaque}
              base={`${base}/${id}`}
              dimensoes={painel?.dimensoes ?? []}
              janela={janela}
              rotuloDe={rotulo}
              carregandoSerie={carregandoSerie}
            />
          )}
        </>
      )}
    </Pagina>
  );
}
