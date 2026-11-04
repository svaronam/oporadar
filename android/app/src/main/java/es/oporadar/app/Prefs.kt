package es.oporadar.app

import android.content.Context

/** Ajustes guardados en el móvil: dirección del servidor en la Pi, token y último anuncio notificado. */
class Prefs(ctx: Context) {
    private val sp = ctx.getSharedPreferences("oporadar", Context.MODE_PRIVATE)

    var servidor: String
        get() = sp.getString("servidor", "") ?: ""
        set(v) = sp.edit().putString("servidor", v.trim().trimEnd('/')).apply()

    var token: String
        get() = sp.getString("token", "") ?: ""
        set(v) = sp.edit().putString("token", v.trim()).apply()

    /** -1 = nunca ha consultado (la primera vez no notifica el histórico). */
    var ultimoId: Long
        get() = sp.getLong("ultimo_id", -1L)
        set(v) = sp.edit().putLong("ultimo_id", v).apply()

    /** Último documento/aviso de convocatorias apuntadas que se ha notificado (-1 = nunca). */
    var ultimoNovId: Long
        get() = sp.getLong("ultimo_nov_id", -1L)
        set(v) = sp.edit().putLong("ultimo_nov_id", v).apply()

    /** Última alerta de funcionamiento (fuente caída, web cambiada) notificada (-1 = nunca). */
    var ultimaAlertaId: Long
        get() = sp.getLong("ultima_alerta_id", -1L)
        set(v) = sp.edit().putLong("ultima_alerta_id", v).apply()

    var minutos: Int
        get() = sp.getInt("minutos", 30)
        set(v) = sp.edit().putInt("minutos", v).apply()

    var ultimaConsulta: String
        get() = sp.getString("ultima_consulta", "") ?: ""
        set(v) = sp.edit().putString("ultima_consulta", v).apply()

    fun configurado() = servidor.startsWith("http")
}
