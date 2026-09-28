import { toast } from "sonner";

export function textoDe(
  erro: unknown,
  padrao = "não foi possível concluir",
): string {
  return erro instanceof Error ? erro.message : padrao;
}

export function falhar(erro: unknown, padrao = "não foi possível concluir") {
  toast.error(textoDe(erro, padrao));
}
