import type { NextRequest } from "next/server";

export function mesmaOrigem(request: NextRequest): boolean {
  const origem = request.headers.get("origin");
  if (!origem) return false;
  try {
    return new URL(origem).origin === request.nextUrl.origin;
  } catch {
    return false;
  }
}
