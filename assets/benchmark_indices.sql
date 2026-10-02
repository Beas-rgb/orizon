-- ============================================================
-- HORIZON — Benchmark de índices (v2, revisado em 01/10/2026)
-- SOMENTE banco descartável de staging/local. Apaga dados.
--
-- Uso:
--   psql "<URL do staging>" -v ambiente=staging -v confirmo_apagar=SIM -f benchmark_indices.sql
--
-- Mudanças em relação à versão enviada:
--   * ON_ERROR_STOP: qualquer erro interrompe o script ANTES do TRUNCATE.
--   * Trava corrigida: a versão anterior comparava 'text' com 1/0 (tipos
--     incompatíveis) e dava erro SEMPRE; como o psql continua após erro, um valor
--     errado de ambiente NÃO impedia o TRUNCATE. Agora a checagem é \if explícito.
--   * Idempotente de verdade: remove os índices de teste antes do "ANTES";
--     a segunda execução volta a medir Seq Scan.
--   * Mantido do original: pais reais (sem session_replication_role), token_hash
--     de 64 caracteres, seed -> ANALYZE -> medir.
--   * Índice de superior_id NÃO entra aqui: nenhuma consulta SQL do app filtra por
--     superior_id hoje (a árvore é montada em Python). Ver FASE_03, T3.4.
-- ============================================================
\set ON_ERROR_STOP on
\set QUIET on
\timing off

\if :{?ambiente}
\else
  \echo 'ABORTADO: falta -v ambiente=staging'
  \quit
\endif
\if :{?confirmo_apagar}
\else
  \echo 'ABORTADO: falta -v confirmo_apagar=SIM (este script APAGA dados)'
  \quit
\endif
select (:'ambiente' = 'staging' and :'confirmo_apagar' = 'SIM') as liberado \gset
\if :liberado
  \echo 'Trava ok: ambiente=staging e confirmacao recebida.'
\else
  \echo 'ABORTADO: valores invalidos (ambiente deve ser staging e confirmo_apagar deve ser SIM).'
  \quit
\endif

select current_database() as banco, current_setting('server_version') as versao;

begin;
truncate sessoes, perfis_funcionario, projeto_usuarios, projetos,
         rotulos_projeto, organizacoes, usuarios cascade;

insert into usuarios(id,nome,email,senha_hash,papel,ativo,tentativas_falhas,criado_em,atualizado_em)
select 'u'||g,'User '||g,'u'||g||'@x.dev','h','FUNCIONARIO',true,0,now(),now() from generate_series(1,5000) g;
insert into usuarios(id,nome,email,senha_hash,papel,ativo,tentativas_falhas,criado_em,atualizado_em)
values ('c1','Consultora Benchmark','c1@x.dev','h','CONSULTOR',true,0,now(),now());
insert into organizacoes(id,cnpj,razao_social,criado_em,atualizado_em)
values ('o1','00000000000191','Org Benchmark LTDA',now(),now());
insert into rotulos_projeto(id,codigo,nome,ordem) values ('r1','BENCH','Benchmark',0);
insert into projetos(id,organizacao_id,consultor_id,rotulo_id,estado,vinculo_tipo,vinculo_titulo,criado_em,atualizado_em)
select 'p'||g,'o1','c1','r1','ATIVO','EDITAL','t',now(),now() from generate_series(1,300) g;
-- 150.000 vínculos: cada usuário em 30 projetos
insert into projeto_usuarios(id,projeto_id,usuario_id,papel)
select 'pu'||row_number() over (), 'p'||(1+((g*7+k*13) % 300)), 'u'||g, 'FUNCIONARIO'
from generate_series(1,5000) g, generate_series(1,30) k on conflict do nothing;
-- 200.000 sessões: 40 por usuário, 1 aberta e 39 revogadas; hash de 64 caracteres
insert into sessoes(id,usuario_id,token_hash,expira_em,revogado_em,criado_em)
select 's'||g||'_'||k,'u'||g,repeat(md5(g||'_'||k),2),now()+interval '7 days',
       case when k<40 then now() else null end, now()
from generate_series(1,5000) g, generate_series(1,40) k;
commit;

-- Estado de partida: sem nenhum dos índices candidatos
drop index if exists ix_projeto_usuarios_usuario_id;
drop index if exists ix_sessoes_usuario_id;
drop index if exists ix_sessoes_usuario_aberta;
analyze;

\echo '=== ANTES (sem índices) ==='
\echo 'A) projetos de um usuário (autorizacao.py:39 — todo request com escopo de projeto)'
explain (analyze, buffers, timing off, summary on) select * from projeto_usuarios where usuario_id='u4242';
explain (analyze, buffers, timing off, summary on) select * from projeto_usuarios where usuario_id='u4242';
\echo 'B) sessões abertas de um usuário (auth.py:_revogar_sessoes)'
explain (analyze, buffers, timing off, summary on) select * from sessoes where usuario_id='u4242' and revogado_em is null;
explain (analyze, buffers, timing off, summary on) select * from sessoes where usuario_id='u4242' and revogado_em is null;

create index ix_projeto_usuarios_usuario_id on projeto_usuarios(usuario_id);
create index ix_sessoes_usuario_aberta on sessoes(usuario_id) where revogado_em is null;
analyze;

\echo '=== DEPOIS ==='
\echo 'A)'
explain (analyze, buffers, timing off, summary on) select * from projeto_usuarios where usuario_id='u4242';
explain (analyze, buffers, timing off, summary on) select * from projeto_usuarios where usuario_id='u4242';
\echo 'B)'
explain (analyze, buffers, timing off, summary on) select * from sessoes where usuario_id='u4242' and revogado_em is null;
explain (analyze, buffers, timing off, summary on) select * from sessoes where usuario_id='u4242' and revogado_em is null;
select pg_size_pretty(pg_relation_size('ix_projeto_usuarios_usuario_id')) as tam_ix_projeto_usuarios,
       pg_size_pretty(pg_relation_size('ix_sessoes_usuario_aberta')) as tam_ix_sessoes_parcial;
\echo 'Fim. Cole os planos ANTES/DEPOIS em docs/PERFORMANCE.md.'
