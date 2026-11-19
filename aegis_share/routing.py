from django.urls import path

from apps.clinical.adt.consumers import AdtBedMapConsumer
from apps.clinical.pep.consumers import PatientClinicalConsumer

websocket_urlpatterns = [
    path(
        "ws/clinical/patients/<uuid:patient_id>/",
        PatientClinicalConsumer.as_asgi(),
    ),
    path("ws/clinical/adt/bed-map/", AdtBedMapConsumer.as_asgi()),
]
