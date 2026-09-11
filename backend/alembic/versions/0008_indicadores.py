"""indicadores"""

import sqlalchemy as sa
from sqlalchemy import column, table
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

ROLE = "kpi_api"

AGREGACOES = "('soma', 'media', 'contagem', 'distintos', 'minimo', 'maximo')"
PERIODOS = (
    "('sempre', 'ultimos_7_dias', 'ultimos_30_dias', 'ultimos_90_dias', 'ano_atual')"
)
ETAPAS_NOVA = "('tabela', 'negocio', 'catalogo', 'indicadores', 'pronta')"
ETAPAS_ANTIGA = "('tabela', 'negocio', 'catalogo', 'pronta')"

# Lista fechada, inspirada nas secoes da CNAE.
SEGMENTOS = [
    ("varejo", "Varejo e comércio"),
    ("atacado", "Atacado e distribuição"),
    ("industria", "Indústria e manufatura"),
    ("servicos", "Serviços profissionais"),
    ("alimentacao", "Alimentação e restaurantes"),
    ("saude", "Saúde e clínicas"),
    ("educacao", "Educação e ensino"),
    ("logistica", "Logística e transporte"),
    ("financeiro", "Serviços financeiros"),
    ("tecnologia", "Tecnologia e software"),
    ("construcao", "Construção civil"),
    ("agro", "Agronegócio"),
    ("outro", "Outro"),
]

# Por segmento: nome, pista do campo, agregacao, papel exigido.
KPIS = {
    "varejo": [
        ("Receita total", "valor da venda", "soma", "metrica"),
        ("Ticket médio", "valor da venda", "media", "metrica"),
        ("Vendas realizadas", None, "contagem", None),
        ("Produtos vendidos", "quantidade de itens", "soma", "metrica"),
        ("Clientes atendidos", "identificador do cliente", "distintos", "dimensao"),
    ],
    "atacado": [
        ("Faturamento", "valor do pedido", "soma", "metrica"),
        ("Pedido médio", "valor do pedido", "media", "metrica"),
        ("Pedidos emitidos", None, "contagem", None),
        ("Volume expedido", "quantidade", "soma", "metrica"),
        ("Clientes ativos", "identificador do cliente", "distintos", "dimensao"),
    ],
    "industria": [
        ("Produção total", "quantidade produzida", "soma", "metrica"),
        ("Custo médio de produção", "custo", "media", "metrica"),
        ("Ordens de produção", None, "contagem", None),
        ("Perdas", "quantidade perdida ou refugada", "soma", "metrica"),
        ("Itens fabricados", "produto", "distintos", "dimensao"),
    ],
    "servicos": [
        ("Receita de serviços", "valor do serviço", "soma", "metrica"),
        ("Valor médio por atendimento", "valor do serviço", "media", "metrica"),
        ("Atendimentos", None, "contagem", None),
        ("Horas trabalhadas", "horas", "soma", "metrica"),
        ("Clientes atendidos", "identificador do cliente", "distintos", "dimensao"),
    ],
    "alimentacao": [
        ("Faturamento", "valor da conta", "soma", "metrica"),
        ("Ticket médio", "valor da conta", "media", "metrica"),
        ("Pedidos", None, "contagem", None),
        ("Itens vendidos", "quantidade", "soma", "metrica"),
        ("Itens do cardápio", "prato ou produto", "distintos", "dimensao"),
    ],
    "saude": [
        ("Atendimentos", None, "contagem", None),
        ("Receita de procedimentos", "valor do procedimento", "soma", "metrica"),
        ("Valor médio por procedimento", "valor do procedimento", "media", "metrica"),
        ("Pacientes atendidos", "identificador do paciente", "distintos", "dimensao"),
        ("Procedimentos distintos", "procedimento", "distintos", "dimensao"),
    ],
    "educacao": [
        ("Matrículas", None, "contagem", None),
        ("Receita de mensalidades", "valor da mensalidade", "soma", "metrica"),
        ("Mensalidade média", "valor da mensalidade", "media", "metrica"),
        ("Alunos", "identificador do aluno", "distintos", "dimensao"),
        ("Cursos oferecidos", "curso", "distintos", "dimensao"),
    ],
    "logistica": [
        ("Entregas", None, "contagem", None),
        ("Custo de frete", "valor do frete", "soma", "metrica"),
        ("Frete médio", "valor do frete", "media", "metrica"),
        ("Peso transportado", "peso", "soma", "metrica"),
        ("Destinos atendidos", "cidade ou destino", "distintos", "dimensao"),
    ],
    "financeiro": [
        ("Volume transacionado", "valor da transação", "soma", "metrica"),
        ("Valor médio", "valor da transação", "media", "metrica"),
        ("Transações", None, "contagem", None),
        ("Tarifas", "tarifa cobrada", "soma", "metrica"),
        ("Clientes", "identificador do cliente", "distintos", "dimensao"),
    ],
    "tecnologia": [
        ("Receita recorrente", "valor do contrato", "soma", "metrica"),
        ("Valor médio por contrato", "valor do contrato", "media", "metrica"),
        ("Contratos", None, "contagem", None),
        ("Clientes", "identificador do cliente", "distintos", "dimensao"),
        ("Planos contratados", "plano", "distintos", "dimensao"),
    ],
    "construcao": [
        ("Custo de obra", "custo", "soma", "metrica"),
        ("Custo médio", "custo", "media", "metrica"),
        ("Obras", None, "contagem", None),
        ("Horas de mão de obra", "horas", "soma", "metrica"),
        ("Materiais utilizados", "material", "distintos", "dimensao"),
    ],
    "agro": [
        ("Produção colhida", "quantidade colhida", "soma", "metrica"),
        ("Receita", "valor da venda", "soma", "metrica"),
        ("Produtividade média", "produtividade por área", "media", "metrica"),
        ("Safras", None, "contagem", None),
        ("Culturas", "cultura plantada", "distintos", "dimensao"),
    ],
}


def upgrade() -> None:
    op.create_table(
        "segmentos",
        sa.Column("chave", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("chave"),
    )
    op.create_table(
        "segmento_kpis",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("segmento", sa.Text(), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("pista", sa.Text(), nullable=True),
        sa.Column("agregacao", sa.Text(), nullable=False),
        sa.Column("papel", sa.Text(), nullable=True),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            f"agregacao in {AGREGACOES}", name="segmento_kpis_agregacao_check"
        ),
        sa.ForeignKeyConstraint(["segmento"], ["segmentos.chave"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        "create unique index segmento_kpis_unico on segmento_kpis (segmento, nome)"
    )

    op.create_table(
        "classificacoes",
        sa.Column("chave", sa.Text(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("segmento", sa.Text(), nullable=False),
        sa.Column(
            "criada_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["segmento"], ["segmentos.chave"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chave"),
    )

    op.create_table(
        "indicadores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("conexao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("agregacao", sa.Text(), nullable=False),
        sa.Column("coluna", sa.Text(), nullable=True),
        sa.Column("dimensao", sa.Text(), nullable=True),
        sa.Column("tempo", sa.Text(), nullable=True),
        sa.Column("periodo", sa.Text(), nullable=True),
        sa.Column("origem", sa.Text(), nullable=False),
        sa.Column(
            "confirmado", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"agregacao in {AGREGACOES}", name="indicadores_agregacao_check"
        ),
        sa.CheckConstraint(
            "origem in ('regra', 'segmento', 'manual')", name="indicadores_origem_check"
        ),
        sa.CheckConstraint(
            f"periodo is null or periodo in {PERIODOS}",
            name="indicadores_periodo_check",
        ),
        sa.ForeignKeyConstraint(["conexao_id"], ["conexoes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("conexoes", sa.Column("segmento", sa.Text(), nullable=True))
    op.create_foreign_key(
        "conexoes_segmento_fkey",
        "conexoes",
        "segmentos",
        ["segmento"],
        ["chave"],
        ondelete="SET NULL",
    )
    op.drop_constraint("conexoes_etapa_check", "conexoes", type_="check")
    op.create_check_constraint(
        "conexoes_etapa_check", "conexoes", f"etapa in {ETAPAS_NOVA}"
    )

    op.bulk_insert(
        table("segmentos", column("chave"), column("nome"), column("ordem")),
        [
            {"chave": chave, "nome": nome, "ordem": i}
            for i, (chave, nome) in enumerate(SEGMENTOS, start=1)
        ],
    )
    op.bulk_insert(
        table(
            "segmento_kpis",
            column("segmento"),
            column("nome"),
            column("pista"),
            column("agregacao"),
            column("papel"),
            column("ordem"),
        ),
        [
            {
                "segmento": segmento,
                "nome": nome,
                "pista": pista,
                "agregacao": agregacao,
                "papel": papel,
                "ordem": i,
            }
            for segmento, lista in KPIS.items()
            for i, (nome, pista, agregacao, papel) in enumerate(lista, start=1)
        ],
    )

    # Os tres primeiros sao dados de referencia: todo mundo le, ninguem apaga.
    for tabela in ("segmentos", "segmento_kpis", "classificacoes"):
        op.execute(f"alter table {tabela} enable row level security")
        op.execute(f'create policy "leitura comum" on {tabela} for all using (true)')
    op.execute(f"grant select on segmentos to {ROLE}")
    op.execute(f"grant select, insert on segmento_kpis to {ROLE}")
    op.execute(f"grant select, insert on classificacoes to {ROLE}")

    op.execute(f"grant select, insert, update, delete on indicadores to {ROLE}")
    op.execute("alter table indicadores enable row level security")
    # A policy de conexoes ja filtra o subselect por organizacao.
    op.execute(
        """
        create policy "indicadores da minha conexao" on indicadores
          for all using (conexao_id in (select id from conexoes))
          with check (conexao_id in (select id from conexoes))
        """
    )


def downgrade() -> None:
    op.drop_table("indicadores")
    op.drop_constraint("conexoes_etapa_check", "conexoes", type_="check")
    op.execute("update conexoes set etapa = 'pronta' where etapa = 'indicadores'")
    op.create_check_constraint(
        "conexoes_etapa_check", "conexoes", f"etapa in {ETAPAS_ANTIGA}"
    )
    op.drop_constraint("conexoes_segmento_fkey", "conexoes", type_="foreignkey")
    op.drop_column("conexoes", "segmento")
    op.drop_table("classificacoes")
    op.drop_table("segmento_kpis")
    op.drop_table("segmentos")
