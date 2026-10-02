"use client";

import { ChevronDown, Loader2, Plug, ShieldCheck } from "lucide-react";
import type { Conexao } from "@/lib/api";
import { Button } from "@/components/ui/button";
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
  editando: boolean;
  podeTestar: boolean;
  onTestar: () => void;
  onEnviar: (e: React.FormEvent) => void;
  onCancelar: () => void;
}) {
  const trocar = (campo: keyof Credenciais) => (v: string) =>
    setForm({ ...form, [campo]: v });

  return (
    <form onSubmit={onEnviar} className="space-y-6">
      <FieldGroup className="gap-5">
        <Field>
          <FieldLabel htmlFor="nome">Como esta conexão se chama?</FieldLabel>
          <Input
            id="nome"
            placeholder="Produção"
            value={form.nome}
            onChange={(e) => trocar("nome")(e.target.value)}
            maxLength={120}
            required
            autoFocus
          />
          <FieldDescription>
            Serve para você reconhecer depois. Pode ter várias do mesmo banco.
          </FieldDescription>
        </Field>

        <div className="grid gap-5 sm:grid-cols-[1fr_7rem]">
          <Field>
            <FieldLabel htmlFor="host">Endereço do servidor</FieldLabel>
            <Input
              id="host"
              placeholder="db.empresa.com"
              value={form.host}
              onChange={(e) => trocar("host")(e.target.value)}
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="porta">Porta</FieldLabel>
            <Input
              id="porta"
              type="number"
              value={form.porta}
              onChange={(e) => trocar("porta")(e.target.value)}
              required
            />
          </Field>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <Field>
            <FieldLabel htmlFor="banco">Banco</FieldLabel>
            <Input
              id="banco"
              placeholder="postgres"
              value={form.banco}
              onChange={(e) => trocar("banco")(e.target.value)}
              required
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="usuario">Usuário</FieldLabel>
            <Input
              id="usuario"
              autoComplete="off"
              value={form.usuario}
              onChange={(e) => trocar("usuario")(e.target.value)}
              required
            />
          </Field>
        </div>

        <Field>
          <FieldLabel htmlFor="senha">Senha</FieldLabel>
          <Input
            id="senha"
            type="password"
            autoComplete="new-password"
            placeholder={
              editando ? "deixe vazio para manter a atual" : undefined
            }
            value={form.senha}
            onChange={(e) => trocar("senha")(e.target.value)}
            required={!editando}
          />
          <FieldDescription className="flex items-center gap-1.5">
            <ShieldCheck className="size-3.5" />
            Um usuário só de leitura basta. A senha é guardada cifrada e não
            volta para a tela.
          </FieldDescription>
        </Field>

        <details className="group border-t pt-4">
          <summary className="text-muted-foreground flex cursor-pointer list-none items-center gap-1.5 text-sm hover:text-foreground">
            <ChevronDown className="size-4 transition-transform group-open:rotate-180" />
            Schema e outros ajustes
          </summary>
          <FieldGroup className="mt-4 gap-5">
            <Field>
              <FieldLabel htmlFor="esquema">Schema</FieldLabel>
              <Input
                id="esquema"
                placeholder="deixe vazio para ver todos"
                value={form.esquema}
                onChange={(e) => trocar("esquema")(e.target.value)}
              />
              <FieldDescription>
                Onde as tabelas moram dentro do banco. Não é o banco. A próxima
                etapa também deixa escolher.
              </FieldDescription>
            </Field>
          </FieldGroup>
        </details>
      </FieldGroup>

      <div className="flex flex-wrap items-center gap-2 border-t pt-4">
        <Button type="button" variant="ghost" onClick={onCancelar}>
          {editando ? "Fechar" : "Cancelar"}
        </Button>
        <div className="flex-1" />
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
          {testando ? <Loader2 className="animate-spin" /> : <Plug />}
          Testar sem salvar
        </Button>
        <Button type="submit" disabled={ocupado || testando}>
          {ocupado && <Loader2 className="animate-spin" />}
          {editando ? "Salvar e reconectar" : "Conectar"}
        </Button>
      </div>
    </form>
  );
}
