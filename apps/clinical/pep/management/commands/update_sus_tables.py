"""Baixa as tabelas oficiais do cadastro SUS e regenera os CSVs de apps/clinical/pep/data/.

Uso: python manage.py update_sus_tables   (depois revise o diff e faca commit dos CSVs)
"""

import csv
import html
import io
import re

import requests
from django.core.management import BaseCommand, CommandError

from apps.clinical.pep.sus_tables import BRAZIL_COUNTRY_CODE, DATA_DIR

IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
LEDI_URL = "https://integracao.esusab.ufsc.br/ledi/documentacao/referencias/"
# Contagens minimas: protege contra sobrescrever os CSVs com uma pagina quebrada.
MINIMUM_ROWS = {"municipios": 5000, "etnias": 300, "paises": 200}


def html_rows(page, anchor=None):
    """Celulas de cada <tr> de uma tabela HTML do LEDI (opcionalmente a partir de um id)."""
    if anchor:
        start = page.find(f'id="{anchor}"')
        if start < 0:
            raise CommandError(f"Tabela '{anchor}' não encontrada na página do LEDI.")
        page = page[start : page.find("</table>", start)]
    rows = []
    for row in re.findall(r"<tr>(.*?)</tr>", page, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        rows.append([" ".join(html.unescape(re.sub(r"<[^>]+>", "", c)).split()) for c in cells])
    return [row for row in rows if row]


def municipality_rows(municipalities):
    def state(item):
        micro = item.get("microrregiao")
        if micro:
            return micro["mesorregiao"]["UF"]["sigla"]
        return item["regiao-imediata"]["regiao-intermediaria"]["UF"]["sigla"]

    rows = [[str(item["id"]), item["nome"], state(item)] for item in municipalities]
    return sorted(rows, key=lambda row: (row[2], row[1]))


def build_tables(ibge_json, dictionary_html, countries_html):
    tables = {
        "municipios": (["codigo", "nome", "uf"], municipality_rows(ibge_json)),
        "etnias": (["codigo", "nome"], [r[1:3] for r in html_rows(dictionary_html, "etnia")]),
        "paises": (["codigo", "nome"], [r[:2] for r in html_rows(countries_html)]),
    }
    for name, (_, rows) in tables.items():
        if len(rows) < MINIMUM_ROWS[name]:
            raise CommandError(f"{name}: só {len(rows)} linhas; arquivos atuais mantidos.")
    if [BRAZIL_COUNTRY_CODE, "BRASIL"] not in tables["paises"][1]:
        raise CommandError(f"paises: BRASIL não tem o código {BRAZIL_COUNTRY_CODE}.")
    return tables


class Command(BaseCommand):
    help = "Atualiza municípios (IBGE), etnias e países (CADSUS/LEDI) usados no cadastro SUS."

    def handle(self, *args, **options):
        def get(url):
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            return response

        tables = build_tables(
            get(IBGE_URL).json(),
            get(LEDI_URL + "dicionario.html").text,
            get(LEDI_URL + "paises.html").text,
        )
        for name, (header, rows) in tables.items():
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow(header)
            writer.writerows(rows)
            (DATA_DIR / f"{name}.csv").write_text(buffer.getvalue(), encoding="utf-8")
            self.stdout.write(f"{name}.csv: {len(rows)} linhas")
