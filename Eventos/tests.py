from django.test import TestCase

from .models import RegistroAsistencia


class RegistroAsistenciaFieldTest(TestCase):
    def test_can_store_registration_metadata(self):
        registro = RegistroAsistencia(
            organizacion_origen="Empresa de prueba",
            seudonimo="Alias de prueba",
        )

        self.assertEqual(registro.organizacion_origen, "Empresa de prueba")
        self.assertEqual(registro.seudonimo, "Alias de prueba")
