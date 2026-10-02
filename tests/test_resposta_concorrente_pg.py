"""Concorrencia da resposta. So roda com TEST_DATABASE_URL_PG."""

from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.tokens import novo_id
from app.models.base import agora
from app.models.configuracao import ConfiguracaoProjeto
from app.models.controle_acesso import ControleAcesso
from app.models.organizacao import Organizacao
from app.models.pesquisa import Pergunta, Resposta
from app.models.projeto import Projeto, ProjetoUsuario, RotuloProjeto
from app.models.usuario import Usuario
from app.services.identidade import ErroAuth
from app.services.pesquisa.crud import adicionar_pergunta, criar_pesquisa, publicar
from app.services.pesquisa.resposta import registrar_respostas_da_pesquisa
from app.services.projeto import IA_SUSPENSA, garantir_rotulos

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL_PG"),
    reason="concorrencia da resposta so e provada no Postgres",
)


def _engine():
    return create_engine(
        os.environ["TEST_DATABASE_URL_PG"],
        pool_size=25,
        max_overflow=5,
    )


def _usuario(papel: str, email: str) -> Usuario:
    agora_ = agora()
    return Usuario(
        id=novo_id(),
        nome=email.split("@")[0][:160],
        email=email,
        senha_hash=None,
        papel=papel,
        tipo_conta="NORMAL",
        ativo=True,
        tentativas_falhas=0,
        criado_em=agora_,
        atualizado_em=agora_,
        deleted_at=None,
    )


def _montar(fabrica) -> tuple[str, list[str]]:
    with fabrica() as db:
        garantir_rotulos(db)
        rotulo = db.scalar(
            select(RotuloProjeto).where(RotuloProjeto.codigo == "CLIMA")
        )
        assert rotulo is not None
        dono = _usuario("CONSULTOR", f"conc-{novo_id()}@horizon.dev")
        db.add(dono)
        db.flush()
        agora_ = agora()
        org = Organizacao(
            id=novo_id(),
            cnpj=f"{int(time.time() * 1000) % 10**14:014d}",
            razao_social="Concorrencia Lab",
            nome_fantasia=None,
            municipio="Lab",
            uf="DF",
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
        db.add(org)
        db.flush()
        projeto = Projeto(
            id=novo_id(),
            organizacao_id=org.id,
            consultor_id=dono.id,
            rotulo_id=rotulo.id,
            estado="ABERTO",
            vinculo_tipo="EDITAL",
            vinculo_titulo="Concorrencia",
            criado_em=agora_,
            atualizado_em=agora_,
            deleted_at=None,
        )
        db.add(projeto)
        db.flush()
        db.add(
            ProjetoUsuario(
                id=novo_id(),
                projeto_id=projeto.id,
                usuario_id=dono.id,
                papel="CONSULTOR",
            )
        )
        db.add(
            ConfiguracaoProjeto(
                id=novo_id(),
                projeto_id=projeto.id,
                pesquisas_habilitadas=True,
                ia_modo=IA_SUSPENSA,
                criado_em=agora_,
                atualizado_em=agora_,
            )
        )
        ids: list[str] = []
        for indice in range(101):
            pessoa = _usuario(
                "FUNCIONARIO",
                f"c{indice}-{novo_id()}@sintetico.invalid",
            )
            db.add(pessoa)
            db.flush()
            ids.append(pessoa.id)
            db.add(
                ProjetoUsuario(
                    id=novo_id(),
                    projeto_id=projeto.id,
                    usuario_id=pessoa.id,
                    papel="FUNCIONARIO",
                )
            )
        db.commit()
        dono = db.get(Usuario, dono.id)
        assert dono is not None
        pesquisa = criar_pesquisa(
            db, dono, projeto.id, "Rajada", "CLIMA", "sintetica"
        )
        adicionar_pergunta(db, dono, pesquisa.id, "Nota", "NOTA_5", True, [])
        publicar(db, dono, pesquisa.id)
        return pesquisa.id, ids


def _um(fabrica, pesquisa_id: str, usuario_id: str) -> tuple[int, str]:
    try:
        with fabrica() as db:
            usuario = db.get(Usuario, usuario_id)
            assert usuario is not None
            pergunta_id = db.scalar(
                select(Pergunta.id).where(Pergunta.pesquisa_id == pesquisa_id)
            )
            registrar_respostas_da_pesquisa(
                db,
                pesquisa_id,
                [{"pergunta_id": pergunta_id, "valor_numerico": 4}],
                usuario,
                ip="203.0.113.9",
            )
        return 200, ""
    except ErroAuth as exc:
        return exc.status, ""
    except OperationalError as exc:
        if "deadlock" in str(exc).lower():
            return 0, "deadlock"
        raise


def test_cem_usuarios_e_duplicata() -> None:
    engine = _engine()
    fabrica = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    pesquisa_id, ids = _montar(fabrica)
    pico = {"n": 0}
    parar = threading.Event()

    def vigiar() -> None:
        with engine.connect() as conexao:
            while not parar.is_set():
                valor = conexao.execute(
                    text(
                        "select count(*) from pg_stat_activity "
                        "where datname = current_database()"
                    )
                ).scalar()
                pico["n"] = max(pico["n"], int(valor or 0))
                time.sleep(0.05)

    vigia = threading.Thread(target=vigiar, daemon=True)
    vigia.start()
    inicio = time.perf_counter()
    deadlocks = 0
    codigos: list[int] = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futuros = [
            pool.submit(_um, fabrica, pesquisa_id, uid) for uid in ids[:100]
        ]
        for futuro in futuros:
            codigo, marca = futuro.result()
            if marca == "deadlock":
                deadlocks += 1
            codigos.append(codigo)
    parar.set()
    vigia.join(timeout=1)
    duracao = time.perf_counter() - inicio
    print(f"100 usuarios em {duracao:.2f}s; pico={pico['n']}")
    assert deadlocks == 0
    assert codigos.count(200) == 100
    with fabrica() as db:
        total = db.scalar(
            select(func.count())
            .select_from(Resposta)
            .join(Pergunta, Pergunta.id == Resposta.pergunta_id)
            .where(Pergunta.pesquisa_id == pesquisa_id)
        )
        assert total == 100
        chaves = db.scalar(
            select(func.count())
            .select_from(ControleAcesso)
            .where(ControleAcesso.chave.like("responder:%"))
        )
        assert chaves == 0

    barreira = threading.Barrier(2)

    def junto() -> tuple[int, str]:
        barreira.wait(timeout=5)
        return _um(fabrica, pesquisa_id, ids[100])

    with ThreadPoolExecutor(max_workers=2) as pool:
        pares = [pool.submit(junto).result(), pool.submit(junto).result()]
    status = sorted(item[0] for item in pares)
    assert status == [200, 409]
    assert "deadlock" not in {item[1] for item in pares}
    with fabrica() as db:
        de_novo = db.scalar(
            select(func.count())
            .select_from(Resposta)
            .join(Pergunta, Pergunta.id == Resposta.pergunta_id)
            .where(Pergunta.pesquisa_id == pesquisa_id)
        )
        assert de_novo == 101
