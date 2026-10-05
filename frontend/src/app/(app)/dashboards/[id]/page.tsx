"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Settings2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  api,
  type Campo,
  type Conexao,
  type Dashboard,
  type Dimensao,
  type Indicador,
  type ItemDashboard,
  type Janela,
} from "@/lib/api";
import { falhar } from "@/lib/erros";
import { humano } from "@/lib/rotulo";
import Destaque from "@/components/painel/destaque";
import ControleJanela from "@/components/painel/janela";
import Tile from "@/components/painel/tile";
import { Cabecalho, Pagina } from "@/components/pagina";
import Confirmar from "@/components/confirmar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrganizacao } from "../../contexto";

export default function DetalheDoDashboard() {
  const { id } = useParams<{ id: string }>();
  const roteador = useRouter();
  const { aberta } = useOrganizacao();
  const [painel, setPainel] = useState<Dashboard | null>(null);
  const [janela, setJanela] = useState<Janela>("30d");
  const [selecionado, setSelecionado] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [escolhendo, setEscolhendo] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [apagando, setApagando] = useState(false);
  const pedido = useRef(0);

  const base = aberta ? `/organizacoes/${aberta.id}/dashboards/${id}` : null;

  const carregar = useCallback(async () => {
    if (!base) return;
    const meu = ++pedido.current;
    setCarregando(true);
    try {
      const novo = await api<Dashboard>(`${base}?janela=${janela}`);
      if (meu !== pedido.current) return;
      setPainel(novo);
      setErro(null);
    } catch (e) {
      if (meu !== pedido.current) return;
      setErro(e instanceof Error ? e.message : "não foi possível carregar");
      falhar(e, "não foi possível carregar o dashboard");
    } finally {
      if (meu === pedido.current) setCarregando(false);
    }
  }, [base, janela]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const indicadores = useMemo(() => painel?.indicadores ?? [], [painel]);
  const bons = useMemo(
    () => indicadores.filter((i) => i.erro === null && i.valor !== null),
    [indicadores],
  );
  const destaque: ItemDashboard | null = useMemo(() => {
    const achado = bons.find((i) => i.id === selecionado);
    return achado ?? bons[0] ?? null;
  }, [bons, selecionado]);

  const [catalogo, setCatalogo] = useState<Campo[]>([]);
  const conexaoDoDestaque = destaque?.conexao_id ?? null;

  useEffect(() => {
    if (!aberta || !conexaoDoDestaque) return;
    let vivo = true;
    api<Campo[]>(
      `/organizacoes/${aberta.id}/conexoes/${conexaoDoDestaque}/catalogo`,
    )
      .then((r) => vivo && setCatalogo(r))
      .catch(() => vivo && setCatalogo([]));
    return () => {
      vivo = false;
    };
  }, [aberta, conexaoDoDestaque]);

  const tempos = useMemo(
    () => new Set(indicadores.map((i) => i.tempo).filter(Boolean) as string[]),
    [indicadores],
  );

  const dimensoes: Dimensao[] = useMemo(
    () =>
      catalogo
        .filter(
          (c) =>
            c.papel === "dimensao" &&
            (c.tipo === "text" || c.tipo.includes("char")) &&
            !/^id$|^id_|_id$/i.test(c.coluna) &&
            !tempos.has(c.coluna),
        )
        .map((c) => ({ coluna: c.coluna, rotulo: c.rotulo ?? c.coluna })),
    [catalogo, tempos],
  );

  const rotulo = useCallback(
    (coluna: string | null) =>
      catalogo.find((c) => c.coluna === coluna)?.rotulo ??
      (coluna ? humano(coluna) : "registros"),
    [catalogo],
  );

  async function trocar(escolhidos: string[]) {
    if (!base || salvando) return;
    setSalvando(true);
    try {
      await api<Dashboard>(`${base}/indicadores`, {
        method: "PUT",
        body: JSON.stringify({ indicadores: escolhidos }),
      });
      setEscolhendo(false);
      await carregar();
      toast.success("indicadores atualizados");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível salvar");
    } finally {
      setSalvando(false);
    }
  }

  async function apagar() {
    if (!base) return;
    try {
      await api(base, { method: "DELETE" });
      toast.success("dashboard apagado");
      roteador.push("/dashboards");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "não foi possível apagar");
    }
  }

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
        titulo={painel?.nome ?? "Dashboard"}
        voltar={{ href: "/dashboards", rotulo: "Dashboards" }}
        descricao={painel?.descricao ?? undefined}
        acoes={
          <>
            <ControleJanela
              janela={janela}
              desabilitado={!painel || indicadores.length === 0}
              onMudar={setJanela}
            />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setEscolhendo(true)}
              disabled={!painel}
            >
              <Settings2 className="size-4" />
              Indicadores
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setApagando(true)}
              disabled={!painel}
              aria-label="Apagar dashboard"
            >
              <Trash2 className="size-4" />
            </Button>
          </>
        }
      />

      {erro && (
        <Alert variant="destructive">
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      )}

      {carregando && !painel ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-36 w-full rounded-xl" />
          ))}
        </div>
      ) : !painel ? null : indicadores.length === 0 ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Settings2 />
            </EmptyMedia>
            <EmptyTitle>Este dashboard está vazio</EmptyTitle>
            <EmptyDescription>
              Escolha indicadores das conexões da organização para montar a
              tela.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button onClick={() => setEscolhendo(true)}>
              Escolher indicadores
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <>
          <div className="grid items-stretch gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {indicadores.map((i) => (
              <Tile
                key={i.id}
                indicador={i}
                janela={rotuloJanela}
                selecionado={destaque?.id === i.id}
                onSelecionar={() => setSelecionado(i.id)}
              />
            ))}
          </div>

          {destaque && (
            <Destaque
              indicador={destaque}
              base={`/organizacoes/${aberta?.id ?? ""}/conexoes/${destaque.conexao_id}`}
              dimensoes={dimensoes}
              janela={janela}
              rotuloDe={rotulo}
              origem={destaque.conexao}
            />
          )}
        </>
      )}

      {base && (
        <EscolherIndicadores
          aberto={escolhendo}
          onAbrir={setEscolhendo}
          org={aberta?.id ?? ""}
          jaEscolhidos={indicadores.map((i) => i.id)}
          salvando={salvando}
          onSalvar={trocar}
        />
      )}

      <Confirmar
        aberto={apagando}
        titulo={`Apagar ${painel?.nome ?? "o dashboard"}?`}
        descricao="Só o dashboard é apagado. Os indicadores e as conexões continuam como estão."
        onConfirmar={apagar}
        onFechar={() => setApagando(false)}
      />
    </Pagina>
  );
}

function EscolherIndicadores({
  aberto,
  onAbrir,
  org,
  jaEscolhidos,
  salvando,
  onSalvar,
}: {
  aberto: boolean;
  onAbrir: (v: boolean) => void;
  org: string;
  jaEscolhidos: string[];
  salvando: boolean;
  onSalvar: (ids: string[]) => void;
}) {
  const [conexoes, setConexoes] = useState<Conexao[]>([]);
  const [porConexao, setPorConexao] = useState<Record<string, Indicador[]>>({});
  const [marcados, setMarcados] = useState<string[]>(jaEscolhidos);
  const [carregando, setCarregando] = useState(false);

  const [visto, setVisto] = useState(false);
  if (aberto !== visto) {
    setVisto(aberto);
    if (aberto) setMarcados(jaEscolhidos);
  }

  useEffect(() => {
    if (!aberto || !org) return;
    let vivo = true;
    setCarregando(true);
    (async () => {
      try {
        const lista = await api<Conexao[]>(`/organizacoes/${org}/conexoes`);
        if (!vivo) return;
        setConexoes(lista);
        const pares = await Promise.all(
          lista.map(async (c) => {
            try {
              return [
                c.id,
                await api<Indicador[]>(
                  `/organizacoes/${org}/conexoes/${c.id}/indicadores`,
                ),
              ] as const;
            } catch {
              return [c.id, [] as Indicador[]] as const;
            }
          }),
        );
        if (vivo) setPorConexao(Object.fromEntries(pares));
      } catch (e) {
        falhar(e, "não foi possível listar as conexões");
      } finally {
        if (vivo) setCarregando(false);
      }
    })();
    return () => {
      vivo = false;
    };
  }, [aberto, org]);

  return (
    <Dialog open={aberto} onOpenChange={onAbrir}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Indicadores do dashboard</DialogTitle>
          <DialogDescription>
            Pode misturar indicadores de conexões diferentes.
          </DialogDescription>
        </DialogHeader>

        {carregando ? (
          <Skeleton className="h-40 w-full" />
        ) : conexoes.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Nenhuma conexão nesta organização.
          </p>
        ) : (
          <div className="max-h-80 space-y-4 overflow-y-auto">
            {conexoes.map((c) => {
              const itens = porConexao[c.id] ?? [];
              if (itens.length === 0) return null;
              return (
                <div key={c.id}>
                  <p className="text-muted-foreground mb-1 text-xs font-medium">
                    {c.nome}
                  </p>
                  <ul className="space-y-1">
                    {itens.map((i) => {
                      const marcado = marcados.includes(i.id);
                      return (
                        <li key={i.id}>
                          <label className="hover:bg-accent flex cursor-pointer items-center gap-2 rounded-md p-2 text-sm transition-colors">
                            <Checkbox
                              checked={marcado}
                              onCheckedChange={() =>
                                setMarcados((antes) =>
                                  marcado
                                    ? antes.filter((x) => x !== i.id)
                                    : [...antes, i.id],
                                )
                              }
                            />
                            {i.nome}
                          </label>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => onAbrir(false)}>
            Cancelar
          </Button>
          <Button disabled={salvando} onClick={() => onSalvar(marcados)}>
            Salvar
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
