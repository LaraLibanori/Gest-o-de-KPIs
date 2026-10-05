async def test_toda_tabela_do_servico_tem_rls(admin):
    sem = await admin.fetch(
        """
        select c.relname from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity
        """
    )
    assert [r["relname"] for r in sem] == []
