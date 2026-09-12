"use client";

import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DialogFooter } from "@/components/ui/dialog";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";

export type Credenciais = {
  nome: string;
  host: string;
  porta: string;
  banco: string;
  usuario: string;
  senha: string;
};

export const VAZIO: Credenciais = {
  nome: "",
  host: "",
  porta: "5432",
  banco: "",
  usuario: "",
  senha: "",
};

export default function PassoCredenciais({
  form,
  setForm,
  ocupado,
  onEnviar,
  onCancelar,
}: {
  form: Credenciais;
  setForm: (f: Credenciais) => void;
  ocupado: boolean;
  onEnviar: (e: React.FormEvent) => void;
  onCancelar: () => void;
}) {
  return (
    <form onSubmit={onEnviar}>
      <FieldGroup className="my-6">
        <Field>
          <FieldLabel htmlFor="nome">Nome</FieldLabel>
          <Input
            id="nome"
            placeholder="Produção"
            value={form.nome}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
            maxLength={120}
            required
            autoFocus
          />
        </Field>
        <div className="grid grid-cols-[1fr_100px] gap-4">
          <Field>
            <FieldLabel htmlFor="host">Host</FieldLabel>
            <Input
              id="host"
              placeholder="db.empresa.com"
              value={form.host}
              onChange={(e) => setForm({ ...form, host: e.target.value })}
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="porta">Porta</FieldLabel>
            <Input
              id="porta"
              type="number"
              value={form.porta}
              onChange={(e) => setForm({ ...form, porta: e.target.value })}
              required
            />
          </Field>
        </div>
        <Field>
          <FieldLabel htmlFor="banco">Banco</FieldLabel>
          <Input
            id="banco"
            placeholder="postgres"
            value={form.banco}
            onChange={(e) => setForm({ ...form, banco: e.target.value })}
            required
          />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="usuario">Usuário</FieldLabel>
            <Input
              id="usuario"
              autoComplete="off"
              value={form.usuario}
              onChange={(e) => setForm({ ...form, usuario: e.target.value })}
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="senha">Senha</FieldLabel>
            <Input
              id="senha"
              type="password"
              autoComplete="new-password"
              value={form.senha}
              onChange={(e) => setForm({ ...form, senha: e.target.value })}
              required
            />
          </Field>
        </div>
        <FieldDescription>
          Um usuário só de leitura basta, e é mais seguro.
        </FieldDescription>
      </FieldGroup>
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onCancelar}>
          Cancelar
        </Button>
        <Button type="submit" disabled={ocupado}>
          {ocupado && <Loader2 className="animate-spin" />}
          Conectar
        </Button>
      </DialogFooter>
    </form>
  );
}
