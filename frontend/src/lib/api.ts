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
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const detalhe = await res.text();
    throw new Error(`${res.status}: ${detalhe}`);
  }

  return res.status === 204 ? (undefined as T) : res.json();
}

export type Dashboard = { id: string; nome: string; criado_em: string };

export type Indicador = {
  id: string;
  dashboard_id: string;
  nome: string;
  fonte: string;
  coluna: string | null;
  agregacao: string;
};

export type Valor = { indicador_id: string; nome: string; valor: number | null };
