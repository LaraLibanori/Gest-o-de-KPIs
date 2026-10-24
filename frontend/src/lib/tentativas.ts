const JANELA = 10 * 60_000;
const registro = new Map<string, { n: number; ate: number }>();

export function excedeu(chave: string, limite: number): boolean {
  const agora = Date.now();
  if (registro.size > 1000)
    for (const [k, v] of registro) if (v.ate < agora) registro.delete(k);
  const atual = registro.get(chave);
  if (!atual || atual.ate < agora) {
    registro.set(chave, { n: 1, ate: agora + JANELA });
    return false;
  }
  atual.n += 1;
  return atual.n > limite;
}
