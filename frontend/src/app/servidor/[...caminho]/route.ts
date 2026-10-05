import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { mesmaOrigem } from "@/lib/origem";

// Na Vercel o backend responde em /api, no mesmo dominio.
const BACKEND = (
  process.env.BACKEND_URL ??
  (process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}/api`
    : "http://127.0.0.1:8000")
).replace(/\/$/, "");

// Maior que o teto de 20s por chamada da LLM, senao o proxy aborta antes.
const PRAZO = 65_000;
const ESCRITA = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function erro(status: number, detail: string) {
  return NextResponse.json({ detail }, { status });
}

async function repassar(
  request: NextRequest,
  contexto: { params: Promise<{ caminho: string[] }> },
) {
  const escrita = ESCRITA.has(request.method);
  if (escrita && !mesmaOrigem(request))
    return erro(403, "origem não permitida");

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return erro(401, "sessão expirada, faça login de novo");

  const { caminho } = await contexto.params;
  const alvo = `${BACKEND}/${caminho.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  const corpo = escrita ? await request.arrayBuffer() : null;

  let resposta: Response;
  try {
    resposta = await fetch(alvo, {
      method: request.method,
      headers: {
        Authorization: `Bearer ${session.access_token}`,
        "Content-Type": "application/json",
      },
      body: corpo && corpo.byteLength > 0 ? corpo : undefined,
      signal: AbortSignal.timeout(PRAZO),
      cache: "no-store",
    });
  } catch {
    return erro(502, "o servidor não respondeu, tente de novo");
  }

  const cabecalhos = new Headers();
  for (const nome of ["content-type", "x-request-id"]) {
    const valor = resposta.headers.get(nome);
    if (valor) cabecalhos.set(nome, valor);
  }
  return new NextResponse(resposta.status === 204 ? null : resposta.body, {
    status: resposta.status,
    headers: cabecalhos,
  });
}

export {
  repassar as GET,
  repassar as POST,
  repassar as PUT,
  repassar as PATCH,
  repassar as DELETE,
};
