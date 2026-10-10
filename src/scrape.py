"""
Etapa 1 — coleta de dados de tabuademares.com/br/paraiba/joao-pessoa.

Objetivo: gravar em data/raw/ os CSVs que as Etapas 2 e 3 vão consumir.

    mares_<ano>.csv      tábua de marés do ano (4 marés por dia)
    mares_previsao.csv   marés do mês corrente, para cruzar com a previsão
    ondas.csv            altura de onda hora a hora (~7 dias à frente)
    vento.csv            velocidade do vento hora a hora (~7 dias à frente)

As funções abaixo estão vazias de propósito. Abra o site no navegador, use o
DevTools para descobrir onde cada dado vive no HTML e implemente o parse.
As colunas de cada CSV são sua decisão — só precisam sustentar as etapas
seguintes (ver README).

Rodar com: uv run python src/scrape.py
"""

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Os imports acima são o ponto de partida: você vai usar todos eles.
# Seu editor pode marcá-los como não usados até você preencher as funções.

URL_BASE = "https://tabuademares.com/br/paraiba/joao-pessoa"
URL_ONDAS = f"{URL_BASE}/previsao/ondas"
URL_VENTO = f"{URL_BASE}/previsao/vento"

# Servidores rejeitam clientes sem User-Agent. Identifique-se.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Segundos de pausa entre requests. Não tire isso.
PAUSA = 1.5

MESES = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
         "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}

DIR_RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def baixar_html(url: str, dados_post: dict | None = None) -> str:
    """Baixa uma página e devolve o HTML.

    Use POST (passando `dados_post`) quando a página só devolver o conteúdo
    que você quer em resposta a um formulário; GET no resto.

    TODO: fazer a requisição com `requests`, checar o status e devolver o texto.
    Dica: `resp.raise_for_status()` falha alto quando o servidor recusa.
    """

    if dados_post is None:
        resp = requests.get(url, headers=HEADERS, timeout=30)
    else:
        resp = requests.post(url, headers=HEADERS, data=dados_post, timeout=30)
    resp.raise_for_status()
    return resp.text

def parsear_mares(html: str, ano: int, mes: int) -> list[dict]:
    
    soup = BeautifulSoup(html, "html.parser")
    linhas = []
    vistos = set()

    for td_dia in soup.select("td.tabla_mareas_dia"):
        num_el = td_dia.select_one("div.tabla_mareas_dia_numero")
        dia_numero = num_el.get_text(strip=True) if num_el else ""
        if not dia_numero or dia_numero in vistos:
            continue
        vistos.add(dia_numero)

        tr = td_dia.find_parent("tr")
        if not tr:
            continue

        tds = tr.find_all("td", recursive=False)
        if len(tds) < 7:
            continue

        data = f"{ano:04d}-{mes:02d}-{int(dia_numero):02d}"

        for td in tds[3:7]:
            texto_bruto = td.get_text(" ", strip=True)
            if not texto_bruto:
                continue

            classes = [
                cls
                for el in [td] + td.find_all(True)
                for cls in el.get("class", [])
            ]
            
            tipo = ""
            if "tabla_mareas_marea_pleamar" in classes:
                tipo = "pleamar"
            elif "tabla_mareas_marea_bajamar" in classes:
                tipo = "bajamar"

            partes = texto_bruto.split()
            hora = partes[0] if len(partes) > 0 else ""
            altura = partes[1] if len(partes) > 1 else ""

            linhas.append({
                "data": data,
                "hora": hora,
                "altura": altura,
                "tipo": tipo,
            })

    return linhas

def parsear_previsao(html: str, ano: int) -> list[dict]:

    soup = BeautifulSoup(html, "html.parser")
    linhas = []

    for ficha in soup.select("div.ficha"):
        dia_el = ficha.select_one("span.dia")
        mes_el = ficha.select_one("span.mes")

        dia = dia_el.get_text(strip=True) if dia_el else ""
        mes = mes_el.get_text(strip=True) if mes_el else ""

        for bloco in ficha.select("div.f_temp_horas"):
            celulas = bloco.select("div.f_temp_hora")
            barra = bloco.select_one("div.grafico_temp_barra_relleno")

            hora = celulas[0].get_text(strip=True) if len(celulas) > 0 else ""
            direcao = celulas[1].get_text(strip=True) if len(celulas) > 1 else ""
            
        
            valor_texto = barra.get_text(" ", strip=True) if barra else ""
            valor = valor_texto.split()[0] if valor_texto else ""

            linhas.append({
                "dia": dia,
                "mes": mes,
                "hora": hora,
                "valor": valor,
                "direcao": direcao,
            })

    return linhas


def coletar_mares_do_ano(ano: int) -> pd.DataFrame:
    quadros = []
    for mes in range(1, 13):
        html = baixar_html(URL_BASE, {"fecha": f"{ano}-{mes:02d}-01"})
        linhas = parsear_mares(html, ano, mes)
        print(f"  {ano}-{mes:02d}: {len(linhas)} marés")
        quadros.append(pd.DataFrame(linhas))
        time.sleep(PAUSA)

    if not quadros:
        return pd.DataFrame()

    return pd.concat(quadros, ignore_index=True)

def coletar_mares_do_ano(ano: int) -> pd.DataFrame:

    quadros = []
    for mes in range(1, 13):
        html = baixar_html(URL_BASE, {"fecha": f"{ano}-{mes:02d}-01"})
        linhas = parsear_mares(html, ano, mes)
        print(f"  {ano}-{mes:02d}: {len(linhas)} marés")
        quadros.append(pd.DataFrame(linhas))
        time.sleep(PAUSA)
    return pd.concat(quadros, ignore_index=True)


def main(ano: int = 2025) -> None:
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    hoje = datetime.now()
    ano = ano or hoje.year
 
    df = coletar_mares_do_ano(ano)
    df.to_csv(DIR_RAW / f"mares_{ano}.csv", index=False)
    print(f"mares_{ano}.csv: {len(df)} linhas")
 
    
    html = baixar_html(URL_BASE, {"fecha": f"{hoje.year}-{hoje.month:02d}-01"})
    df = pd.DataFrame(parsear_mares(html, hoje.year, hoje.month))
    df.to_csv(DIR_RAW / "mares_previsao.csv", index=False)
    print(f"mares_previsao.csv: {len(df)} linhas")
    time.sleep(PAUSA)
 
    
    df = pd.DataFrame(parsear_previsao(baixar_html(URL_ONDAS), hoje.year))
    df.to_csv(DIR_RAW / "ondas.csv", index=False)
    print(f"ondas.csv: {len(df)} linhas")
    time.sleep(PAUSA)
 
    
    df = pd.DataFrame(parsear_previsao(baixar_html(URL_VENTO), hoje.year))
    df.to_csv(DIR_RAW / "vento.csv", index=False)
    print(f"vento.csv: {len(df)} linhas")


if __name__ == "__main__":
    main()