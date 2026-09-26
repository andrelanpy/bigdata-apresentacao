# Filmes e Classificacoes (IMDb) - analise inicial

## 1. Ingestao TSV -> Parquet

| tabela           |   TSV (MB) |   Parquet (MB) |      linhas | conversao       |
|:-----------------|-----------:|---------------:|------------:|:----------------|
| title.basics     |      1,109 |            279 |  12,779,198 | (ja convertido) |
| title.ratings    |         30 |              9 |   1,708,828 | (ja convertido) |
| title.akas       |      3,003 |            320 |  59,292,348 | (ja convertido) |
| title.principals |      4,547 |            567 | 101,716,017 | (ja convertido) |
| name.basics      |        967 |            266 |  15,649,515 | (ja convertido) |

### Nulos por coluna (title.basics)

| coluna         |   % nulo |
|:---------------|---------:|
| tconst         |      0   |
| titleType      |      0   |
| primaryTitle   |      0   |
| originalTitle  |      0   |
| isAdult        |      0   |
| startYear      |     11.6 |
| endYear        |     98.7 |
| runtimeMinutes |     63.7 |
| genres         |      4.2 |

Titulos com ano de lancamento futuro (anunciados): 3,435, ate 2115

## 2. Tipos de titulo

| tipo         |   titulos |   com_avaliacao |   pct_avaliados |
|:-------------|----------:|----------------:|----------------:|
| tvEpisode    |   9879775 |          881873 |             8.9 |
| short        |   1156677 |          184286 |            15.9 |
| movie        |    756513 |          348283 |            46   |
| video        |    331119 |           60020 |            18.1 |
| tvSeries     |    305074 |          113967 |            37.4 |
| tvMovie      |    156058 |           57165 |            36.6 |
| tvMiniSeries |     72841 |           26069 |            35.8 |
| tvSpecial    |     59936 |           14357 |            24   |
| videoGame    |     50146 |           20204 |            40.3 |
| tvShort      |     11058 |            2604 |            23.5 |
| tvPilot      |         1 |               0 |             0   |

Filmes (longa-metragem, nao adulto) com avaliacao: 343,580

## 3. Filmes lancados por ano

- 1920: 2,647 filmes
- 1950: 2,007 filmes
- 1980: 4,185 filmes
- 2000: 5,376 filmes
- 2010: 13,079 filmes
- 2019: 19,565 filmes
- 2020: 16,800 filmes
- 2021: 19,304 filmes

## 4. Notas e votos

- Nota media 6.16, mediana 6.3, desvio-padrao 1.38
- Votos por filme: mediana 66, media 3,772, maximo 3,236,691
- Correlacao entre nota e log(votos): -0.08
- Os 1% filmes mais votados concentram 68.8% de todos os votos; os 10% concentram 95.4%
- 57.4% dos filmes tem menos de 100 votos

## 5. Generos (filmes com 1.000+ votos)

| genero      |   filmes |   nota_media |   votos_mediana |
|:------------|---------:|-------------:|----------------:|
| Documentary |     2570 |         7.19 |          2320   |
| Biography   |     2598 |         6.9  |          4604   |
| Film-Noir   |      463 |         6.85 |          2955   |
| History     |     1932 |         6.83 |          3520   |
| War         |     1229 |         6.77 |          3325   |
| Music       |     1486 |         6.7  |          3388   |
| Animation   |     1622 |         6.64 |          4952.5 |
| Musical     |      852 |         6.58 |          2880   |
| Sport       |      921 |         6.53 |          3735   |
| Drama       |    27334 |         6.49 |          3495   |
| Western     |      665 |         6.39 |          2735   |
| Romance     |     8157 |         6.39 |          3489   |
| Crime       |     8170 |         6.3  |          4326.5 |
| Family      |     2056 |         6.23 |          3204   |
| Comedy      |    16329 |         6.15 |          3595   |
| Adventure   |     5310 |         6.1  |          5571.5 |
| Mystery     |     4165 |         5.98 |          4492   |
| Fantasy     |     2657 |         5.94 |          4660   |
| Action      |     8905 |         5.93 |          4602   |
| Thriller    |     7496 |         5.82 |          3623   |
| Sci-Fi      |     2380 |         5.43 |          4605.5 |
| Horror      |     6632 |         5.25 |          3372   |

## 6. Por decada (filmes com 1.000+ votos)

|   decada |   filmes |   nota_media |   duracao_mediana_min |
|---------:|---------:|-------------:|----------------------:|
|     1920 |      242 |         7.03 |                    89 |
|     1930 |      814 |         6.79 |                    85 |
|     1940 |     1140 |         6.8  |                    94 |
|     1950 |     1623 |         6.65 |                    94 |
|     1960 |     2027 |         6.61 |                   100 |
|     1970 |     2607 |         6.47 |                    98 |
|     1980 |     3372 |         6.27 |                    98 |
|     1990 |     4342 |         6.33 |                   101 |
|     2000 |     8466 |         6.2  |                   100 |
|     2010 |    14510 |         6.07 |                   100 |
|     2020 |     9845 |         6.1  |                   107 |

## 7. Top 10 por media ponderada (bayesiana)

| titulo                                            |   ano |   nota |   votos |   nota_ponderada |
|:--------------------------------------------------|------:|-------:|--------:|-----------------:|
| The Shawshank Redemption                          |  1994 |    9.3 | 3236691 |             9.28 |
| The Godfather                                     |  1972 |    9.2 | 2254950 |             9.17 |
| The Dark Knight                                   |  2008 |    9.1 | 3225158 |             9.08 |
| The Lord of the Rings: The Return of the King     |  2003 |    9   | 2192035 |             8.97 |
| Schindler's List                                  |  1993 |    9   | 1602571 |             8.96 |
| The Godfather Part II                             |  1974 |    9   | 1512442 |             8.95 |
| 12 Angry Men                                      |  1957 |    9   | 1002246 |             8.93 |
| The Lord of the Rings: The Fellowship of the Ring |  2001 |    8.9 | 2235755 |             8.87 |
| Inception                                         |  2010 |    8.8 | 2867229 |             8.78 |
| Fight Club                                        |  1999 |    8.8 | 2659893 |             8.78 |

## 8. Diretores com melhor media (5+ filmes com 10.000+ votos)

Junção de 101,716,017 linhas de principals executada em 1.4s

| diretor           |   filmes |   nota_media |     votos_totais |
|:------------------|---------:|-------------:|-----------------:|
| Ertem Eğilmez     |        9 |         8.56 | 199408           |
| Sergio Leone      |        6 |         8.2  |      2.30179e+06 |
| Charles Chaplin   |        8 |         8.2  |      1.12644e+06 |
| Christopher Nolan |       13 |         8.18 |      1.91382e+07 |
| Vetrimaaran       |        5 |         8.16 | 109113           |
| Haruo Sotozaki    |        6 |         8.12 | 272235           |
| Akira Kurosawa    |       16 |         8.07 |      1.41926e+06 |
| Yasujirō Ozu      |        5 |         8.02 | 136534           |
| Mani Ratnam       |        9 |         7.94 | 204609           |
| Frank Capra       |        8 |         7.94 | 976635           |
| Andrei Tarkovsky  |        7 |         7.93 | 496081           |
| Hayao Miyazaki    |       12 |         7.92 |      3.63802e+06 |
| Quentin Tarantino |       13 |         7.92 |      1.24093e+07 |
| Fritz Lang        |        8 |         7.9  | 501810           |
| Ingmar Bergman    |       17 |         7.88 | 867734           |

## 9. Brasil (tabela akas)

- Titulos com nome registrado para o Brasil: 137,668
- Regioes com mais titulos traduzidos (a maioria sao episodios de TV com titulo generico,
  p.ex. 'Episodio #1.1' - um alerta de veracidade):

| region   |   titulos |
|:---------|----------:|
| IN       |   5777302 |
| DE       |   5618724 |
| FR       |   5577561 |
| JP       |   5563745 |
| ES       |   5491997 |
| IT       |   5470000 |
| PT       |   5382009 |
| US       |   1761167 |
| GB       |    748786 |
| CA       |    529731 |

Filmes mais votados, com o titulo usado no Brasil:

| titulo_no_brasil                        | titulo_principal                                  |   ano |   nota |   votos |
|:----------------------------------------|:--------------------------------------------------|------:|-------:|--------:|
| Um Sonho de Liberdade                   | The Shawshank Redemption                          |  1994 |    9.3 | 3236691 |
| Batman: O Cavaleiro das Trevas          | The Dark Knight                                   |  2008 |    9.1 | 3225158 |
| A Origem                                | Inception                                         |  2010 |    8.8 | 2867229 |
| Clube da Luta                           | Fight Club                                        |  1999 |    8.8 | 2659893 |
| Interestelar                            | Interstellar                                      |  2014 |    8.7 | 2605003 |
| Forrest Gump - O Contador de Histórias  | Forrest Gump                                      |  1994 |    8.8 | 2533678 |
| Pulp Fiction: Tempo de Violência        | Pulp Fiction                                      |  1994 |    8.8 | 2466357 |
| Matrix                                  | The Matrix                                        |  1999 |    8.7 | 2277081 |
| O Poderoso Chefão                       | The Godfather                                     |  1972 |    9.2 | 2254950 |
| O Senhor dos Anéis: A Sociedade do Anel | The Lord of the Rings: The Fellowship of the Ring |  2001 |    8.9 | 2235755 |

Obs.: o dataset nao informa pais de producao; 'filmes brasileiros' exigiria outra fonte (p.ex. ANCINE) ou heuristica sobre a tabela akas.