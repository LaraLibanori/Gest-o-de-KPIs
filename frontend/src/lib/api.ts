const BASE = "/servidor";

// Maior que o teto de 20s por chamada da LLM, senao a pagina aborta antes.
const PRAZO = 15000;
const PRAZO_LLM = 70000;

// Conflito: apagar ou mexer nisso quebraria algo que ja esta em uso.
export class Conflito extends Error {
  readonly status = 409;
}

function sessaoExpirada(): never {
  if (typeof window !== "undefined") {
    const { pathname, search } = window.location;
    window.location.assign(
      `/login?proxima=${encodeURIComponent(pathname + search)}`,
    );
  }
  throw new Error("sessão expirada, faça login de novo");
}

export async function api<T>(
  path: string,
  init?: RequestInit & { llm?: boolean },
): Promise<T> {
  const { llm, ...resto } = init ?? {};

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...resto,
      signal: AbortSignal.timeout(llm ? PRAZO_LLM : PRAZO),
      headers: {
        "Content-Type": "application/json",
        ...resto?.headers,
      },
    });
  } catch {
    // Estouro de tempo ou rede fora: a mensagem crua do navegador não ajuda.
    throw new Error("o servidor não respondeu, tente de novo");
  }

  if (res.status === 401) sessaoExpirada();

  // 409 e conflito de estado: a tela precisa perguntar, nao só mostrar erro.
  if (res.status === 409) throw new Conflito(await mensagem(res));
  if (!res.ok) throw new Error(await mensagem(res));

  return res.status === 204 ? (undefined as T) : res.json();
}

// O backend escreve o detalhe em português; só escondo onde ele não ajuda.
const GENERICO: Record<number, string> = {
  403: "você não tem permissão para isso",
  404: "não encontrado",
  422: "confira os dados preenchidos",
};

async function mensagem(res: Response): Promise<string> {
  // 422 do FastAPI vem como lista de campo: so o texto simples do backend presta.
  const corpo = await res.json().catch(() => null);
  if (typeof corpo?.detail === "string") return corpo.detail;
  return GENERICO[res.status] ?? "não foi possível completar a ação";
}

export type Papel = "dono" | "membro";

export type Organizacao = {
  id: string;
  nome: string;
  criada_em: string;
  papel: Papel;
};

export type Convite = {
  id: string | null;
  email: string;
  papel: Papel;
  situacao: "membro" | "pendente";
  criado_em: string;
};

export type Membro = {
  usuario_id: string;
  email: string;
  nome: string | null;
  papel: Papel;
  criado_em: string;
};

export type Conexao = {
  id: string;
  nome: string;
  host: string;
  porta: number;
  banco: string;
  esquema: string | null;
  usuario: string;
  tabela_fato: string | null;
  tabela_tipo: string | null;
  descricao_negocio: string | null;
  segmento: string | null;
  etapa: "tabela" | "negocio" | "catalogo" | "indicadores" | "pronta";
  verificada_em: string | null;
  verificacao_erro: string | null;
  criada_em: string;
};

export type Relacao = {
  nome: string;
  tipo: "tabela" | "view" | "view materializada";
};

export type Verificacao = {
  ok: boolean;
  erro: string | null;
  relacoes: Relacao[];
  esquemas: string[];
};

export type PapelCampo = "metrica" | "dimensao" | "tempo" | "ignorar";

export type Sugestao = { aplicadas: number; campos: Campo[] };

export type Campo = {
  id: string;
  coluna: string;
  tipo: string;
  cardinalidade: number | null;
  papel: PapelCampo;
  rotulo: string | null;
  formula?: string | null;
  em_uso?: number;
  confirmado: boolean;
  ordem: number;
};

export type CampoCalculadoIn = {
  nome: string;
  rotulo: string;
  formula: string;
  papel: "metrica" | "dimensao";
};

export type Segmento = { chave: string; nome: string };

export type Agregacao =
  "soma" | "media" | "contagem" | "distintos" | "minimo" | "maximo";

export type Periodo =
  | "sempre"
  | "ultimos_7_dias"
  | "ultimos_30_dias"
  | "ultimos_90_dias"
  | "ano_atual";

export type Janela = "7d" | "30d" | "90d" | "12m" | "tudo";

export const JANELAS: { valor: Janela; rotulo: string }[] = [
  { valor: "7d", rotulo: "7 dias" },
  { valor: "30d", rotulo: "30 dias" },
  { valor: "90d", rotulo: "90 dias" },
  { valor: "12m", rotulo: "12 meses" },
  { valor: "tudo", rotulo: "Tudo" },
];

export type Indicador = {
  id: string;
  nome: string;
  agregacao: Agregacao;
  coluna: string | null;
  dimensao: string | null;
  tempo: string | null;
  periodo: Periodo | null;
  grafico: Grafico;
  origem: "regra" | "segmento" | "manual";
  confirmado: boolean;
  ordem: number;
};

export type Proposta = {
  segmento: string | null;
  indicadores: Indicador[];
  descartados: { nome: string; motivo: string }[];
};

// Mesma lista do backend: qual papel de campo serve para cada conta.
export const PAPEIS_ACEITOS: Record<Agregacao, PapelCampo[]> = {
  soma: ["metrica"],
  media: ["metrica"],
  minimo: ["metrica"],
  maximo: ["metrica"],
  distintos: ["dimensao", "ignorar"],
  contagem: [],
};

export const AGREGACOES: Record<Agregacao, string> = {
  soma: "Soma",
  media: "Média",
  contagem: "Contagem",
  distintos: "Quantidade",
  minimo: "Menor",
  maximo: "Maior",
};

// Como o indicador se le por extenso, no cartao do painel.
export const FRASES: Record<Agregacao, (campo: string) => string> = {
  soma: (c) => `Soma de ${c}`,
  media: (c) => `Média de ${c}`,
  contagem: () => "Contagem de registros",
  distintos: (c) => `Quantidade de ${c}`,
  minimo: (c) => `Menor ${c}`,
  maximo: (c) => `Maior ${c}`,
};

export const PERIODOS: Record<Periodo, string> = {
  sempre: "todo o período",
  ultimos_7_dias: "últimos 7 dias",
  ultimos_30_dias: "últimos 30 dias",
  ultimos_90_dias: "últimos 90 dias",
  ano_atual: "ano atual",
};

export type IndicadorNovo = {
  nome: string;
  agregacao: Agregacao;
  coluna: string | null;
  dimensao: string | null;
  tempo: string | null;
  periodo: Periodo | null;
};

export type SugestaoGrafico = { aplicadas: number; indicadores: Indicador[] };

export type Grafico = "numero" | "barra" | "linha" | "pizza" | "tabela";

export const GRAFICOS: Record<Grafico, string> = {
  numero: "Número",
  barra: "Barra",
  linha: "Linha",
  pizza: "Pizza",
  tabela: "Tabela",
};

// Mesma lista do backend: o que cada forma exige do indicador.
export const EXIGENCIAS: Record<Grafico, ("dimensao" | "tempo")[]> = {
  numero: [],
  barra: ["dimensao"],
  pizza: ["dimensao"],
  tabela: ["dimensao"],
  linha: ["tempo"],
};

export function formasPossiveis(i: {
  dimensao: string | null;
  tempo: string | null;
}): Grafico[] {
  return (Object.keys(EXIGENCIAS) as Grafico[]).filter((f) =>
    EXIGENCIAS[f].every((campo) => i[campo]),
  );
}

export type Quebra = { rotulo: string; valor: number | null };

export type IndicadorCalculado = Indicador & {
  valor: number | null;
  anterior: number | null;
  variacao: number | null;
  serie: Quebra[];
  erro: string | null;
};

export type ItemDashboard = IndicadorCalculado & {
  conexao_id: string;
  conexao: string;
};

export type Dashboard = {
  id: string;
  nome: string;
  descricao: string | null;
  criado_em: string;
  indicadores: ItemDashboard[];
  conexoes: string[];
};

export type DashboardIn = {
  nome: string;
  descricao?: string | null;
};

export type Dimensao = { coluna: string; rotulo: string };

export type Composicao = {
  coluna: string;
  rotulo: string;
  total: number | null;
  pontos: Quebra[];
};

export type Painel = {
  tabela: string | null;
  janela: Janela;
  indicadores: IndicadorCalculado[];
  dimensoes: Dimensao[];
  janelavel: boolean;
  erro: string | null;
  avisos?: string[];
};
