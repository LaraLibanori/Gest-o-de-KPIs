import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import Shell from "./shell";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) redirect("/login");

  return <Shell email={user.email ?? ""}>{children}</Shell>;
}
