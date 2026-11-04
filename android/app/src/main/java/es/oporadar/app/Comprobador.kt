package es.oporadar.app

import android.content.Context
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.Worker
import androidx.work.WorkerParameters
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * Cada X minutos pregunta a la Pi (por Tailscale) si hay anuncios nuevos desde el último que vio
 * y lanza una notificación por cada uno. Si la Pi no responde (Tailscale apagado, sin red...) no pasa nada:
 * lo intentará en la siguiente vuelta y no se pierde ninguno, porque el servidor guarda el histórico.
 */
class Comprobador(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        val p = Prefs(applicationContext)
        if (!p.configurado()) return Result.success()
        return try {
            val json = get("${p.servidor}/api/nuevas?desde=${p.ultimoId}&desde_nov=${p.ultimoNovId}&desde_alerta=${p.ultimaAlertaId}", p.token)

            // 0) alertas de funcionamiento del radar (una fuente no responde o su web ha cambiado)
            val als = json.optJSONArray("alertas")
            if (p.ultimaAlertaId >= 0 && als != null) {
                for (i in 0 until minOf(als.length(), 5)) Avisos.alerta(applicationContext, als.getJSONObject(i))
            }
            p.ultimaAlertaId = maxOf(p.ultimaAlertaId, json.optLong("max_alerta", 0))

            // 1) novedades de convocatorias en las que estás apuntado: siempre una notificación por cada una
            val novs = json.optJSONArray("novedades")
            val maxNov = json.optLong("max_nov", 0)
            val nn = novs?.length() ?: 0
            if (p.ultimoNovId >= 0) {
                for (i in 0 until minOf(nn, 10)) Avisos.novedad(applicationContext, novs!!.getJSONObject(i))
                if (nn > 10) Avisos.resumenNovedades(applicationContext, nn)
            }
            val ultimaNov = if (nn > 0) novs!!.getJSONObject(nn - 1).optLong("id") else maxNov
            p.ultimoNovId = if (nn >= 50) ultimaNov else maxOf(maxNov, ultimaNov)

            // 2) anuncios nuevos del radar
            val items = json.optJSONArray("items")
            val maxId = json.optLong("max_id", 0)
            val n = items?.length() ?: 0
            if (p.ultimoId >= 0 && n > 0) {
                var prioritarias = 0
                val lista = (0 until n).map { items!!.getJSONObject(it) }
                lista.forEach { if (it.optString("nivel") == "prioritaria") prioritarias++ }
                if (n <= 6) {
                    lista.forEach { Avisos.item(applicationContext, it) }
                } else {
                    // muchas de golpe (p. ej. tras rellenar el último mes): resumen + sólo las mejores
                    lista.sortedByDescending { it.optInt("score") }.take(4).forEach { Avisos.item(applicationContext, it) }
                }
                if (n > 1) Avisos.resumen(applicationContext, n, prioritarias)
            }
            // si vinieron 50 (el máximo por consulta) quedan más: avanzamos sólo hasta la última recibida
            val ultimaRecibida = if (n > 0) items!!.getJSONObject(n - 1).optLong("id") else maxId
            p.ultimoId = if (n >= 50) ultimaRecibida else maxOf(maxId, ultimaRecibida)
            p.ultimaConsulta = "OK " + SimpleDateFormat("dd/MM HH:mm", Locale("es")).format(Date()) + " · $n anuncios, $nn de tus convocatorias"
            Result.success()
        } catch (e: Exception) {
            p.ultimaConsulta = "Sin conexión " + SimpleDateFormat("dd/MM HH:mm", Locale("es")).format(Date()) +
                " · ${e.javaClass.simpleName}"
            Result.success()
        }
    }

    companion object {
        private const val NOMBRE = "oporadar-comprobar"

        fun get(url: String, token: String): JSONObject {
            val c = URL(url).openConnection() as HttpURLConnection
            c.connectTimeout = 15000
            c.readTimeout = 20000
            if (token.isNotBlank()) c.setRequestProperty("X-Token", token)
            try {
                if (c.responseCode == 401) throw IllegalStateException("Token incorrecto")
                return JSONObject(c.inputStream.bufferedReader().use { it.readText() })
            } finally {
                c.disconnect()
            }
        }

        fun programar(ctx: Context, reemplazar: Boolean = false) {
            val min = Prefs(ctx).minutos.coerceAtLeast(15).toLong()
            val req = PeriodicWorkRequestBuilder<Comprobador>(min, TimeUnit.MINUTES)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(ctx).enqueueUniquePeriodicWork(
                NOMBRE,
                if (reemplazar) ExistingPeriodicWorkPolicy.UPDATE else ExistingPeriodicWorkPolicy.KEEP,
                req)
        }

        fun ahora(ctx: Context) {
            WorkManager.getInstance(ctx).enqueue(OneTimeWorkRequestBuilder<Comprobador>().build())
        }
    }
}
