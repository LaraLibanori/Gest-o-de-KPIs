import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import Formulario from "./formulario";

export default async function Login() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) redirect("/dashboards");

  return <Formulario />;
}
