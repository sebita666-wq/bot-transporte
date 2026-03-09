from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import pytz
import re
import json
import os

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=3)

# Configurar zona horaria de Argentina
os.environ['TZ'] = 'America/Argentina/Buenos_Aires'
try:
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
except:
    timezone = pytz.timezone('America/Argentina/Cordoba')

print("🚀 BOT INICIADO - VERSIÓN COMPLETA PARA STARTER")

# ============================================
# CONFIGURACIÓN
# ============================================
NUMERO_DUENIO = os.environ.get('NUMERO_DUENIO', "whatsapp:+5493434727811")
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_para_sesiones')
STATS_FILE = 'estadisticas.json'

app.secret_key = SECRET_KEY

# ============================================
# FUNCIÓN PARA OBTENER HORA ARGENTINA
# ============================================
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

# ============================================
# HORARIOS - DÍAS HÁBILES
# ============================================

tramos_habiles = [
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "04:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "05:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "05:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "06:05", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "04:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "05:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "06:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "06:25", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "06:45", "ruta": "R10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "05:35", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "06:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "07:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "07:20", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "07:45", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "09:25", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "09:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:05", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "11:15", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "08:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "09:55", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "10:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "10:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "10:15", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "11:55", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "12:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "12:35", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "12:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "13:05", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "14:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "14:30", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "14:45", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "15:05", "ruta": "R10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "14:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:40", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "15:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "16:40", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "17:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "16:30", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "18:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "18:35", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "18:55", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:05", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "17:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "18:25", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "18:40", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "18:55", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "19:15", "ruta": "R10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "18:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "19:40", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "19:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "20:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "21:55", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "22:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "22:25", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "23:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "23:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "23:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "00:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "23:00", "ruta": "R18"},
]

# ============================================
# HORARIOS - SÁBADOS
# ============================================

tramos_sabados = [
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "06:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "06:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "04:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "05:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "06:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "06:25", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "06:45", "ruta": "R10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "05:35", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "06:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "07:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "07:20", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "07:45", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "12:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "12:20", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "12:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "11:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "12:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "13:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "14:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "14:30", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "14:50", "ruta": "R10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "14:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:15", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "15:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "16:20", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "16:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "17:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "18:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "18:30", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "18:45", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "19:05", "ruta": "R10"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "16:30", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "18:20", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "18:40", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "19:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:10", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "19:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "20:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "21:55", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "22:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "22:30", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "23:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "23:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "23:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "00:30", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "23:00", "ruta": "R18"},
]

# ============================================
# HORARIOS - DOMINGOS
# ============================================

tramos_domingos = [
    {"origen": "Parana", "destino": "Viale", "hora_salida": "07:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "08:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "07:45", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "09:34", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "09:48", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:07", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "11:35", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "10:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:00", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "12:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "13:59", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "14:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "14:30", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "14:50", "ruta": "R10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "15:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "16:25", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "16:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:10", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "17:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "18:29", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "18:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "19:00", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "19:25", "ruta": "R10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "19:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:45", "ruta": "R18"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "21:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "22:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "22:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "23:08", "ruta": "R18"},
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
    ("Viale", "Aldea San Antonio"): 2100,
    ("Aldea San Antonio", "Viale"): 2100,
    ("Tabossi", "Sosa"): 1800,
    ("Sosa", "Tabossi"): 1800,
    ("Tabossi", "Maria Grande"): 2100,
    ("Maria Grande", "Tabossi"): 2100,
    ("Tabossi", "Aldea San Antonio"): 3400,
    ("Aldea San Antonio", "Tabossi"): 3400,
    ("Sosa", "Maria Grande"): 1800,
    ("Maria Grande", "Sosa"): 1800,
    ("Sosa", "Aldea San Antonio"): 4100,
    ("Aldea San Antonio", "Sosa"): 4100,
    ("Maria Grande", "Aldea San Antonio"): 4900,
    ("Aldea San Antonio", "Maria Grande"): 4900,
}

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def hora_a_minutos(hora_str):
    if not hora_str: return None
    h, m = map(int, hora_str.split(':'))
    return h*60 + m

def minutos_a_hora(minutos):
    if not minutos: return ""
    return f"{minutos//60:02d}:{minutos%60:02d}"

def obtener_tipo_dia(fecha):
    if es_feriado_nacional(fecha):
        return "domingos"
    if fecha.weekday() < 5:
        return "habiles"
    elif fecha.weekday() == 5:
        return "sabados"
    else:
        return "domingos"

def obtener_tramos_por_dia(tipo_dia):
    if tipo_dia == "habiles": return tramos_habiles
    if tipo_dia == "sabados": return tramos_sabados
    return tramos_domingos

def extraer_origen_destino(mensaje):
    mensaje = mensaje.lower().strip()
    mensaje = re.sub(r'[¿?!¡.,;]', '', mensaje)
    
    frases = ["cual es el", "podrias decirme", "quiero saber", "decime", "contame", "y el", "el"]
    for frase in frases:
        mensaje = mensaje.replace(frase, "")
    
    mensaje = re.sub(r'\s+', ' ', mensaje).strip()
    print(f"🧹 Mensaje limpio: '{mensaje}'")
    
    patron = r'de\s+(.+?)\s+a\s+(.+)'
    match = re.search(patron, mensaje)
    if not match:
        patron = r'^(.+?)\s+a\s+(.+)$'
        match = re.search(patron, mensaje)
    
    if match:
        o = match.group(1).strip()
        d = match.group(2).strip()
        
        # Limpiar palabras temporales
        for palabra in ["mañana", "manana", "hoy", "para", "el", "la", "del"]:
            d = d.replace(palabra, "").strip()
        
        # Normalizar localidades
        loc_map = {
            "parana": "Parana", "viale": "Viale", "tabossi": "Tabossi",
            "sosa": "Sosa", "maria grande": "Maria Grande",
            "aldea san antonio": "Aldea San Antonio", "san antonio": "Aldea San Antonio"
        }
        
        origen = next((v for k,v in loc_map.items() if k in o), None)
        destino = next((v for k,v in loc_map.items() if k in d), None)
        
        if origen and destino:
            print(f"✅ Extraído: {origen} -> {destino}")
            return origen, destino
    
    print("❌ No se pudo extraer")
    return None, None

def detectar_intencion(mensaje):
    m = mensaje.lower()
    if any(p in m for p in ["primer", "primero"]): return "primer"
    if any(p in m for p in ["próximo", "proximo", "siguiente"]): return "proximo"
    if any(p in m for p in ["último", "ultimo", "final"]): return "ultimo"
    return None

def extraer_hora_limite(mensaje):
    m = mensaje.lower()
    patrones = [
        r'(?:después|despues|a partir)\s+de\s+las?\s*(\d{1,2})(?::(\d{2}))?',
        r'(\d{1,2})(?::(\d{2}))?\s*(?:en adelante|para adelante|hacia adelante)'
    ]
    for p in patrones:
        match = re.search(p, m)
        if match:
            hora = int(match.group(1))
            mins = int(match.group(2)) if match.group(2) else 0
            return hora*60 + mins
    return None

def interpretar_fecha(mensaje):
    m = mensaje.lower()
    hoy = ahora_argentina().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if "mañana" in m or "manana" in m:
        return hoy + timedelta(days=1)
    if "hoy" in m:
        return hoy
    
    dias = {"lunes":0, "martes":1, "miercoles":2, "miércoles":2,
            "jueves":3, "viernes":4, "sabado":5, "sábado":5, "domingo":6}
    for dia, num in dias.items():
        if dia in m:
            return hoy + timedelta(days=(num - hoy.weekday() + 7) % 7)
    
    return hoy

def buscar_servicios_por_ruta(origen, destino, tipo_dia, hora_limite=None):
    print(f"🔍 Buscando: {origen} -> {destino} ({tipo_dia})")
    tramos = obtener_tramos_por_dia(tipo_dia)
    resultados = {"R10": [], "R18": []}
    
    # Buscar tramos directos
    for t in tramos:
        if t["origen"] == origen and t["destino"] == destino:
            hora_min = hora_a_minutos(t["hora_salida"])
            if hora_limite is None or hora_min >= hora_limite:
                resultados[t["ruta"]].append(t["hora_salida"])
    
    # Buscar servicios con múltiples tramos
    servicios = {}
    for t in tramos:
        if t["origen"] == origen:
            if t["hora_salida"] not in servicios:
                servicios[t["hora_salida"]] = []
            servicios[t["hora_salida"]].append(t)
    
    for hora, tramos_servicio in servicios.items():
        destinos = [t["destino"] for t in tramos_servicio]
        if destino in destinos:
            hora_min = hora_a_minutos(hora)
            if hora_limite is None or hora_min >= hora_limite:
                if any(t.get("ruta") == "R10" for t in tramos_servicio):
                    if hora not in resultados["R10"]:
                        resultados["R10"].append(hora)
                else:
                    if hora not in resultados["R18"]:
                        resultados["R18"].append(hora)
    
    for r in resultados:
        resultados[r].sort(key=hora_a_minutos)
    
    print(f"  → R10: {len(resultados['R10'])} servicios")
    print(f"  → R18: {len(resultados['R18'])} servicios")
    return resultados

def primer_colectivo(origen, destino, tipo_dia):
    res = buscar_servicios_por_ruta(origen, destino, tipo_dia)
    if res["R10"] and res["R18"]:
        return min((res["R10"][0], "R10"), (res["R18"][0], "R18"), key=lambda x: hora_a_minutos(x[0]))
    if res["R10"]: return (res["R10"][0], "R10")
    if res["R18"]: return (res["R18"][0], "R18")
    return None

def proximo_colectivo(origen, destino, tipo_dia):
    ahora = ahora_argentina()
    ahora_min = ahora.hour*60 + ahora.minute
    res = buscar_servicios_por_ruta(origen, destino, tipo_dia, ahora_min)
    candidatos = []
    if res["R10"]: candidatos.append((res["R10"][0], "R10"))
    if res["R18"]: candidatos.append((res["R18"][0], "R18"))
    return min(candidatos, key=lambda x: hora_a_minutos(x[0])) if candidatos else None

def ultimo_colectivo(origen, destino, tipo_dia):
    res = buscar_servicios_por_ruta(origen, destino, tipo_dia)
    ultimo, ruta_ultimo = None, None
    if res["R10"]: ultimo, ruta_ultimo = res["R10"][-1], "R10"
    if res["R18"]:
        if not ultimo or hora_a_minutos(res["R18"][-1]) > hora_a_minutos(ultimo):
            ultimo, ruta_ultimo = res["R18"][-1], "R18"
    return (ultimo, ruta_ultimo) if ultimo else None

def formatear_horarios(resultados, origen, destino, fecha_str):
    texto = f"🚌 Servicios de {origen} a {destino} para {fecha_str}:\n\n"
    if resultados["R10"]:
        texto += "🛣️ Por Ruta 10 (directo):\n" + "\n".join([f"• {h}" for h in resultados["R10"][:5]]) + "\n\n"
    if resultados["R18"]:
        texto += "🛣️ Por Ruta 18 (con paradas):\n" + "\n".join([f"• {h}" for h in resultados["R18"][:5]]) + "\n\n"
    if not resultados["R10"] and not resultados["R18"]:
        return f"😕 No encontré servicios de {origen} a {destino} para {fecha_str}."
    texto += "😊 ¿Necesitas precio, duración, próximo o último?"
    return texto

def obtener_precio(origen, destino):
    return precios.get((origen, destino))

# ============================================
# ESTADÍSTICAS
# ============================================

def cargar_estadisticas():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {"usuarios": {}, "metricas": {"total_usuarios_unicos": 0, "total_mensajes": 0, "ultimo_reinicio": ahora_argentina().strftime("%Y-%m-%d %H:%M:%S")}}

def guardar_estadisticas(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def registrar_interaccion(sender, mensaje, tipo=None):
    stats = cargar_estadisticas()
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
    guardar_estadisticas(stats)

def obtener_resumen_estadisticas():
    stats = cargar_estadisticas()
    ahora = ahora_argentina()
    hoy = ahora.strftime("%Y-%m-%d")
    semana = (ahora - timedelta(days=7)).strftime("%Y-%m-%d")
    return {
        "total_usuarios": stats["metricas"]["total_usuarios_unicos"],
        "total_mensajes": stats["metricas"]["total_mensajes"],
        "usuarios_hoy": sum(1 for u in stats["usuarios"].values() if u["ultimo_contacto"].startswith(hoy)),
        "usuarios_semana": sum(1 for u in stats["usuarios"].values() if u["ultimo_contacto"][:10] >= semana),
        "ultimo_reinicio": stats["metricas"]["ultimo_reinicio"]
    }

# ============================================
# FUNCIONES DE RESPUESTA
# ============================================

def mostrar_menu():
    return ("👋 Hola, soy el asistente de transporte.\n\n"
            "1️⃣ Ver horarios\n2️⃣ Consultar precios\n3️⃣ Información útil\n4️⃣ Preguntas frecuentes\n\n"
            "Ej: 'De Viale a Parana', 'Primer colectivo de Parana a Viale mañana'")

def preguntar_origen_destino(tipo):
    return f"📝 Decime de dónde a dónde querés viajar (ej: De Viale a Parana)"

def mostrar_info_util():
    return ("📌 *Información útil*\n📍 Terminal Paraná: Av. Ramírez 1200\n📍 Terminal María Grande: San Martín 450\n📞 Teléfono: 343 456-7890")

def mostrar_faq():
    return ("❓ *Preguntas frecuentes*\n• ¿Cómo pago? Efectivo o tarjeta\n• ¿WiFi? Sí, gratis\n• ¿Mascotas? En jaula")

def despedida():
    return "😊 ¡Gracias! Escribime 'Hola' para empezar de nuevo."

def no_entendido():
    return "🤔 No entendí. Probá con 'Hola', 'De Viale a Parana' o 'Precio de Parana a Maria Grande'"

def resetear_contexto(sender):
    session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}

def responder_pregunta_frecuente(mensaje):
    m = mensaje.lower()
    if any(p in m for p in ["tarjeta", "pago"]): return "💳 Aceptamos efectivo y tarjetas"
    if any(p in m for p in ["wifi", "internet"]): return "📶 WiFi gratis en todos los colectivos"
    if any(p in m for p in ["qr", "mercadopago"]): return "📱 Próximamente pago con QR"
    if any(p in m for p in ["perro", "mascota"]): return "🐕 Mascotas viajan en jaula"
    return None

# ============================================
# WEBHOOK PRINCIPAL
# ============================================

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    print(f"\n📩 Mensaje: '{incoming_msg}' de {sender}")
    
    resp = MessagingResponse()
    msg = resp.message()
    
    registrar_interaccion(sender, incoming_msg)
    
    if sender not in session:
        session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
    
    ctx = session[sender]
    
    # Comando dueño
    if incoming_msg.lower() == "/estadisticas" and sender == NUMERO_DUENIO:
        res = obtener_resumen_estadisticas()
        msg.body(f"📊 Estadísticas\n👥 Usuarios: {res['total_usuarios']}\n💬 Mensajes: {res['total_mensajes']}\n📅 Hoy: {res['usuarios_hoy']}\n📆 Semana: {res['usuarios_semana']}")
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
    if incoming_msg.lower() in ["menu", "reiniciar", "reset"]:
        resetear_contexto(sender)
        msg.body(mostrar_menu())
        return str(resp)
    
    # FAQ sueltas
    faq = responder_pregunta_frecuente(incoming_msg)
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
    
    # Procesar según estado
    if ctx.get("estado") == "esperando_origen_precios":
        o, d = extraer_origen_destino(incoming_msg)
        if o and d:
            precio = obtener_precio(o, d)
            msg.body(f"💰 El pasaje de {o} a {d} cuesta ${precio}" if precio else f"😕 No tengo precio de {o} a {d}")
            ctx["ultimo_origen"], ctx["ultimo_destino"] = o, d
            ctx["estado"] = "menu"
        else:
            msg.body("🤔 No entendí. Escribí algo como 'De Viale a Parana'")
        return str(resp)
    
    if ctx.get("estado") == "esperando_origen_horarios":
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
            ctx["estado"] = "esperando_origen_precios"
            msg.body("📝 Decime de dónde a dónde querés saber el precio")
            return str(resp)
        
        o, d = extraer_origen_destino(incoming_msg)
        if o and d:
            fecha = ctx.get("fecha_pendiente") or interpretar_fecha(incoming_msg)
            tipo = obtener_tipo_dia(fecha)
            intencion = ctx.get("intencion")
            
            if intencion == "primer":
                res = primer_colectivo(o, d, tipo)
                if res:
                    msg.body(f"🚌 El primer colectivo de {o} a {d} para {fecha.strftime('%d/%m/%Y')} sale a las {res[0]} por {res[1]}")
                else:
                    msg.body(f"😕 No hay servicios de {o} a {d} para esa fecha")
            elif intencion == "proximo":
                res = proximo_colectivo(o, d, tipo)
                if res:
                    msg.body(f"🚌 El próximo colectivo de {o} a {d} sale a las {res[0]} por {res[1]}")
                else:
                    msg.body(f"😕 No hay más servicios de {o} a {d} hoy")
            elif intencion == "ultimo":
                res = ultimo_colectivo(o, d, tipo)
                if res:
                    msg.body(f"🚌 El último colectivo de {o} a {d} sale a las {res[0]} por {res[1]}")
                else:
                    msg.body(f"😕 No hay servicios de {o} a {d} hoy")
            else:
                hora_limite = extraer_hora_limite(incoming_msg)
                resultados = buscar_servicios_por_ruta(o, d, tipo, hora_limite)
                fecha_str = fecha.strftime("%d/%m/%Y")
                msg.body(formatear_horarios(resultados, o, d, fecha_str))
            
            ctx["ultimo_origen"], ctx["ultimo_destino"] = o, d
            ctx["estado"] = "menu"
            ctx["intencion"] = None
            ctx["fecha_pendiente"] = None
        else:
            msg.body("🤔 No entendí. Escribí algo como 'De Viale a Parana'")
        return str(resp)
    
    # Consulta directa
    intencion = detectar_intencion(incoming_msg)
    fecha = interpretar_fecha(incoming_msg)
    o, d = extraer_origen_destino(incoming_msg)
    
    if o and d:
        tipo = obtener_tipo_dia(fecha)
        
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
            precio = obtener_precio(o, d)
            msg.body(f"💰 El pasaje de {o} a {d} cuesta ${precio}" if precio else f"😕 No tengo precio de {o} a {d}")
        
        elif intencion == "primer":
            res = primer_colectivo(o, d, tipo)
            if res:
                msg.body(f"🚌 El primer colectivo de {o} a {d} para {fecha.strftime('%d/%m/%Y')} sale a las {res[0]} por {res[1]}")
            else:
                msg.body(f"😕 No hay servicios de {o} a {d} para esa fecha")
        
        elif intencion == "proximo":
            res = proximo_colectivo(o, d, tipo)
            if res:
                msg.body(f"🚌 El próximo colectivo de {o} a {d} sale a las {res[0]} por {res[1]}")
            else:
                msg.body(f"😕 No hay más servicios de {o} a {d} hoy")
        
        elif intencion == "ultimo":
            res = ultimo_colectivo(o, d, tipo)
            if res:
                msg.body(f"🚌 El último colectivo de {o} a {d} sale a las {res[0]} por {res[1]}")
            else:
                msg.body(f"😕 No hay servicios de {o} a {d} hoy")
        
        else:
            hora_limite = extraer_hora_limite(incoming_msg)
            resultados = buscar_servicios_por_ruta(o, d, tipo, hora_limite)
            fecha_str = fecha.strftime("%d/%m/%Y")
            msg.body(formatear_horarios(resultados, o, d, fecha_str))
        
        ctx["ultimo_origen"], ctx["ultimo_destino"] = o, d
        ctx["fecha_pendiente"] = fecha
        return str(resp)
    
    # Intención sin origen/destino
    if intencion and not o:
        if ctx.get("fecha_pendiente"):
            fecha = ctx["fecha_pendiente"]
        ctx["estado"] = "esperando_origen_horarios"
        ctx["intencion"] = intencion
        ctx["fecha_pendiente"] = fecha
        msg.body("📝 Decime de dónde a dónde querés viajar")
        return str(resp)
    
    # Consulta sin contexto
    if not ctx["ultimo_origen"]:
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "próximo", "proximo", "último", "ultimo", "primer"]):
            msg.body("📝 Primero decime de dónde a dónde querés viajar. Ej: 'De Viale a Parana'")
            return str(resp)
    
    # Seguimiento con contexto
    if ctx["ultimo_origen"] and ctx["ultimo_destino"]:
        o, d = ctx["ultimo_origen"], ctx["ultimo_destino"]
        tipo = obtener_tipo_dia(ahora_argentina())
        
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
            precio = obtener_precio(o, d)
            msg.body(f"💰 El pasaje de {o} a {d} cuesta ${precio}" if precio else f"😕 No tengo precio de {o} a {d}")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["primer", "primero"]):
            res = primer_colectivo(o, d, tipo)
            if res:
                msg.body(f"🚌 El primer colectivo de {o} a {d} sale a las {res[0]} por {res[1]}")
            else:
                msg.body(f"😕 No hay servicios de {o} a {d} hoy")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["próximo", "proximo", "siguiente"]):
            res = proximo_colectivo(o, d, tipo)
            if res:
                msg.body(f"🚌 El próximo colectivo de {o} a {d} sale a las {res[0]} por {res[1]}")
            else:
                msg.body(f"😕 No hay más servicios de {o} a {d} hoy")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["último", "ultimo", "final"]):
            res = ultimo_colectivo(o, d, tipo)
            if res:
                msg.body(f"🚌 El último colectivo de {o} a {d} sale a las {res[0]} por {res[1]}")
            else:
                msg.body(f"😕 No hay servicios de {o} a {d} hoy")
            return str(resp)
    
    # No entendido
    msg.body(no_entendido())
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando bot en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
