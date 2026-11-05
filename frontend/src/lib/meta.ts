import type { Agregacao, Janela } from "@/lib/api";

const MESES: Record<Janela, number | null> = {
  "7d": 7 / 30,
  "30d": 1,
  "90d": 3,
  "12m": 12,
  tudo: null,
};

const POR_PONTO: Record<Janela, number> = {
  "7d": 1 / 30,
  "30d": 1 / 30,
  "90d": 7 / 30,
  "12m": 1,
  tudo: 1,
};

export type Situacao = "atingiu" | "perto" | "longe";

export function acumula(agregacao: Agregacao): boolean {
  return agregacao === "soma" || agregacao === "contagem";
}

export function metaDaJanela(
  meta: number | null,
  agregacao: Agregacao,
  janela: Janela,
): number | null {
  const meses = MESES[janela];
  if (meta === null || meses === null) return null;
  return acumula(agregacao) ? meta * meses : meta;
}

export function metaPorPonto(
  meta: number | null,
  agregacao: Agregacao,
  janela: Janela,
): number | null {
  if (meta === null) return null;
  return acumula(agregacao) ? meta * POR_PONTO[janela] : meta;
}

export function situacao(valor: number, alvo: number, bom: boolean): Situacao {
  if (bom) {
    if (valor >= alvo) return "atingiu";
    return valor >= alvo * 0.9 ? "perto" : "longe";
  }
  if (valor <= alvo) return "atingiu";
  return valor <= alvo * 1.1 ? "perto" : "longe";
}
