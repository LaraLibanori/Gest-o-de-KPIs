import type { NextRequest } from "next/server";

// Com cookie de sessão, escrita vinda de outro site tem que ser barrada.
export function mesmaOrigem(request: NextRequest): boolean {
  const origem = request.headers.get("origin");
  if (!origem) return false;
  try {
    return new URL(origem).origin === request.nextUrl.origin;
  } catch {
    return false;
  }
}
