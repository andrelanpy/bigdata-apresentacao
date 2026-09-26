"""Analise inicial - Estudo do Clima Global (Berkeley Earth, via Kaggle).

Processa os CSVs brutos com DuckDB (motor colunar, execucao vetorizada e
paralela, capaz de trabalhar com dados maiores que a memoria) e gera tabelas
em resultados/ e graficos PNG.

Uso: python clima/scripts/analise_inicial_clima.py   (a partir de trabalho_apresentacao/)
"""
import os
import sys
import time
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
import estilo  # noqa: E402

estilo.aplicar()

DADOS = Path(os.environ.get(
    "CLIMA_DIR",
    Path.home() / ".cache/kagglehub/datasets/berkeleyearth/"
    "climate-change-earth-surface-temperature-data/versions/2",
))
SAIDA = RAIZ / "clima" / "resultados"
PARQUET = RAIZ / "dados" / "clima"
SAIDA.mkdir(parents=True, exist_ok=True)
PARQUET.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
log = []


def registrar(texto=""):
    print(texto)
    log.append(texto)


def csv(nome):
    # quote explicito: a deteccao automatica falha em nomes como "Bonaire, Saint Eustatius And Saba"
    return f"""read_csv_auto('{(DADOS / nome).as_posix()}', header=true, quote='"', escape='"')"""


def tabela_md(df, casas=3):
    df = df.copy()
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].round(casas)
    return df.to_markdown(index=False)


# ---------------------------------------------------------------------------
# 1. Perfil dos arquivos (Volume / Veracidade)
# ---------------------------------------------------------------------------
registrar("# Clima Global - analise inicial\n")
registrar("## 1. Perfil dos arquivos\n")
arquivos = {
    "GlobalTemperatures.csv": ("LandAverageTemperature", None),
    "GlobalLandTemperaturesByCountry.csv": ("AverageTemperature", "Country"),
    "GlobalLandTemperaturesByState.csv": ("AverageTemperature", "State || '/' || Country"),
    "GlobalLandTemperaturesByMajorCity.csv": ("AverageTemperature", "City || '/' || Country"),
    "GlobalLandTemperaturesByCity.csv": ("AverageTemperature", "City || '/' || Country"),
}
linhas = []
for nome, (col, entidade) in arquivos.items():
    t0 = time.perf_counter()
    ent = f"count(DISTINCT {entidade})" if entidade else "NULL"
    r = con.sql(f"""
        SELECT count(*) AS linhas,
               min(dt) AS inicio, max(dt) AS fim,
               100.0 * count(*) FILTER (WHERE {col} IS NULL) / count(*) AS pct_nulos,
               {ent} AS entidades
        FROM {csv(nome)}
    """).fetchone()
    dt = time.perf_counter() - t0
    tam = (DADOS / nome).stat().st_size / 1e6
    linhas.append((nome, f"{tam:,.1f}", f"{r[0]:,}", str(r[1])[:10], str(r[2])[:10],
                   f"{r[3]:.1f}%", "-" if r[4] is None else f"{r[4]:,}", f"{dt:.2f}s"))
import pandas as pd  # noqa: E402

perfil = pd.DataFrame(linhas, columns=["arquivo", "MB", "linhas", "inicio", "fim",
                                       "% temp. nula", "entidades", "tempo leitura"])
registrar(perfil.to_markdown(index=False))
perfil.to_csv(SAIDA / "01_perfil_arquivos.csv", index=False)

# ---------------------------------------------------------------------------
# 2. CSV x Parquet (argumento de engenharia de Big Data)
# ---------------------------------------------------------------------------
registrar("\n## 2. CSV x Parquet (arquivo por cidade)\n")
pq = (PARQUET / "by_city.parquet").as_posix()
t0 = time.perf_counter()
con.sql(f"""COPY (SELECT * FROM {csv('GlobalLandTemperaturesByCity.csv')})
           TO '{pq}' (FORMAT parquet, COMPRESSION zstd)""")
t_conv = time.perf_counter() - t0
consulta = """SELECT Country, avg(AverageTemperature) FROM {src}
              WHERE year(dt) >= 2000 GROUP BY Country"""
t0 = time.perf_counter(); con.sql(consulta.format(src=csv("GlobalLandTemperaturesByCity.csv"))).fetchall()
t_csv = time.perf_counter() - t0
t0 = time.perf_counter(); con.sql(consulta.format(src=f"'{pq}'")).fetchall()
t_pq = time.perf_counter() - t0
tam_csv = (DADOS / "GlobalLandTemperaturesByCity.csv").stat().st_size / 1e6
tam_pq = Path(pq).stat().st_size / 1e6
registrar(f"- Tamanho: CSV {tam_csv:,.0f} MB -> Parquet {tam_pq:,.0f} MB "
          f"({tam_csv / tam_pq:.1f}x menor); conversao em {t_conv:.1f}s")
registrar(f"- Mesma consulta agregada: CSV {t_csv:.2f}s x Parquet {t_pq:.2f}s "
          f"({t_csv / t_pq:.0f}x mais rapido)")
con.sql(f"CREATE VIEW cidade AS SELECT * FROM '{pq}'")
con.sql(f"CREATE VIEW pais AS SELECT * FROM {csv('GlobalLandTemperaturesByCountry.csv')}")
con.sql(f"CREATE VIEW estado AS SELECT * FROM {csv('GlobalLandTemperaturesByState.csv')}")
con.sql(f"CREATE VIEW temp_global AS SELECT * FROM {csv('GlobalTemperatures.csv')}")

# ---------------------------------------------------------------------------
# 3. Serie global anual e anomalia (base 1951-1980, convencao NASA/NOAA)
# ---------------------------------------------------------------------------
registrar("\n## 3. Temperatura media global anual\n")
anual = con.sql("""
    WITH a AS (
        SELECT year(dt) AS ano,
               avg(LandAverageTemperature) AS terra,
               avg(LandAverageTemperatureUncertainty) AS incerteza,
               avg(LandAndOceanAverageTemperature) AS terra_oceano,
               count(LandAverageTemperature) AS meses
        FROM temp_global GROUP BY ano
    ), base AS (
        SELECT avg(terra) AS b_terra, avg(terra_oceano) AS b_to FROM a
        WHERE ano BETWEEN 1951 AND 1980
    )
    SELECT ano, terra, terra - b_terra AS anomalia_terra,
           terra_oceano - b_to AS anomalia_terra_oceano, incerteza
    FROM a, base WHERE meses = 12 ORDER BY ano
""").df()
anual["media_movel_10a"] = anual["anomalia_terra"].rolling(10, center=True).mean()
anual.to_csv(SAIDA / "02_global_anual.csv", index=False)

decadas = con.sql("""
    SELECT (ano // 10) * 10 AS decada, avg(anomalia_terra) AS anomalia_terra_C,
           avg(anomalia_terra_oceano) AS anomalia_terra_oceano_C,
           avg(incerteza) AS incerteza_media_C
    FROM anual GROUP BY decada ORDER BY decada
""").df()
decadas.to_csv(SAIDA / "03_global_decadas.csv", index=False)
registrar(tabela_md(decadas[decadas.decada >= 1850], 2))

registrar("\n### Taxa de aquecimento (regressao linear, terra)\n")
taxas = []
for ini in (1850, 1900, 1950, 1980):
    s = con.sql(f"""SELECT regr_slope(terra, ano) * 100, regr_slope(terra_oceano, ano) * 100
                    FROM (SELECT ano, anomalia_terra AS terra, anomalia_terra_oceano AS terra_oceano
                          FROM anual WHERE ano >= {ini})""").fetchone()
    taxas.append((f"{ini}-2015", s[0], s[1]))
taxas = pd.DataFrame(taxas, columns=["periodo", "terra_C_por_seculo", "terra_oceano_C_por_seculo"])
taxas.to_csv(SAIDA / "04_taxa_aquecimento.csv", index=False)
registrar(tabela_md(taxas, 2))

# Grafico 1 - anomalia global
fig, ax = plt.subplots(figsize=(10, 4.6))
a = anual[anual.ano >= 1850]
ax.bar(a.ano, a.anomalia_terra, width=0.8,
       color=[estilo.VERMELHO if v > 0 else estilo.AZUL for v in a.anomalia_terra], alpha=0.45)
ax.plot(a.ano, a.media_movel_10a, color=estilo.TEXTO, lw=2, label="Media movel 10 anos")
ax.axhline(0, color=estilo.TEXTO_SEC, lw=0.8)
ax.set_title("Anomalia da temperatura media da superficie terrestre (base 1951-1980)")
ax.set_ylabel("°C em relacao a 1951-1980")
ax.legend(loc="upper left")
fig.text(0.01, -0.03, "Fonte: Berkeley Earth (Kaggle). Somente anos com 12 meses medidos.",
         color=estilo.TEXTO_SEC, fontsize=8)
fig.savefig(SAIDA / "g1_anomalia_global.png"); plt.close(fig)

# Grafico 2 - incerteza ao longo do tempo (Veracidade)
fig, ax = plt.subplots(figsize=(10, 3.6))
ax.plot(anual.ano, anual.incerteza, color=estilo.AZUL)
ax.set_title("Incerteza da medicao por ano (terra) - a qualidade do dado muda com o tempo")
ax.set_ylabel("± °C (IC 95%)")
fig.savefig(SAIDA / "g2_incerteza.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Cobertura: quantas cidades medem cada ano (Volume / Variedade)
# ---------------------------------------------------------------------------
registrar("\n## 4. Cobertura da rede de medicao (arquivo por cidade)\n")
cobertura = con.sql("""
    SELECT year(dt) AS ano, count(DISTINCT City || Country) AS cidades_com_dado,
           count(DISTINCT Country) AS paises_com_dado
    FROM cidade WHERE AverageTemperature IS NOT NULL GROUP BY ano ORDER BY ano
""").df()
cobertura.to_csv(SAIDA / "05_cobertura_cidades.csv", index=False)
for ano in (1750, 1800, 1850, 1900, 1950, 2000, 2013):
    r = cobertura[cobertura.ano == ano].iloc[0]
    registrar(f"- {ano}: {int(r.cidades_com_dado):,} cidades, {int(r.paises_com_dado)} paises")

fig, ax = plt.subplots(figsize=(10, 3.6))
ax.plot(cobertura.ano, cobertura.cidades_com_dado, color=estilo.AZUL)
ax.set_title("Cidades com ao menos uma medicao por ano")
ax.set_ylabel("cidades")
fig.savefig(SAIDA / "g3_cobertura.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 5. Aquecimento por pais: media 1990-2012 x 1901-1930 (anos completos)
#    Remove agregados continentais e duplicatas do tipo "X (Europe)".
# ---------------------------------------------------------------------------
registrar("\n## 5. Paises que mais aqueceram (1990-2012 vs 1901-1930)\n")
paises = con.sql("""
    WITH anos AS (
        SELECT Country, year(dt) AS ano, avg(AverageTemperature) AS t,
               count(AverageTemperature) AS m
        FROM pais
        WHERE Country NOT IN ('Africa','Asia','Europe','North America','South America',
                              'Oceania','Antarctica')
          AND Country NOT LIKE '%(%'
        GROUP BY ALL
    )
    SELECT Country AS pais,
           avg(t) FILTER (WHERE ano BETWEEN 1901 AND 1930) AS media_1901_1930,
           avg(t) FILTER (WHERE ano BETWEEN 1990 AND 2012) AS media_1990_2012,
           media_1990_2012 - media_1901_1930 AS variacao_C,
           count(*) FILTER (WHERE ano BETWEEN 1901 AND 1930) AS anos_base
    FROM anos WHERE m = 12 GROUP BY pais
    HAVING anos_base >= 25 AND count(*) FILTER (WHERE ano BETWEEN 1990 AND 2012) >= 20
    ORDER BY variacao_C DESC
""").df()
paises.to_csv(SAIDA / "06_aquecimento_por_pais.csv", index=False)
registrar(f"Paises com serie suficiente: {len(paises)}; "
          f"mediana da variacao: {paises.variacao_C.median():.2f} °C; "
          f"paises que esfriaram: {(paises.variacao_C < 0).sum()}\n")
registrar(tabela_md(paises.head(10)[["pais", "media_1901_1930", "media_1990_2012", "variacao_C"]], 2))
br = paises[paises.pais == "Brazil"]
if len(br):
    pos = paises.index.get_loc(br.index[0]) + 1
    registrar(f"\nBrasil: {br.variacao_C.iloc[0]:+.2f} °C (posicao {pos} de {len(paises)})")

top = paises.head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 5.4))
ax.barh(top.pais, top.variacao_C, color=estilo.VERMELHO, height=0.7)
ax.grid(axis="y", visible=False)
for y, v in enumerate(top.variacao_C):
    ax.text(v + 0.03, y, f"+{v:.2f}", va="center", color=estilo.TEXTO_SEC, fontsize=9)
ax.set_title("15 paises com maior aquecimento\n(media 1990-2012 menos media 1901-1930)")
ax.set_xlabel("°C")
fig.savefig(SAIDA / "g4_top_paises.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 6. Brasil: estados e grandes cidades
# ---------------------------------------------------------------------------
registrar("\n## 6. Brasil por estado (1990-2012 vs 1901-1930)\n")
estados = con.sql("""
    WITH anos AS (
        SELECT State, year(dt) AS ano, avg(AverageTemperature) AS t, count(AverageTemperature) AS m
        FROM estado WHERE Country = 'Brazil' GROUP BY ALL
    )
    SELECT State AS estado,
           avg(t) FILTER (WHERE ano BETWEEN 1901 AND 1930) AS media_1901_1930,
           avg(t) FILTER (WHERE ano BETWEEN 1990 AND 2012) AS media_1990_2012,
           media_1990_2012 - media_1901_1930 AS variacao_C
    FROM anos WHERE m = 12 GROUP BY estado ORDER BY variacao_C DESC
""").df()
estados.to_csv(SAIDA / "07_brasil_estados.csv", index=False)
registrar(tabela_md(estados, 2))

cidades_br = con.sql("""
    SELECT count(DISTINCT City) AS cidades, min(dt) AS inicio FROM cidade WHERE Country = 'Brazil'
""").fetchone()
registrar(f"\nCidades brasileiras no arquivo por cidade: {cidades_br[0]} (desde {str(cidades_br[1])[:10]})")

(SAIDA / "resumo_clima.md").write_text("\n".join(log), encoding="utf-8")
print("\nOK - resultados em", SAIDA)
