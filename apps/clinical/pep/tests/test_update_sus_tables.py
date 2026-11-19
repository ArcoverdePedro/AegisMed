from django.core.management import CommandError
from django.test import SimpleTestCase

from ..management.commands import update_sus_tables as command

DICTIONARY = """<h3 id="etnia">etnia</h3><table>
<tr><th>Código</th></tr>
<tr><td>1</td><td>0001</td><td>ACONA  (WAKONAS)</td></tr>
<tr><td>2</td><td>0002</td><td>AIKANA &amp; MAS</td></tr>
</table><table><tr><td>x</td><td>outra tabela</td></tr></table>"""
COUNTRIES = (
    "<table><tr><td>13</td><td>ARGENTINA</td></tr><tr><td>31</td><td>BRASIL</td></tr></table>"
)
IBGE = [
    {"id": 2611606, "nome": "Recife", "microrregiao": {"mesorregiao": {"UF": {"sigla": "PE"}}}},
    {
        "id": 5104526,
        "nome": "Boa Esperança do Norte",
        "microrregiao": None,
        "regiao-imediata": {"regiao-intermediaria": {"UF": {"sigla": "MT"}}},
    },
]


class UpdateSusTablesTests(SimpleTestCase):
    def test_parses_official_formats(self):
        self.assertEqual(
            [row[1:] for row in command.html_rows(DICTIONARY, "etnia")],
            [["0001", "ACONA (WAKONAS)"], ["0002", "AIKANA & MAS"]],
        )
        self.assertEqual(
            command.municipality_rows(IBGE),
            [["5104526", "Boa Esperança do Norte", "MT"], ["2611606", "Recife", "PE"]],
        )

    def test_refuses_to_overwrite_with_truncated_tables(self):
        with self.assertRaisesMessage(CommandError, "arquivos atuais mantidos"):
            command.build_tables(IBGE, DICTIONARY, COUNTRIES)
