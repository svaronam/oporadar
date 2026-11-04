package es.oporadar.app

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.Color
import org.json.JSONObject

/** Notificaciones nativas con tres canales según la importancia (los puedes ajustar en Ajustes de Android). */
object Avisos {
    const val CANAL_PRIORITARIA = "prioritaria"
    const val CANAL_INTERESANTE = "interesante"
    const val CANAL_VIGILAR = "vigilar"
    const val CANAL_RESUMEN = "resumen"
    const val CANAL_APUNTADO = "apuntado"
    const val CANAL_ESTADO = "estado"

    fun crearCanales(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CANAL_PRIORITARIA, "Prioritarias (≥75)",
            NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Oposiciones de informática muy alineadas contigo: suena y aparece arriba"
            enableLights(true); lightColor = Color.parseColor("#C2410C"); enableVibration(true)
        })
        nm.createNotificationChannel(NotificationChannel(CANAL_INTERESANTE, "Interesantes (55-74)",
            NotificationManager.IMPORTANCE_DEFAULT).apply { description = "Merecen un vistazo" })
        nm.createNotificationChannel(NotificationChannel(CANAL_VIGILAR, "A vigilar (35-54)",
            NotificationManager.IMPORTANCE_LOW).apply { description = "Sin sonido" })
        nm.createNotificationChannel(NotificationChannel(CANAL_APUNTADO, "📌 Mis convocatorias",
            NotificationManager.IMPORTANCE_HIGH).apply {
            description = "Documentos y avisos nuevos de las convocatorias en las que estás apuntado"
            enableVibration(true)
        })
        nm.createNotificationChannel(NotificationChannel(CANAL_ESTADO, "⚠ Estado del radar",
            NotificationManager.IMPORTANCE_DEFAULT).apply {
            description = "Si un boletín deja de responder o su web cambia y el radar podría perderse convocatorias"
        })
        nm.createNotificationChannel(NotificationChannel(CANAL_RESUMEN, "Resúmenes",
            NotificationManager.IMPORTANCE_LOW).apply { description = "Cuando llegan muchas a la vez" })
    }

    private fun abrir(ctx: Context, itemId: Long, ancla: String = if (itemId > 0) "item-$itemId" else ""): PendingIntent {
        val i = Intent(ctx, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("ancla", ancla)
        }
        return PendingIntent.getActivity(ctx, ancla.hashCode(), i,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    /** Documento o anuncio nuevo de una convocatoria apuntada: "📌 A2 · Técnico Informático · Tarazona". */
    fun novedad(ctx: Context, n: JSONObject) {
        val itemId = n.optLong("item_id")
        val grupos = n.optString("grupos").takeIf { it.isNotBlank() && it != "null" }?.replace(",", "/")
        val cab = listOfNotNull(grupos, n.optString("puesto").takeIf { it.isNotBlank() && it != "null" },
            n.optString("lugar").takeIf { it.isNotBlank() && it != "null" }).joinToString(" · ")
        val origen = when (n.optString("origen")) { "web" -> "Nuevo documento"; "BOE" -> "Nuevo en el BOE"; "BOC" -> "Nuevo en el BOC"; else -> "Novedad" }
        val nt = Notification.Builder(ctx, CANAL_APUNTADO)
            .setSmallIcon(R.drawable.ic_stat)
            .setColor(Color.parseColor("#7C3AED"))
            .setContentTitle("📌 ${cab.ifBlank { n.optString("organismo") }}")
            .setContentText("$origen: ${n.optString("titulo")}")
            .setStyle(Notification.BigTextStyle().bigText("$origen:\n${n.optString("titulo")}"))
            .setAutoCancel(true)
            .setGroup("oporadar-apuntado")
            .setContentIntent(abrir(ctx, itemId, "apuntado-$itemId"))
            .build()
        ctx.getSystemService(NotificationManager::class.java).notify(500000 + n.optInt("id"), nt)
    }

    fun alerta(ctx: Context, a: JSONObject) {
        val nt = Notification.Builder(ctx, CANAL_ESTADO)
            .setSmallIcon(R.drawable.ic_stat)
            .setColor(Color.parseColor("#B7791F"))
            .setContentTitle("⚠ OpoRadar · ${a.optString("fuente")}")
            .setContentText(a.optString("texto"))
            .setStyle(Notification.BigTextStyle().bigText(a.optString("texto")))
            .setAutoCancel(true)
            .setContentIntent(abrir(ctx, 0, ""))
            .build()
        ctx.getSystemService(NotificationManager::class.java).notify(900000 + a.optInt("id"), nt)
    }

    fun resumenNovedades(ctx: Context, total: Int) {
        val nt = Notification.Builder(ctx, CANAL_APUNTADO)
            .setSmallIcon(R.drawable.ic_stat)
            .setContentTitle("📌 $total novedades en tus convocatorias")
            .setContentText("Toca para verlas")
            .setAutoCancel(true)
            .setGroup("oporadar-apuntado")
            .setGroupSummary(true)
            .setContentIntent(abrir(ctx, 0, "apuntado"))
            .build()
        ctx.getSystemService(NotificationManager::class.java).notify(3, nt)
    }

    private val ZONA = mapOf("cantabria" to "Cantabria", "limitrofe" to "Limítrofe", "estatal" to "Estatal",
        "cercana" to "Norte", "resto" to "Resto", "desconocida" to "Zona ?")
    private val SIS = mapOf("oposicion" to "Oposición", "concurso-oposicion" to "Concurso-oposición", "concurso" to "Concurso")
    private val VIN = mapOf("funcionario" to "Funcionario", "laboral" to "Laboral fijo", "temporal" to "Temporal")

    fun item(ctx: Context, it: JSONObject) {
        val id = it.getLong("id")
        val nivel = it.optString("nivel")
        val canal = when (nivel) {
            "prioritaria" -> CANAL_PRIORITARIA
            "interesante" -> CANAL_INTERESANTE
            else -> CANAL_VIGILAR
        }
        val emoji = when (nivel) { "prioritaria" -> "🔴"; "interesante" -> "🟠"; else -> "🔵" }
        val org = it.optString("organismo").ifBlank { it.optString("departamento") }
        val grupos = it.optJSONArray("grupos")?.let { a -> (0 until a.length()).joinToString("/") { a.getString(it) } } ?: ""
        val etiquetas = listOfNotNull(
            ZONA[it.optString("zona")],
            SIS[it.optString("sistema")],
            VIN[it.optString("vinculo")],
            grupos.ifBlank { null },
            if (it.optString("tipo") == "oep") "Oferta de empleo" else null,
        ).joinToString(" · ")
        val plazo = it.optString("plazo_txt").let { p ->
            if (p.isBlank() || p == "null") "" else {
                val fin = it.optString("plazo_fin")
                "\n⏳ $p" + if (fin.isNotBlank() && fin != "null") " · hasta $fin" else ""
            }
        }
        val detalle = it.optString("detalle").takeIf { d -> d.isNotBlank() && d != "null" } ?: it.optString("titulo")
        val color = when (nivel) { "prioritaria" -> "#C2410C"; "interesante" -> "#B7791F"; else -> "#2F6F9F" }

        val n = Notification.Builder(ctx, canal)
            .setSmallIcon(R.drawable.ic_stat)
            .setColor(Color.parseColor(color))
            .setContentTitle("$emoji ${it.optInt("score")} · $org")
            .setContentText(etiquetas)
            .setStyle(Notification.BigTextStyle().bigText("$etiquetas$plazo\n\n$detalle"))
            .setSubText(it.optString("fuente"))
            .setAutoCancel(true)
            .setGroup("oporadar")
            .setContentIntent(abrir(ctx, id))
            .build()
        ctx.getSystemService(NotificationManager::class.java).notify((id + 1000).toInt(), n)
    }

    fun resumen(ctx: Context, total: Int, prioritarias: Int) {
        val n = Notification.Builder(ctx, CANAL_RESUMEN)
            .setSmallIcon(R.drawable.ic_stat)
            .setContentTitle("$total oposiciones nuevas de informática")
            .setContentText(if (prioritarias > 0) "$prioritarias prioritarias · toca para verlas" else "Toca para verlas")
            .setAutoCancel(true)
            .setGroup("oporadar")
            .setGroupSummary(true)
            .setContentIntent(abrir(ctx, 0))
            .build()
        ctx.getSystemService(NotificationManager::class.java).notify(1, n)
    }

    fun prueba(ctx: Context) {
        val n = Notification.Builder(ctx, CANAL_PRIORITARIA)
            .setSmallIcon(R.drawable.ic_stat)
            .setColor(Color.parseColor("#C2410C"))
            .setContentTitle("🔴 100 · Notificación de prueba")
            .setContentText("Cantabria · Oposición · Funcionario · A2")
            .setAutoCancel(true)
            .setContentIntent(abrir(ctx, 0))
            .build()
        ctx.getSystemService(NotificationManager::class.java).notify(2, n)
    }
}
