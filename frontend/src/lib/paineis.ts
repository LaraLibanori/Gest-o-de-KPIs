import type { Painel } from "./api";

export const paineis = new Map<
  string,
  { rapido: Painel; completo?: Painel; em: number }
>();
