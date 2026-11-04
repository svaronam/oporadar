"""Lectores de BOC, BOCYL, BOPA y BOPV con fragmentos copiados de sus webs reales (oct. 2026), sin red."""
import datetime as dt
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from oporadar.sources import boc, bocyl, bopa, bopv  # noqa: E402

F = dt.date(2026, 10, 27)

BOC_JSON = json.dumps([
    {"id": 47265, "fecBol": "oct 26, 2026", "tipoBol": 0, "numBol": 205, "fecBolMilis": 1792969200000},
    {"id": 47285, "fecBol": "oct 27, 2026", "tipoBol": 0, "numBol": 206, "fecBolMilis": 1793055600000},
    {"id": 47345, "fecBol": "oct 26, 2026", "tipoBol": 1, "numBol": 28, "fecBolMilis": 1792969200000}])
BOC_SUM = """<html><body>
<a name="sec21"></a><span class="spanH5">2.1.Nombramientos, Ceses y Otras Situaciones</span>
<a name="dpto1"></a><span class="spanH4">Ayuntamiento de Laredo</span>
<p>Nombramiento de funcionario en prácticas de Técnico Informático.</p>
<div class="enlacesDoc"><div class="tipoPDFanuncio"><a href="verAnuncioAction.do?idAnuBlob=442100">PDF (BOC-2026-8300 - 200 Kb)</a></div></div>
<a name="sec22"></a><span class="spanH5">2.2.Cursos, Oposiciones y Concursos</span>
<div class="margin-bottom-24"></div><div class="ancla"><a href="#contenido">Subir</a></div>
<a name="dpto23281"></a><span class="spanH4">Universidad de Cantabria</span>
<div class="margin-top-24"></div>
<p>Resoluci&oacute;n Rectoral (R.R. 1346/2026), por la que se convoca oposici&oacute;n libre para el ingreso en la Escala de Gesti&oacute;n de Sistemas e Inform&aacute;tica, subgrupo A2.</p>
<div class="enlacesDoc"><div class="tipoPDFanuncio">
<a href="verAnuncioAction.do?idAnuBlob=442219" title="Este documento se abrir&aacute; en una nueva ventana" target="blank">PDF (BOC-2026-8321 - 1,31 Mb)</a>
</div></div>
<a name="dpto23288"></a><span class="spanH4">Ayuntamiento de Valderredible</span>
<p>Bases reguladoras y convocatoria del proceso selectivo para la provisi&oacute;n de una plaza de Administrativo, Subgrupo C1.</p>
<div class="enlacesDoc"><div class="tipoPDFanuncio"><a href="verAnuncioAction.do?idAnuBlob=442214">PDF (BOC-2026-8320 - 527 Kb)</a></div></div>
<a name="sec23"></a><span class="spanH5">2.3.Otros</span>
<a name="dpto219942"></a><span class="spanH4">Consejer&iacute;a de Salud</span>
<span class="spanH6">Secretar&iacute;a General</span>
<p>Tr&aacute;mite de audiencia en relaci&oacute;n con el recurso de reposici&oacute;n contra la relaci&oacute;n de aspirantes que han superado las pruebas selectivas.</p>
<div class="enlacesDoc"><div class="tipoPDFanuncio"><a href="verAnuncioAction.do?idAnuBlob=442203">PDF (BOC-2026-8308 - 262 Kb)</a></div></div>
<a name="dpto23276"></a><span class="spanH4">Ayuntamiento de Santander</span>
<p>Aprobaci&oacute;n de la Relaci&oacute;n de Puestos de Trabajo del Servicio Municipal de Transportes Urbanos.</p>
<div class="enlacesDoc"><div class="tipoPDFanuncio"><a href="verAnuncioAction.do?idAnuBlob=442222">PDF (BOC-2026-8326 - 854 Kb)</a></div></div>
<a name="sec44"></a><span class="titulo2 margin-bottom-12">4.Econom&iacute;a, Hacienda y Seguridad Social</span>
<span class="spanH5">4.1.Actuaciones en materia Presupuestaria</span>
<span class="spanH4">Ayuntamiento de Noja</span><p>Aprobación del presupuesto general con plazas de informática.</p>
<div class="enlacesDoc"><a href="verAnuncioAction.do?idAnuBlob=442299">PDF (BOC-2026-8399 - 1 Kb)</a></div>
</body></html>"""

BOCYL = """<html><body>
<h4 class="encabezado4_sinlinea">A. DISPOSICIONES GENERALES</h4>
<h5 class="encabezado6">CONSEJERÍA DE MEDIO AMBIENTE Y ENERGÍA</h5>
<p>DECRETO por el que se regula la informática ambiental.</p>
<ul class="descargaBoletin"><li><a href='https://bocyl.jcyl.es/boletines/2026/10/27/pdf/BOCYL-D-27102026-1.pdf'>BOCYL-D-27102026-1.pdf</a></li></ul>
<h4 class="encabezado4" id="I.B._AUTORIDADES_Y_PERSONAL-B.2._Oposiciones_y_Concursos">B. AUTORIDADES Y PERSONAL: B.2. Oposiciones y Concursos</h4>
<h5 class="encabezado6">CONSEJERÍA DE LA PRESIDENCIA</h5>
      <p>RESOLUCIÓN de 21 de octubre de 2026, de la Viceconsejería de Administraciones Públicas, por la que se convoca proceso selectivo para el ingreso en el Cuerpo de Gestión, Escala de Gestión de Sistemas de Información, de la Administración de la Comunidad de Castilla y León.</p>
      <ul class="descargaBoletin">
      	<li><a href='https://bocyl.jcyl.es/boletines/2026/10/27/pdf/BOCYL-D-27102026-208-3.pdf' title="x"><img class="imagenEnlace" src="img/ico_pdf.jpg" alt="" /> BOCYL-D-27102026-208-3.pdf - 1161 KB</a></li>
      	<!-- <li><a href='https://bocyl.jcyl.es/boletines/2026/10/27/pdf/BOCYL-D-27102026-208-3.pdf'>dup</a></li> -->
      	<li><a href='html/2026/10/27/html/BOCYL-D-27102026-208-3.do' title="x"><img class="imagenEnlace" src="img/ico_html.jpg" alt="" />BOCYL-D-27102026-208-3.html y otros formatos</a></li>
      </ul>
<h5 class="encabezado6">UNIVERSIDAD DE LEÓN</h5>
      <p>RESOLUCIÓN por la que se aprueba la relación de admitidos en las pruebas de Técnico Especialista de Informática.</p>
      <ul class="descargaBoletin"><li><a href='https://bocyl.jcyl.es/boletines/2026/10/27/pdf/BOCYL-D-27102026-208-4.pdf'>pdf</a></li>
      <li><a href='html/2026/10/27/html/BOCYL-D-27102026-208-4.do'>html</a></li></ul>
<h4 class="encabezado4">C. SUBVENCIONES: C.2. Convocatorias</h4>
<h5 class="encabezado6">UNIVERSIDAD DE BURGOS</h5>
<p>Ayudas para equipos informáticos.</p><ul><li><a href='https://bocyl.jcyl.es/boletines/2026/10/27/pdf/BOCYL-D-27102026-9.pdf'>pdf</a></li></ul>
<h4 class="encabezado4_sinlinea">A. DISPOSICIONES Y ACTOS</h4>
<h5 class="encabezado6">AYUNTAMIENTO DE SOLOSANCHO (ÁVILA)</h5>
<p>Bases para la provisión de una plaza de Técnico Informático, subgrupo A2, por oposición libre.</p>
<ul><li><a href='https://bocyl.jcyl.es/boletines/2026/10/27/pdf/BOCYL-D-27102026-20.pdf'>pdf</a></li></ul>
<h5 class="encabezado6">AYUNTAMIENTO DE FUENTESAÚCO (ZAMORA)</h5>
<p>Aprobación de la ordenanza fiscal.</p>
<ul><li><a href='https://bocyl.jcyl.es/boletines/2026/10/27/pdf/BOCYL-D-27102026-21.pdf'>pdf</a></li></ul>
</body></html>"""

BOPA = """<html><body><div class="menu"><h4>Menú</h4></div>
<div id="bopa-boletin"> <h4>I. Principado de Asturias</h4> <h5>AUTORIDADES Y PERSONAL</h5>
<h6 style="text-transform: uppercase;">CONSEJERÍA DE SALUD</h6>
<p style="font-size: 0.95em;" class="subAuthor">SERVICIO DE SALUD DEL PRINCIPADO DE ASTURIAS (SESPA)</p>
<dl> <dt> Resolución de 9 de octubre de 2026, por la que se resuelve la convocatoria para la cobertura temporal, con carácter interino, de una plaza de Grupo Técnico de la Función Administrativa, con destino a la Unida de Costes y Sistemas de Información de Personal de la Dirección de profesionales.&nbsp;<strong>[Cód. 2026-08468]</strong> </dt>
<dd> <a title="Texto de la disposición" href="https://miprincipado.asturias.es/bopa/disposiciones?p_p_id=x&amp;p_r_p_dispositionText=2026-08468&amp;p_r_p_dispositionDate=27%2F10%2F2026">Texto de la disposición</a> &nbsp; <span class="pdfResultadoBopa"><a title="PDF de la disposición" href="/bopa/2026/10/27/2026-08468.pdf" target="_blank">PDF de la disposición</a>(135KB)&nbsp;</span> </dd> </dl>
<dl> <dt> Resolución por la que se convocan pruebas selectivas para el ingreso en el Cuerpo de Técnicos Auxiliares de Informática de la Administración del Principado de Asturias.&nbsp;<strong>[Cód. 2026-08480]</strong> </dt>
<dd> <a title="Texto de la disposición" href="https://miprincipado.asturias.es/bopa/disposiciones?p_r_p_dispositionText=2026-08480">Texto de la disposición</a> <span class="pdfResultadoBopa"><a href="/bopa/2026/10/27/2026-08480.pdf">PDF de la disposición</a></span> </dd> </dl>
<h5>OTRAS DISPOSICIONES</h5> <h6 style="text-transform: uppercase;">CONSEJERÍA DE HACIENDA</h6>
<dl><dt>Resolución sobre el sistema informático de gestión tributaria. <strong>[Cód. 2026-08490]</strong></dt><dd><a href="/bopa/2026/10/27/2026-08490.pdf">PDF</a></dd></dl>
<h4>IV. Administración Local</h4> <h5>AYUNTAMIENTOS</h5>
<h6 style="text-transform: uppercase;">DE GIJÓN/XIXÓN</h6>
<dl> <dt> Anuncio. Bases de la convocatoria para la provisión de dos plazas de Técnico/a de Sistemas Informáticos, Subgrupo A2, mediante oposición libre.&nbsp;<strong>[Cód. 2026-08471]</strong> </dt>
<dd> <a title="Texto de la disposición" href="https://miprincipado.asturias.es/bopa/disposiciones?p_r_p_dispositionText=2026-08471">Texto de la disposición</a> <span class="pdfResultadoBopa"><a href="/bopa/2026/10/27/2026-08471.pdf">PDF de la disposición</a></span> </dd> </dl>
<h6 style="text-transform: uppercase;">DE TINEO</h6>
<dl> <dt> Anuncio. Delegación de funciones de Alcaldía para la celebración de matrimonio.&nbsp;<strong>[Cód. 2026-08502]</strong> </dt>
<dd> <a href="/bopa/2026/10/27/2026-08502.pdf">PDF de la disposición</a> </dd> </dl>
</div></body></html>"""

BOPV_ULT = """<html><head><meta http-equiv="Content-Type" content="text/html; charset=ISO-8859-1"></head><body>
<h2>Consulta</h2><p>Sumario n.º 205 , martes 27 de octubre de 2026</p>
<a href="2026/10/s26_0205.pdf">PDF (220 KB - 4 Pág.)</a>
<a name="anclaBOPVSeccion1"></a><h4 class="BOPVSumarioSeccion">AUTORIDADES Y PERSONAL</h4>
<h5 class="BOPVSumarioSubSeccion">Nombramientos</h5>
<h5 class="BOPVSumarioOrganismo">UPV/EHU </h5>
<div class="txtBloque"><p class="BOPVSumarioTitulo"><a href="2026/10/2604501a.shtml">RESOLUCIÓN de nombramiento de personal informático.</a></p><span class="BOPVSumarioOrden">4501</span></div>
<a name="anclaBOPVSeccion4"></a><h4 class="BOPVSumarioSeccion"> </h4><a name="anclaBOPVSubSeccion4"></a>
<h5 class="BOPVSumarioSubSeccion">Oposiciones y concursos</h5>
<h5 class="BOPVSumarioOrganismo">DEPARTAMENTO DE GOBERNANZA, ADMINISTRACIÓN DIGITAL Y AUTOGOBIERNO </h5>
<div class="txtBloque"><p class="BOPVSumarioTitulo"><a href="2026/10/2604506a.shtml">RESOLUCIÓN de 16 de octubre de 2026, de la directora del Instituto Vasco de Administración Pública, por la que se convocan pruebas selectivas de acceso al Cuerpo Superior Facultativo, Escala Informática, de la Administración de la Comunidad Autónoma de Euskadi.</a></p><span class="BOPVSumarioOrden">4506</span></div>
<h5 class="BOPVSumarioOrganismo">AYUNTAMIENTO DE BARAKALDO </h5>
<div class="txtBloque"><p class="BOPVSumarioTitulo"><a href="2026/10/2604507a.shtml">ANUNCIO relativo a la Oferta de Empleo Público 2026.</a></p></div>
<a name="anclaBOPVSeccion5"></a><h4 class="BOPVSumarioSeccion">OTRAS DISPOSICIONES</h4>
<h5 class="BOPVSumarioSubSeccion"> </h5><h5 class="BOPVSumarioOrganismo">LEHENDAKARITZA </h5>
<div class="txtBloque"><p class="BOPVSumarioTitulo"><a href="2026/10/2604508a.shtml">CORRECCIÓN DE ERRORES de ayudas informáticas.</a></p></div>
</body></html>"""
BOPV_ANT = BOPV_ULT.replace("n.º 205 , martes 27", "n.º 204 , lunes 26").replace("2604506a", "2604490a") \
    .replace("2604507a", "2604491a").replace("Escala Informática", "Escala de Analistas")
BOPV_VIEJO = BOPV_ULT.replace("n.º 205 , martes 27", "n.º 203 , viernes 23")


class TBoc(unittest.TestCase):
    def test_boc(self):
        def fake(url, **kw):
            if "busquedaBoletines" in url:
                self.assertEqual(kw.get("data"), b"")  # es un POST
                return BOC_JSON, "text/plain;charset=UTF-8"
            self.assertIn("idBolOrd=47285", url)
            return BOC_SUM, "text/html"
        boc.fetch = fake
        boc._cache_mes.clear()
        self.assertEqual(boc.urls_boletin_del_dia(dt.date(2026, 10, 26)),
                         ["https://boc.cantabria.es/boces/verBoletin.do?idBolOrd=47265",
                          "https://boc.cantabria.es/boces/verBoletinExtraordinario.do?id=47345"])
        cs = boc.candidatos(F)
        tit = [c["titulo"] for c in cs]
        self.assertEqual(len(cs), 3, tit)  # 2 de 2.2 + 1 de 2.3 que suena a proceso selectivo
        self.assertIn("Gestión de Sistemas e Informática", tit[0])
        self.assertEqual(cs[0]["uid"], "BOC:BOC-2026-8321")
        self.assertEqual(cs[0]["departamento"], "Universidad de Cantabria")
        self.assertEqual(cs[0]["url"], "https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=442219")
        self.assertEqual(cs[2]["departamento"], "Consejería de Salud")


class TBocyl(unittest.TestCase):
    def test_bocyl(self):
        bocyl.fetch = lambda url, **kw: (BOCYL + "<p>27102026</p>", "text/html")
        cs = bocyl.candidatos(F)
        tit = [c["titulo"][:40] for c in cs]
        self.assertEqual(len(cs), 3, tit)
        self.assertEqual(cs[0]["uid"], "BOCYL:BOCYL-D-27102026-208-3")
        self.assertEqual(cs[0]["url"], "https://bocyl.jcyl.es/html/2026/10/27/html/BOCYL-D-27102026-208-3.do")
        self.assertEqual(cs[0]["departamento"], "Consejería de la Presidencia")
        self.assertEqual(cs[1]["departamento"], "Universidad de León")
        self.assertIn("Solosancho", cs[2]["departamento"])

    def test_sin_boletin(self):
        bocyl.fetch = lambda url, **kw: ("<html>portada</html>", "text/html")
        self.assertEqual(bocyl.candidatos(dt.date(2026, 10, 25)), [])


class TBopa(unittest.TestCase):
    def test_bopa(self):
        bopa.fetch = lambda url, **kw: (BOPA, "text/html")
        cs = bopa.candidatos(F)
        tit = [c["titulo"][:50] for c in cs]
        self.assertEqual(len(cs), 3, tit)  # 2 de Autoridades y personal + Gijón (Tineo no es selectivo)
        self.assertEqual(cs[0]["uid"], "BOPA:2026-08468")
        self.assertNotIn("[Cód.", cs[0]["titulo"].split("[Cód. 2026")[0])
        self.assertEqual(cs[1]["url_pdf"], "https://miprincipado.asturias.es/bopa/2026/10/27/2026-08480.pdf")
        self.assertEqual(cs[2]["departamento"], "Ayuntamiento de Gijón/xixón")

    def test_sin_boletin(self):
        bopa.fetch = lambda url, **kw: ("<html>no hay</html>", "text/html")
        self.assertEqual(bopa.candidatos(dt.date(2026, 10, 25)), [])


class TBopv(unittest.TestCase):
    def test_bopv(self):
        import urllib.error

        def fake(url, **kw):
            if url.endswith("Ultimo.shtml"):
                return BOPV_ULT, "text/html"
            if url.endswith("2026/10/s26_0205.shtml"):
                return BOPV_ULT, "text/html"
            if url.endswith("2026/10/s26_0204.shtml"):
                return BOPV_ANT, "text/html"
            if url.endswith("2026/10/s26_0203.shtml"):
                return BOPV_VIEJO, "text/html"
            if "/datos/2026/" in url:  # carpeta equivocada: 200 sin sumario, como la web real
                return "<html><h2>Consulta</h2></html>", "text/html"
            raise urllib.error.HTTPError(url, 404, "no", {}, None)
        bopv.fetch = fake
        bopv._cache.clear()
        res = bopv.candidatos_por_fecha(dt.date(2026, 10, 26))
        self.assertEqual(sorted(res), [dt.date(2026, 10, 26), F])
        hoy = res[F]
        self.assertEqual(len(hoy), 2)
        self.assertEqual(hoy[0]["url"], "https://www.euskadi.eus/web01-bopv/es/bopv2/datos/2026/10/2604506a.shtml")
        self.assertEqual(hoy[0]["uid"], "BOPV:2604506a")
        self.assertIn("Gobernanza", hoy[0]["departamento"])
        self.assertIn("Analistas", res[dt.date(2026, 10, 26)][0]["titulo"])


class TArticulo(unittest.TestCase):
    def test_extraer_por_id(self):
        from oporadar.util import extraer_por_id, html_to_text
        h = ('<html><div id="menu">menu</div><div id="bopa-articulo"><h4>AUTORIDADES</h4><div><p>Texto <br> de la '
             'plaza</p></div><img src=x></div><script>Liferay.Portlet.onLoad()</script><div>pie</div></html>')
        t = html_to_text(extraer_por_id(h, "bopa-articulo"))
        self.assertIn("plaza", t)
        self.assertNotIn("Liferay", t)
        self.assertNotIn("pie", t)
        self.assertNotIn("menu", t)


class TCharset(unittest.TestCase):
    def test_latin1(self):
        from oporadar.util import decodificar
        b = '<meta charset="ISO-8859-1"><p>Técnico Informático</p>'.encode("latin-1")
        self.assertIn("Informático", decodificar(b, "text/html"))
        self.assertIn("Informático", decodificar("Técnico Informático".encode("latin-1"), ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
