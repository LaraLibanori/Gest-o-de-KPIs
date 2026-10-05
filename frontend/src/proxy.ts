import { NextResponse, type NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";

// O navegador não renova a sessão (o cookie é httpOnly), então isso fica aqui.
export async function proxy(request: NextRequest) {
  let resposta = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.SUPABASE_URL!,
    process.env.SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll: () => request.cookies.getAll(),
        setAll: (lista) => {
          lista.forEach(({ name, value }) => request.cookies.set(name, value));
          resposta = NextResponse.next({ request });
          lista.forEach(({ name, value, options }) =>
            resposta.cookies.set(name, value, {
              ...options,
              httpOnly: true,
              secure: process.env.NODE_ENV === "production",
            }),
          );
        },
      },
    },
  );

  await supabase.auth.getSession();
  return resposta;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|icon.svg|servidor|auth).*)"],
};
