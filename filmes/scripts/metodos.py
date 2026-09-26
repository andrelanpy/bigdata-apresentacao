"""Metodos estatisticos das atividades da disciplina, adaptados para uso em script.

Origem (pasta bigdata/, fora deste repositorio):
- descritivas()        -> Atividade_03_Estatistica_.ipynb e Medidaeficiencia.ipynb
- tabela_frequencia()  -> Atividade_03_Estatistica_.ipynb (frequencia absoluta, relativa,
                          percentual e acumulada por classes)
- analisar()           -> Medidaeficiencia.ipynb / Aula_06_Dispersao,_Covariancia_e_Coef_Correlacao.ipynb
                          (covariancia amostral, r de Pearson, r2 e conferencia r = cov/(sx*sy))
- ajuste_normal()      -> Exemplos_de_Distribuicoes.ipynb / ativ.ipynb (histograma comparado a
                          curva teorica)

Diferencas em relacao aos notebooks: nada e exibido com plt.show(); as funcoes devolvem
tabelas e numeros para serem gravados em resultados/. O desvio-padrao e a variancia sao
calculados com numpy (ddof=1), equivalente a statistics.stdev/variance, mas vetorizado -
statistics e lento para centenas de milhares de valores.
"""
import numpy as np
import pandas as pd
from scipy import stats


def descritivas(v, nome):
    """Media, mediana, moda, amplitude, quartis, IQR, desvio-padrao, variancia e CV."""
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    q1, q2, q3 = np.percentile(v, [25, 50, 75])
    dp = v.std(ddof=1)
    return {
        "Variavel": nome,
        "n": len(v),
        "Media": v.mean(),
        "Mediana": q2,
        "Moda": stats.mode(v, keepdims=False).mode,
        "Minimo": v.min(),
        "Maximo": v.max(),
        "Amplitude": v.max() - v.min(),
        "Q1": q1,
        "Q3": q3,
        "IQR": q3 - q1,
        "Desvio Padrao": dp,
        "Variancia": v.var(ddof=1),
        "CV (%)": 100 * dp / v.mean(),
    }


def tabela_frequencia(v, limites):
    """Frequencia absoluta, relativa, percentual e acumulada por classes [a, b)."""
    classes = pd.cut(np.asarray(v, dtype=float), bins=limites, right=False)
    freq_abs = classes.value_counts().sort_index()
    freq_rel = freq_abs / freq_abs.sum()
    return pd.DataFrame({
        "Classe": freq_abs.index.astype(str),
        "Freq. Absoluta": freq_abs.values,
        "Freq. Relativa": freq_rel.values.round(4),
        "Freq. Percentual (%)": (freq_rel.values * 100).round(1),
        "Freq. Acumulada": freq_abs.cumsum().values,
    })


def analisar(x, y, nome_x, nome_y):
    """Covariancia amostral, r de Pearson e r2, com a conferencia manual da formula."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = ~(np.isnan(x) | np.isnan(y))
    x, y = x[ok], y[ok]
    cov = np.cov(x, y)[0, 1]
    r = np.corrcoef(x, y)[0, 1]
    r_conferencia = cov / (x.std(ddof=1) * y.std(ddof=1))
    m, b = np.polyfit(x, y, 1)
    return {
        "X": nome_x, "Y": nome_y, "n": len(x),
        "Covariancia": cov, "r": r, "r2": r ** 2,
        "r conferencia cov/(sx*sy)": r_conferencia,
        "inclinacao": m, "intercepto": b,
    }


DISTRIBUICOES = {"Normal": stats.norm, "Exponencial": stats.expon,
                 "Gama": stats.gamma, "Weibull": stats.weibull_min}


def comparar_distribuicoes(v, piso):
    """Ajusta as distribuicoes do notebook de exemplos e mede a aderencia (KS).

    `piso` e o menor valor possivel dos dados: as distribuicoes deslocadas (exponencial,
    gama, Weibull) comecam nele. A Normal e ajustada livremente. D de Kolmogorov-Smirnov:
    maior distancia entre a distribuicao acumulada dos dados e a teorica (menor = melhor).
    """
    v = np.asarray(v, dtype=float)
    v = v[~np.isnan(v)]
    saida = []
    for nome, dist in DISTRIBUICOES.items():
        params = dist.fit(v) if nome == "Normal" else dist.fit(v, floc=piso)
        saida.append({"distribuicao": nome, "params": params,
                      "KS D": stats.kstest(v, dist.cdf, args=params).statistic})
    return sorted(saida, key=lambda d: d["KS D"]), stats.skew(v)
