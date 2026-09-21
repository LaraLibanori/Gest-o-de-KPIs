const CURTO = new Intl.NumberFormat("pt-BR", {
  notation: "compact",
  maximumFractionDigits: 1,
});
const CHEIO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

export function curto(valor: number): string {
  return Math.abs(valor) >= 1e6 ? CURTO.format(valor) : CHEIO.format(valor);
}

export function cheio(valor: number): string {
  return CHEIO.format(valor);
}
