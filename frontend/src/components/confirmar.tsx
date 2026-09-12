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
  onConfirmar,
  onFechar,
}: {
  aberto: boolean;
  titulo: string;
  descricao: string;
  acao?: string;
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
          <AlertDialogAction onClick={onConfirmar}>{acao}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
