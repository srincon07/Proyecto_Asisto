from django.test import TestCase
from django.utils import timezone

from EstructuraApp.models import Cargo, Linea, Objetivo, Organizacion, TipoActividad, Unidad
from PersonasApp.models import Persona

from .models import ActividadProgramada, RegistroAsistencia
from .services import get_or_create_persona, procesar_verificacion_asistente


class RegistroAsistenciaFieldTest(TestCase):
    def test_can_store_registration_metadata(self):
        registro = RegistroAsistencia(
            organizacion_origen="Empresa de prueba",
            seudonimo="Alias de prueba",
        )

        self.assertEqual(registro.organizacion_origen, "Empresa de prueba")
        self.assertEqual(registro.seudonimo, "Alias de prueba")


class VerificacionAsistenteServiceTest(TestCase):
    def test_blank_email_is_normalized_for_registration(self):
        Persona.objects.create(identificacion="111111111", nombres="Otro", apellidos="Usuario", email="")

        request = type("Request", (), {"POST": {"identificacion": "999999999", "nombres": "Ana", "apellidos": "Pérez", "correo": "", "telefono": "", "genero": "Femenino", "autoriza_datos": "off"}})()

        persona = get_or_create_persona(request)

        self.assertEqual(persona.identificacion, "999999999")
        self.assertNotEqual(persona.email, "")
        self.assertTrue(persona.email.endswith("@asisto.local"))

    def test_existing_persona_verification_does_not_raise(self):
        organizacion = Organizacion.objects.create(
            nombre_organizacion="Org Test",
            nit="900000000",
            direccion="Calle 1",
            telefono="123",
            correo_electronico="org@example.com",
        )
        unidad = Unidad.objects.create(id_organizacion=organizacion, nombre_unidad="Unidad Test")
        Cargo.objects.create(id_unidad=unidad, nombre_cargo="Cargo Test")

        objetivo = Objetivo.objects.create(id_unidad=unidad, nombre_objetivo="Objetivo Test")
        linea = Linea.objects.create(id_objetivo=objetivo, nombre_linea="Línea Test")
        tipo_actividad = TipoActividad.objects.create(
            id_linea=linea,
            nombre="Actividad Test",
            modalidad=TipoActividad.ModalidadChoices.PRESENCIAL,
        )

        responsable = Persona.objects.create(
            identificacion="1000000000",
            nombres="Responsable",
            apellidos="Test",
            email="responsable@example.com",
        )
        actividad = ActividadProgramada.objects.create(
            id_tipo_actividad=tipo_actividad,
            id_responsable=responsable,
            nombre_evento="Evento Test",
            requiere_preregistro=False,
            fecha_hora_inicio=timezone.now() + timezone.timedelta(hours=1),
            fecha_hora_fin=timezone.now() + timezone.timedelta(hours=2),
            lugar_desarrollo="Lugar Test",
        )
        persona = Persona.objects.create(
            identificacion="123456789",
            nombres="Juan",
            apellidos="Pérez",
            email="juan@example.com",
        )

        resultado, status_code = procesar_verificacion_asistente(actividad, persona.identificacion)

        self.assertEqual(status_code, 200)
        self.assertEqual(resultado["status"], "COMPLETAR_REGISTRO")
        self.assertEqual(resultado["organizacion_origen"], "")
