import next from "eslint-config-next";

const regras = [
  ...next,
  {
    // O app busca dados dentro de useEffect e grava o resultado em state. A
    // regra do React Compiler reclama disso, mas a saida so com uma camada de
    // dados (SWR, React Query) ou server components, que e reescrever o app.
    // Fica como aviso: aparece no lint, mas nao trava o CI.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default regras;
