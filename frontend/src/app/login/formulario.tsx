"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, Building2, Loader2 } from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type Modo = "entrar" | "criar";

// As mensagens do Supabase vêm em inglês e cruas demais para a tela.
function traduzir(codigo: string | undefined, mensagem: string): string {
  if (codigo === "user_already_exists") return "Já existe uma conta com esse e-mail.";
  if (codigo === "invalid_credentials") return "E-mail ou senha incorretos.";
  if (codigo === "weak_password") return "A senha precisa de pelo menos 6 caracteres.";
  if (codigo === "over_request_rate_limit")
    return "Muitas tentativas seguidas. Espere um pouco.";
  return mensagem || "Não foi possível concluir. Tente de novo.";
}

export default function Formulario() {
  const router = useRouter();
  const [modo, setModo] = useState<Modo>("entrar");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (carregando) return;
    setErro(null);
    setCarregando(true);

    const supabase = createClient();
    const { error } =
      modo === "entrar"
        ? await supabase.auth.signInWithPassword({ email, password: senha })
        : await supabase.auth.signUp({ email, password: senha });

    setCarregando(false);

    if (error) {
      setErro(traduzir(error.code, error.message));
      return;
    }

    // A conta já nasce ativa, então quem se cadastra entra direto.
    if (modo === "criar") sessionStorage.setItem("conta-criada", "1");
    router.push("/");
    router.refresh();
  }

  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="bg-primary text-primary-foreground flex size-11 items-center justify-center rounded-xl">
            <Building2 className="size-5" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">KPI Builder</h1>
            <p className="text-muted-foreground text-sm">
              Indicadores a partir do seu banco, sem programar.
            </p>
          </div>
        </div>

        <Card>
          <CardHeader>
            <Tabs
              value={modo}
              onValueChange={(v) => {
                setModo(v as Modo);
                setErro(null);
              }}
            >
              <TabsList className="w-full">
                <TabsTrigger value="entrar">Entrar</TabsTrigger>
                <TabsTrigger value="criar">Criar conta</TabsTrigger>
              </TabsList>
            </Tabs>
            <CardTitle className="sr-only">
              {modo === "entrar" ? "Entrar" : "Criar conta"}
            </CardTitle>
            <CardDescription className="pt-2">
              {modo === "entrar"
                ? "Entre para ver suas organizações."
                : "A conta já fica ativa, sem confirmar e-mail."}
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={enviar}>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="email">E-mail</FieldLabel>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="voce@empresa.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </Field>

                <Field>
                  <FieldLabel htmlFor="senha">Senha</FieldLabel>
                  <Input
                    id="senha"
                    type="password"
                    autoComplete={
                      modo === "entrar" ? "current-password" : "new-password"
                    }
                    placeholder="pelo menos 6 caracteres"
                    value={senha}
                    onChange={(e) => setSenha(e.target.value)}
                    minLength={6}
                    required
                  />
                </Field>

                {erro && (
                  <Alert variant="destructive">
                    <AlertCircle />
                    <AlertDescription>{erro}</AlertDescription>
                  </Alert>
                )}

                <Button type="submit" className="w-full" disabled={carregando}>
                  {carregando && <Loader2 className="animate-spin" />}
                  {modo === "entrar" ? "Entrar" : "Criar conta"}
                </Button>
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
