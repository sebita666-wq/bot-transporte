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

print("🚀 BOT INICIADO - VERSIÓN COMPLETA (SOSA, SÁBADOS, DOMINGOS)")

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
        print(f"📅 FERIADO: {fecha.strftime('%d/%m/%Y')} → se trata como domingo")
        return "domingos"
    if fecha.weekday() < 5:
        return "habiles"
    elif fecha.weekday() == 5:
        return "sabados"
    else:
        return "domingos"

# ============================================
# HORARIOS - DÍAS HÁBILES (COMPLETOS)
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
    
    # Parana → Sosa
    {"origen": "Parana", "destino": "Sosa", "hora": "04:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Sosa", "hora": "12:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Sosa", "hora": "13:05", "ruta": "R18"},
    {"origen": "Parana", "destino": "Sosa", "hora": "16:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Sosa", "hora": "17:15", "ruta": "R18"},
    {"origen": "Parana", "destino": "Sosa", "hora": "20:45", "ruta": "R18"},
    
    # Sosa → Parana
    {"origen": "Sosa", "destino": "Parana", "hora": "06:25", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "11:55", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "14:30", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "14:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "18:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "18:55", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "22:25", "ruta": "R18"},
    
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
    
    # Viale → Tabossi
    {"origen": "Viale", "destino": "Tabossi", "hora": "05:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "06:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "09:55", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "14:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "16:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "18:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "21:55", "ruta": "R18"},
    
    # Tabossi → Viale
    {"origen": "Tabossi", "destino": "Viale", "hora": "04:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "05:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "07:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "10:25", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "12:35", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "17:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "23:30", "ruta": "R18"},
    
    # Viale → Sosa
    {"origen": "Viale", "destino": "Sosa", "hora": "05:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Sosa", "hora": "06:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Sosa", "hora": "13:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Sosa", "hora": "14:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Sosa", "hora": "16:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Sosa", "hora": "18:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Sosa", "hora": "21:55", "ruta": "R18"},
    
    # Sosa → Viale
    {"origen": "Sosa", "destino": "Viale", "hora": "06:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Viale", "hora": "09:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Viale", "hora": "12:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Viale", "hora": "18:35", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Viale", "hora": "23:15", "ruta": "R18"},
    
    # Tabossi → Sosa
    {"origen": "Tabossi", "destino": "Sosa", "hora": "06:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora": "14:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora": "14:30", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora": "18:30", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora": "22:10", "ruta": "R18"},
    
    # Sosa → Tabossi
    {"origen": "Sosa", "destino": "Tabossi", "hora": "06:25", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora": "14:30", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora": "14:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora": "18:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora": "22:30", "ruta": "R18"},
    
    # Sosa → Maria Grande
    {"origen": "Sosa", "destino": "Maria Grande", "hora": "06:25", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora": "14:30", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora": "14:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora": "18:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora": "22:30", "ruta": "R18"},
    
    # Maria Grande → Sosa
    {"origen": "Maria Grande", "destino": "Sosa", "hora": "09:25", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora": "11:55", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora": "18:15", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora": "23:00", "ruta": "R18"},
]

# ============================================
# HORARIOS - SÁBADOS (COMPLETOS)
# ============================================
horarios_sabados = [
    {"origen": "Parana", "destino": "Viale", "hora": "07:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "08:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "09:00", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Parana", "hora": "11:00", "ruta": "R10"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "10:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Parana", "hora": "12:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Sosa", "hora": "14:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "16:00", "ruta": "R18"},
]

# ============================================
# HORARIOS - DOMINGOS (COMPLETOS)
# ============================================
horarios_domingos = [
    {"origen": "Parana", "destino": "Viale", "hora": "08:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora": "09:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora": "10:00", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Parana", "hora": "12:00", "ruta": "R10"},
    {"origen": "Parana", "destino": "Tabossi", "hora": "11:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Parana", "hora": "13:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Sosa", "hora": "15:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Parana", "hora": "17:00", "ruta": "R18"},
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
    ("Viale", "Tabossi"): 1800,
    ("Tabossi", "Viale"): 1800,
    ("Viale", "Sosa"): 2100,
    ("Sosa", "Viale"): 2100,
    ("Viale", "Maria Grande"): 3400,
    ("Maria Grande", "Viale"): 3400,
    ("Tabossi", "Sosa"): 1800,
    ("Sosa", "Tabossi"): 1800,
    ("Tabossi", "Maria Grande"): 2100,
    ("Maria Grande", "Tabossi"): 2100,
    ("Sosa", "Maria Grande"): 1800,
    ("Maria Grande", "Sosa"): 1800,
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
    print(f"🔍 EXTRAYENDO de: '{m}'")
    
    # Eliminar signos de puntuación comunes
    m = re.sub(r'[¿?!¡.,;:]', '', m)
    
    # Caso: "de x a y"
    if "de " in m and " a " in m:
        partes = m.split("de ", 1)
        resto = partes[1]
        partes2 = resto.split(" a ")
        if len(partes2) == 2:
            origen = partes2[0].strip()
            destino = partes2[1].strip()
            print(f"  → Posible origen: '{origen}', destino: '{destino}'")
            
            localidades = ["parana", "viale", "tabossi", "sosa", "maria grande", "aldea san antonio"]
            if origen in localidades and destino in localidades:
                print(f"✅ EXTRAÍDO: {origen.title()} -> {destino.title()}")
                return origen.title(), destino.title()
    
    print("❌ No se pudo extraer")
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
            print(f"⏰ Hora límite: {hora:02d}:{minutos:02d}")
            return hora*60 + minutos
    return None

def interpretar_fecha(m):
    ml = m.lower()
    hoy = ahora_argentina().replace(hour=0, minute=0, second=0, microsecond=0)
    if "mañana" in ml or "manana" in ml:
        print("📅 Fecha: mañana")
        return hoy + timedelta(days=1)
    if "hoy" in ml:
        print("📅 Fecha: hoy")
        return hoy
    print("📅 Fecha: hoy (por defecto)")
    return hoy

def obtener_horarios_por_dia(tipo):
    if tipo == "habiles": return horarios_habiles
    if tipo == "sabados": return horarios_sabados
    return horarios_domingos

def buscar_horarios(origen, destino, tipo, hora_limite=None):
    print(f"🔍 Buscando {origen} → {destino} en {tipo}")
    resultados = {"R10": [], "R18": []}
    for h in obtener_horarios_por_dia(tipo):
        if h["origen"] == origen and h["destino"] == destino:
            if hora_limite is None or hora_a_minutos(h["hora"]) >= hora_limite:
                resultados[h["ruta"]].append(h["hora"])
    for r in resultados:
        resultados[r].sort(key=hora_a_minutos)
    print(f"  → R10: {len(resultados['R10'])} servicios")
    print(f"  → R18: {len(resultados['R18'])} servicios")
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
    precio = precios.get((o, d))
    print(f"💰 Precio consultado: {o}→{d} = {precio}")
    return precio

# ============================================
# PREGUNTAS FRECUENTES
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
            "Ej: 'De Parana a Viale', 'Precio de Parana a Viale'")

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
    print(f"🔄 Contexto reiniciado para {sender}")

# ============================================
# ESTADÍSTICAS
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
        print(f"📊 Nuevo usuario: {sender}")
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
        print(f"\n📩 MENSAJE RECIBIDO: '{incoming_msg}' de {sender}")

        resp = MessagingResponse()
        msg = resp.message()
        registrar_interaccion(sender, incoming_msg)

        if sender not in session:
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
            print("🆕 Nueva sesión creada")
        ctx = session[sender]
        print(f"📌 Contexto actual: {ctx}")

        # ============================================
        # COMANDO DUEÑO
        # ============================================
        if incoming_msg.lower() == "/estadisticas" and sender == NUMERO_DUENIO:
            print("✅ Comando: estadísticas")
            r = resumen_stats()
            msg.body(f"📊 Estadísticas\n👥 Usuarios: {r['total_usuarios']}\n💬 Mensajes: {r['total_mensajes']}\n📅 Hoy: {r['usuarios_hoy']}\n📆 Semana: {r['usuarios_semana']}")
            return str(resp)

        # ============================================
        # DESPEDIDA
        # ============================================
        if any(p in incoming_msg.lower() for p in ["chau", "adiós", "adios", "bye"]):
            print("✅ Despedida")
            resetear_contexto(sender)
            msg.body(despedida())
            return str(resp)
        if "gracias" in incoming_msg.lower():
            print("✅ Agradecimiento")
            resetear_contexto(sender)
            msg.body(despedida())
            return str(resp)

        # ============================================
        # FAQ
        # ============================================
        faq = responder_faq(incoming_msg)
        if faq:
            print("✅ Pregunta frecuente detectada")
            msg.body(faq)
            return str(resp)

        # ============================================
        # OPCIONES NUMÉRICAS
        # ============================================
        if incoming_msg == "1":
            print("✅ Opción 1: Horarios")
            resetear_contexto(sender)
            ctx["estado"] = "esperando_origen_horarios"
            session[sender] = ctx
            msg.body(preguntar_origen_destino("horarios"))
            return str(resp)
        if incoming_msg == "2":
            print("✅ Opción 2: Precios")
            resetear_contexto(sender)
            ctx["estado"] = "esperando_origen_precios"
            session[sender] = ctx
            msg.body(preguntar_origen_destino("precios"))
            return str(resp)
        if incoming_msg == "3":
            print("✅ Opción 3: Información útil")
            msg.body(mostrar_info_util())
            return str(resp)
        if incoming_msg == "4":
            print("✅ Opción 4: Preguntas frecuentes")
            msg.body(mostrar_faq())
            return str(resp)

        # ============================================
        # SALUDO
        # ============================================
        if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes", "ayuda"]:
            print("✅ Saludo")
            msg.body(mostrar_menu())
            return str(resp)

        # ============================================
        # PROCESAR SEGÚN ESTADO
        # ============================================
        if ctx.get("estado") == "esperando_origen_precios":
            print("🔍 Estado: esperando origen para PRECIO")
            origen, destino = extraer_origen_destino(incoming_msg)
            if origen and destino:
                precio = obtener_precio(origen, destino)
                if precio:
                    msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {origen} a {destino}.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                session[sender] = ctx
                return str(resp)
            else:
                msg.body("🤔 No entendí. Por favor, escribí algo como 'De Viale a Parana'")
                return str(resp)

        if ctx.get("estado") == "esperando_origen_horarios":
            print("🔍 Estado: esperando origen para HORARIOS")
            origen, destino = extraer_origen_destino(incoming_msg)
            if origen and destino:
                fecha = ctx.get("fecha_pendiente") or interpretar_fecha(incoming_msg)
                tipo_dia = obtener_tipo_dia(fecha)
                intencion = ctx.get("intencion")
                print(f"  → Intención pendiente: {intencion}")
                
                if intencion == "primer":
                    print("  → Buscando PRIMER colectivo")
                    resultados = buscar_horarios(origen, destino, tipo_dia)
                    if resultados["R10"] or resultados["R18"]:
                        primer_hora = "99:99"
                        primer_ruta = ""
                        if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(primer_hora):
                            primer_hora = resultados["R10"][0]
                            primer_ruta = "R10"
                        if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(primer_hora):
                            primer_hora = resultados["R18"][0]
                            primer_ruta = "R18"
                        fecha_str = fecha.strftime("%d/%m/%Y")
                        msg.body(f"🚌 El primer colectivo de {origen} a {destino} para el {fecha_str} sale a las {primer_hora} por {primer_ruta}.")
                    else:
                        msg.body(f"😕 No hay servicios de {origen} a {destino} para esa fecha.")
                
                elif intencion == "proximo":
                    print("  → Buscando PRÓXIMO colectivo")
                    ahora = ahora_argentina()
                    hora_actual_min = ahora.hour*60 + ahora.minute
                    resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual_min)
                    if resultados["R10"] or resultados["R18"]:
                        prox_hora = "99:99"
                        prox_ruta = ""
                        if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(prox_hora):
                            prox_hora = resultados["R10"][0]
                            prox_ruta = "R10"
                        if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(prox_hora):
                            prox_hora = resultados["R18"][0]
                            prox_ruta = "R18"
                        msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox_hora} por {prox_ruta}.")
                    else:
                        msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                
                elif intencion == "ultimo":
                    print("  → Buscando ÚLTIMO colectivo")
                    resultados = buscar_horarios(origen, destino, tipo_dia)
                    if resultados["R10"] or resultados["R18"]:
                        ult_hora = "00:00"
                        ult_ruta = ""
                        if resultados["R10"] and hora_a_minutos(resultados["R10"][-1]) > hora_a_minutos(ult_hora):
                            ult_hora = resultados["R10"][-1]
                            ult_ruta = "R10"
                        if resultados["R18"] and hora_a_minutos(resultados["R18"][-1]) > hora_a_minutos(ult_hora):
                            ult_hora = resultados["R18"][-1]
                            ult_ruta = "R18"
                        msg.body(f"🚌 El último colectivo de {origen} a {destino} sale a las {ult_hora} por {ult_ruta}.")
                    else:
                        msg.body(f"😕 No hay servicios de {origen} a {destino} hoy.")
                
                else:
                    hora_limite = extraer_hora_limite(incoming_msg)
                    resultados = buscar_horarios(origen, destino, tipo_dia, hora_limite)
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    msg.body(formatear_horarios(resultados, origen, destino, fecha_str))
                
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                ctx["intencion"] = None
                ctx["fecha_pendiente"] = None
                session[sender] = ctx
                return str(resp)
            else:
                msg.body("🤔 No entendí. Por favor, escribí algo como 'De Viale a Parana'")
                return str(resp)

        # ============================================
        # NUEVA CONSULTA DIRECTA
        # ============================================
        print("🔍 Procesando como consulta directa")
        intencion = detectar_intencion(incoming_msg)
        fecha = interpretar_fecha(incoming_msg)
        origen, destino = extraer_origen_destino(incoming_msg)

        if origen and destino:
            print(f"✅ Consulta directa: {origen} → {destino}, intención: {intencion}")
            tipo_dia = obtener_tipo_dia(fecha)
            
            # PRIORIDAD 1: PRECIO
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
                print("  → Es consulta de PRECIO")
                precio = obtener_precio(origen, destino)
                if precio:
                    msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {origen} a {destino}.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            
            # PRIORIDAD 2: PRIMER
            elif intencion == "primer":
                print("  → Es consulta de PRIMER")
                resultados = buscar_horarios(origen, destino, tipo_dia)
                if resultados["R10"] or resultados["R18"]:
                    primer_hora = "99:99"
                    primer_ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(primer_hora):
                        primer_hora = resultados["R10"][0]
                        primer_ruta = "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(primer_hora):
                        primer_hora = resultados["R18"][0]
                        primer_ruta = "R18"
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    msg.body(f"🚌 El primer colectivo de {origen} a {destino} para el {fecha_str} sale a las {primer_hora} por {primer_ruta}.")
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} para esa fecha.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            
            # PRIORIDAD 3: PRÓXIMO
            elif intencion == "proximo":
                print("  → Es consulta de PRÓXIMO")
                ahora = ahora_argentina()
                hora_actual_min = ahora.hour*60 + ahora.minute
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual_min)
                if resultados["R10"] or resultados["R18"]:
                    prox_hora = "99:99"
                    prox_ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(prox_hora):
                        prox_hora = resultados["R10"][0]
                        prox_ruta = "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(prox_hora):
                        prox_hora = resultados["R18"][0]
                        prox_ruta = "R18"
                    msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox_hora} por {prox_ruta}.")
                else:
                    msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            
            # PRIORIDAD 4: ÚLTIMO
            elif intencion == "ultimo":
                print("  → Es consulta de ÚLTIMO")
                resultados = buscar_horarios(origen, destino, tipo_dia)
                if resultados["R10"] or resultados["R18"]:
                    ult_hora = "00:00"
                    ult_ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][-1]) > hora_a_minutos(ult_hora):
                        ult_hora = resultados["R10"][-1]
                        ult_ruta = "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][-1]) > hora_a_minutos(ult_hora):
                        ult_hora = resultados["R18"][-1]
                        ult_ruta = "R18"
                    msg.body(f"🚌 El último colectivo de {origen} a {destino} sale a las {ult_hora} por {ult_ruta}.")
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} hoy.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            
            # PRIORIDAD 5: HORARIOS COMUNES
            else:
                print("  → Asumiendo consulta de HORARIOS")
                hora_limite = extraer_hora_limite(incoming_msg)
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_limite)
                fecha_str = fecha.strftime("%d/%m/%Y")
                msg.body(formatear_horarios(resultados, origen, destino, fecha_str))
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)

        # ============================================
        # INTENCIÓN SIN ORIGEN/DESTINO
        # ============================================
        if intencion and not origen:
            print(f"✅ Intención detectada sin origen/destino: {intencion}")
            if ctx.get("fecha_pendiente"):
                fecha = ctx["fecha_pendiente"]
                print(f"📅 Manteniendo fecha anterior: {fecha.strftime('%d/%m/%Y')}")
            ctx["estado"] = "esperando_origen_horarios"
            ctx["intencion"] = intencion
            ctx["fecha_pendiente"] = fecha
            session[sender] = ctx
            msg.body("📝 Decime de dónde a dónde querés viajar.")
            return str(resp)

        # ============================================
        # CONSULTA SIN CONTEXTO
        # ============================================
        if not ctx["ultimo_origen"]:
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$", "próximo", "proximo", "último", "ultimo", "primer"]):
                print("✅ Consulta sin contexto, pidiendo origen/destino")
                msg.body("📝 Primero decime de dónde a dónde querés viajar. Ej: 'De Viale a Parana'")
                return str(resp)

        # ============================================
        # SEGUIMIENTO CON CONTEXTO
        # ============================================
        if ctx["ultimo_origen"] and ctx["ultimo_destino"]:
            o = ctx["ultimo_origen"]
            d = ctx["ultimo_destino"]
            print(f"✅ Seguimiento con contexto: {o}→{d}")
            fecha = ahora_argentina()
            tipo_dia = obtener_tipo_dia(fecha)
            
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
                print("  → SUB-CASO: PRECIO (con contexto)")
                precio = obtener_precio(o, d)
                if precio:
                    msg.body(f"💰 El pasaje de {o} a {d} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {o} a {d}.")
                return str(resp)
            
            if any(p in incoming_msg.lower() for p in ["primer", "primero"]):
                print("  → SUB-CASO: PRIMER (con contexto)")
                resultados = buscar_horarios(o, d, tipo_dia)
                if resultados["R10"] or resultados["R18"]:
                    primer_hora = "99:99"
                    primer_ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(primer_hora):
                        primer_hora = resultados["R10"][0]
                        primer_ruta = "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(primer_hora):
                        primer_hora = resultados["R18"][0]
                        primer_ruta = "R18"
                    msg.body(f"🚌 El primer colectivo de {o} a {d} sale a las {primer_hora} por {primer_ruta}.")
                else:
                    msg.body(f"😕 No hay servicios de {o} a {d} hoy.")
                return str(resp)
            
            if any(p in incoming_msg.lower() for p in ["próximo", "proximo", "siguiente"]):
                print("  → SUB-CASO: PRÓXIMO (con contexto)")
                ahora = ahora_argentina()
                hora_actual_min = ahora.hour*60 + ahora.minute
                resultados = buscar_horarios(o, d, tipo_dia, hora_actual_min)
                if resultados["R10"] or resultados["R18"]:
                    prox_hora = "99:99"
                    prox_ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(prox_hora):
                        prox_hora = resultados["R10"][0]
                        prox_ruta = "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(prox_hora):
                        prox_hora = resultados["R18"][0]
                        prox_ruta = "R18"
                    msg.body(f"🚌 El próximo colectivo de {o} a {d} sale a las {prox_hora} por {prox_ruta}.")
                else:
                    msg.body(f"😕 No hay más servicios de {o} a {d} hoy.")
                return str(resp)
            
            if any(p in incoming_msg.lower() for p in ["último", "ultimo", "final"]):
                print("  → SUB-CASO: ÚLTIMO (con contexto)")
                resultados = buscar_horarios(o, d, tipo_dia)
                if resultados["R10"] or resultados["R18"]:
                    ult_hora = "00:00"
                    ult_ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][-1]) > hora_a_minutos(ult_hora):
                        ult_hora = resultados["R10"][-1]
                        ult_ruta = "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][-1]) > hora_a_minutos(ult_hora):
                        ult_hora = resultados["R18"][-1]
                        ult_ruta = "R18"
                    msg.body(f"🚌 El último colectivo de {o} a {d} sale a las {ult_hora} por {ult_ruta}.")
                else:
                    msg.body(f"😕 No hay servicios de {o} a {d} hoy.")
                return str(resp)

        # ============================================
        # NO ENTENDIDO
        # ============================================
        print("❌ No entendido")
        msg.body(no_entendido())
        return str(resp)

    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {e}")
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
