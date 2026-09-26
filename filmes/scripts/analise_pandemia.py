"""Filmes e pandemia de COVID-19 - o que mudou no IMDb entre 2015 e 2025.

Pre-requisito: rodar antes analise_inicial_filmes.py, que gera o Parquet em dados/imdb/.

Periodos comparados:
    Pre-pandemia  2015-2019
    Pandemia      2020-2021  (fechamento de cinemas e paralisacao de filmagens)
    Pos-pandemia  2022-2025

As agregacoes pesadas (12,8 mi de titulos) rodam em DuckDB. Os metodos estatisticos
das atividades da disciplina (filmes/scripts/metodos.py) sao aplicados sobre a base
de longas-metragens do periodo (~118 mil filmes avaliados).

Uso: python filmes/scripts/analise_pandemia.py   (a partir de trabalho_apresentacao/)
"""
import sys
from pathlib import Path

import duckdb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))
import estilo  # noqa: E402
from metodos import (DISTRIBUICOES, analisar, comparar_distribuicoes, descritivas,  # noqa: E402
                     tabela_frequencia)

estilo.aplicar()

PARQUET = RAIZ / "dados" / "imdb"
SAIDA = RAIZ / "filmes" / "resultados" / "pandemia"
SAIDA.mkdir(parents=True, exist_ok=True)

PERIODOS = {"Pre-pandemia": (2015, 2019), "Pandemia": (2020, 2021), "Pos-pandemia": (2022, 2025)}
BASE_ANOS = (2017, 2019)  # linha de base: media dos 3 anos anteriores a pandemia
COR_PERIODO = {"Pre-pandemia": estilo.AZUL, "Pandemia": estilo.LARANJA, "Pos-pandemia": estilo.VERDE_AGUA}

con = duckdb.connect()
for tabela, view in (("title_basics", "basics"), ("title_ratings", "ratings")):
    arq = PARQUET / f"{tabela}.parquet"
    if not arq.exists():
        sys.exit(f"Falta {arq}. Rode antes filmes/scripts/analise_inicial_filmes.py")
    con.sql(f"CREATE VIEW {view} AS SELECT * FROM '{arq.as_posix()}'")

con.sql("""
    CREATE MACRO periodo(ano) AS CASE
        WHEN ano BETWEEN 2015 AND 2019 THEN 'Pre-pandemia'
        WHEN ano BETWEEN 2020 AND 2021 THEN 'Pandemia'
        WHEN ano BETWEEN 2022 AND 2025 THEN 'Pos-pandemia' END
""")
# Longas-metragens nao adultos 2010-2025, com avaliacao quando existir
con.sql("""
    CREATE TABLE filmes AS
    SELECT b.tconst, b.startYear AS ano, periodo(b.startYear) AS periodo,
           b.runtimeMinutes AS duracao, b.genres,
           r.averageRating AS nota, r.numVotes AS votos
    FROM basics b LEFT JOIN ratings r USING (tconst)
    WHERE b.titleType = 'movie' AND b.isAdult = 0 AND b.startYear BETWEEN 2010 AND 2025
""")

log = []


def registrar(texto=""):
    print(texto, flush=True)
    log.append(texto)


def md(df, casas=2):
    df = df.copy()
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].round(casas)
    return df.to_markdown(index=False)


def sombrear_pandemia(ax):
    ax.axvspan(2019.5, 2021.5, color=estilo.LARANJA, alpha=0.10, lw=0)
    ax.text(2020.5, 0.98, "pandemia", transform=ax.get_xaxis_transform(), ha="center",
            va="top", color=estilo.TEXTO_SEC, fontsize=9)


registrar("# Filmes e pandemia - IMDb 2015-2025\n")
registrar("Periodos: " + ", ".join(f"{k} {a}-{b}" for k, (a, b) in PERIODOS.items())
          + f". Linha de base: media {BASE_ANOS[0]}-{BASE_ANOS[1]}.\n")

# ---------------------------------------------------------------------------
# 1. Quantos filmes deixaram de ser lancados?
#    Duas estimativas do "esperado sem pandemia":
#    (a) media 2017-2019  (b) tendencia linear 2015-2019, com r e r2 (Aula 06)
# ---------------------------------------------------------------------------
registrar("## 1. Producao de longas-metragens\n")
por_ano = con.sql("""
    SELECT ano, count(*) AS lancados, count(nota) AS avaliados
    FROM filmes GROUP BY ano ORDER BY ano
""").df()
base = por_ano[por_ano.ano.between(*BASE_ANOS)].lancados.mean()
treino = por_ano[por_ano.ano.between(2015, 2019)]
tend = analisar(treino.ano, treino.lancados, "ano", "filmes lancados")
por_ano["esperado_media_2017_2019"] = base
por_ano["esperado_tendencia"] = tend["inclinacao"] * por_ano.ano + tend["intercepto"]
por_ano.to_csv(SAIDA / "01_producao_por_ano.csv", index=False)

registrar("(longas nao adultos; a secao 2 inclui todos os titulos, por isso os totais diferem um pouco)\n")
registrar(f"- Media 2017-2019: {base:,.0f} filmes/ano")
registrar(f"- Tendencia 2015-2019: +{tend['inclinacao']:,.0f} filmes/ano "
          f"(r = {tend['r']:.3f}, r2 = {tend['r2']:.3f})\n")
linhas = []
for ano in (2020, 2021, 2022):
    obs = int(por_ano.loc[por_ano.ano == ano, "lancados"].iloc[0])
    esp_t = tend["inclinacao"] * ano + tend["intercepto"]
    linhas.append({"ano": ano, "observado": obs,
                   "vs media 2017-19 (%)": 100 * (obs / base - 1),
                   "esperado pela tendencia": esp_t,
                   "vs tendencia (%)": 100 * (obs / esp_t - 1)})
deficit = pd.DataFrame(linhas)
registrar(md(deficit, 1))
perdidos_media = sum(base - r.observado for r in deficit.itertuples() if r.ano <= 2021)
perdidos_tend = sum(r._4 - r.observado for r in deficit.itertuples() if r.ano <= 2021)
registrar(f"\nFilmes 'a menos' em 2020-2021: entre {perdidos_media:,.0f} (contra a media) "
          f"e {perdidos_tend:,.0f} (contra a tendencia).")

fig, ax = plt.subplots(figsize=(10, 4.2))
sombrear_pandemia(ax)
ax.plot(por_ano.ano, por_ano.lancados, color=estilo.AZUL, marker="o", ms=5,
        mec=estilo.SUPERFICIE, mew=1.5, label="Lancados (observado)")
fut = por_ano[por_ano.ano >= 2015]
ax.plot(fut.ano, fut.esperado_tendencia, color=estilo.TEXTO_SEC, ls="--", lw=1.5,
        label=f"Tendencia 2015-2019 (r2 = {tend['r2']:.2f})")
ax.axhline(base, color=estilo.TEXTO_SEC, ls=":", lw=1.5, label="Media 2017-2019")
v20 = por_ano.loc[por_ano.ano == 2020, "lancados"].iloc[0]
ax.annotate(f"2020: {v20:,.0f}\n({100 * (v20 / base - 1):+.0f}% vs media)".replace(",", "."),
            (2020, v20), xytext=(-95, -38), textcoords="offset points",
            color=estilo.TEXTO, fontsize=9, arrowprops=dict(arrowstyle="-", color=estilo.TEXTO_SEC))
ax.set_title("Longas-metragens lancados por ano (IMDb)")
ax.set_ylabel("filmes")
ax.set_xticks(range(2010, 2026, 1))
ax.tick_params(axis="x", labelsize=8)
ax.legend(loc="upper left")
fig.savefig(SAIDA / "g1_producao_tendencia.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 2. Quais formatos cairam e quais cresceram? (todos os tipos de titulo)
# ---------------------------------------------------------------------------
registrar("\n## 2. Formatos: variacao contra a media 2017-2019\n")
formatos = con.sql(f"""
    WITH c AS (
        SELECT titleType AS formato, startYear AS ano, count(*) AS n
        FROM basics WHERE startYear BETWEEN 2017 AND 2022 AND titleType <> 'tvPilot'
        GROUP BY ALL
    )
    SELECT formato,
           avg(n) FILTER (WHERE ano BETWEEN {BASE_ANOS[0]} AND {BASE_ANOS[1]}) AS media_2017_2019,
           any_value(n) FILTER (WHERE ano = 2020) AS n_2020,
           any_value(n) FILTER (WHERE ano = 2021) AS n_2021,
           100 * (n_2020 / media_2017_2019 - 1) AS var_2020_pct,
           100 * (n_2021 / media_2017_2019 - 1) AS var_2021_pct
    FROM c GROUP BY formato ORDER BY var_2020_pct
""").df()
nomes_fmt = {"movie": "Longa-metragem", "tvMovie": "Filme para TV", "short": "Curta",
             "video": "Video", "videoGame": "Jogo", "tvShort": "Curta para TV",
             "tvEpisode": "Episodio de TV", "tvSeries": "Serie de TV",
             "tvMiniSeries": "Minisserie", "tvSpecial": "Especial de TV"}
formatos["formato"] = formatos.formato.map(nomes_fmt).fillna(formatos.formato)
formatos.to_csv(SAIDA / "02_formatos.csv", index=False)
registrar(md(formatos, 1))

f = formatos.sort_values("var_2020_pct")
fig, ax = plt.subplots(figsize=(8, 4.6))
cores = [estilo.VERMELHO if v < 0 else estilo.AZUL for v in f.var_2020_pct]
ax.barh(f.formato, f.var_2020_pct, color=cores, height=0.65)
ax.axvline(0, color=estilo.TEXTO_SEC, lw=0.8)
ax.grid(axis="y", visible=False)
for y, v in enumerate(f.var_2020_pct):
    ax.text(v + (1 if v >= 0 else -1), y, f"{v:+.0f}%", va="center",
            ha="left" if v >= 0 else "right", color=estilo.TEXTO_SEC, fontsize=9)
lim = max(abs(f.var_2020_pct.min()), f.var_2020_pct.max()) + 8
ax.set_xlim(-lim, lim)
ax.set_title("Titulos lancados em 2020 contra a media 2017-2019, por formato")
ax.set_xlabel("variacao (%)")
fig.savefig(SAIDA / "g2_formatos_2020.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 3. Mix de generos dos longas: participacao por periodo
# ---------------------------------------------------------------------------
registrar("\n## 3. Generos: participacao no total de marcacoes de genero dos longas (%)\n")
# Um filme pode ter ate 3 generos, e a media de generos por filme caiu na pandemia
# (cadastro mais enxuto nos filmes recentes). Medida como "% dos filmes", quase todo
# genero pareceria encolher. A participacao no total de marcacoes soma 100% em cada
# periodo e compara o mix de forma justa.
por_filme = con.sql("""
    SELECT periodo, avg(len(string_split(genres, ','))) AS generos_por_filme
    FROM filmes WHERE periodo IS NOT NULL AND genres IS NOT NULL GROUP BY periodo
""").df().set_index("periodo").generos_por_filme
registrar("Generos por filme: " + ", ".join(f"{p} {por_filme[p]:.2f}" for p in PERIODOS) + "\n")
generos = con.sql("""
    WITH g AS (
        SELECT periodo, unnest(string_split(genres, ',')) AS genero
        FROM filmes WHERE periodo IS NOT NULL AND genres IS NOT NULL
    )
    SELECT genero, periodo,
           100.0 * count(*) / sum(count(*)) OVER (PARTITION BY periodo) AS pct
    FROM g GROUP BY genero, periodo
""").df().pivot(index="genero", columns="periodo", values="pct").fillna(0)
generos = generos[list(PERIODOS)]
generos["delta_pandemia_pp"] = generos["Pandemia"] - generos["Pre-pandemia"]
generos["delta_pos_pp"] = generos["Pos-pandemia"] - generos["Pre-pandemia"]
generos = generos[generos["Pre-pandemia"] >= 0.7].sort_values("delta_pandemia_pp")
generos.reset_index().to_csv(SAIDA / "03_generos_participacao.csv", index=False)
registrar(md(generos.reset_index(), 2))

g = generos.reset_index()
fig, ax = plt.subplots(figsize=(8, 6.2))
cores = [estilo.VERMELHO if v < 0 else estilo.AZUL for v in g.delta_pandemia_pp]
ax.barh(g.genero, g.delta_pandemia_pp, color=cores, height=0.65)
ax.axvline(0, color=estilo.TEXTO_SEC, lw=0.8)
ax.grid(axis="y", visible=False)
for y, v in enumerate(g.delta_pandemia_pp):
    ax.text(v + (0.05 if v >= 0 else -0.05), y, f"{v:+.1f}", va="center",
            ha="left" if v >= 0 else "right", color=estilo.TEXTO_SEC, fontsize=8.5)
lim = g.delta_pandemia_pp.abs().max() + 0.4
ax.set_xlim(-lim, lim)
ax.set_title("Participacao de cada genero nas marcacoes de genero dos longas:\n"
             "pandemia (2020-21) menos pre-pandemia (2015-19)")
ax.set_xlabel("pontos percentuais")
fig.savefig(SAIDA / "g3_generos_delta.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Estatistica descritiva por periodo (Atividade 03)
# ---------------------------------------------------------------------------
registrar("\n## 4. Estatistica descritiva por periodo (metodo da Atividade 03)\n")
dados = con.sql("""
    SELECT periodo, ano, nota, votos, log10(votos) AS log_votos, duracao
    FROM filmes WHERE periodo IS NOT NULL AND nota IS NOT NULL
""").df()
desc = []
for per in PERIODOS:
    d = dados[dados.periodo == per]
    desc.append({"Periodo": per, **descritivas(d.nota, "nota")})
    desc.append({"Periodo": per, **descritivas(d.duracao.where(d.duracao.between(40, 300)),
                                               "duracao (min)")})
    desc.append({"Periodo": per, **descritivas(d.votos, "votos")})
desc = pd.DataFrame(desc)
desc.to_csv(SAIDA / "04_descritivas_por_periodo.csv", index=False)
cols = ["Periodo", "Variavel", "n", "Media", "Mediana", "Moda", "Q1", "Q3", "IQR",
        "Desvio Padrao", "CV (%)"]
for var in ("nota", "duracao (min)", "votos"):
    registrar(f"\n### {var}\n")
    registrar(md(desc[desc.Variavel == var][cols], 2))
registrar("\nDuracao limitada a 40-300 min para excluir erros de cadastro. "
          "Votos tem CV altissimo: a media nao representa o filme tipico, a mediana sim.")

registrar("\n### Tabela de frequencias das notas (classes de 1 ponto)\n")
limites = list(range(1, 10)) + [10.001]  # ultima classe [9, 10] fechada
freqs = []
for per in PERIODOS:
    t = tabela_frequencia(dados[dados.periodo == per].nota, limites)
    t.insert(0, "Periodo", per)
    freqs.append(t)
freqs = pd.concat(freqs)
freqs["Classe"] = freqs.Classe.str.replace("10.001)", "10.0]")
freqs.to_csv(SAIDA / "05_frequencia_notas.csv", index=False)
comp = freqs.pivot(index="Classe", columns="Periodo", values="Freq. Percentual (%)")[list(PERIODOS)]
comp = comp.loc[freqs.Classe.unique()]
registrar("Frequencia percentual (%) por periodo:\n")
registrar(comp.reset_index().to_markdown(index=False))

fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
for ax, (col, titulo, rot) in zip(axs, (("nota", "Nota media IMDb", "nota"),
                                         ("duracao", "Duracao (min, 40-300)", "minutos"))):
    series = [dados[(dados.periodo == p)][col].dropna() for p in PERIODOS]
    if col == "duracao":
        series = [s[s.between(40, 300)] for s in series]
    bp = ax.boxplot(series, tick_labels=list(PERIODOS), showfliers=False, widths=0.5,
                    patch_artist=True, medianprops=dict(color=estilo.TEXTO, lw=2))
    for patch, p in zip(bp["boxes"], PERIODOS):
        patch.set_facecolor(COR_PERIODO[p]); patch.set_alpha(0.35); patch.set_edgecolor(COR_PERIODO[p])
    ax.set_title(titulo); ax.set_ylabel(rot); ax.grid(axis="x", visible=False)
fig.suptitle("Boxplot por periodo (sem outliers)", x=0.01, y=1.03, ha="left", fontweight="bold")
fig.savefig(SAIDA / "g4_boxplots.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 5. Covariancia e correlacao por periodo (Aula 06 / Medida de eficiencia)
# ---------------------------------------------------------------------------
registrar("\n## 5. Covariancia e correlacao de Pearson por periodo (metodo da Aula 06)\n")
pares = [("log_votos", "nota", "log10(votos)", "nota"),
         ("duracao", "nota", "duracao (min)", "nota")]
corrs = []
for per in PERIODOS:
    d = dados[dados.periodo == per]
    for cx, cy, nx, ny in pares:
        dd = d[d.duracao.between(40, 300)] if cx == "duracao" else d
        corrs.append({"Periodo": per, **analisar(dd[cx], dd[cy], nx, ny)})
corrs = pd.DataFrame(corrs)
# Conferencia: o mesmo r calculado dentro do DuckDB (SQL, sem trazer dados para o Python)
sql_r = con.sql("""
    SELECT periodo, corr(nota, log10(votos)) AS r_sql, covar_samp(log10(votos), nota) AS cov_sql
    FROM filmes WHERE periodo IS NOT NULL AND nota IS NOT NULL GROUP BY periodo
""").df().set_index("periodo")
corrs["r (DuckDB)"] = [sql_r.loc[p, "r_sql"] if x == "log10(votos)" else np.nan
                       for p, x in zip(corrs.Periodo, corrs.X)]
corrs.to_csv(SAIDA / "06_correlacoes.csv", index=False)
registrar(md(corrs[["Periodo", "X", "Y", "n", "Covariancia", "r", "r2",
                    "r conferencia cov/(sx*sy)", "r (DuckDB)"]], 4))
registrar("\nA conferencia r = cov/(sx*sy) e o r calculado em SQL pelo DuckDB coincidem com np.corrcoef.")

fig, axs = plt.subplots(1, 3, figsize=(13, 4), sharex=True, sharey=True)
for ax, per in zip(axs, PERIODOS):
    d = dados[dados.periodo == per]
    ax.hexbin(d.log_votos, d.nota, gridsize=40, cmap="Blues", mincnt=1, bins="log", linewidths=0)
    c = corrs[(corrs.Periodo == per) & (corrs.X == "log10(votos)")].iloc[0]
    xs = np.linspace(d.log_votos.min(), d.log_votos.max(), 50)
    ax.plot(xs, c.inclinacao * xs + c.intercepto, color=estilo.LARANJA, lw=2)
    ax.set_title(f"{per}\nr = {c.r:.3f}   r2 = {c.r2:.3f}", fontsize=11)
    ax.set_xlabel("log10(votos)"); ax.grid(False)
axs[0].set_ylabel("nota")
fig.suptitle("Dispersao nota x popularidade (densidade de filmes) e reta de tendencia",
             x=0.01, y=1.06, ha="left", fontweight="bold")
fig.savefig(SAIDA / "g5_dispersao_periodos.png"); plt.close(fig)

# ---------------------------------------------------------------------------
# 6. Distribuicoes (Exemplos de Distribuicoes): qual curva teorica descreve os votos?
#    Hipotese inicial: votos ~ lognormal, ou seja, log10(votos) ~ Normal. Comparamos a
#    Normal com Exponencial, Gama e Weibull (todas do notebook da aula), deslocadas para
#    comecar no piso do IMDb: so ha nota publicada a partir de 5 votos.
# ---------------------------------------------------------------------------
registrar("\n## 6. Distribuicao dos votos (metodo de Exemplos de Distribuicoes)\n")
PISO = np.log10(4.99)  # log10 de 5 votos, com folga numerica para o ajuste
piso_real = con.sql("SELECT min(numVotes) FROM ratings").fetchone()[0]
registrar(f"Menor numero de votos publicado no IMDb: {piso_real} (os dados sao truncados ai).\n")
ajustes = []
fig, axs = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
for ax, per in zip(axs, PERIODOS):
    v = dados[dados.periodo == per].log_votos.dropna().to_numpy()
    ranking, assim = comparar_distribuicoes(v, PISO)
    for d in ranking:
        ajustes.append({"Periodo": per, "distribuicao": d["distribuicao"], "KS D": d["KS D"],
                        "parametros": ", ".join(f"{p:.3f}" for p in d["params"]),
                        "assimetria dos dados": assim})
    ax.hist(v, bins=40, density=True, color=COR_PERIODO[per], alpha=0.45, edgecolor=estilo.SUPERFICIE)
    xs = np.linspace(PISO + 1e-3, v.max(), 300)
    por_nome = {d["distribuicao"]: d for d in ranking}
    for nome, estilo_linha in (("Normal", ":"), ("Weibull", "-")):
        d = por_nome[nome]
        ax.plot(xs, DISTRIBUICOES[nome].pdf(xs, *d["params"]), color=estilo.TEXTO, lw=2,
                ls=estilo_linha, label=f"{nome} (D = {d['KS D']:.3f})")
    ax.set_title(per, fontsize=11)
    ax.legend(loc="upper right", fontsize=8.5)
    ax.set_xlabel("log10(votos)"); ax.grid(axis="x", visible=False)
axs[0].set_ylabel("densidade")
fig.suptitle("log10(votos): curva Normal (hipotese lognormal) x Weibull a partir do piso de 5 votos",
             x=0.01, y=1.04, ha="left", fontweight="bold")
fig.savefig(SAIDA / "g6_distribuicao_votos.png"); plt.close(fig)
ajustes = pd.DataFrame(ajustes)
ajustes.to_csv(SAIDA / "07_ajuste_distribuicoes.csv", index=False)
registrar(md(ajustes, 4))
registrar("\nD de Kolmogorov-Smirnov: menor e melhor. A lognormal (Normal no log) erra porque os dados "
          "sao truncados em 5 votos e o log ainda e assimetrico a direita; a Weibull deslocada "
          "descreve a distribuicao nos tres periodos, e o formato praticamente nao muda com a pandemia.")

# ---------------------------------------------------------------------------
# 7. A diferenca de notas entre periodos e relevante? (extensao: tamanho do efeito)
#    Com n na casa das dezenas de milhares qualquer diferenca vira "significativa";
#    por isso o que importa e o tamanho do efeito (d de Cohen).
# ---------------------------------------------------------------------------
registrar("\n## 7. Tamanho do efeito na nota (extensao)\n")
efeitos = []
pre = dados[dados.periodo == "Pre-pandemia"].nota
for per in ("Pandemia", "Pos-pandemia"):
    outro = dados[dados.periodo == per].nota
    sp = np.sqrt(((len(pre) - 1) * pre.var() + (len(outro) - 1) * outro.var())
                 / (len(pre) + len(outro) - 2))
    u = stats.mannwhitneyu(outro, pre)
    efeitos.append({"comparacao": f"{per} x Pre-pandemia",
                    "diferenca de medias": outro.mean() - pre.mean(),
                    "d de Cohen": (outro.mean() - pre.mean()) / sp,
                    "p (Mann-Whitney)": u.pvalue})
efeitos = pd.DataFrame(efeitos)
efeitos.to_csv(SAIDA / "08_tamanho_efeito.csv", index=False)
registrar(md(efeitos, 4))
registrar("\n|d| < 0,2 e considerado efeito desprezivel (Cohen, 1988).")

(SAIDA / "resumo_pandemia.md").write_text("\n".join(log), encoding="utf-8")
print("\nOK - resultados em", SAIDA)
