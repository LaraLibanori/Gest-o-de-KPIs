"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function Formulario() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [modo, setModo] = useState<"entrar" | "criar">("entrar");
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setAviso(null);
    setCarregando(true);

    const supabase = createClient();
    const { error } =
      modo === "entrar"
        ? await supabase.auth.signInWithPassword({ email, password: senha })
        : await supabase.auth.signUp({ email, password: senha });

    setCarregando(false);

    if (error) {
      setErro(error.message);
    } else if (modo === "criar") {
      setAviso("Conta criada. Confirme o e-mail e depois entre.");
      setModo("entrar");
    } else {
      router.push("/dashboards");
      router.refresh();
    }
  }

  return (
    <main className="container" style={{ maxWidth: 400, paddingTop: 100 }}>
      <h1>KPI Builder</h1>
      <p className="muted">
        {modo === "entrar" ? "Entre para ver seus dashboards." : "Crie sua conta."}
      </p>

      <form onSubmit={enviar} className="card" style={{ marginTop: 24 }}>
        <label htmlFor="email">E-mail</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <label htmlFor="senha">Senha</label>
        <input
          id="senha"
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          minLength={6}
          required
        />

        <button type="submit" disabled={carregando}>
          {carregando ? "..." : modo === "entrar" ? "Entrar" : "Criar conta"}
        </button>

        {erro && <p className="erro">{erro}</p>}
        {aviso && <p className="ok">{aviso}</p>}
      </form>

      <button
        className="link"
        onClick={() => setModo(modo === "entrar" ? "criar" : "entrar")}
      >
        {modo === "entrar" ? "Não tenho conta" : "Já tenho conta"}
      </button>
    </main>
  );
}
