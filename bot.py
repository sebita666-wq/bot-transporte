from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import re
import json
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'
app.permanent_session_lifetime = timedelta(minutes=3)

print("🚀 BOT INICIADO - CHECKPOINT 2 (CORREGIDO: PRÓXIMO/ÚLTIMO/PRIMER)")

# ============================================
# CONFIGURACIÓN
# ============================================
NUMERO_DUENIO = "whatsapp:+5493434727811"
STATS_FILE = 'estadisticas.json'

# ============================================
# ESTADÍSTICAS DE USO
# ============================================

def cargar_estadisticas():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "usuarios": {},
        "metricas": {
            "total_usuarios_unicos": 0,
            "total_mensajes": 0,
            "ultimo_reinicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

def guardar_estadisticas(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def registrar_interaccion(sender, mensaje, tipo_consulta=None):
    stats = cargar_estadisticas()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if sender not in stats["usuarios"]:
        stats["usuarios"][sender] = {
            "primer_contacto": ahora,
            "ultimo_contacto": ahora,
            "mensajes": 1,
            "consultas": [tipo_consulta] if tipo_consulta else []
        }
        stats["metricas"]["total_usuarios_unicos"] += 1
        print(f"📊 NUEVO USUARIO REGISTRADO: {sender}")
    else:
        stats["usuarios"][sender]["ultimo_contacto"] = ahora
        stats["usuarios"][sender]["mensajes"] += 1
        if tipo_consulta and tipo_consulta not in stats["usuarios"][sender]["consultas"]:
            stats["usuarios"][sender]["consultas"].append(tipo_consulta)
    
    stats["metricas"]["total_mensajes"] += 1
    guardar_estadisticas(stats)

def obtener_resumen_estadisticas():
    stats = cargar_estadisticas()
    ahora = datetime.now()
    hoy = ahora.strftime("%Y-%m-%d")
    semana_pasada = (ahora - timedelta(days=7)).strftime("%Y-%m-%d")
    
    usuarios_hoy = sum(1 for u in stats["usuarios"].values() 
                      if u["ultimo_contacto"].startswith(hoy))
    usuarios_semana = sum(1 for u in stats["usuarios"].values() 
                         if u["ultimo_contacto"][:10] >= semana_pasada)
    
    return {
        "total_usuarios": stats["metricas"]["total_usuarios_unicos"],
        "total_mensajes": stats["metricas"]["total_mensajes"],
        "usuarios_hoy": usuarios_hoy,
        "usuarios_semana": usuarios_semana,
        "ultimo_reinicio": stats["metricas"]["ultimo_reinicio"]
    }

# ============================================
# HORARIOS ACTUALIZADOS
# ============================================

tramos = [
    # DÍAS HÁBILES - RUTA 18
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "04:50", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "05:10", "dia": "habiles", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "05:45", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "06:05", "dia": "habiles", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "07:00", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "07:20", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "08:15", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "10:25", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:00", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:30", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:40", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:00", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "18:35", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "19:40", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "dia": "habiles", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "22:45", "dia": "habiles", "ruta": "R18"},
    {"origen": "A. San Antonio", "destino": "Parana", "hora_salida": "23:15", "dia": "habiles", "ruta": "R18"},
    {"origen": "Parana", "destino": "A. San Antonio", "hora_salida": "23:30", "dia": "habiles", "ruta": "R18"},

    # DÍAS SÁBADOS - RUTA 18
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "06:15", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "06:30", "dia": "sabados", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "07:00", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "07:20", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "08:15", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "09:40", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "10:55", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:10", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:45", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "14:40", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:15", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "16:15", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:00", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "18:10", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "19:55", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:30", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "22:15", "dia": "sabados", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "23:00", "dia": "sabados", "ruta": "R18"},
    {"origen": "A. San Antonio", "destino": "Parana", "hora_salida": "23:15", "dia": "sabados", "ruta": "R18"},
    {"origen": "Parana", "destino": "A. San Antonio", "hora_salida": "23:30", "dia": "sabados", "ruta": "R18"},

    # DÍAS DOMINGOS - RUTA 18
    {"origen": "Viale", "destino": "Parana", "hora_salida": "08:45", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "09:40", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "10:55", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:10", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:45", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "14:40", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:15", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "16:15", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:00", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "18:10", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "19:55", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:30", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "22:15", "dia": "domingos", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "23:00", "dia": "domingos", "ruta": "R18"},
    {"origen": "A. San Antonio", "destino": "Parana", "hora_salida": "23:15", "dia": "domingos", "ruta": "R18"},
    {"origen": "Parana", "destino": "A. San Antonio", "hora_salida": "23:30", "dia": "domingos", "ruta": "R18"},

    # DÍAS DOMINGOS - RUTA 10
    {"origen": "Viale", "destino": "Parana", "hora_salida": "08:45", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "09:40", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "10:55", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:10", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:45", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "14:40", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:15", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "16:15", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:00", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "18:10", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "19:55", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:30", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "22:15", "dia": "domingos", "ruta": "R10"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "23:00", "dia": "domingos", "ruta": "R10"},
    {"origen": "A. San Antonio", "destino": "Parana", "hora_salida": "23:15", "dia": "domingos", "ruta": "R10"},
    {"origen": "Parana", "destino": "A. San Antonio", "hora_salida": "23:30", "dia": "domingos", "ruta": "R10"},
]

# ============================================
# TABLA DE PRECIOS
# ============================================

precios = {
    ("Parana", "Viale"): 1200,
    ("Viale", "Parana"): 1200,
    ("Parana", "Tabossi"): 1500,
    ("Tabossi", "Parana"): 1500,
    ("Parana", "Sosa"): 1800,
    ("Sosa", "Parana"): 1800,
    ("Parana", "Maria Grande"): 2000,
    ("Maria Grande", "Parana"): 2000,
    ("Viale", "Tabossi"): 400,
    ("Tabossi", "Viale"): 400,
    ("Viale", "Sosa"): 700,
    ("Sosa", "Viale"): 700,
    ("Viale", "Maria Grande"): 900,
    ("Maria Grande", "Viale"): 900,
    ("Tabossi", "Sosa"): 300,
    ("Sosa", "Tabossi"): 300,
    ("Tabossi", "Maria Grande"): 600,
    ("Maria Grande", "Tabossi"): 600,
    ("Sosa", "Maria Grande"): 300,
    ("Maria Grande", "Sosa"): 300,
    ("A. San Antonio", "Parana"): 500,
    ("Parana", "A. San Antonio"): 500,
}

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================

def hora_a_minutos(hora_str):
    if not hora_str:
        return None
    h, m = map(int, hora_str.split(':'))
    return h * 60 + m

def minutos_a_hora(minutos):
    if minutos is None:
        return ""
    h = minutos // 60
    m = minutos % 60
    return f"{h:02d}:{m:02d}"

def normalizar_texto(texto):
    texto = texto.lower()
    replacements = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n'}
    for acentuada, normal in replacements.items():
        texto = texto.replace(acentuada, normal)
    return texto

def extraer_origen_destino(mensaje):
    mensaje_original = mensaje
    mensaje = normalizar_texto(mensaje)
    mensaje = re.sub(r'[¿?!¡.,;:\s]+$', '', mensaje)
    
    localidades_validas = ["parana", "viale", "tabossi", "sosa", "maria grande", "a. san antonio", "aldea san antonio"]
    
    patron_de_a = r'de\s+([a-z]+(?:\s+[a-z]+\.?)?)\s+a\s+([a-z]+(?:\s+[a-z]+\.?)?)'
    match = re.search(patron_de_a, mensaje)
    
    if match:
        origen = match.group(1).strip()
        destino = match.group(2).strip()
        
        if origen in localidades_validas and destino in localidades_validas:
            origen = origen.title()
            destino = destino.title()
            if origen == "A. San Antonio" or origen == "Aldea San Antonio":
                origen = "A. San Antonio"
            if destino == "A. San Antonio" or destino == "Aldea San Antonio":
                destino = "A. San Antonio"
            print(f"✅ EXTRAÍDO: {origen} -> {destino}")
            return origen, destino
    
    patron_simple = r'^([a-z]+(?:\s+[a-z]+\.?)?)\s+a\s+([a-z]+(?:\s+[a-z]+\.?)?)$'
    match = re.search(patron_simple, mensaje)
    
    if match:
        origen = match.group(1).strip()
        destino = match.group(2).strip()
        
        if origen in localidades_validas and destino in localidades_validas:
            origen = origen.title()
            destino = destino.title()
            if origen == "A. San Antonio" or origen == "Aldea San Antonio":
                origen = "A. San Antonio"
            if destino == "A. San Antonio" or destino == "Aldea San Antonio":
                destino = "A. San Antonio"
            print(f"✅ EXTRAÍDO: {origen} -> {destino}")
            return origen, destino
    
    print(f"❌ NO EXTRAJO: '{mensaje_original}'")
    return None, None

def extraer_hora_limite(mensaje):
    mensaje = mensaje.lower()
    patrones = [
        r'(?:después|despues|a partir)\s+de\s+las?\s*(\d{1,2})(?::(\d{2}))?',
        r'(?:>|mayor a|mayor que)\s*(\d{1,2})(?::(\d{2}))?',
        r'(\d{1,2})(?::(\d{2}))?\s*(?:en adelante|para adelante|hacia adelante)'
    ]
    for patron in patrones:
        match = re.search(patron, mensaje)
        if match:
            hora = int(match.group(1))
            minutos = int(match.group(2)) if match.group(2) else 0
            print(f"⏰ HORA LÍMITE: {hora:02d}:{minutos:02d}")
            return hora * 60 + minutos
    return None

def interpretar_fecha(mensaje):
    mensaje = mensaje.lower()
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if "hoy" in mensaje:
        print(f"📅 FECHA: Hoy ({hoy.strftime('%d/%m/%Y')})")
        return hoy
    if "mañana" in mensaje or "manana" in mensaje:
        manana = hoy + timedelta(days=1)
        print(f"📅 FECHA: Mañana ({manana.strftime('%d/%m/%Y')})")
        return manana
    
    dias_semana = {"lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
                   "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6}
    for dia_nombre, dia_num in dias_semana.items():
        if dia_nombre in mensaje:
            fecha = hoy + timedelta(days=(dia_num - hoy.weekday() + 7) % 7)
            print(f"📅 FECHA: Próximo {dia_nombre} ({fecha.strftime('%d/%m/%Y')})")
            return fecha
    
    print(f"📅 FECHA: Hoy por defecto ({hoy.strftime('%d/%m/%Y')})")
    return hoy

def obtener_tipo_dia(fecha):
    if fecha.weekday() < 5:
        return "habiles"
    elif fecha.weekday() == 5:
        return "sabados"
    else:
        return "domingos"

def buscar_tramos(origen, destino, tipo_dia, hora_limite=None, ruta=None):
    print(f"🔍 BUSCANDO TRAMOS: {origen} -> {destino} | día: {tipo_dia} | hora_limite: {hora_limite}")
    resultados = []
    for t in tramos:
        if t["origen"] == origen and t["destino"] == destino and t["dia"] == tipo_dia:
            if ruta is None or t.get("ruta") == ruta:
                hora_min = hora_a_minutos(t["hora_salida"])
                if hora_limite is None or hora_min >= hora_limite:
                    print(f"  → Encontrado: {t['hora_salida']} ({t.get('ruta', '')})")
                    resultados.append(t)
    resultados.sort(key=lambda x: hora_a_minutos(x["hora_salida"]))
    print(f"  → Total: {len(resultados)} resultados")
    return resultados

def obtener_precio(origen, destino):
    precio = precios.get((origen, destino))
    print(f"💰 PRECIO {origen}->{destino}: {precio}")
    return precio

def primer_colectivo(origen, destino, tipo_dia):
    print(f"🔍 BUSCANDO PRIMER COLECTIVO: {origen} -> {destino}")
    resultados = buscar_tramos(origen, destino, tipo_dia)
    if resultados:
        print(f"  → PRIMERO: {resultados[0]['hora_salida']}")
        return resultados[0]
    print(f"  → No hay servicios")
    return None

def proximo_colectivo(origen, destino, tipo_dia):
    ahora = datetime.now()
    hora_actual_min = ahora.hour * 60 + ahora.minute
    print(f"🕐 HORA ACTUAL: {ahora.strftime('%H:%M')} ({hora_actual_min} minutos)")
    resultados = buscar_tramos(origen, destino, tipo_dia, hora_actual_min)
    if resultados:
        print(f"  → PRÓXIMO: {resultados[0]['hora_salida']}")
        return resultados[0]
    print(f"  → No hay más servicios hoy")
    return None

def ultimo_colectivo(origen, destino, tipo_dia):
    print(f"🔍 BUSCANDO ÚLTIMO COLECTIVO: {origen} -> {destino}")
    resultados = buscar_tramos(origen, destino, tipo_dia)
    if resultados:
        print(f"  → ÚLTIMO: {resultados[-1]['hora_salida']}")
        return resultados[-1]
    print(f"  → No hay servicios")
    return None

def formatear_horarios(resultados):
    if not resultados:
        return None
    texto = ""
    for r in resultados[:8]:
        ruta_text = f" ({r['ruta']})" if r.get('ruta') else ""
        texto += f"• {r['hora_salida']}{ruta_text}\n"
    return texto

def responder_pregunta_frecuente(mensaje):
    mensaje = mensaje.lower()
    if any(p in mensaje for p in ["tarjeta", "credito", "debito", "pago"]):
        print("💳 RESPUESTA: Pregunta sobre tarjeta")
        return "💳 Aceptamos efectivo y tarjetas en terminal. A bordo solo efectivo."
    if any(p in mensaje for p in ["wifi", "internet", "conexion"]):
        print("📶 RESPUESTA: Pregunta sobre WiFi")
        return "📶 Todos los colectivos tienen WiFi gratis."
    if any(p in mensaje for p in ["qr", "mercadopago"]):
        print("📱 RESPUESTA: Pregunta sobre QR")
        return "📱 Próximamente pago con QR. Por ahora efectivo y tarjeta."
    if any(p in mensaje for p in ["perro", "mascota", "animal"]):
        print("🐕 RESPUESTA: Pregunta sobre mascotas")
        return "🐕 Mascotas viajan en jaula o bolso. Perros de asistencia sin restricción."
    if any(p in mensaje for p in ["equipaje", "valija", "encomienda"]):
        print("🧳 RESPUESTA: Pregunta sobre equipaje")
        return "🧳 Hasta 10kg de equipaje sin cargo. Encomiendas con costo adicional."
    return None

# ============================================
# FUNCIONES DE RESPUESTA
# ============================================

def mostrar_menu():
    return ("👋 Hola, soy el asistente de la empresa de transporte.\n\n"
            "Elegí una opción:\n\n"
            "1️⃣ Ver horarios\n"
            "2️⃣ Consultar precios\n"
            "3️⃣ Información útil\n"
            "4️⃣ Preguntas frecuentes\n\n"
            "O escribí directamente lo que necesitas, por ejemplo:\n"
            "• 'De Viale a Parana'\n"
            "• 'De Tabossi a María Grande'\n"
            "• 'Precio de Paraná a A. San Antonio'")

def preguntar_origen_destino(tipo):
    if tipo == "horarios":
        return "📝 Decime de dónde a dónde querés viajar (ej: De Viale a Parana)"
    return "📝 Decime de dónde a dónde querés viajar para consultar el precio (ej: De Viale a Parana)"

def mostrar_info_util():
    return ("📌 *Información útil*\n\n"
            "📍 Terminal Paraná: Av. Ramírez 1200\n"
            "📍 Terminal María Grande: San Martín 450\n"
            "📞 Teléfono: 343 456-7890\n"
            "⏰ Atención: Lun a Vie 8 a 18hs\n"
            "🌐 Web: www.transporteviale.com.ar")

def mostrar_faq():
    return ("❓ *Preguntas frecuentes*\n\n"
            "• ¿Cómo pago el boleto? Efectivo al subir o en terminal con tarjeta.\n"
            "• ¿Hay descuentos para estudiantes? Sí, 50% presentando certificado.\n"
            "• ¿Se puede llevar encomienda? Sí, hasta 10kg por pasajero.\n"
            "• ¿Los perros viajan? Sí, en jaula o bolso transportador.")

def despedida():
    return "😊 ¡Gracias por consultar! Cuando necesites algo, escribime 'Hola'. ¡Buen viaje!"

def no_entendido():
    return ("🤔 No entendí bien tu consulta.\n\n"
            "Podés escribir:\n"
            "• 'Hola' para ver el menú\n"
            "• 'De Viale a Parana' para horarios\n"
            "• 'De Tabossi a María Grande'\n"
            "• 'Precio de Paraná a A. San Antonio'")

def resetear_contexto(sender):
    session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu"}
    print(f"🔄 CONTEXTO REINICIADO para {sender}")

# ============================================
# WEBHOOK PRINCIPAL
# ============================================

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    print(f"\n📩 MENSAJE RECIBIDO: '{incoming_msg}' de {sender}")
    
    resp = MessagingResponse()
    msg = resp.message()
    
    registrar_interaccion(sender, incoming_msg)
    
    if sender not in session:
        print("🆕 NUEVA SESIÓN")
        session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu"}
    
    contexto = session[sender]
    print(f"📌 CONTEXTO: {contexto}")
    
    # ============================================
    # COMANDO PARA EL DUEÑO (ESTADÍSTICAS)
    # ============================================
    if incoming_msg.lower() == "/estadisticas" and sender == NUMERO_DUENIO:
        print("✅ CASO: ESTADÍSTICAS")
        resumen = obtener_resumen_estadisticas()
        msg.body(
            f"📊 *Estadísticas del bot*\n\n"
            f"👥 Usuarios únicos totales: {resumen['total_usuarios']}\n"
            f"💬 Mensajes totales: {resumen['total_mensajes']}\n"
            f"📅 Usuarios hoy: {resumen['usuarios_hoy']}\n"
            f"📆 Usuarios última semana: {resumen['usuarios_semana']}\n"
            f"🔄 Último reinicio: {resumen['ultimo_reinicio']}"
        )
        return str(resp)
    
    # ============================================
    # RESETEO
    # ============================================
    if any(p in incoming_msg.lower() for p in ["chau", "adiós", "adios", "bye"]):
        print("✅ CASO: DESPEDIDA")
        resetear_contexto(sender)
        msg.body(despedida())
        return str(resp)
    
    if "gracias" in incoming_msg.lower():
        print("✅ CASO: AGRADECIMIENTO")
        resetear_contexto(sender)
        msg.body(despedida())
        return str(resp)
    
    if incoming_msg.lower() in ["menu", "reiniciar", "reset", "empezar", "inicio"]:
        print("✅ CASO: REINICIO MANUAL")
        resetear_contexto(sender)
        msg.body(mostrar_menu())
        return str(resp)
    
    # ============================================
    # PREGUNTAS FRECUENTES SUELTAS
    # ============================================
    faq_resp = responder_pregunta_frecuente(incoming_msg)
    if faq_resp:
        print("✅ CASO: PREGUNTA FRECUENTE SUELTA")
        registrar_interaccion(sender, incoming_msg, "faq")
        msg.body(faq_resp)
        return str(resp)
    
    # ============================================
    # OPCIONES NUMÉRICAS
    # ============================================
    if incoming_msg == "1":
        print("✅ CASO: OPCIÓN 1 - HORARIOS")
        resetear_contexto(sender)
        msg.body(preguntar_origen_destino("horarios"))
        return str(resp)
    
    if incoming_msg == "2":
        print("✅ CASO: OPCIÓN 2 - PRECIOS")
        resetear_contexto(sender)
        msg.body(preguntar_origen_destino("precios"))
        return str(resp)
    
    if incoming_msg == "3":
        print("✅ CASO: OPCIÓN 3 - INFORMACIÓN ÚTIL")
        msg.body(mostrar_info_util())
        return str(resp)
    
    if incoming_msg == "4":
        print("✅ CASO: OPCIÓN 4 - PREGUNTAS FRECUENTES")
        msg.body(mostrar_faq())
        return str(resp)
    
    # ============================================
    # SALUDO
    # ============================================
    if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes", "ayuda"]:
        print("✅ CASO: SALUDO")
        msg.body(mostrar_menu())
        return str(resp)
    
    # ============================================
    # PROCESAR SEGÚN ESTADO
    # ============================================
    
    if contexto.get("estado") == "esperando_origen_precios":
        print("🔍 Procesando respuesta para PRECIO...")
        origen, destino = extraer_origen_destino(incoming_msg)
        if origen and destino:
            precio = obtener_precio(origen, destino)
            if precio:
                msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
            else:
                msg.body(f"😕 No tengo precio de {origen} a {destino}.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            contexto["estado"] = "menu"
            session[sender] = contexto
            return str(resp)
        else:
            msg.body("🤔 No entendí. Por favor, escribí algo como 'De Viale a Parana'")
            return str(resp)
    
    if contexto.get("estado") == "esperando_origen_horarios":
        print("🔍 Procesando respuesta para HORARIOS...")
        origen, destino = extraer_origen_destino(incoming_msg)
        if origen and destino:
            fecha = interpretar_fecha(incoming_msg)
            tipo_dia = obtener_tipo_dia(fecha)
            hora_limite = extraer_hora_limite(incoming_msg)
            resultados = buscar_tramos(origen, destino, tipo_dia, hora_limite)
            if resultados:
                fecha_str = fecha.strftime("%d/%m/%Y")
                if hora_limite:
                    texto = f"🚌 Horarios de {origen} a {destino} después de {minutos_a_hora(hora_limite)} ({tipo_dia}):\n"
                else:
                    texto = f"🚌 Horarios de {origen} a {destino} para {fecha_str} ({tipo_dia}):\n"
                texto += formatear_horarios(resultados)
                msg.body(texto)
            else:
                msg.body(f"😕 No encontré horarios de {origen} a {destino} para {tipo_dia}.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            contexto["estado"] = "menu"
            session[sender] = contexto
            return str(resp)
        else:
            msg.body("🤔 No entendí. Por favor, escribí algo como 'De Viale a Parana'")
            return str(resp)
    
    # ============================================
    # NUEVA CONSULTA DIRECTA
    # ============================================
    print("🔍 Intentando extraer origen/destino...")
    origen, destino = extraer_origen_destino(incoming_msg)
    if origen and destino:
        print(f"✅ CONSULTA DIRECTA: {origen} -> {destino}")
        fecha = interpretar_fecha(incoming_msg)
        tipo_dia = obtener_tipo_dia(fecha)
        
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "$"]):
            print("  → Es consulta de PRECIO")
            precio = obtener_precio(origen, destino)
            if precio:
                msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
            else:
                msg.body(f"😕 No tengo precio de {origen} a {destino}.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            session[sender] = contexto
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["primer", "primero"]):
            print("  → Es consulta de PRIMER")
            primer = primer_colectivo(origen, destino, tipo_dia)
            if primer:
                msg.body(f"🚌 El primer colectivo de {origen} a {destino} sale a las {primer['hora_salida']}.")
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} para hoy.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            session[sender] = contexto
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["próximo", "proximo", "siguiente"]):
            print("  → Es consulta de PRÓXIMO")
            prox = proximo_colectivo(origen, destino, tipo_dia)
            if prox:
                msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox['hora_salida']}.")
            else:
                msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            session[sender] = contexto
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["último", "ultimo", "final"]):
            print("  → Es consulta de ÚLTIMO")
            ult = ultimo_colectivo(origen, destino, tipo_dia)
            if ult:
                msg.body(f"🚌 El último colectivo de {origen} a {destino} sale a las {ult['hora_salida']}.")
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} hoy.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            session[sender] = contexto
            return str(resp)
        
        # Si no es ninguna especial, asumimos horarios
        print("  → Asumiendo consulta de HORARIOS")
        hora_limite = extraer_hora_limite(incoming_msg)
        resultados = buscar_tramos(origen, destino, tipo_dia, hora_limite)
        if resultados:
            fecha_str = fecha.strftime("%d/%m/%Y")
            if hora_limite:
                texto = f"🚌 Horarios de {origen} a {destino} después de {minutos_a_hora(hora_limite)} ({tipo_dia}):\n"
            else:
                texto = f"🚌 Horarios de {origen} a {destino} para {fecha_str} ({tipo_dia}):\n"
            texto += formatear_horarios(resultados)
            msg.body(texto)
        else:
            msg.body(f"😕 No encontré horarios de {origen} a {destino} para {tipo_dia}.")
        contexto["ultimo_origen"] = origen
        contexto["ultimo_destino"] = destino
        session[sender] = contexto
        return str(resp)
    
    # ============================================
    # CONSULTAS SIN CONTEXTO
    # ============================================
    if not contexto["ultimo_origen"]:
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "$", "dura", "tiempo", "próximo", "proximo", "siguiente", "último", "ultimo", "final", "primer", "primero"]):
            print("✅ CASO: CONSULTA SIN CONTEXTO")
            msg.body("📝 Primero decime de dónde a dónde querés viajar. Ej: 'De Viale a Parana'")
            return str(resp)
    
    # ============================================
    # SEGUIMIENTO CON CONTEXTO
    # ============================================
    if contexto["ultimo_origen"] and contexto["ultimo_destino"]:
        o = contexto["ultimo_origen"]
        d = contexto["ultimo_destino"]
        print(f"✅ SEGUIMIENTO: {o}->{d}")
        fecha = datetime.now()
        tipo_dia = obtener_tipo_dia(fecha)
        
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "$"]):
            print("  → SUB-CASO: PRECIO")
            precio = obtener_precio(o, d)
            msg.body(f"💰 El pasaje de {o} a {d} cuesta ${precio}." if precio else f"😕 No tengo precio de {o} a {d}.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["primer", "primero"]):
            print("  → SUB-CASO: PRIMER")
            primer = primer_colectivo(o, d, tipo_dia)
            if primer:
                msg.body(f"🚌 El primer colectivo de {o} a {d} sale a las {primer['hora_salida']}.")
            else:
                msg.body(f"😕 No hay servicios de {o} a {d} hoy.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["próximo", "proximo", "siguiente"]):
            print("  → SUB-CASO: PRÓXIMO")
            prox = proximo_colectivo(o, d, tipo_dia)
            if prox:
                msg.body(f"🚌 El próximo colectivo de {o} a {d} sale a las {prox['hora_salida']}.")
            else:
                msg.body(f"😕 No hay más servicios de {o} a {d} hoy.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["último", "ultimo", "final"]):
            print("  → SUB-CASO: ÚLTIMO")
            ult = ultimo_colectivo(o, d, tipo_dia)
            if ult:
                msg.body(f"🚌 El último colectivo de {o} a {d} sale a las {ult['hora_salida']}.")
            else:
                msg.body(f"😕 No hay servicios de {o} a {d} hoy.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["dura", "tiempo", "demora"]):
            print("  → SUB-CASO: DURACIÓN (pendiente)")
            msg.body(f"⏱️ La duración del viaje de {o} a {d} no está disponible aún.")
            return str(resp)
    
    # ============================================
    # INFORMACIÓN ÚTIL / FAQ
    # ============================================
    if any(p in incoming_msg.lower() for p in ["info", "telefono", "direccion"]):
        print("✅ CASO: INFORMACIÓN ÚTIL")
        msg.body(mostrar_info_util())
        return str(resp)
    
    if any(p in incoming_msg.lower() for p in ["faq", "pregunta", "como", "cómo"]):
        print("✅ CASO: PREGUNTAS FRECUENTES")
        msg.body(mostrar_faq())
        return str(resp)
    
    # ============================================
    # NO ENTENDIDO
    # ============================================
    print("❌ CASO: NO ENTENDIDO")
    msg.body(no_entendido())
    session[sender] = contexto
    return str(resp)

# ============================================
# INICIO
# ============================================

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
