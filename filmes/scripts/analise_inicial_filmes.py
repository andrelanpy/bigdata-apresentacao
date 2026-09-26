"""Analise inicial - Filmes e Classificacoes (IMDb non-commercial datasets, via Kaggle).

Etapa 1 converte os TSV brutos (~9,6 GB) para Parquet em dados/imdb/ (executada
uma unica vez). Etapa 2 roda as analises com DuckDB sobre o Parquet.

Uso: python filmes/scripts/analise_inicial_filmes.py   (a partir de trabalho_apresentacao/)
"""
import os
import sys
import tempfile
import time
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
import estilo  # noqa: E402

estilo.aplicar()

DADOS = Path(os.environ.get(
    "IMDB_DIR",
    Path.home() / ".cache/kagglehub/datasets/ashirwadsangwan/imdb-dataset/versions/903",
))
SAIDA = RAIZ / "filmes" / "resultados"
PARQUET = RAIZ / "dados" / "imdb"
SAIDA.mkdir(parents=True, exist_ok=True)
PARQUET.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.sql(f"SET temp_directory = '{Path(tempfile.gettempdir()).as_posix()}/duckdb_tmp'")
con.sql("SET preserve_insertion_order = false")
log = []


def registrar(texto=""):
    print(texto, flush=True)
    log.append(texto)


def tabela_md(df, casas=2):
    df = df.copy()
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].round(casas)
    return df.to_markdown(index=False)


# arquivo -> nome da view usada nas consultas
TABELAS = {"title.basics": "basics", "title.ratings": "ratings", "title.akas": "akas",
           "title.principals": "principals", "name.basics": "names"}

# ---------------------------------------------------------------------------
# 1. Ingestao: TSV -> Parquet (Volume)
# ---------------------------------------------------------------------------
registrar("# Filmes e Classificacoes (IMDb) - analise inicial\n")
registrar("## 1. Ingestao TSV -> Parquet\n")
linhas = []
for t, view in TABELAS.items():
    tsv = DADOS / f"{t}.tsv"
    pq = PARQUET / f"{t.replace('.', '_')}.parquet"
    t0 = time.perf_counter()
    convertido = not pq.exists()
    if convertido:
        # IMDb usa \N como nulo e nao usa aspas (titulos podem conter ")
        con.sql(f"""COPY (SELECT * FROM read_csv('{tsv.as_posix()}', delim='\t', header=true,
                                                 quote='', escape='', nullstr='\\N',
                                                 sample_size=-1))
                   TO '{pq.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    dt = time.perf_counter() - t0
    n = con.sql(f"SELECT count(*) FROM '{pq.as_posix()}'").fetchone()[0]
    linhas.append((t, f"{tsv.stat().st_size / 1e6:,.0f}", f"{pq.stat().st_size / 1e6:,.0f}",
                   f"{n:,}", f"{dt:.1f}s" if convertido else "(ja convertido)"))
    con.sql(f"CREATE VIEW {view} AS SELECT * FROM '{pq.as_posix()}'")
ingestao = pd.DataFrame(linhas, columns=["tabela", "TSV (MB)", "Parquet (MB)", "linhas", "conversao"])
registrar(ingestao.to_markdown(index=False))
ingestao.to_csv(SAIDA / "01_ingestao.csv", index=False)

registrar("\n### Nulos por coluna (title.basics)\n")
cols = [c[0] for c in con.sql("DESCRIBE basics").fetchall()]
nulos = con.sql("SELECT " + ", ".join(
    f"100.0 * count(*) FILTER (WHERE \"{c}\" IS NULL) / count(*) AS \"{c}\"" for c in cols)
    + " FROM basics").df().T.reset_index()
nulos.columns = ["coluna", "% nulo"]
registrar(tabela_md(nulos, 1))

futuros = con.sql("SELECT count(*), max(startYear) FROM basics WHERE startYear > year(current_date)").fetchone()
registrar(f"\nTitulos com ano de lancamento futuro (anunciados): {futuros[0]:,}, ate {futuros[1]}")
# ultimo ano completo; o ano corrente ainda esta em andamento no snapshot
ano_max = con.sql("SELECT year(current_date)").fetchone()[0]

# ---------------------------------------------------------------------------
# 2. Tipos de titulo e cobertura de avaliacoes
# ---------------------------------------------------------------------------
registrar("\n## 2. Tipos de titulo\n")
tipos = con.sql("""
    SELECT b.titleType AS tipo, count(*) AS titulos,
           count(r.tconst) AS com_avaliacao,
           100.0 * count(r.tconst) / count(*) AS pct_avaliados
    FROM basics b LEFT JOIN ratings r USING (tconst)
    GROUP BY tipo ORDER BY titulos DESC
""").df()
tipos.to_csv(SAIDA / "02_tipos_titulo.csv", index=False)
registrar(tabela_md(tipos, 1))

# Base analitica: longas-metragens (titleType = movie) com avaliacao
con.sql("""
    CREATE TABLE filmes AS
    SELECT b.tconst, b.primaryTitle AS titulo, b.startYear AS ano, b.runtimeMinutes AS duracao,
           b.genres, r.averageRating AS nota, r.numVotes AS votos
    FROM basics b JOIN ratings r USING (tconst)
    WHERE b.titleType = 'movie' AND b.isAdult = 0
""")
n_filmes = con.sql("SELECT count(*) FROM filmes").fetchone()[0]
registrar(f"\nFilmes (longa-metragem, nao adulto) com avaliacao: {n_filmes:,}")

# ---------------------------------------------------------------------------
# 3. Producao ao longo do tempo
# ---------------------------------------------------------------------------
registrar("\n## 3. Filmes lancados por ano\n")
por_ano = con.sql(f"""
    SELECT startYear AS ano, count(*) AS filmes_lancados,
           count(r.tconst) AS filmes_avaliados
    FROM basics b LEFT JOIN ratings r USING (tconst)
    WHERE titleType = 'movie' AND startYear BETWEEN 1900 AND {ano_max - 1}
    GROUP BY ano ORDER BY ano
""").df()
por_ano.to_csv(SAIDA / "03_filmes_por_ano.csv", index=False)
for a in (1920, 1950, 1980, 2000, 2010, 2019, 2020, 2021):
    r = por_ano[por_ano.ano == a]
    if len(r):
        registrar(f"- {a}: {int(r.filmes_lancados.iloc[0]):,} filmes")

fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(por_ano.ano, por_ano.filmes_lancados, color=estilo.AZUL, label="Cadastrados")
ax.plot(por_ano.ano, por_ano.filmes_avaliados, color=estilo.LARANJA, label="Com ao menos 1 avaliacao")
ax.set_title("Longas-metragens por ano de lancamento no IMDb")
ax.set_ylabel("filmes")
ax.legend(loc="upper left")
fig.savefig(SAIDA / "g1_filmes_por_ano.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Distribuicao das notas e concentracao dos votos (cauda longa)
# ---------------------------------------------------------------------------
registrar("\n## 4. Notas e votos\n")
est = con.sql("""
    SELECT avg(nota), median(nota), stddev(nota), median(votos), avg(votos), max(votos),
           corr(nota, ln(votos))
    FROM filmes
""").fetchone()
registrar(f"- Nota media {est[0]:.2f}, mediana {est[1]:.1f}, desvio-padrao {est[2]:.2f}")
registrar(f"- Votos por filme: mediana {est[3]:,.0f}, media {est[4]:,.0f}, maximo {est[5]:,}")
registrar(f"- Correlacao entre nota e log(votos): {est[6]:.2f}")

conc = con.sql("""
    WITH o AS (SELECT votos, row_number() OVER (ORDER BY votos DESC) AS pos,
                      count(*) OVER () AS n, sum(votos) OVER () AS total FROM filmes)
    SELECT 100.0 * sum(votos) FILTER (WHERE pos <= n * 0.01) / any_value(total),
           100.0 * sum(votos) FILTER (WHERE pos <= n * 0.10) / any_value(total),
           100.0 * count(*) FILTER (WHERE votos < 100) / any_value(n)
    FROM o
""").fetchone()
registrar(f"- Os 1% filmes mais votados concentram {conc[0]:.1f}% de todos os votos; "
          f"os 10% concentram {conc[1]:.1f}%")
registrar(f"- {conc[2]:.1f}% dos filmes tem menos de 100 votos")

hist = con.sql("""
    SELECT round(nota * 2) / 2 AS faixa,
           count(*) AS todos, count(*) FILTER (WHERE votos >= 1000) AS com_1000_votos
    FROM filmes GROUP BY faixa ORDER BY faixa
""").df()
hist.to_csv(SAIDA / "04_hist_notas.csv", index=False)
fig, axs = plt.subplots(1, 2, figsize=(11, 3.8), sharex=True)
axs[0].bar(hist.faixa, hist.todos, width=0.4, color=estilo.AZUL)
axs[0].set_title("Todos os filmes avaliados")
axs[1].bar(hist.faixa, hist.com_1000_votos, width=0.4, color=estilo.AZUL)
axs[1].set_title("Somente filmes com 1.000+ votos")
for ax in axs:
    ax.set_xlabel("nota media IMDb"); ax.grid(axis="x", visible=False)
axs[0].set_ylabel("filmes")
fig.suptitle("Distribuicao das notas", x=0.01, y=1.04, ha="left", fontweight="bold")
fig.savefig(SAIDA / "g2_hist_notas.png"); plt.close(fig)

curva = con.sql("""
    SELECT votos FROM filmes ORDER BY votos DESC
""").df().votos.to_numpy()
acum = np.cumsum(curva) / curva.sum() * 100
x = np.arange(1, len(curva) + 1) / len(curva) * 100
fig, ax = plt.subplots(figsize=(6.5, 4))
ax.plot(x, acum, color=estilo.AZUL)
for px, rot in ((1, "1%"), (10, "10%")):
    py = acum[int(len(curva) * px / 100) - 1]
    ax.plot(px, py, "o", color=estilo.AZUL, ms=8, mec=estilo.SUPERFICIE, mew=2)
    ax.annotate(f"{rot} dos filmes = {py:.0f}% dos votos", (px, py), xytext=(-150, 8),
                textcoords="offset points", color=estilo.TEXTO, fontsize=9)
ax.set_xscale("log"); ax.set_xlim(0.01, 100)
ax.set_title("Concentracao dos votos (curva de Lorenz)")
ax.set_xlabel("% dos filmes, do mais votado ao menos (escala log)")
ax.set_ylabel("% acumulado dos votos")
fig.savefig(SAIDA / "g3_concentracao_votos.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 5. Generos (campo multivalorado -> unnest)
# ---------------------------------------------------------------------------
registrar("\n## 5. Generos (filmes com 1.000+ votos)\n")
generos = con.sql("""
    SELECT g AS genero, count(*) AS filmes, avg(nota) AS nota_media,
           median(votos) AS votos_mediana
    FROM (SELECT unnest(string_split(genres, ',')) AS g, nota, votos
          FROM filmes WHERE votos >= 1000 AND genres IS NOT NULL)
    GROUP BY g HAVING count(*) >= 200 ORDER BY nota_media DESC
""").df()
generos.to_csv(SAIDA / "05_generos.csv", index=False)
registrar(tabela_md(generos, 2))

g = generos.sort_values("nota_media")
fig, ax = plt.subplots(figsize=(8, 6))
ax.barh(g.genero, g.nota_media, color=estilo.AZUL, height=0.7)
ax.set_xlim(4.5, 7.5); ax.grid(axis="y", visible=False)
for y, v in enumerate(g.nota_media):
    ax.text(v + 0.02, y, f"{v:.2f}", va="center", color=estilo.TEXTO_SEC, fontsize=9)
ax.set_title("Nota media por genero (filmes com 1.000+ votos)")
ax.set_xlabel("nota media (eixo inicia em 4,5)")
fig.savefig(SAIDA / "g4_generos_nota.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 6. Evolucao por decada: nota e duracao
# ---------------------------------------------------------------------------
registrar("\n## 6. Por decada (filmes com 1.000+ votos)\n")
decadas = con.sql("""
    SELECT (ano // 10) * 10 AS decada, count(*) AS filmes, avg(nota) AS nota_media,
           median(duracao) AS duracao_mediana_min
    FROM filmes WHERE votos >= 1000 AND ano >= 1920 GROUP BY decada ORDER BY decada
""").df()
decadas.to_csv(SAIDA / "06_decadas.csv", index=False)
registrar(tabela_md(decadas, 2))

# ---------------------------------------------------------------------------
# 7. Ranking com media bayesiana (formula historica do Top 250 do IMDb)
#    WR = v/(v+m)*R + m/(v+m)*C, m = 25.000 votos, C = media geral
# ---------------------------------------------------------------------------
registrar("\n## 7. Top 10 por media ponderada (bayesiana)\n")
top = con.sql("""
    WITH c AS (SELECT avg(nota) AS C FROM filmes WHERE votos >= 1000)
    SELECT titulo, ano, nota, votos,
           votos / (votos + 25000) * nota + 25000 / (votos + 25000) * C AS nota_ponderada
    FROM filmes, c ORDER BY nota_ponderada DESC LIMIT 10
""").df()
top.to_csv(SAIDA / "07_top_bayesiano.csv", index=False)
registrar(tabela_md(top, 2))

# ---------------------------------------------------------------------------
# 8. Diretores: junta principals (dezenas de milhoes de linhas) + filmes + nomes
# ---------------------------------------------------------------------------
registrar("\n## 8. Diretores com melhor media (5+ filmes com 10.000+ votos)\n")
t0 = time.perf_counter()
diretores = con.sql("""
    SELECT n.primaryName AS diretor, count(*) AS filmes, avg(f.nota) AS nota_media,
           sum(f.votos) AS votos_totais
    FROM principals p
    JOIN filmes f USING (tconst)
    JOIN names n USING (nconst)
    WHERE p.category = 'director' AND f.votos >= 10000
    GROUP BY n.primaryName HAVING count(*) >= 5
    ORDER BY nota_media DESC LIMIT 15
""").df()
t_join = time.perf_counter() - t0
n_princ = con.sql("SELECT count(*) FROM principals").fetchone()[0]
registrar(f"Junção de {n_princ:,} linhas de principals executada em {t_join:.1f}s\n")
diretores.to_csv(SAIDA / "08_diretores.csv", index=False)
registrar(tabela_md(diretores, 2))

# ---------------------------------------------------------------------------
# 9. Brasil: titulos distribuidos no Brasil (akas) e filmes de producao brasileira
# ---------------------------------------------------------------------------
registrar("\n## 9. Brasil (tabela akas)\n")
br = con.sql("""
    SELECT count(DISTINCT titleId) AS titulos_com_nome_no_brasil,
           count(*) AS linhas_br
    FROM akas WHERE region = 'BR'
""").fetchone()
regioes = con.sql("""
    SELECT region, count(DISTINCT titleId) AS titulos FROM akas
    WHERE region IS NOT NULL GROUP BY region ORDER BY titulos DESC LIMIT 10
""").df()
regioes.to_csv(SAIDA / "09_regioes_akas.csv", index=False)
registrar(f"- Titulos com nome registrado para o Brasil: {br[0]:,}")
registrar("- Regioes com mais titulos traduzidos (a maioria sao episodios de TV com titulo generico,\n"
          "  p.ex. 'Episodio #1.1' - um alerta de veracidade):\n")
registrar(tabela_md(regioes))
top_br = con.sql("""
    SELECT a.title AS titulo_no_brasil, f.titulo AS titulo_principal, f.ano, f.nota, f.votos
    FROM filmes f JOIN akas a ON a.titleId = f.tconst
    WHERE a.region = 'BR' ORDER BY f.votos DESC LIMIT 10
""").df()
top_br.to_csv(SAIDA / "09_mais_votados_titulo_br.csv", index=False)
registrar("\nFilmes mais votados, com o titulo usado no Brasil:\n")
registrar(tabela_md(top_br))
registrar("\nObs.: o dataset nao informa pais de producao; 'filmes brasileiros' exigiria outra fonte "
          "(p.ex. ANCINE) ou heuristica sobre a tabela akas.")

(SAIDA / "resumo_filmes.md").write_text("\n".join(log), encoding="utf-8")
print("\nOK - resultados em", SAIDA)
