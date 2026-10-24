const CURTO = new Intl.NumberFormat("pt-BR", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const CHEIO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
const REAL_CURTO = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  maximumFractionDigits: 1,
});
const REAL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});
const REAL_INTEIRO = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

const DINHEIRO =
  /valor|preco|preço|receita|faturamento|custo|desconto|ticket|frete|lucro|margem_bruta/i;

const RUINS_SE_SOBEM =
  /custo|desconto|cancel|devol|estorno|atraso|reclama|inadimpl|perda|churn|despesa|abandono/i;

export function subirEBom(indicador: {
  nome: string;
  coluna: string | null;
}): boolean {
  return !RUINS_SE_SOBEM.test(
    `${indicador.nome} ${indicador.coluna ?? ""}`
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, ""),
  );
}

export function ehDinheiro(indicador: {
  agregacao: string;
  coluna: string | null;
}): boolean {
  return (
    indicador.agregacao !== "contagem" &&
    indicador.agregacao !== "distintos" &&
    DINHEIRO.test(indicador.coluna ?? "")
  );
}

export function curto(valor: number, moeda = false): string {
  if (Math.abs(valor) >= 1e6) return (moeda ? REAL_CURTO : CURTO).format(valor);
  return (moeda ? REAL : CHEIO).format(valor);
}

export function eixo(valor: number, moeda = false): string {
  if (Math.abs(valor) >= 1e4) return (moeda ? REAL_CURTO : CURTO).format(valor);
  return (moeda ? REAL_INTEIRO : CHEIO).format(valor);
}

export function cheio(valor: number, moeda = false): string {
  return (moeda ? REAL : CHEIO).format(valor);
}
