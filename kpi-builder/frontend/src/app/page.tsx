"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Health = { status: string; service: string; timestamp: string };

export default function Home() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setHealth)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main style={{ maxWidth: 760, margin: "0 auto", padding: "80px 24px" }}>
      <span
        style={{
          display: "inline-block",
          fontSize: 12,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--muted)",
          border: "1px solid #263150",
          borderRadius: 999,
          padding: "4px 12px",
        }}
      >
        TCC &middot; Entrega Parcial 2
      </span>

      <h1 style={{ fontSize: 40, lineHeight: 1.2, marginTop: 20 }}>
        KPI Builder
      </h1>

      <p style={{ fontSize: 18, color: "var(--muted)" }}>
        Conecte seu banco de dados e monte seus proprios dashboards de
        indicadores &mdash; sem precisar programar.
      </p>

      <div
        style={{
          background: "var(--card)",
          border: "1px solid #263150",
          borderRadius: 12,
          padding: 20,
          marginTop: 32,
        }}
      >
        <strong>Conexao com a API</strong>
        <p style={{ margin: "8px 0 0", color: "var(--muted)" }}>
          Front (Next.js) chamando o backend (FastAPI) em <code>{API_URL}</code>.
        </p>
        <p style={{ margin: "12px 0 0" }}>
          {health ? (
            <span style={{ color: "#4ade80" }}>
              &#9679; API online &mdash; status: {health.status} (
              {health.service})
            </span>
          ) : error ? (
            <span style={{ color: "#f87171" }}>
              &#9679; API offline &mdash; suba o backend com{" "}
              <code>uvicorn app.main:app --reload</code> ({error})
            </span>
          ) : (
            <span style={{ color: "var(--muted)" }}>&#9679; verificando...</span>
          )}
        </p>
      </div>
    </main>
  );
}
