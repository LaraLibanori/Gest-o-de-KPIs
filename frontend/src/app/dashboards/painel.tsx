"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Dashboard, type Indicador, type Valor } from "@/lib/api";

const AGREGACOES = ["count", "sum", "avg", "min", "max"] as const;
const COLUNAS = ["quantidade", "valor"];

export default function Painel() {
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [ativo, setAtivo] = useState<string | null>(null);
  const [indicadores, setIndicadores] = useState<Indicador[]>([]);
  const [valores, setValores] = useState<Record<string, Valor>>({});
  const [erro, setErro] = useState<string | null>(null);

  const [nomeDashboard, setNomeDashboard] = useState("");
  const [nomeIndicador, setNomeIndicador] = useState("");
  const [agregacao, setAgregacao] = useState<string>("sum");
  const [coluna, setColuna] = useState("valor");

  const falhar = (e: unknown) => setErro(e instanceof Error ? e.message : String(e));

  const carregarDashboards = useCallback(async () => {
    try {
      const lista = await api<Dashboard[]>("/dashboards");
      setDashboards(lista);
      setAtivo((atual) => atual ?? lista[0]?.id ?? null);
    } catch (e) {
      falhar(e);
    }
  }, []);

  const carregarIndicadores = useCallback(async (dashboardId: string) => {
    try {
      const lista = await api<Indicador[]>(`/dashboards/${dashboardId}/indicadores`);
      setIndicadores(lista);

      const calculados = await Promise.all(
        lista.map((i) => api<Valor>(`/indicadores/${i.id}/valor`)),
      );
      setValores(Object.fromEntries(calculados.map((v) => [v.indicador_id, v])));
    } catch (e) {
      falhar(e);
    }
  }, []);

  useEffect(() => {
    carregarDashboards();
  }, [carregarDashboards]);

  useEffect(() => {
    if (ativo) carregarIndicadores(ativo);
  }, [ativo, carregarIndicadores]);

  async function criarDashboard(e: React.FormEvent) {
    e.preventDefault();
    try {
      const novo = await api<Dashboard>("/dashboards", {
        method: "POST",
        body: JSON.stringify({ nome: nomeDashboard }),
      });
      setNomeDashboard("");
      setDashboards((d) => [novo, ...d]);
      setAtivo(novo.id);
    } catch (e) {
      falhar(e);
    }
  }

  async function criarIndicador(e: React.FormEvent) {
    e.preventDefault();
    if (!ativo) return;
    try {
      await api<Indicador>(`/dashboards/${ativo}/indicadores`, {
        method: "POST",
        body: JSON.stringify({
          nome: nomeIndicador,
          fonte: "vendas",
          coluna: agregacao === "count" ? null : coluna,
          agregacao,
        }),
      });
      setNomeIndicador("");
      carregarIndicadores(ativo);
    } catch (e) {
      falhar(e);
    }
  }

  async function removerIndicador(id: string) {
    try {
      await api<void>(`/indicadores/${id}`, { method: "DELETE" });
      if (ativo) carregarIndicadores(ativo);
    } catch (e) {
      falhar(e);
    }
  }

  return (
    <>
      {erro && <p className="erro">{erro}</p>}

      <form onSubmit={criarDashboard} className="linha">
        <input
          placeholder="Nome do dashboard"
          value={nomeDashboard}
          onChange={(e) => setNomeDashboard(e.target.value)}
          required
        />
        <button type="submit">Criar dashboard</button>
      </form>

      <nav className="abas">
        {dashboards.map((d) => (
          <button
            key={d.id}
            className={d.id === ativo ? "aba ativa" : "aba"}
            onClick={() => setAtivo(d.id)}
          >
            {d.nome}
          </button>
        ))}
      </nav>

      {ativo && (
        <>
          <section className="grade">
            {indicadores.map((i) => (
              <article key={i.id} className="card indicador">
                <button
                  className="remover"
                  onClick={() => removerIndicador(i.id)}
                  aria-label={`Remover ${i.nome}`}
                >
                  ×
                </button>
                <strong>{i.nome}</strong>
                <span className="numero">
                  {valores[i.id]?.valor?.toLocaleString("pt-BR", {
                    maximumFractionDigits: 2,
                  }) ?? "—"}
                </span>
                <span className="muted">
                  {i.agregacao}
                  {i.coluna ? ` · ${i.coluna}` : ""} · {i.fonte}
                </span>
              </article>
            ))}
            {indicadores.length === 0 && (
              <p className="muted">Nenhum indicador ainda. Crie o primeiro abaixo.</p>
            )}
          </section>

          <form onSubmit={criarIndicador} className="linha">
            <input
              placeholder="Nome do indicador"
              value={nomeIndicador}
              onChange={(e) => setNomeIndicador(e.target.value)}
              required
            />
            <select value={agregacao} onChange={(e) => setAgregacao(e.target.value)}>
              {AGREGACOES.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <select
              value={coluna}
              onChange={(e) => setColuna(e.target.value)}
              disabled={agregacao === "count"}
            >
              {COLUNAS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <button type="submit">Adicionar</button>
          </form>
        </>
      )}
    </>
  );
}
