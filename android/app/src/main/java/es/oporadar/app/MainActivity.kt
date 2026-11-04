package es.oporadar.app

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

/**
 * La app es una ventana a la web que sirve la Pi (misma interfaz que en el navegador) más el aviso
 * en segundo plano. Así cualquier mejora en el servidor llega al móvil sin recompilar la APK.
 */
class MainActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var prefs: Prefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        Avisos.crearCanales(this)
        window.statusBarColor = Color.parseColor("#0F1720")

        web = WebView(this).apply {
            layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.setSupportMultipleWindows(false)
            addJavascriptInterface(Puente(), "Android")
            webViewClient = Cliente()
            webChromeClient = WebChromeClient()  // necesario para que funcionen alert/confirm/prompt de la web
        }
        setContentView(web)

        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }

        if (prefs.configurado()) {
            Comprobador.programar(this)
            cargar(intent)
        } else {
            web.loadDataWithBaseURL(null, paginaInicio(), "text/html", "utf-8", null)
            ajustes()
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (prefs.configurado()) cargar(intent)
    }

    private fun cargar(i: Intent?) {
        val a = i?.getStringExtra("ancla") ?: ""
        val tok = if (prefs.token.isNotBlank()) "?token=" + Uri.encode(prefs.token) else ""
        val ancla = if (a.isNotBlank()) "#$a" else ""
        web.loadUrl(prefs.servidor + "/" + tok + ancla)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    // ------------------------------------------------------------------ ajustes
    private fun ajustes() {
        val pad = (16 * resources.displayMetrics.density).toInt()
        val caja = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad / 2, pad, 0)
        }
        fun etiqueta(t: String) = TextView(this).apply { text = t; setPadding(0, pad / 2, 0, 0) }
        val url = EditText(this).apply {
            hint = "http://homelab2:8790"
            setText(prefs.servidor.ifBlank { "http://homelab2:8790" })
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setSingleLine(true)
        }
        val token = EditText(this).apply {
            hint = "(vacío si no pusiste token)"
            setText(prefs.token)
            setSingleLine(true)
        }
        val minutos = EditText(this).apply {
            setText(prefs.minutos.toString())
            inputType = InputType.TYPE_CLASS_NUMBER
            setSingleLine(true)
        }
        val estado = TextView(this).apply {
            text = "Última comprobación: " + prefs.ultimaConsulta.ifBlank { "—" }
            setPadding(0, pad / 2, 0, 0)
            alpha = 0.7f
        }
        caja.addView(etiqueta("Servidor en la Raspberry (por Tailscale)"))
        caja.addView(url)
        caja.addView(etiqueta("Token"))
        caja.addView(token)
        caja.addView(etiqueta("Comprobar avisos cada (minutos, mínimo 15)"))
        caja.addView(minutos)
        caja.addView(estado)

        val d = AlertDialog.Builder(this)
            .setTitle("OpoRadar")
            .setView(caja)
            .setPositiveButton("Guardar", null)
            .setNeutralButton("Probar aviso", null)
            .setNegativeButton("Cerrar", null)
            .create()
        d.setOnShowListener {
            d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val u = url.text.toString().trim().let { if (it.startsWith("http")) it else "http://$it" }
                prefs.servidor = u
                prefs.token = token.text.toString()
                prefs.minutos = (minutos.text.toString().toIntOrNull() ?: 30).coerceAtLeast(15)
                comprobarConexion(d)
            }
            d.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
                Avisos.prueba(this)
                Comprobador.ahora(this)
            }
        }
        d.show()
    }

    private fun comprobarConexion(d: AlertDialog) {
        Thread {
            val r = try {
                val j = Comprobador.get(prefs.servidor + "/api/estado", prefs.token)
                "OK · servidor " + j.optString("version")
            } catch (e: Exception) {
                "ERROR: " + (e.message ?: e.javaClass.simpleName)
            }
            runOnUiThread {
                if (r.startsWith("OK")) {
                    Toast.makeText(this, "Conectado ($r)", Toast.LENGTH_SHORT).show()
                    Comprobador.programar(this, reemplazar = true)
                    d.dismiss()
                    cargar(null)
                } else {
                    Toast.makeText(this, "No llego a la Pi. ¿Tailscale activo? $r", Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    // ------------------------------------------------------------------ web
    inner class Puente {
        @JavascriptInterface
        fun openSettings() = runOnUiThread { ajustes() }

        @JavascriptInterface
        fun checkNow() = runOnUiThread { Comprobador.ahora(this@MainActivity) }
    }

    inner class Cliente : WebViewClient() {
        override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest): Boolean {
            val host = Uri.parse(prefs.servidor).host
            if (req.url.host == host) return false
            // enlaces al BOE/BOC/PDF: en el navegador del móvil
            try { startActivity(Intent(Intent.ACTION_VIEW, req.url)) } catch (e: Exception) { }
            return true
        }

        override fun onReceivedError(view: WebView, req: WebResourceRequest, err: WebResourceError) {
            if (req.isForMainFrame) {
                view.loadDataWithBaseURL(null, paginaError(err.description?.toString() ?: ""), "text/html", "utf-8", null)
            }
        }
    }

    private fun paginaInicio() = """
        <html><body style="font-family:sans-serif;background:#0f1720;color:#e8e4da;padding:28px">
        <h2>Opo<span style="color:#f07a3c">Radar</span></h2>
        <p>Pon la dirección del servidor de tu Raspberry (por Tailscale), p. ej. <b>http://homelab2:8790</b>.</p>
        <button onclick="Android.openSettings()" style="padding:10px 16px;border-radius:10px;border:0">Ajustes</button>
        </body></html>""".trimIndent()

    private fun paginaError(msg: String) = """
        <html><body style="font-family:sans-serif;background:#0f1720;color:#e8e4da;padding:28px">
        <h2>No llego a la Raspberry</h2>
        <p style="opacity:.75">$msg</p>
        <p>Comprueba que Tailscale está activo en el móvil y que el servicio <code>oporadar</code> corre en la Pi.</p>
        <button onclick="location.href='${prefs.servidor}/'" style="padding:10px 16px;border-radius:10px;border:0">Reintentar</button>
        <button onclick="Android.openSettings()" style="padding:10px 16px;border-radius:10px;border:0">Ajustes</button>
        </body></html>""".trimIndent()
}
