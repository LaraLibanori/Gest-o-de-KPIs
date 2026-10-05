// Piso de rotulo para quando a LLM nao respondeu.
const TABELA: Record<string, string> = {
  id: "Identificador",
  dia: "Dia",
  mes: "Mês",
  ano: "Ano",
  data: "Data",
  hora: "Hora",
  total: "Total",
  valor: "Valor",
  media: "Média",
  minimo: "Mínimo",
  maximo: "Máximo",
  nome: "Nome",
  descricao: "Descrição",
  quantidade: "Quantidade",
  numero: "Número",
};

export function humano(coluna: string): string {
  const semPrefixo = coluna.replace(/^id_/, "").replace(/_id$/, "");
  const base = semPrefixo || coluna;
  const palavras = base
    .split("_")
    .filter(Boolean)
    .map((p) => TABELA[p.toLowerCase()] ?? capitalizar(p));
  return palavras.join(" ") || coluna;
}

function capitalizar(palavra: string): string {
  return palavra.charAt(0).toUpperCase() + palavra.slice(1);
}

export function variacao(percentual: number | null): string | null {
  if (percentual === null || !Number.isFinite(percentual)) return null;
  const sinal = percentual > 0 ? "+" : "";
  return `${sinal}${percentual.toFixed(1).replace(".", ",")}%`;
}
