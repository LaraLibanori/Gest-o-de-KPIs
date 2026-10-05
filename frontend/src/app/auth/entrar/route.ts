import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { mesmaOrigem } from "@/lib/origem";
import { excedeu } from "@/lib/tentativas";

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

  // Atras da Vercel todos chegam ao Supabase pelo mesmo IP, entao o limite fica aqui.
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "";
  if (excedeu(`ip:${ip}`, 30) || excedeu(`email:${email.toLowerCase()}`, 8))
    return NextResponse.json(
      { codigo: "over_request_rate_limit", mensagem: "" },
      { status: 429 },
    );

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
