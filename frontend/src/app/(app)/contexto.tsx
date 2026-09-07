"use client";

import { createContext, useContext } from "react";
import type { Organizacao } from "@/lib/api";

type Valor = {
  email: string;
  organizacoes: Organizacao[];
  aberta: Organizacao | null;
  carregando: boolean;
  recarregar: () => Promise<void>;
};

const Contexto = createContext<Valor | null>(null);

export const OrganizacaoProvider = Contexto.Provider;

export function useOrganizacao() {
  const valor = useContext(Contexto);
  if (!valor) throw new Error("useOrganizacao precisa estar dentro do Shell");
  return valor;
}
