import { createClient } from "@/lib/supabase/server";
import Painel from "./painel";

export default async function Dashboards() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <main className="container">
      <header className="topo">
        <div>
          <h1>KPI Builder</h1>
          <p className="muted">{user?.email}</p>
        </div>
        <form action="/auth/signout" method="post">
          <button className="link">Sair</button>
        </form>
      </header>

      <Painel />
    </main>
  );
}
