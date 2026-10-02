from app.core.database import argumentos_conexao


def test_pooler_desliga_prepared_statement() -> None:
    url = "postgresql://u:p@ep-abc-pooler.neon.tech/db"
    assert argumentos_conexao(url) == {"prepare_threshold": None}
    assert argumentos_conexao("postgresql://u:p@ep-abc.neon.tech/db") == {}


def test_timeout_do_pool_vira_503(client) -> None:
    from sqlalchemy.exc import TimeoutError as PoolTimeout

    from app.main import app

    @app.get("/_teste_pool")
    def _estoura() -> dict:
        raise PoolTimeout("pool", "timeout", "timeout")

    resposta = client.get("/_teste_pool")
    assert resposta.status_code == 503
    assert resposta.headers["retry-after"] == "3"
