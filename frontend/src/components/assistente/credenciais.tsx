"use client";

import { CircleCheck, Loader2, Plug, TriangleAlert } from "lucide-react";
import type { Conexao } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
  esquema: string;
  usuario: string;
  senha: string;
};

export const VAZIO: Credenciais = {
  nome: "",
  host: "",
  porta: "5432",
  banco: "",
  esquema: "",
  usuario: "",
  senha: "",
};

export function de(conexao: Conexao): Credenciais {
  return {
    nome: conexao.nome,
    host: conexao.host,
    porta: String(conexao.porta),
    banco: conexao.banco,
    esquema: conexao.esquema ?? "",
    usuario: conexao.usuario,
    senha: "",
  };
}

export type Aviso = { tipo: "erro" | "okto"; titulo: string; texto: string };

export default function PassoCredenciais({
  form,
  setForm,
  ocupado,
  testando,
  aviso,
  editando,
  podeTestar,
  onTestar,
  onEnviar,
  onCancelar,
}: {
  form: Credenciais;
  setForm: (f: Credenciais) => void;
  ocupado: boolean;
  testando: boolean;
  aviso: Aviso | null;
  editando: boolean;
  podeTestar: boolean;
  onTestar: () => void;
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
        <div className="grid gap-4 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="banco">Banco</FieldLabel>
            <Input
              id="banco"
              placeholder="postgres"
              value={form.banco}
              onChange={(e) => setForm({ ...form, banco: e.target.value })}
              required
            />
            <FieldDescription>
              O servidor a que você se conecta. No Supabase é sempre{" "}
              <span className="font-mono">postgres</span>.
            </FieldDescription>
          </Field>
          <Field>
            <FieldLabel htmlFor="esquema">Schema</FieldLabel>
            <Input
              id="esquema"
              placeholder="deixe vazio para ver todos"
              value={form.esquema}
              onChange={(e) => setForm({ ...form, esquema: e.target.value })}
            />
            <FieldDescription>
              Onde as tabelas moram dentro do banco. Não é o banco.
            </FieldDescription>
          </Field>
        </div>
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
              placeholder={editando ? "deixe vazio para manter" : undefined}
              value={form.senha}
              onChange={(e) => setForm({ ...form, senha: e.target.value })}
              required={!editando}
            />
          </Field>
        </div>
        <FieldDescription>
          Um usuário só de leitura basta, e é mais seguro.
        </FieldDescription>
      </FieldGroup>
      {aviso && (
        <Alert
          variant={aviso.tipo === "erro" ? "destructive" : "default"}
          className="mb-2"
        >
          {aviso.tipo === "erro" ? <TriangleAlert /> : <CircleCheck />}
          <AlertTitle>{aviso.titulo}</AlertTitle>
          <AlertDescription>{aviso.texto}</AlertDescription>
        </Alert>
      )}
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onCancelar}>
          {editando ? "Fechar" : "Cancelar"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={onTestar}
          disabled={ocupado || testando || !podeTestar}
          title={
            podeTestar
              ? undefined
              : "a senha guardada não volta para a tela; digite-a para testar"
          }
        >
          {testando ? (
            <Loader2 className="animate-spin" />
          ) : (
            <Plug />
          )}
          Testar conexão
        </Button>
        <Button type="submit" disabled={ocupado || testando}>
          {ocupado && <Loader2 className="animate-spin" />}
          {editando ? "Salvar e reconectar" : "Conectar"}
        </Button>
      </DialogFooter>
    </form>
  );
}
