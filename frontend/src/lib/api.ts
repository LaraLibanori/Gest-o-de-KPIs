import { createClient } from "./supabase/client";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api";

// O token do Supabase vai no header. É com ele que o FastAPI sabe quem é.
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) throw new Error("sessão expirada, faça login de novo");

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    signal: AbortSignal.timeout(15000),
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
      ...init?.headers,
    },
  });

  if (!res.ok) throw new Error(await mensagem(res));

  return res.status === 204 ? (undefined as T) : res.json();
}

// O backend escreve o detalhe em português; só escondo onde ele não ajuda.
const GENERICO: Record<number, string> = {
  401: "sessão expirada, faça login de novo",
  403: "você não tem permissão para isso",
  404: "não encontrado",
  422: "confira os dados preenchidos",
};

async function mensagem(res: Response): Promise<string> {
  if (res.status === 401 || res.status === 422) return GENERICO[res.status];
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
  confirmado: boolean;
  ordem: number;
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

export type Indicador = {
  id: string;
  nome: string;
  agregacao: Agregacao;
  coluna: string | null;
  dimensao: string | null;
  tempo: string | null;
  periodo: Periodo | null;
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
  distintos: "Quantidade de",
  minimo: "Menor",
  maximo: "Maior",
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
