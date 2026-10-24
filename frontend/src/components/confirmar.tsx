"use client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function Confirmar({
  aberto,
  titulo,
  descricao,
  acao = "Apagar",
  fecharAoConfirmar = true,
  outra,
  onConfirmar,
  onFechar,
}: {
  aberto: boolean;
  titulo: string;
  descricao: string;
  acao?: string;
  fecharAoConfirmar?: boolean;
  outra?: { rotulo: string; onClick: () => void };
  onConfirmar: () => void;
  onFechar: () => void;
}) {
  return (
    <AlertDialog open={aberto} onOpenChange={(o) => !o && onFechar()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{titulo}</AlertDialogTitle>
          <AlertDialogDescription>{descricao}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Voltar</AlertDialogCancel>
          {outra && (
            <AlertDialogCancel onClick={outra.onClick}>
              {outra.rotulo}
            </AlertDialogCancel>
          )}
          <AlertDialogAction
            onClick={(e) => {
              onConfirmar();
              if (!fecharAoConfirmar) e.preventDefault();
            }}
          >
            {acao}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
