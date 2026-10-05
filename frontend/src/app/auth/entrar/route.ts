import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { mesmaOrigem } from "@/lib/origem";

export async function POST(request: NextRequest) {
  if (!mesmaOrigem(request))
    return NextResponse.json(
      { mensagem: "origem não permitida" },
      { status: 403 },
    );

  const { modo, email, senha } = await request.json().catch(() => ({}));
  if (
    (modo !== "entrar" && modo !== "criar") ||
    typeof email !== "string" ||
    typeof senha !== "string"
  )
    return NextResponse.json({ mensagem: "dados inválidos" }, { status: 400 });

  const supabase = await createClient();
  const { error } =
    modo === "entrar"
      ? await supabase.auth.signInWithPassword({ email, password: senha })
      : await supabase.auth.signUp({ email, password: senha });

  if (error)
    return NextResponse.json(
      { codigo: error.code, mensagem: error.message },
      { status: 400 },
    );
  return NextResponse.json({ ok: true });
}
