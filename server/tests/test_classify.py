"""Casos con textos de anuncios reales (redacción típica de BOE/BOC). Ejecutar: python3 -m unittest discover tests"""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from oporadar.classify import clasificar  # noqa: E402

D = dt.date(2026, 10, 26)


class T(unittest.TestCase):
    def test_ayto_cantabria_boe_extracto(self):
        c = clasificar(
            "Resolución de 14 de octubre de 2026, del Ayuntamiento de Camargo (Cantabria), referente a la convocatoria para proveer varias plazas.",
            "En el «Boletín Oficial de Cantabria» número 198, de 13 de octubre de 2026, se han publicado íntegramente las bases "
            "que han de regir la convocatoria para proveer: Una plaza de Técnico/a Informático/a, perteneciente a la escala de "
            "Administración Especial, subescala Técnica, clase Media, Grupo A, Subgrupo A2, mediante el sistema de oposición, "
            "en turno libre. Dos plazas de Auxiliar Administrativo, grupo C, subgrupo C2, mediante concurso-oposición. "
            "El plazo de presentación de solicitudes será de veinte días naturales a contar desde el siguiente al de la publicación "
            "de este extracto en el «Boletín Oficial del Estado».",
            "ADMINISTRACIÓN LOCAL", "BOE", D)
        self.assertIsNotNone(c)
        self.assertEqual(c["zona"], "cantabria")
        self.assertEqual(c["sistema"], "oposicion")
        self.assertEqual(c["vinculo"], "funcionario")
        self.assertEqual(c["grupos"], ["A2"])
        self.assertEqual(c["tipo"], "convocatoria")
        self.assertEqual(c["nivel"], "prioritaria")
        self.assertEqual(c["plazo_fin"], "2026-11-15")
        self.assertEqual(c["organismo"], "Ayuntamiento de Camargo (Cantabria)")

    def test_gsi_age(self):
        c = clasificar(
            "Resolución de 20 de octubre de 2026, de la Secretaría de Estado de Función Pública, por la que se convoca proceso selectivo "
            "para ingreso, por el sistema general de acceso libre, en el Cuerpo de Gestión de Sistemas e Informática de la Administración del Estado.",
            "El proceso selectivo se realizará mediante el sistema de oposición, con las valoraciones, ejercicios y puntuaciones que se especifican en el anexo I.",
            "MINISTERIO PARA LA TRANSFORMACIÓN DIGITAL Y DE LA FUNCIÓN PÚBLICA", "BOE", D)
        self.assertEqual(c["zona"], "estatal")
        self.assertEqual(c["grupos"], ["A2"])
        self.assertTrue(c["grupo_inferido"])
        self.assertEqual(c["vinculo"], "funcionario")
        self.assertIn(c["nivel"], ("prioritaria",))

    def test_no_it_por_medios_informaticos(self):
        c = clasificar(
            "Resolución del Ayuntamiento de Laredo (Cantabria), referente a la convocatoria para proveer una plaza.",
            "Una plaza de Agente de Policía Local mediante oposición libre. Las solicitudes podrán presentarse por medios informáticos "
            "a través de la sede electrónica.", "ADMINISTRACIÓN LOCAL", "BOE", D)
        self.assertIsNone(c)

    def test_laboral_concurso_lejos(self):
        c = clasificar(
            "Resolución de la Universidad de Sevilla, por la que se convoca proceso selectivo para cubrir plazas de Técnico Especialista en Informática como personal laboral fijo.",
            "El sistema de selección será el de concurso-oposición.", "UNIVERSIDADES", "BOE", D)
        self.assertEqual(c["zona"], "resto")
        self.assertEqual(c["vinculo"], "laboral")
        self.assertEqual(c["sistema"], "concurso-oposicion")
        self.assertIn(c["nivel"], ("vigilar", "baja"))

    def test_admitidos_es_seguimiento(self):
        c = clasificar(
            "Resolución de la Universidad de Oviedo, por la que se aprueba la relación de admitidos y excluidos en las pruebas selectivas "
            "para ingreso en la Escala de Técnicos Auxiliares de Informática.", "", "UNIVERSIDADES", "BOE", D)
        self.assertEqual(c["tipo"], "seguimiento")
        self.assertEqual(c["zona"], "limitrofe")
        self.assertEqual(c["grupos"], ["C1"])

    def test_promocion_interna(self):
        c = clasificar(
            "Orden por la que se convocan pruebas selectivas para el ingreso, por promoción interna, en el Cuerpo Técnico Superior, Escala de Sistemas Informáticos.",
            "", "COMUNIDAD AUTÓNOMA DE CANTABRIA", "BOE", D)
        self.assertEqual(c["acceso"], "interna")
        self.assertNotEqual(c["nivel"], "prioritaria")

    def test_c2_fuera(self):
        c = clasificar("Convocatoria para proveer una plaza de Operador Informático, grupo C, subgrupo C2, mediante oposición libre.",
                       "", "", "BOC", D, fuente_zona="cantabria")
        self.assertEqual(c["grupos"], ["C2"])
        self.assertEqual(c["nivel"], "baja")

    def test_bases_boc_plazo_desde_boe(self):
        c = clasificar(
            "Bases de la convocatoria para la provisión en propiedad de una plaza de Técnico de Sistemas, personal funcionario, subgrupo A1, mediante oposición libre.",
            "El plazo de presentación de solicitudes será de veinte días naturales contados a partir del día siguiente a la publicación del extracto de la convocatoria en el Boletín Oficial del Estado.",
            "Ayuntamiento de Santander", "BOC", D, fuente_zona="cantabria")
        self.assertIn("BOE", c["plazo_txt"])
        self.assertEqual(c["score"], 100)

    def test_sistema_de_riego_no(self):
        c = clasificar("Convocatoria de una plaza de Técnico de sistemas de riego, mediante oposición.", "", "", "BOC", D, fuente_zona="cantabria")
        self.assertIsNone(c)

    def test_ope(self):
        c = clasificar("Resolución del Ayuntamiento de Torrelavega (Cantabria), por la que se anuncia la oferta de empleo público para 2026.",
                       "Personal funcionario: Escala de Administración Especial. Subgrupo A2. Técnico Informático. Una plaza. "
                       "Subgrupo C2. Auxiliar administrativo. Tres plazas.", "ADMINISTRACIÓN LOCAL", "BOE", D)
        self.assertEqual(c["tipo"], "oep")
        self.assertEqual(c["grupos"], ["A2"])


    def test_titular(self):
        c = clasificar("Resolución de 20 de octubre de 2026, del Ayuntamiento de Alhambra (Ciudad Real), referente a la convocatoria para proveer una plaza.",
                       "Una plaza de Técnico/a Informático/a, perteneciente a la escala de Administración Especial, subescala Técnica y clase Media, "
                       "por el sistema de concurso-oposición, en turno libre.", "ADMINISTRACIÓN LOCAL", "BOE", D)
        self.assertEqual(c["grupos"], ["A2"])
        self.assertEqual(c["puesto"], "Técnico/a Informático/a")
        self.assertEqual(c["lugar"], "Alhambra (Ciudad Real)")
        self.assertTrue(500 < c["km"] < 650)

    def test_pdi_fuera(self):
        self.assertIsNone(clasificar("Resolución de la Universidad de Jaén, por la que se convoca concurso de acceso a plazas de cuerpos docentes universitarios.",
                                     "Área de Lenguajes y Sistemas Informáticos", "UNIVERSIDADES", "BOE", D))


    def test_destino_no_es_puesto(self):
        self.assertIsNone(clasificar(
            "Resolución por la que se resuelve la convocatoria para la cobertura temporal de una plaza de Grupo Técnico de "
            "la Función Administrativa, con destino a la Unida de Costes y Sistemas de Información de Personal.",
            "", "CONSEJERÍA DE SALUD", "BOPA", D))

    def test_vocabulario_ampliado(self):
        for t in ["Bases para la provisión de una plaza de Analista, subgrupo A1, mediante oposición libre.",
                  "Convocatoria de una plaza de Técnico de Administración Electrónica, subgrupo A2.",
                  "Bases de una plaza de Ingeniero/a de Telecomunicación, personal funcionario.",
                  "Convocatoria para cubrir dos plazas de Técnico de Redes y Comunicaciones.",
                  "Proceso selectivo para una plaza de Técnico/a de Desarrollo de Software."]:
            self.assertIsNotNone(clasificar(t, "", "", "BOC", D, fuente_zona="cantabria"), t)
        for t in ["Convocatoria de una plaza de Analista Clínico, personal estatutario.",
                  "Bases de una plaza de Agente de Policía Local. Solicitudes en sede electrónica o en soporte informático."]:
            self.assertIsNone(clasificar(t, "", "", "BOC", D, fuente_zona="cantabria"), t)

    def test_falsos_positivos_sespa(self):
        # textos reales del BOPA del 27-10-2026
        casos = [
            ("Resolución de 9 de octubre de 2026, de la Dirección Gerencia del Servicio de Salud del Principado de Asturias, "
             "por la que se resuelve la convocatoria para la cobertura temporal, con carácter interino, de una plaza de Grupo "
             "Técnico de la Función Administrativa, con destino a la Unida de Costes y Sistemas de Información de Personal.",
             "provisión mediante nombramiento estatutario de interinidad, con un perfil técnico específico relacionado con las "
             "especificidades técnicas de la Unidad de Costes y Sistemas de Información de Personal de la Dirección de Profesionales"),
            ("Resolución por la que se convoca la cobertura temporal de una plaza de Facultativo Especialista de Área, en el "
             "Servicio de Genética y Genómica.",
             "se requiere experiencia en la configuración e integración de sistemas de información del laboratorio (SIL), y "
             "conocimientos teórico-prácticos en la implantación de sistemas de gestión de la calidad"),
            ("Resolución por la que se efectúa convocatoria pública para la cobertura de un puesto de Jefe/a de Servicio "
             "Facultativo: Laboratorio Clínico.",
             "Velar por la utilización adecuada de los sistemas de información clínica disponibles. Este documento deberá "
             "presentarse en soporte informático (CD-ROM, o lápiz de memoria)"),
        ]
        for t, x in casos:
            self.assertIsNone(clasificar(t, x, "Consejería de Salud", "BOPA", D, zona_defecto="limitrofe"), t[:60])

    def test_cuerpo_con_plaza_it_si(self):
        c = clasificar("Resolución del Ayuntamiento de Siero, referente a la convocatoria para proveer varias plazas.",
                       "Una plaza de Técnico/a de Sistemas Informáticos, subgrupo A2, mediante oposición libre.",
                       "ADMINISTRACIÓN LOCAL", "BOE", D)
        self.assertIsNotNone(c)

    def test_zona_defecto(self):
        c = clasificar("Resolución por la que se convocan pruebas selectivas para el Cuerpo de Técnicos Auxiliares de Informática.",
                       "", "Consejería de Hacienda", "BOPA", D, zona_defecto="limitrofe")
        self.assertEqual(c["zona"], "limitrofe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
