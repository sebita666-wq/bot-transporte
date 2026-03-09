from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import pytz
import re
import json
import os
import traceback

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=3)

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================
os.environ['TZ'] = 'America/Argentina/Buenos_Aires'
try:
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
except:
    timezone = pytz.timezone('America/Argentina/Cordoba')

print("🚀 BOT INICIADO - VERSIÓN FINAL CON R10/R18 DIFERENCIADAS")

NUMERO_DUENIO = os.environ.get('NUMERO_DUENIO', "whatsapp:+5493434727811")
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_para_sesiones')
STATS_FILE = 'estadisticas.json'

app.secret_key = SECRET_KEY

def ahora_argentina():
    return datetime.now(timezone)

# ============================================
# FERIADOS NACIONALES 2026
# ============================================
FERIADOS_NACIONALES = [
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-03-24", "2026-04-02",
    "2026-04-03", "2026-05-01", "2026-05-25", "2026-06-15", "2026-06-20",
    "2026-07-09", "2026-08-17", "2026-10-12", "2026-11-23", "2026-12-08",
    "2026-12-25"
]

def es_feriado_nacional(fecha):
    return fecha.strftime("%Y-%m-%d") in FERIADOS_NACIONALES

def obtener_tipo_dia(fecha):
    if es_feriado_nacional(fecha):
        return "domingos"
    if fecha.weekday() < 5:
        return "habiles"
    elif fecha.weekday() == 5:
        return "sabados"
    else:
        return "domingos"

# ============================================
# HORARIOS - DÍAS HÁBILES
# ============================================

horarios_habiles = [
    # Parana → Viale
    {"origen": "Parana", "destino": "Viale", "hora": "04:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "05:35", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "08:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "10:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "12:15", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "13:05", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "14:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "15:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "17:15", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "18:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "19:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "20:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora": "23:00", "ruta": "R18"},
    
    # Viale → Parana
    {"origen": "Viale", "destino": "Parana", "hora": "05:10", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "06:05", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "07:20", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "08:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "10:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "10:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "12:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "13:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "15:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "17:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "19:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "21:10", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "00:30", "ruta": "R18"},
    
    # Parana → Maria Grande (R10)
    {"origen": "Parana", "destino": "Maria Grande", "hora": "07:45", "ruta": "R10"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "10:15", "ruta": "R10"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "16:30", "ruta": "R10"},
    
    # Parana → Maria Grande (R18)
    {"origen": "Parana", "destino": "Maria Grande", "hora": "04:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "12:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "17:15", "ruta": "R18"},
    
    # Maria Grande → Parana (R10)
    {"origen": "Maria Grande", "destino": "Parana", "hora": "06:45", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Parana", "hora": "14:50", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Parana", "hora": "19:15", "ruta": "R10"},
    
    # Maria Grande → Parana (R18)
    {"origen": "Maria Grande", "destino": "Parana", "hora": "15:05", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora": "19:25", "ruta": "R18"},
    
    # Parana → Tabossi
    {"origen": "Parana", "destino": "Tabossi", "hora": "04:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "05:35", "ruta": "R18"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "08:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "12:15", "ruta": "R18"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "15:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "17:15", "ruta": "R18"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "20:45", "ruta": "R18"},
    
    # Tabossi → Parana
    {"origen": "Tabossi", "destino": "Parana", "hora": "06:20", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Parana", "hora": "07:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Parana", "hora": "08:30", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Parana", "hora": "11:55", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Parana", "hora": "14:40", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Parana", "hora": "18:25", "ruta": "R18"},
]

# ============================================
# HORARIOS - SÁBADOS (simplificados)
# ============================================
horarios_sabados = [
    {"origen": "Parana", "destino": "Viale", "hora": "07:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "08:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "09:00", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Parana", "hora": "11:00", "ruta": "R10"},
]

# ============================================
# HORARIOS - DOMINGOS (simplificados)
# ============================================
horarios_domingos = [
    {"origen": "Parana", "destino": "Viale", "hora": "08:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "09:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "10:00", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Parana", "hora": "12:00", "ruta": "R10"},
]

# ============================================
# TABLA DE PRECIOS
# ============================================
precios = {
    ("Parana", "Viale"): 6300,
    ("Viale", "Parana"): 6300,
    ("Parana", "Tabossi"): 7700,
    ("Tabossi", "Parana"): 7700,
    ("Parana", "Sosa"): 8000,
    ("Sosa", "Parana"): 8000,
    ("Parana", "Maria Grande"): 8400,
    ("Maria Grande", "Parana"): 8400,
    ("Parana", "Aldea San Antonio"): 3100,
    ("Aldea San Antonio", "Parana"): 3100,
}

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================
def hora_a_minutos(h):
    if not h: return None
    hh, mm = map(int, h.split(':'))
    return hh*60 + mm

def minutos_a_hora(m):
    if not m: return ""
    return f"{m//60:02d}:{m%60:02d}"

def extraer_origen_destino(mensaje):
    m = mensaje.lower().strip()
    print(f"🧹 Mensaje: '{m}'")
    
    if "de " in m and " a " in m:
        partes = m.split("de ", 1)
        resto = partes[1]
        partes2 = resto.split(" a ")
        if len(partes2) == 2:
            origen = partes2[0].strip()
            destino = partes2[1].strip()
            localidades = ["parana", "viale", "tabossi", "sosa", "maria grande", "aldea san antonio"]
            if origen in localidades and destino in localidades:
                return origen.title(), destino.title()
    return None, None

def detectar_intencion(m):
    ml = m.lower()
    if any(p in ml for p in ["primer", "primero"]): return "primer"
    if any(p in ml for p in ["próximo", "proximo", "siguiente"]): return "proximo"
    if any(p in ml for p in ["último", "ultimo", "final"]): return "ultimo"
    return None

def extraer_hora_limite(m):
    patrones = [
        r'(?:después|despues|a partir)\s+de\s+las?\s*(\d{1,2})(?::(\d{2}))?',
        r'(\d{1,2})(?::(\d{2}))?\s*(?:en adelante|para adelante|hacia adelante)'
    ]
    for p in patrones:
        match = re.search(p, m.lower())
        if match:
            hora = int(match.group(1))
            minutos = int(match.group(2)) if match.group(2) else 0
            return hora*60 + minutos
    return None

def interpretar_fecha(m):
    ml = m.lower()
    hoy = ahora_argentina().replace(hour=0, minute=0, second=0, microsecond=0)
    if "mañana" in ml or "manana" in ml: return hoy + timedelta(days=1)
    if "hoy" in ml: return hoy
    return hoy

def obtener_horarios_por_dia(tipo):
    if tipo == "habiles": return horarios_habiles
    if tipo == "sabados": return horarios_sabados
    return horarios_domingos

def buscar_horarios(origen, destino, tipo, hora_limite=None):
    resultados = {"R10": [], "R18": []}
    for h in obtener_horarios_por_dia(tipo):
        if h["origen"] == origen and h["destino"] == destino:
            if hora_limite is None or hora_a_minutos(h["hora"]) >= hora_limite:
                resultados[h["ruta"]].append(h["hora"])
    for r in resultados:
        resultados[r].sort(key=hora_a_minutos)
    return resultados

def formatear_horarios(resultados, origen, destino, fecha_str):
    if not resultados["R10"] and not resultados["R18"]:
        return f"😕 No encontré servicios de {origen} a {destino} para {fecha_str}."
    texto = f"🚌 Servicios de {origen} a {destino} para {fecha_str}:\n\n"
    if resultados["R10"]:
        texto += "🛣️ *Por Ruta 10 (directo)*:\n" + "\n".join([f"• {h}" for h in resultados["R10"]]) + "\n\n"
    if resultados["R18"]:
        texto += "🛣️ *Por Ruta 18 (con paradas)*:\n" + "\n".join([f"• {h}" for h in resultados["R18"]]) + "\n\n"
    texto += "😊 ¿Necesitas precio, duración, próximo o último?"
    return texto

def obtener_precio(o, d):
    return precios.get((o, d))

# ============================================
# PREGUNTAS FRECUENTES (ACTUALIZADAS)
# ============================================
def responder_faq(mensaje):
    m = mensaje.lower()
    if any(p in m for p in ["pago", "pagar", "sube", "tarjeta", "qr", "mercadopago", "debito", "credito"]):
        return ("💳 *Medios de pago*\n\n"
                "A partir de Febrero de 2026, el único medio de pago disponible es a través de la **red SUBE**.\n"
                "Podés pagar con:\n"
                "• Tarjeta SUBE\n"
                "• Tarjeta de débito o crédito\n"
                "• Mercado Pago QR\n\n"
                "Todos los pagos se realizan en la terminal antes de subir.")
    if any(p in m for p in ["equipaje", "valija", "bulto", "maleta"]):
        return ("🧳 *Límite de equipaje*\n\n"
                "Podés llevar hasta **2 bultos por persona** con un peso máximo total de **10 kg**.\n"
                "Si necesitás llevar más, consultanos con anticipación para evaluar disponibilidad en bodega.")
    if any(p in m for p in ["mascota", "perro", "gato", "animal"]):
        return ("🐕 *Mascotas a bordo*\n\n"
                "• Mascotas pequeñas viajan **en jaula o bolso transportador**, únicamente en **bodega** (por disposición de Transporte Provincial).\n"
                "• **Perros de asistencia** viajan sin restricciones.\n"
                "• No se permiten mascotas sueltas en el interior del colectivo.")
    if any(p in m for p in ["perdi", "objeto", "olvide", "cartera", "celular", "llaves"]):
        return ("📞 *Objetos perdidos*\n\n"
                "Si perdiste algo en un colectivo, comunicate al 📱 **343 456-7890** o acercate a nuestra empresa en:\n"
                "📍 **Guetto de Varsovia 211, Paraná** (Empresa Grupo ERSA)\n\n"
                "Tené a mano el día y horario del viaje para ayudarte a ubicarlo.")
    if any(p in m for p in ["descuento", "estudiante", "jubilado", "beneficio"]):
        return ("👨‍🎓 *Descuentos*\n\n"
                "El descuento lo aplica directamente el **sistema SUBE**.\n"
                "Nosotros no podemos gestionar ningún tipo de descuento. Solo aquellas personas que tengan el beneficio activado en su tarjeta SUBE podrán acceder a la tarifa reducida.")
    if any(p in m for p in ["niño", "nene", "bebe", "menor"]):
        return ("👶 *Menores*\n\n"
                "• **Menores de 5 años** que viajen en el regazo de un adulto abonan un **seguro mínimo**.\n"
                "• **A partir de los 5 años**, deben pagar pasaje completo.")
    if any(p in m for p in ["asiento", "sentarme", "lugar", "elegir"]):
        return ("🪑 *Asignación de asientos*\n\n"
                "La asignación de asientos es **por orden de llegada**.\n"
                "Si necesitás un lugar especial (ej. cerca de la puerta por movilidad reducida), avisale al chofer al subir.")
    if any(p in m for p in ["reclamo", "problema", "queja", "sugerencia"]):
        return ("🚌 *Reclamos y sugerencias*\n\n"
                "Podés acercarte a cualquiera de nuestras terminales o escribirnos a este mismo WhatsApp.\n"
                "Tu opinión nos ayuda a mejorar.")
    return None

# ============================================
# FUNCIONES DE RESPUESTA
# ============================================
def mostrar_menu():
    return ("👋 Hola, soy el asistente de transporte.\n\n"
            "Elegí una opción o escribí directamente:\n"
            "1️⃣ Ver horarios\n"
            "2️⃣ Consultar precios\n"
            "3️⃣ Información útil\n"
            "4️⃣ Preguntas frecuentes\n\n"
            "Ej: 'De Parana a Viale', 'Primer colectivo de Parana a Viale mañana'")

def preguntar_origen_destino(tipo):
    return f"📝 Decime de dónde a dónde querés viajar (ej: De Viale a Parana)"

def mostrar_info_util():
    return ("📌 *Información útil*\n\n"
            "📍 Terminal Paraná: Av. Ramírez 1200\n"
            "📍 Terminal María Grande: San Martín 450\n"
            "📞 Teléfono: 343 456-7890")

def mostrar_faq():
    return ("❓ *Preguntas frecuentes*\n\n"
            "Escribí una palabra clave como 'pago', 'equipaje', 'mascota', 'objetos perdidos', 'descuento', 'niños', 'asiento' o 'reclamo'.")

def despedida():
    return "😊 ¡Gracias por consultar! Escribime 'Hola' para empezar de nuevo."

def no_entendido():
    return "🤔 No entendí. Probá con 'Hola', 'De Parana a Viale' o 'Precio de Parana a Viale'."

def resetear_contexto(sender):
    session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}

# ============================================
# ESTADÍSTICAS (SIMPLIFICADAS)
# ============================================
def cargar_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {"usuarios": {}, "metricas": {"total_usuarios_unicos": 0, "total_mensajes": 0, "ultimo_reinicio": ahora_argentina().strftime("%Y-%m-%d %H:%M:%S")}}

def guardar_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def registrar_interaccion(sender, mensaje, tipo=None):
    stats = cargar_stats()
    ahora = ahora_argentina().strftime("%Y-%m-%d %H:%M:%S")
    if sender not in stats["usuarios"]:
        stats["usuarios"][sender] = {"primer_contacto": ahora, "ultimo_contacto": ahora, "mensajes": 1, "consultas": [tipo] if tipo else []}
        stats["metricas"]["total_usuarios_unicos"] += 1
    else:
        stats["usuarios"][sender]["ultimo_contacto"] = ahora
        stats["usuarios"][sender]["mensajes"] += 1
        if tipo and tipo not in stats["usuarios"][sender]["consultas"]:
            stats["usuarios"][sender]["consultas"].append(tipo)
    stats["metricas"]["total_mensajes"] += 1
    guardar_stats(stats)

def resumen_stats():
    stats = cargar_stats()
    ahora = ahora_argentina()
    hoy = ahora.strftime("%Y-%m-%d")
    semana = (ahora - timedelta(days=7)).strftime("%Y-%m-%d")
    return {
        "total_usuarios": stats["metricas"]["total_usuarios_unicos"],
        "total_mensajes": stats["metricas"]["total_mensajes"],
        "usuarios_hoy": sum(1 for u in stats["usuarios"].values() if u["ultimo_contacto"].startswith(hoy)),
        "usuarios_semana": sum(1 for u in stats["usuarios"].values() if u["ultimo_contacto"][:10] >= semana),
    }

# ============================================
# WEBHOOK PRINCIPAL
# ============================================
@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    try:
        incoming_msg = request.values.get('Body', '').strip()
        sender = request.values.get('From', '')
        print(f"\n📩 Mensaje de {sender}: {incoming_msg}")

        resp = MessagingResponse()
        msg = resp.message()
        registrar_interaccion(sender, incoming_msg)

        if sender not in session:
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
        ctx = session[sender]

        # Comando dueño
        if incoming_msg.lower() == "/estadisticas" and sender == NUMERO_DUENIO:
            r = resumen_stats()
            msg.body(f"📊 Estadísticas\n👥 Usuarios: {r['total_usuarios']}\n💬 Mensajes: {r['total_mensajes']}\n📅 Hoy: {r['usuarios_hoy']}\n📆 Semana: {r['usuarios_semana']}")
            return str(resp)

        # Despedida
        if any(p in incoming_msg.lower() for p in ["chau", "adiós", "adios", "bye"]):
            resetear_contexto(sender)
            msg.body(despedida())
            return str(resp)
        if "gracias" in incoming_msg.lower():
            resetear_contexto(sender)
            msg.body(despedida())
            return str(resp)

        # FAQ
        faq = responder_faq(incoming_msg)
        if faq:
            msg.body(faq)
            return str(resp)

        # Opciones numéricas
        if incoming_msg == "1":
            resetear_contexto(sender)
            ctx["estado"] = "esperando_origen_horarios"
            msg.body(preguntar_origen_destino("horarios"))
            return str(resp)
        if incoming_msg == "2":
            resetear_contexto(sender)
            ctx["estado"] = "esperando_origen_precios"
            msg.body(preguntar_origen_destino("precios"))
            return str(resp)
        if incoming_msg == "3":
            msg.body(mostrar_info_util())
            return str(resp)
        if incoming_msg == "4":
            msg.body(mostrar_faq())
            return str(resp)

        # Saludo
        if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes", "ayuda"]:
            msg.body(mostrar_menu())
            return str(resp)

        # Detectar intención y fecha
        intencion = detectar_intencion(incoming_msg)
        fecha = interpretar_fecha(incoming_msg)
        origen, destino = extraer_origen_destino(incoming_msg)

        if origen and destino:
            tipo_dia = obtener_tipo_dia(fecha)
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
                precio = obtener_precio(origen, destino)
                msg.body(f"💰 El pasaje de {origen} a {destino} cuesta ${precio}" if precio else f"😕 No tengo precio de {origen} a {destino}")
            else:
                hora_limite = extraer_hora_limite(incoming_msg) if not intencion else None
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_limite)
                fecha_str = fecha.strftime("%d/%m/%Y")
                msg.body(formatear_horarios(resultados, origen, destino, fecha_str))
            ctx["ultimo_origen"], ctx["ultimo_destino"] = origen, destino
            ctx["fecha_pendiente"] = fecha
            return str(resp)

        # Intención sin origen/destino
        if intencion and not origen:
            if ctx.get("fecha_pendiente"):
                fecha = ctx["fecha_pendiente"]
            ctx["estado"] = "esperando_origen_horarios"
            ctx["intencion"] = intencion
            ctx["fecha_pendiente"] = fecha
            msg.body("📝 Decime de dónde a dónde querés viajar")
            return str(resp)

        # Consulta sin contexto
        if not ctx["ultimo_origen"]:
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$", "próximo", "proximo", "último", "ultimo", "primer"]):
                msg.body("📝 Primero decime de dónde a dónde querés viajar. Ej: 'De Viale a Parana'")
                return str(resp)

        # Seguimiento con contexto
        if ctx["ultimo_origen"] and ctx["ultimo_destino"]:
            o, d = ctx["ultimo_origen"], ctx["ultimo_destino"]
            tipo_dia = obtener_tipo_dia(ahora_argentina())
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
                precio = obtener_precio(o, d)
                msg.body(f"💰 El pasaje de {o} a {d} cuesta ${precio}" if precio else f"😕 No tengo precio de {o} a {d}")
                return str(resp)

        msg.body(no_entendido())
        return str(resp)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
        resp = MessagingResponse()
        msg = resp.message()
        msg.body("⚠️ Ocurrió un error. Por favor, intentá de nuevo.")
        return str(resp)

# ============================================
# INICIO
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Bot listo en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
