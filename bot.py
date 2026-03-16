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

print("🚀 BOT INICIADO - VERSIÓN CORREGIDA (PROXIMO)")

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
# LOCALIDADES CON ALIAS
# ============================================
localidades = [
    { "principal": "Genolet", "alias": ["San Benito", "Colonia Avellaneda"] },
    { "principal": "Sauce", "alias": [] },
    { "principal": "3 Bocas", "alias": ["Tres Bocas"] },
    { "principal": "Quebracho", "alias": [] },
    { "principal": "El Ramblón", "alias": ["Ramblon", "El Ramblon"] },
    { "principal": "Viale", "alias": [] },
    { "principal": "Tabossi", "alias": [] },
    { "principal": "Estación Sosa", "alias": ["Est. Sosa", "Sosa"] },
    { "principal": "María Grande", "alias": ["Maria Grande", "M. Grande"] },
    { "principal": "Paraje de las Piedras", "alias": ["P. de las Piedras", "Paraje Las Piedras"] },
    { "principal": "Arroyo Carmona", "alias": ["A. Carmona", "Carmona"] },
    { "principal": "Sauce Montrull", "alias": ["Sauce Montrul"] },
    { "principal": "Paraná", "alias": ["Parana"] }
]

def normalizar_localidad(texto):
    if not texto:
        return None
    texto = texto.lower().strip()
    texto = texto.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    for loc in localidades:
        principal_sin_tilde = loc["principal"].lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        if texto == principal_sin_tilde:
            return loc["principal"]
        for alias in loc["alias"]:
            alias_sin_tilde = alias.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            if texto == alias_sin_tilde:
                return loc["principal"]
    return None

def obtener_lista_localidades():
    lista = []
    for loc in localidades:
        nombre = loc["principal"].lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        lista.append(nombre)
        for alias in loc["alias"]:
            alias_sin_tilde = alias.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            if alias_sin_tilde not in lista:
                lista.append(alias_sin_tilde)
    return lista

# ============================================
# EXTRACCIÓN DE ORIGEN/DESTINO
# ============================================
def extraer_origen_destino(mensaje):
    m = mensaje.lower().strip()
    print(f"🔍 EXTRAYENDO de: '{m}'")
    
    m = re.sub(r'[¿?!¡.,;:]', '', m)
    
    palabras_irrelevantes = ['cual', 'es', 'el', 'la', 'los', 'las', 'y', 'e']
    
    if m.startswith('cual es '):
        m = m[8:]
        print(f"  → Limpiado 'cual es': '{m}'")
    
    partes = m.split()
    if partes and partes[0] in palabras_irrelevantes:
        m = ' '.join(partes[1:])
        print(f"  → Limpiado inicio: '{m}'")
    
    # CASO 1: Buscar "de X a Y"
    palabras = m.split()
    for i, palabra in enumerate(palabras):
        if palabra == "de":
            for j in range(i + 2, len(palabras)):
                if palabras[j] == "a":
                    origen = " ".join(palabras[i+1:j])
                    destino = " ".join(palabras[j+1:])
                    print(f"  → Encontré 'de' en {i}, 'a' en {j}: origen='{origen}', destino='{destino}'")
                    origen_norm = normalizar_localidad(origen)
                    destino_norm = normalizar_localidad(destino)
                    if origen_norm and destino_norm:
                        print(f"✅ EXTRAÍDO: {origen_norm} -> {destino_norm}")
                        return origen_norm, destino_norm
                    if origen_norm:
                        palabras_destino = destino.split()
                        for k in range(len(palabras_destino), 0, -1):
                            posible_destino = " ".join(palabras_destino[:k])
                            destino_norm = normalizar_localidad(posible_destino)
                            if destino_norm:
                                print(f"✅ EXTRAÍDO (parcial): {origen_norm} -> {destino_norm}")
                                return origen_norm, destino_norm
                    break
    
    # CASO 2: Buscar "X a Y"
    if " a " in m and not m.startswith('de '):
        idx_a = m.find(" a ")
        if idx_a != -1:
            origen = m[:idx_a].strip()
            destino = m[idx_a + 3:].strip()
            if "de" not in origen.split():
                print(f"  → Formato simple: origen='{origen}', destino='{destino}'")
                origen_norm = normalizar_localidad(origen)
                destino_norm = normalizar_localidad(destino)
                if origen_norm and destino_norm:
                    print(f"✅ EXTRAÍDO: {origen_norm} -> {destino_norm}")
                    return origen_norm, destino_norm
                if origen_norm:
                    palabras_destino = destino.split()
                    for j in range(len(palabras_destino), 0, -1):
                        posible_destino = " ".join(palabras_destino[:j])
                        destino_norm = normalizar_localidad(posible_destino)
                        if destino_norm:
                            print(f"✅ EXTRAÍDO (parcial): {origen_norm} -> {destino_norm}")
                            return origen_norm, destino_norm
    
    print("❌ No se pudo extraer")
    return None, None

# ============================================
# DETECCIÓN DE FECHA
# ============================================
def interpretar_fecha(mensaje):
    m = mensaje.lower().strip()
    hoy = ahora_argentina().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Formato DD/MM o DD/MM/YYYY
    match = re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', m)
    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        anio = int(match.group(3)) if match.group(3) else hoy.year
        if anio < 100:
            anio += 2000
        try:
            fecha = datetime(anio, mes, dia, tzinfo=hoy.tzinfo)
            print(f"📅 Fecha detectada: {fecha.strftime('%d/%m/%Y')}")
            return fecha
        except ValueError:
            print(f"⚠️ Fecha inválida: {dia}/{mes}/{anio}")
    
    # Formato "17 de marzo"
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
        'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    match = re.search(r'(\d{1,2})\s+de\s+([a-z]+)', m)
    if match:
        dia = int(match.group(1))
        mes_nombre = match.group(2)
        mes = meses.get(mes_nombre)
        if mes:
            try:
                fecha = datetime(hoy.year, mes, dia, tzinfo=hoy.tzinfo)
                if fecha < hoy:
                    fecha = datetime(hoy.year + 1, mes, dia, tzinfo=hoy.tzinfo)
                print(f"📅 Fecha detectada: {fecha.strftime('%d/%m/%Y')}")
                return fecha
            except ValueError:
                print(f"⚠️ Fecha inválida: {dia} de {mes_nombre}")
    
    # Palabras clave
    if "mañana" in m or "manana" in m:
        print("📅 Fecha: mañana")
        return hoy + timedelta(days=1)
    if "hoy" in m:
        print("📅 Fecha: hoy")
        return hoy
    
    print("📅 Fecha: hoy (por defecto)")
    return hoy

# ============================================
# MATRIZ DE PRECIOS
# ============================================
matriz_precios = [
    [1852,1852,1852,1852,1852,1852,1852,1852,1852,1852,1852,1852,1852],
    [1852,2100,2150,2200,2904,3432,3828,2508,2300,2772,3960,4488,2100],
    [1852,2150,2376,3564,4620,5544,4224,3960,3168,5412,5808,7128,2244],
    [1852,2200,3564,4092,5280,6732,5940,5280,3960,7920,8580,9900,3432],
    [1852,2904,4620,5280,5808,7392,6996,6732,5412,9768,10560,11880,5148],
    [1852,3432,5544,6732,7392,7524,7920,7524,6732,10296,11088,12408,7524],
    [1852,3828,4224,5940,6996,7920,8316,7788,7128,10692,11484,12804,9106],
    [1852,2508,3960,5280,6732,7524,7788,9372,8712,11220,12012,13332,9372],
    [1852,2300,3168,3960,5412,6732,7128,8712,9900,10296,11088,12408,9900],
    [1852,2772,5412,7920,9768,10296,10692,11220,10296,12144,12936,14256,12144],
    [1852,3960,5808,8580,10560,11088,11484,12012,11088,12936,14784,16104,14784],
    [1852,4488,7128,9900,11880,12408,12804,13332,12408,14256,16104,16632,16632],
    [1852,2100,2244,3432,5148,7524,9106,9372,9900,12144,14784,16632,19272]
]

def obtener_precio(origen, destino):
    try:
        o_norm = normalizar_localidad(origen)
        d_norm = normalizar_localidad(destino)
        if not o_norm or not d_norm:
            return None
        if (o_norm == "María Grande" and d_norm == "Paraná") or (o_norm == "Paraná" and d_norm == "María Grande"):
            return {"R10": 8580, "R18": 9900}
        indices = {loc["principal"]: i for i, loc in enumerate(localidades)}
        return matriz_precios[indices[o_norm]][indices[d_norm]]
    except:
        return None

# ============================================
# HORARIOS - DÍAS HÁBILES
# ============================================
horarios_habiles = [
    {"origen": "Paraná", "destino": "Viale", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "05:35", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "06:40", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "08:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "10:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "12:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "13:05", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "14:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "15:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "17:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "18:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "19:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "20:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "23:00", "ruta": "R18"},
    
    {"origen": "Viale", "destino": "Paraná", "hora": "05:10", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "06:05", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "07:20", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "08:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "10:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "10:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "12:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "13:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "15:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "17:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "19:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "21:10", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "00:30", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Tabossi", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "05:35", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "08:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "13:05", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "15:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "17:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "20:45", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Tabossi", "hora": "07:45", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "10:15", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "16:30", "ruta": "R10"},
    
    {"origen": "Tabossi", "destino": "Paraná", "hora": "04:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "05:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "07:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "10:25", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "12:35", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "17:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "23:30", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "13:05", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "17:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "20:45", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "07:45", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "10:15", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "16:30", "ruta": "R10"},
    
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "06:25", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "11:55", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "14:30", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "14:45", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "18:15", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "18:55", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "22:25", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "María Grande", "hora": "07:45", "ruta": "R10"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "10:15", "ruta": "R10"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "16:30", "ruta": "R10"},
    
    {"origen": "Paraná", "destino": "María Grande", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "13:05", "ruta": "R18"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "17:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "20:45", "ruta": "R18"},
    
    {"origen": "María Grande", "destino": "Paraná", "hora": "06:45", "ruta": "R10"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "14:50", "ruta": "R10"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "19:15", "ruta": "R10"},
    
    {"origen": "María Grande", "destino": "Paraná", "hora": "15:05", "ruta": "R18"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "19:25", "ruta": "R18"},
    
    {"origen": "Viale", "destino": "Tabossi", "hora": "05:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "06:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "09:55", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "14:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "16:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "18:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora": "21:55", "ruta": "R18"},
    
    {"origen": "Tabossi", "destino": "Viale", "hora": "04:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "05:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "07:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "10:25", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "12:35", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "17:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora": "23:30", "ruta": "R18"},
    
    {"origen": "Viale", "destino": "Estación Sosa", "hora": "05:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Estación Sosa", "hora": "06:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Estación Sosa", "hora": "13:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Estación Sosa", "hora": "14:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Estación Sosa", "hora": "16:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Estación Sosa", "hora": "18:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Estación Sosa", "hora": "21:55", "ruta": "R18"},
    
    {"origen": "Estación Sosa", "destino": "Viale", "hora": "06:10", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Viale", "hora": "09:45", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Viale", "hora": "12:15", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Viale", "hora": "18:35", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Viale", "hora": "23:15", "ruta": "R18"},
    
    {"origen": "Tabossi", "destino": "Estación Sosa", "hora": "06:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Estación Sosa", "hora": "14:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Estación Sosa", "hora": "14:30", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Estación Sosa", "hora": "18:30", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Estación Sosa", "hora": "22:10", "ruta": "R18"},
    
    {"origen": "Estación Sosa", "destino": "Tabossi", "hora": "06:25", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Tabossi", "hora": "14:30", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Tabossi", "hora": "14:45", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Tabossi", "hora": "18:45", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Tabossi", "hora": "22:30", "ruta": "R18"},
    
    {"origen": "Estación Sosa", "destino": "María Grande", "hora": "06:25", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "María Grande", "hora": "14:30", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "María Grande", "hora": "14:45", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "María Grande", "hora": "18:45", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "María Grande", "hora": "22:30", "ruta": "R18"},
    
    {"origen": "María Grande", "destino": "Estación Sosa", "hora": "09:25", "ruta": "R18"},
    {"origen": "María Grande", "destino": "Estación Sosa", "hora": "11:55", "ruta": "R18"},
    {"origen": "María Grande", "destino": "Estación Sosa", "hora": "18:15", "ruta": "R18"},
    {"origen": "María Grande", "destino": "Estación Sosa", "hora": "23:00", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Aldea San Antonio", "hora": "06:40", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Aldea San Antonio", "hora": "10:15", "ruta": "R18"},
    
    {"origen": "Aldea San Antonio", "destino": "Paraná", "hora": "12:55", "ruta": "R18"},
    {"origen": "Aldea San Antonio", "destino": "Paraná", "hora": "23:15", "ruta": "R18"},
]

# ============================================
# HORARIOS - SÁBADOS
# ============================================
horarios_sabados = [
    {"origen": "Paraná", "destino": "Viale", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "05:35", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "07:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "08:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "11:40", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "14:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "15:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "17:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "19:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "20:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "23:00", "ruta": "R18"},
    
    {"origen": "Viale", "destino": "Paraná", "hora": "08:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "11:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "12:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "13:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "15:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "16:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "21:10", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Tabossi", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "05:35", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "10:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "15:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "17:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "20:45", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Tabossi", "hora": "07:45", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "10:15", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "16:30", "ruta": "R10"},
    
    {"origen": "Tabossi", "destino": "Paraná", "hora": "06:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "07:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "12:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "16:40", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "17:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "20:45", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "07:45", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "10:15", "ruta": "R10"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "16:30", "ruta": "R10"},
    
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "06:25", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "12:00", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "14:30", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "18:20", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "23:00", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "María Grande", "hora": "07:45", "ruta": "R10"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "10:15", "ruta": "R10"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "16:30", "ruta": "R10"},
    
    {"origen": "Paraná", "destino": "María Grande", "hora": "04:45", "ruta": "R18"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "17:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "20:45", "ruta": "R18"},
    
    {"origen": "María Grande", "destino": "Paraná", "hora": "06:45", "ruta": "R10"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "14:50", "ruta": "R10"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "19:05", "ruta": "R10"},
    
    {"origen": "María Grande", "destino": "Paraná", "hora": "09:10", "ruta": "R18"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "18:00", "ruta": "R18"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "22:45", "ruta": "R18"},
]

# ============================================
# HORARIOS - DOMINGOS
# ============================================
horarios_domingos = [
    {"origen": "Paraná", "destino": "Viale", "hora": "07:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "08:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "10:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "15:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "17:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "19:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Viale", "hora": "21:00", "ruta": "R18"},
    
    {"origen": "Viale", "destino": "Paraná", "hora": "08:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "09:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "12:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Paraná", "hora": "20:45", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Tabossi", "hora": "11:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "15:15", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "17:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Tabossi", "hora": "21:00", "ruta": "R18"},
    
    {"origen": "Tabossi", "destino": "Paraná", "hora": "13:00", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "16:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Paraná", "hora": "22:50", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "15:00", "ruta": "R18"},
    {"origen": "Paraná", "destino": "Estación Sosa", "hora": "17:00", "ruta": "R18"},
    
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "14:30", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "17:00", "ruta": "R18"},
    {"origen": "Estación Sosa", "destino": "Paraná", "hora": "19:00", "ruta": "R18"},
    
    {"origen": "Paraná", "destino": "María Grande", "hora": "07:45", "ruta": "R10"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "10:00", "ruta": "R10"},
    
    {"origen": "Paraná", "destino": "María Grande", "hora": "12:30", "ruta": "R18"},
    {"origen": "Paraná", "destino": "María Grande", "hora": "17:00", "ruta": "R18"},
    
    {"origen": "María Grande", "destino": "Paraná", "hora": "09:10", "ruta": "R10"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "12:00", "ruta": "R10"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "14:50", "ruta": "R10"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "19:25", "ruta": "R10"},
    
    {"origen": "María Grande", "destino": "Paraná", "hora": "16:25", "ruta": "R18"},
    {"origen": "María Grande", "destino": "Paraná", "hora": "20:55", "ruta": "R18"},
]

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================
def hora_a_minutos(h):
    if not h: return None
    hh, mm = map(int, h.split(':'))
    return hh*60 + mm

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
        texto += "🛣️ *Por Ruta 10 (vía María Grande)*:\n" + "\n".join([f"• {h}" for h in resultados["R10"]]) + "\n\n"
    if resultados["R18"]:
        texto += "🛣️ *Por Ruta 18 (con paradas)*:\n" + "\n".join([f"• {h}" for h in resultados["R18"]]) + "\n\n"
    texto += "😊 ¿Necesitas precio, duración, próximo o último?"
    return texto

# ============================================
# FUNCIONES DE RESPUESTA (MEJORADAS)
# ============================================

def mostrar_menu():
    return (
        "👋 *Hola! Soy el asistente virtual de Empresa Fluviales* 🚌\n\n"
        "¿Qué querés hacer hoy?\n\n"
        "🔹 *1* → Ver horarios de colectivos\n"
        "🔹 *2* → Consultar precios de pasajes\n"
        "🔹 *3* → Información útil (terminales, teléfono)\n"
        "🔹 *4* → Preguntas frecuentes (equipaje, mascotas, etc.)\n\n"
        "📝 *También podés escribir directamente:*\n"
        "• 'De Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n"
        "• 'Próximo de Tabossi a Parana'\n"
        "• 'Último de Parana a Sosa el 17/03'\n\n"
        "💬 *Escribí 'Ayuda' si querés más detalles.*"
    )

def mostrar_ayuda_detallada():
    return (
        "📘 *GUÍA COMPLETA DE USO DEL BOT*\n\n"
        "✅ *FRASES QUE SÍ FUNCIONAN:*\n"
        "• 'De Parana a Viale'\n"
        "• 'Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n"
        "• 'Próximo de Tabossi a Parana'\n"
        "• 'Último de Parana a Sosa el 17/03'\n"
        "• 'Horarios de Parana a Tabossi después de las 15'\n\n"
        "❌ *FRASES QUE NO FUNCIONAN (ERRORES COMUNES):*\n"
        "• 'Parana Viale' → ❌ Falta la palabra 'a'\n"
        "• 'Quiero ir a Viale' → ❌ Falta el origen\n"
        "• 'De Parana a Buenos Aires' → ❌ Localidad no válida\n"
        "• 'Primero' → ❌ Falta origen y destino\n"
        "• 'Precio' → ❌ Falta origen y destino\n\n"
        "💡 *CONSEJOS PARA EVITAR ERRORES:*\n"
        "• Usá siempre el formato *'De X a Y'* o *'X a Y'*\n"
        "• Las localidades válidas son: Parana, Viale, Tabossi, Sosa, Maria Grande, Genolet, Sauce, 3 Bocas, Quebracho, El Ramblón, Aldea San Antonio, Paraje de las Piedras, Arroyo Carmona, Sauce Montrull\n"
        "• Podés escribir con o sin tildes (ej: 'Maria' funciona igual que 'María')\n"
        "• Para fechas específicas, usá formato *'17/03'* o *'17 de marzo'*\n\n"
        "📌 *EJEMPLOS DE CONSULTAS AVANZADAS:*\n"
        "• 'Cual es el primer colectivo de Parana a Viale el 20/03'\n"
        "• 'El próximo de Maria Grande a Parana'\n"
        "• 'Último de Tabossi a Parana mañana'\n"
        "• 'Precio de Genolet a Sauce'\n\n"
        "👋 *Escribí 'Hola' para volver al menú principal.*"
    )

def no_entendido():
    return (
        "🤔 *Ups! No entendí lo que escribiste.*\n\n"
        "Intentá con frases como:\n"
        "• 'De Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n\n"
        "O escribí *'Ayuda'* para ver la guía completa."
    )

def mostrar_faq():
    return (
        "❓ *Preguntas frecuentes*\n\n"
        "Escribí la palabra clave que te interese:\n\n"
        "💰 *pago* – Medios de pago aceptados\n"
        "🧳 *equipaje* – Límite de bultos\n"
        "🐕 *mascota* – Cómo viajan las mascotas\n"
        "👮 *boleto seguro* – Para policías y menores\n"
        "👶 *menores* – Pasajes para niños\n"
        "📞 *objetos perdidos* – Dónde reclamar\n"
        "💺 *asiento* – Asignación de asientos\n"
        "📝 *reclamo* – Cómo hacer un reclamo\n\n"
        "➡️ Ej: 'pago', 'equipaje', 'mascota'"
    )

def mostrar_info_util():
    return (
        "📌 *Información útil*\n\n"
        "📍 *Terminal Paraná:* Av. Ramírez 1200\n"
        "📍 *Terminal María Grande:* San Martín 450\n"
        "📍 *Terminal Viale:* (pendiente)\n\n"
        "📞 *Teléfono de contacto:* 343 456-7890\n"
        "⏰ *Atención:* Lun a Dom 6:00 a 22:00\n\n"
        "🌐 *Web:* www.fluviales.com.ar"
    )

def despedida():
    return (
        "😊 *¡Gracias por consultar!*\n\n"
        "Si necesitás algo más, ya sabés dónde encontrarme.\n"
        "Escribí *'Hola'* para empezar de nuevo."
    )

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
                "• **Menores de 5 años** que viajen en el regazo de un adulto abonan un **seguro mínimo** ($1.852).\n"
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

        if sender not in session:
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
        ctx = session[sender]

        # Comandos rápidos
        if incoming_msg.lower() == "/estadisticas" and sender == NUMERO_DUENIO:
            msg.body("📊 Estadísticas: (implementar)")
            return str(resp)

        if any(p in incoming_msg.lower() for p in ["chau", "adiós", "adios", "bye", "gracias"]):
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
            msg.body(despedida())
            return str(resp)

        faq = responder_faq(incoming_msg)
        if faq:
            msg.body(faq)
            return str(resp)

        # Menú
        if incoming_msg == "1":
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "esperando_origen_horarios", "intencion": None, "fecha_pendiente": None}
            msg.body("📝 Decime de dónde a dónde querés viajar (ej: De Viale a Parana)")
            return str(resp)
        if incoming_msg == "2":
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "esperando_origen_precios", "intencion": None, "fecha_pendiente": None}
            msg.body("📝 Decime de dónde a dónde querés viajar (ej: De Viale a Parana)")
            return str(resp)
        if incoming_msg == "3":
            msg.body(mostrar_info_util())
            return str(resp)
        if incoming_msg == "4":
            msg.body(mostrar_faq())
            return str(resp)

        if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes"]:
            msg.body(mostrar_menu())
            return str(resp)

        if incoming_msg.lower() == "ayuda":
            msg.body(mostrar_ayuda_detallada())
            return str(resp)

        # Procesar según estado
        if ctx.get("estado") == "esperando_origen_precios":
            origen, destino = extraer_origen_destino(incoming_msg)
            if origen and destino:
                precio = obtener_precio(origen, destino)
                if isinstance(precio, dict):
                    msg.body(f"💰 El pasaje de {origen} a {destino} tiene dos precios:\n\n🛣️ Ruta 10: $8.580\n🛣️ Ruta 18: $9.900")
                elif precio:
                    msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {origen} a {destino}.")
                session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
                return str(resp)
            else:
                msg.body(no_entendido())
                return str(resp)

        if ctx.get("estado") == "esperando_origen_horarios":
            origen, destino = extraer_origen_destino(incoming_msg)
            if origen and destino:
                fecha = ctx.get("fecha_pendiente") or interpretar_fecha(incoming_msg)
                tipo_dia = obtener_tipo_dia(fecha)
                intencion = ctx.get("intencion")
                hora_limite = extraer_hora_limite(incoming_msg) if not intencion else None
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_limite)
                fecha_str = fecha.strftime("%d/%m/%Y")

                if intencion == "primer":
                    if resultados["R10"] or resultados["R18"]:
                        primer = "99:99"
                        ruta = ""
                        if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(primer):
                            primer, ruta = resultados["R10"][0], "R10"
                        if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(primer):
                            primer, ruta = resultados["R18"][0], "R18"
                        msg.body(f"🚌 El primer colectivo de {origen} a {destino} el {fecha_str} sale a las {primer} por {ruta}.")
                    else:
                        msg.body(f"😕 No hay servicios de {origen} a {destino} para {fecha_str}.")
                
                elif intencion == "proximo":
                    ahora = ahora_argentina()
                    hora_actual = ahora.hour*60 + ahora.minute
                    resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual)
                    if resultados["R10"] or resultados["R18"]:
                        # Combinar todos los horarios y ordenarlos
                        todos = []
                        for h in resultados["R10"]:
                            todos.append((h, "R10"))
                        for h in resultados["R18"]:
                            todos.append((h, "R18"))
                        todos.sort(key=lambda x: hora_a_minutos(x[0]))
                        
                        if todos:
                            prox_hora, prox_ruta = todos[0]
                            msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox_hora} por {prox_ruta}.")
                        else:
                            msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                    else:
                        msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                
                elif intencion == "ultimo":
                    if resultados["R10"] or resultados["R18"]:
                        ult = "00:00"
                        ruta = ""
                        if resultados["R10"] and hora_a_minutos(resultados["R10"][-1]) > hora_a_minutos(ult):
                            ult, ruta = resultados["R10"][-1], "R10"
                        if resultados["R18"] and hora_a_minutos(resultados["R18"][-1]) > hora_a_minutos(ult):
                            ult, ruta = resultados["R18"][-1], "R18"
                        msg.body(f"🚌 El último colectivo de {origen} a {destino} el {fecha_str} sale a las {ult} por {ruta}.")
                    else:
                        msg.body(f"😕 No hay servicios de {origen} a {destino} para {fecha_str}.")
                else:
                    msg.body(formatear_horarios(resultados, origen, destino, fecha_str))
                
                session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
                return str(resp)
            else:
                msg.body(no_entendido())
                return str(resp)

        # Consulta directa
        intencion = detectar_intencion(incoming_msg)
        fecha = interpretar_fecha(incoming_msg)
        origen, destino = extraer_origen_destino(incoming_msg)

        if origen and destino:
            tipo_dia = obtener_tipo_dia(fecha)
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
                precio = obtener_precio(origen, destino)
                if isinstance(precio, dict):
                    msg.body(f"💰 El pasaje de {origen} a {destino} tiene dos precios:\n\n🛣️ Ruta 10: $8.580\n🛣️ Ruta 18: $9.900")
                elif precio:
                    msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {origen} a {destino}.")
                session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
                return str(resp)

            hora_limite = extraer_hora_limite(incoming_msg) if not intencion else None
            resultados = buscar_horarios(origen, destino, tipo_dia, hora_limite)
            fecha_str = fecha.strftime("%d/%m/%Y")

            if intencion == "primer":
                if resultados["R10"] or resultados["R18"]:
                    primer = "99:99"
                    ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][0]) < hora_a_minutos(primer):
                        primer, ruta = resultados["R10"][0], "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][0]) < hora_a_minutos(primer):
                        primer, ruta = resultados["R18"][0], "R18"
                    msg.body(f"🚌 El primer colectivo de {origen} a {destino} el {fecha_str} sale a las {primer} por {ruta}.")
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} para {fecha_str}.")
            
            elif intencion == "proximo":
                ahora = ahora_argentina()
                hora_actual = ahora.hour*60 + ahora.minute
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual)
                if resultados["R10"] or resultados["R18"]:
                    # Combinar todos los horarios y ordenarlos
                    todos = []
                    for h in resultados["R10"]:
                        todos.append((h, "R10"))
                    for h in resultados["R18"]:
                        todos.append((h, "R18"))
                    todos.sort(key=lambda x: hora_a_minutos(x[0]))
                    
                    if todos:
                        prox_hora, prox_ruta = todos[0]
                        msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox_hora} por {prox_ruta}.")
                    else:
                        msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                else:
                    msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
            
            elif intencion == "ultimo":
                if resultados["R10"] or resultados["R18"]:
                    ult = "00:00"
                    ruta = ""
                    if resultados["R10"] and hora_a_minutos(resultados["R10"][-1]) > hora_a_minutos(ult):
                        ult, ruta = resultados["R10"][-1], "R10"
                    if resultados["R18"] and hora_a_minutos(resultados["R18"][-1]) > hora_a_minutos(ult):
                        ult, ruta = resultados["R18"][-1], "R18"
                    msg.body(f"🚌 El último colectivo de {origen} a {destino} el {fecha_str} sale a las {ult} por {ruta}.")
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} para {fecha_str}.")
            else:
                msg.body(formatear_horarios(resultados, origen, destino, fecha_str))
            
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
            return str(resp)

        if intencion and not origen:
            ctx["estado"] = "esperando_origen_horarios"
            ctx["intencion"] = intencion
            ctx["fecha_pendiente"] = fecha
            session[sender] = ctx
            msg.body("📝 Decime de dónde a dónde querés viajar.")
            return str(resp)

        msg.body(no_entendido())
        return str(resp)

    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
        resp = MessagingResponse()
        resp.message().body("⚠️ Ocurrió un error. Intentá de nuevo.")
        return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Bot listo en puerto {port} - VERSIÓN CORREGIDA (PROXIMO)")
    app.run(host='0.0.0.0', port=port, debug=False)
