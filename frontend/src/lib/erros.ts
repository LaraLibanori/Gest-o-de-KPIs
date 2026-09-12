import { toast } from "sonner";

export function falhar(erro: unknown, padrao = "não foi possível concluir") {
  toast.error(erro instanceof Error ? erro.message : padrao);
}
