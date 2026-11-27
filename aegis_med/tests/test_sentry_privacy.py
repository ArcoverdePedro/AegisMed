import sentry_sdk
from django.conf import settings
from django.test import SimpleTestCase
from sentry_sdk.data_collection import _apply_data_collection_filtering_to_query_string
from sentry_sdk.integrations._wsgi_common import _filter_headers

SEARCH_URL = "https://aegis.test/pep/?q=Maria+Silva+12345678900"


class SentryPrivacyTests(SimpleTestCase):
    def test_busca_de_paciente_nao_vai_para_o_sentry(self):
        client = sentry_sdk.Client(
            dsn="https://key@o0.ingest.sentry.io/0",
            data_collection=settings.SENTRY_DATA_COLLECTION,
        )
        with sentry_sdk.new_scope() as scope:
            scope.set_client(client)
            headers = _filter_headers(
                {"Referer": SEARCH_URL, "HX-Current-URL": SEARCH_URL, "Cookie": "sessionid=x"}
            )

        self.assertNotIn("Maria", str(headers))
        self.assertNotIn("12345678900", str(headers))
        self.assertIsNone(
            _apply_data_collection_filtering_to_query_string(
                "q=12345678900", client.options["data_collection"]["url_query_params"]
            )
        )
