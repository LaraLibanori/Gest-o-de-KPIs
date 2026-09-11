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

// O detalhe cru do backend não serve para o usuário final.
async function mensagem(res: Response): Promise<string> {
  if (res.status === 401) return "sessão expirada, faça login de novo";
  if (res.status === 403) return "você não tem permissão para isso";
  if (res.status === 404) return "não encontrado";
  if (res.status === 409) {
    const corpo = await res.json().catch(() => null);
    return typeof corpo?.detail === "string" ? corpo.detail : "conflito";
  }
  if (res.status === 422) return "confira os dados preenchidos";
  return "não foi possível completar a ação";
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
  etapa: "tabela" | "negocio" | "catalogo" | "pronta";
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
