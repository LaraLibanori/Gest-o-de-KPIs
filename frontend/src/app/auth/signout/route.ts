import { NextResponse, type NextRequest } from "next/server";
import { mesmaOrigem } from "@/lib/origem";
import { createClient } from "@/lib/supabase/server";

export async function POST(request: NextRequest) {
  if (!mesmaOrigem(request))
    return NextResponse.redirect(new URL("/login", request.url), {
      status: 303,
    });
  const supabase = await createClient();
  await supabase.auth.signOut();
  return NextResponse.redirect(new URL("/login", request.url), { status: 303 });
}
