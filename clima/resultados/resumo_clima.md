# Clima Global - analise inicial

## 1. Perfil dos arquivos

| arquivo                               |    MB |    linhas | inicio     | fim        | % temp. nula   | entidades   | tempo leitura   |
|:--------------------------------------|------:|----------:|:-----------|:-----------|:---------------|:------------|:----------------|
| GlobalTemperatures.csv                |   0.2 |     3,192 | 1750-01-01 | 2015-12-01 | 0.4%           | -           | 0.03s           |
| GlobalLandTemperaturesByCountry.csv   |  22.7 |   577,462 | 1743-11-01 | 2013-09-01 | 5.7%           | 243         | 0.14s           |
| GlobalLandTemperaturesByState.csv     |  30.8 |   645,675 | 1743-11-01 | 2013-09-01 | 4.0%           | 241         | 0.13s           |
| GlobalLandTemperaturesByMajorCity.csv |  14.1 |   239,177 | 1743-11-01 | 2013-09-01 | 4.6%           | 100         | 0.08s           |
| GlobalLandTemperaturesByCity.csv      | 532.8 | 8,599,212 | 1743-11-01 | 2013-09-01 | 4.2%           | 3,490       | 0.81s           |

## 2. CSV x Parquet (arquivo por cidade)

- Tamanho: CSV 533 MB -> Parquet 43 MB (12.4x menor); conversao em 2.1s
- Mesma consulta agregada: CSV 0.71s x Parquet 0.07s (10x mais rapido)

## 3. Temperatura media global anual

|   decada |   anomalia_terra_C |   anomalia_terra_oceano_C |   incerteza_media_C |
|---------:|-------------------:|--------------------------:|--------------------:|
|     1850 |              -0.59 |                     -0.37 |                0.81 |
|     1860 |              -0.55 |                     -0.35 |                0.64 |
|     1870 |              -0.38 |                     -0.24 |                0.5  |
|     1880 |              -0.61 |                     -0.34 |                0.39 |
|     1890 |              -0.51 |                     -0.34 |                0.33 |
|     1900 |              -0.4  |                     -0.37 |                0.28 |
|     1910 |              -0.38 |                     -0.37 |                0.26 |
|     1920 |              -0.17 |                     -0.22 |                0.25 |
|     1930 |              -0.02 |                     -0.11 |                0.24 |
|     1940 |               0.07 |                      0.03 |                0.22 |
|     1950 |              -0.04 |                     -0.02 |                0.16 |
|     1960 |              -0.02 |                     -0.01 |                0.1  |
|     1970 |               0    |                     -0.01 |                0.09 |
|     1980 |               0.25 |                      0.15 |                0.09 |
|     1990 |               0.5  |                      0.3  |                0.08 |
|     2000 |               0.84 |                      0.49 |                0.08 |
|     2010 |               0.96 |                      0.58 |                0.09 |

### Taxa de aquecimento (regressao linear, terra)

| periodo   |   terra_C_por_seculo |   terra_oceano_C_por_seculo |
|:----------|---------------------:|----------------------------:|
| 1850-2015 |                 0.85 |                        0.54 |
| 1900-2015 |                 1.07 |                        0.79 |
| 1950-2015 |                 1.85 |                        1.09 |
| 1980-2015 |                 2.65 |                        1.59 |

## 4. Cobertura da rede de medicao (arquivo por cidade)

- 1750: 675 cidades, 41 paises
- 1800: 1,238 cidades, 55 paises
- 1850: 2,894 cidades, 131 paises
- 1900: 3,490 cidades, 159 paises
- 1950: 3,490 cidades, 159 paises
- 2000: 3,490 cidades, 159 paises
- 2013: 3,490 cidades, 159 paises

## 5. Paises que mais aqueceram (1990-2012 vs 1901-1930)

Paises com serie suficiente: 228; mediana da variacao: 0.95 °C; paises que esfriaram: 0

| pais                   |   media_1901_1930 |   media_1990_2012 |   variacao_C |
|:-----------------------|------------------:|------------------:|-------------:|
| Mongolia               |             -1.09 |              0.56 |         1.65 |
| Turkmenistan           |             14.52 |             16.05 |         1.53 |
| Russia                 |             -5.74 |             -4.24 |         1.5  |
| Kazakhstan             |              5.01 |              6.48 |         1.47 |
| Uzbekistan             |             12.03 |             13.49 |         1.46 |
| Canada                 |             -5.31 |             -3.9  |         1.41 |
| Svalbard And Jan Mayen |             -7.61 |             -6.2  |         1.41 |
| Iran                   |             17.36 |             18.74 |         1.39 |
| Belarus                |              5.71 |              7.08 |         1.37 |
| Kyrgyzstan             |              2.95 |              4.32 |         1.36 |

Brasil: +0.97 °C (posicao 111 de 228)

## 6. Brasil por estado (1990-2012 vs 1901-1930)

| estado              |   media_1901_1930 |   media_1990_2012 |   variacao_C |
|:--------------------|------------------:|------------------:|-------------:|
| Pernambuco          |             25.11 |             26.19 |         1.08 |
| Alagoas             |             24.51 |             25.57 |         1.06 |
| Rio Grande Do Norte |             26.67 |             27.72 |         1.06 |
| Tocantins           |             25.65 |             26.7  |         1.05 |
| Bahia               |             23.86 |             24.91 |         1.05 |
| Sergipe             |             25.2  |             26.25 |         1.05 |
| Minas Gerais        |             21.7  |             22.73 |         1.03 |
| Distrito Federal    |             21.61 |             22.63 |         1.02 |
| Rio De Janeiro      |             21.75 |             22.77 |         1.02 |
| Roraima             |             25.53 |             26.54 |         1.01 |
| Santa Catarina      |             18.18 |             19.13 |         0.95 |
| Rio Grande Do Sul   |             18.59 |             19.51 |         0.91 |
| Amazonas            |             25.91 |             26.82 |         0.91 |
| Mato Grosso         |             25.41 |             26.29 |         0.88 |
| Mato Grosso Do Sul  |             23.49 |             24.35 |         0.85 |
| Acre                |             25.55 |             26.36 |         0.81 |

Cidades brasileiras no arquivo por cidade: 220 (desde 1824-01-01)