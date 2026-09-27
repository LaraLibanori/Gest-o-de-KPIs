class ConexaoFalsa:
    async def fetch(self, sql, *args):
        return []


def conexao_falsa() -> ConexaoFalsa:
    return ConexaoFalsa()
