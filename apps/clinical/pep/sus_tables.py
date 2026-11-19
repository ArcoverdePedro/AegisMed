"""Tabelas oficiais do cadastro SUS do paciente, em CSV versionado em data/.

Fontes (baixadas em 17/11/2026; atualizar substituindo os CSVs):
- municipios.csv: IBGE, https://servicodados.ibge.gov.br/api/v1/localidades/municipios
- etnias.csv: codigo CADSUS, dicionario LEDI/e-SUS APS
  (https://integracao.esusab.ufsc.br/ledi/documentacao/referencias/dicionario.html#etnia)
- paises.csv: codigo CADSUS, LEDI/e-SUS APS
  (https://integracao.esusab.ufsc.br/ledi/documentacao/referencias/paises.html)
"""

import csv
import unicodedata
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
BRAZIL_COUNTRY_CODE = "31"


@cache
def table(name: str) -> dict[str, dict[str, str]]:
    with (DATA_DIR / f"{name}.csv").open(encoding="utf-8", newline="") as file:
        return {row["codigo"]: row for row in csv.DictReader(file)}


def choices(name: str) -> list[tuple[str, str]]:
    return [("", "---------")] + [(code, row["nome"]) for code, row in table(name).items()]


def _fold(text: str) -> str:
    """Comparacao sem acento e sem caixa: 'sao jose' encontra 'São José'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def municipality_label(code: str) -> str:
    row = table("municipios").get(code)
    return f"{row['nome']}/{row['uf']}" if row else ""


@cache
def _folded_labels() -> dict[str, tuple[str, str]]:
    """Rotulo 'nome/uf' normalizado -> (codigo IBGE, rotulo original)."""
    return {
        _fold(municipality_label(code)): (code, municipality_label(code))
        for code in table("municipios")
    }


def municipality_code_for(label: str) -> str | None:
    found = _folded_labels().get(_fold(" ".join(label.split())))
    return found[0] if found else None


def search_municipalities(query: str, limit: int = 20) -> list[str]:
    query = _fold(query.strip())
    if len(query) < 2:
        return []
    starts, contains = [], []
    for folded, (_, label) in _folded_labels().items():
        if folded.startswith(query):
            starts.append(label)
        elif query in folded:
            contains.append(label)
    return (starts + contains)[:limit]
