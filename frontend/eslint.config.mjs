import next from "eslint-config-next";

const regras = [
  ...next,
  {
    // O app busca dado em useEffect; a regra so passa com camada de dados.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
    },
  },
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts"],
  },
];

export default regras;
