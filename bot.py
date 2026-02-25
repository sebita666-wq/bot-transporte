from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'
app.permanent_session_lifetime = timedelta(minutes=3)

print("🚀 BOT INICIADO - VERSIÓN CORREGIDA (EXTACCIÓN FUNCIONAL)")

# ============================================
# DATOS DEL BOT (horarios, precios, tiempos)
# ============================================

servicios = [
    {"servicio": "1M", "ida": None, "vuelta": {"origen": "Tabossi", "hora": "06:15", "viale": "06:30", "parana": "07:30"}},
    {"servicio": "2M", "ida": {"parana": "04:45", "viale": "05:50", "tabossi": "06:10", "sosa": "06:25", "maria grande": "06:45"}, "vuelta": {"origen": "Maria Grande", "hora": "06:45", "ruta": "R10", "parana": "08:15"}},
    {"servicio": "3M", "ida": {"parana": "05:45", "viale": "06:43", "tabossi": "07:00"}, "vuelta": {"origen": "Tabossi", "hora": "07:00", "viale": "07:20", "parana": "08:30"}},
    {"servicio": "1M", "ida": {"parana": "07:45", "maria grande": "09:10", "ruta": "R10"}, "vuelta": {"origen": "Maria Grande", "hora": "09:10", "sosa": "09:34", "tabossi": "09:48", "viale": "10:07", "parana": "11:15"}},
    {"servicio": "2M", "ida": {"parana": "08:45", "viale": "09:55"}, "vuelta": {"origen": "Viale", "hora": "11:00", "parana": "12:10"}},
    {"servicio": "3M", "ida": {"parana": "10:15", "maria grande": "11:40", "ruta": "R10"}, "vuelta": {"origen": "Maria Grande", "hora": "11:40", "sosa": "12:00", "tabossi": "12:20", "viale": "12:40", "parana": "13:45"}},
    {"servicio": "1M", "ida": {"parana": "11:40", "viale": "12:50"}, "vuelta": {"origen": "Viale", "hora": "13:30", "parana": "14:40"}},
    {"servicio": "2T", "ida": {"parana": "12:40", "viale": "13:40", "tabossi": "14:10", "sosa": "14:30", "maria grande": "14:50"}, "vuelta": {"origen": "Maria Grande", "hora": "14:50", "ruta": "R10", "parana": "16:15"}},
    {"servicio": "3T", "ida": {"parana": "14:00", "viale": "15:00"}, "vuelta": {"origen": "Viale", "hora": "15:15", "parana": "16:15"}},
    {"servicio": "1T", "ida": {"parana": "15:15", "viale": "16:20", "tabossi": "16:35"}, "vuelta": {"origen": "Tabossi", "hora": "16:40", "viale": "17:00", "parana": "18:10"}},
    {"servicio": "3T", "ida": {"parana": "16:30", "viale": "18:00", "tabossi": "18:20", "sosa": "18:40", "maria grande": "19:00", "ruta": "R10"}, "vuelta": {"origen": "Maria Grande", "hora": "18:00", "sosa": "18:20", "tabossi": "18:40", "viale": "19:00", "parana": "20:10"}},
    {"servicio": "2T", "ida": {"parana": "17:00", "viale": "18:10", "tabossi": "18:30", "sosa": "18:45", "maria grande": "19:00"}, "vuelta": {"origen": "Maria Grande", "hora": "19:00", "ruta": "R10", "parana": "20:30"}},
    {"servicio": "1T", "ida": {"parana": "19:30", "viale": "20:40"}, "vuelta": {"origen": "Viale", "hora": "21:00", "parana": "22:05"}},
    {"servicio": "3T", "ida": {"parana": "20:40", "viale": "21:50", "tabossi": "22:15", "sosa": "22:25", "maria grande": "22:40"}, "vuelta": {"origen": "Maria Grande", "hora": "22:45", "sosa": "22:55", "tabossi": "23:15", "viale": "23:40", "parana": "00:40"}},
    {"servicio": "2T", "ida": {"parana": "21:00", "viale": "22:00"}, "vuelta": {"origen": "Viale", "hora": "22:05", "parana": "23:05"}},
    {"servicio": "1T", "ida": {"parana": "22:30", "viale": "23:30"}, "vuelta": None}
]

tiempos_viaje = {
    ("Parana", "Viale"): 70, ("Viale", "Parana"): 70,
    ("Parana", "Tabossi"): 85, ("Tabossi", "Parana"): 85,
    ("Parana", "Sosa"): 105, ("Sosa", "Parana"): 105,
    ("Parana", "Maria Grande"): 120, ("Maria Grande", "Parana"): 90,
    ("Viale", "Tabossi"): 15, ("Tabossi", "Viale"): 15,
    ("Viale", "Sosa"): 35, ("Sosa", "Viale"): 35,
    ("Viale", "Maria Grande"): 50, ("Maria Grande", "Viale"): 50,
    ("Tabossi", "Sosa"): 20, ("Sosa", "Tabossi"): 20,
    ("Tabossi", "Maria Grande"): 35, ("Maria Grande", "Tabossi"): 35,
    ("Sosa", "Maria Grande"): 15, ("Maria Grande", "Sosa"): 15,
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
    """
    Versión mejorada que acepta:
    - "de viale a parana"
    - "viale a parana"
    - "d viale a parana"
    - "De viale a parana" (con mayúsculas)
    """
    mensaje_original = mensaje
    mensaje = normalizar_texto(mensaje)
    mensaje = re.sub(r'[¿?!¡.,;:\s]+$', '', mensaje)
    
    # Lista de localidades válidas (para validación)
    localidades_validas = ["parana", "viale", "tabossi", "sosa", "maria grande"]
    
    # Primero, intentar con el patrón más común "de X a Y"
    patron_de_a = r'de\s+([a-z]+(?:\s+[a-z]+)?)\s+a\s+([a-z]+(?:\s+[a-z]+)?)'
    match = re.search(patron_de_a, mensaje)
    
    if match:
        origen = match.group(1).strip()
        destino = match.group(2).strip()
        
        # Validar que sean localidades conocidas
        if origen in localidades_validas and destino in localidades_validas:
            origen = origen.title()
            destino = destino.title()
            print(f"✅ EXTRAÍDO (patrón 'de a'): {origen} -> {destino}")
            return origen, destino
    
    # Si no funcionó, probar con "X a Y"
    patron_simple = r'^([a-z]+(?:\s+[a-z]+)?)\s+a\s+([a-z]+(?:\s+[a-z]+)?)$'
    match = re.search(patron_simple, mensaje)
    
    if match:
        origen = match.group(1).strip()
        destino = match.group(2).strip()
        
        if origen in localidades_validas and destino in localidades_validas:
            origen = origen.title()
            destino = destino.title()
            print(f"✅ EXTRAÍDO (patrón 'a'): {origen} -> {destino}")
            return origen, destino
    
    # Si tampoco, probar con "X Y" (sin "a")
    patron_xy = r'^([a-z]+(?:\s+[a-z]+)?)\s+([a-z]+(?:\s+[a-z]+)?)$'
    match = re.search(patron_xy, mensaje)
    
    if match:
        origen = match.group(1).strip()
        destino = match.group(2).strip()
        
        if origen in localidades_validas and destino in localidades_validas:
            origen = origen.title()
            destino = destino.title()
            print(f"✅ EXTRAÍDO (patrón XY): {origen} -> {destino}")
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
            print(f"⏰ HORA LÍMITE DETECTADA: {hora:02d}:{minutos:02d}")
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
    
    patron_fecha = r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})'
    match = re.search(patron_fecha, mensaje)
    if match:
        dia, mes, anio = map(int, match.groups())
        try:
            fecha = datetime(anio, mes, dia)
            print(f"📅 FECHA: {fecha.strftime('%d/%m/%Y')}")
            return fecha
        except:
            pass
    
    dias_semana = {"lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
                   "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6}
    for dia_nombre, dia_num in dias_semana.items():
        if dia_nombre in mensaje:
            dias_para_summar = (dia_num - hoy.weekday() + 7) % 7
            fecha = hoy + timedelta(days=dias_para_summar)
            print(f"📅 FECHA: Próximo {dia_nombre} ({fecha.strftime('%d/%m/%Y')})")
            return fecha
    
    print(f"📅 FECHA: Hoy por defecto ({hoy.strftime('%d/%m/%Y')})")
    return hoy

def es_dia_habil(fecha):
    return fecha.weekday() < 5

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
            "• 'Viale a Paraná'\n"
            "• 'De Tabossi a María Grande'\n"
            "• 'Precio de Paraná a María Grande'")

def preguntar_origen_destino(tipo):
    if tipo == "horarios":
        return "📝 Decime de dónde a dónde querés viajar (ej: Viale a Paraná)"
    return "📝 Decime de dónde a dónde querés viajar para consultar el precio (ej: Viale a Paraná)"

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
    return "😊 ¡Gracias por consultar! Cuando necesites algo, escribime 'Hola' para empezar de nuevo. ¡Buen viaje!"

def no_entendido():
    return ("🤔 No entendí bien tu consulta.\n\n"
            "Podés escribir:\n"
            "• 'Hola' para ver el menú\n"
            "• 'Viale a Paraná' para horarios\n"
            "• 'De Tabossi a María Grande'\n"
            "• 'Precio de Paraná a María Grande'")

def resetear_contexto(sender):
    session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "ultima_fecha": None}
    print(f"🔄 CONTEXTO REINICIADO para {sender}")

# ============================================
# FUNCIONES DE NEGOCIO
# ============================================

def obtener_precio(origen, destino):
    precios = {
        ("Viale", "Parana"): 1200, ("Parana", "Viale"): 1200,
        ("Tabossi", "Parana"): 1500, ("Parana", "Tabossi"): 1500,
        ("Sosa", "Parana"): 1800, ("Parana", "Sosa"): 1800,
        ("Maria Grande", "Parana"): 2000, ("Parana", "Maria Grande"): 2000,
        ("Viale", "Tabossi"): 400, ("Tabossi", "Viale"): 400,
        ("Viale", "Sosa"): 700, ("Sosa", "Viale"): 700,
        ("Viale", "Maria Grande"): 900, ("Maria Grande", "Viale"): 900,
        ("Tabossi", "Sosa"): 300, ("Sosa", "Tabossi"): 300,
        ("Tabossi", "Maria Grande"): 600, ("Maria Grande", "Tabossi"): 600,
        ("Sosa", "Maria Grande"): 300, ("Maria Grande", "Sosa"): 300,
    }
    print(f"💰 PRECIO {origen}->{destino}: {precios.get((origen, destino))}")
    return precios.get((origen, destino))

def obtener_duracion(origen, destino):
    duracion = tiempos_viaje.get((origen, destino))
    print(f"⏱️ DURACIÓN {origen}->{destino}: {duracion} minutos")
    return duracion

def formatear_duracion(minutos):
    if not minutos:
        return None
    horas = minutos // 60
    mins = minutos % 60
    if horas == 0:
        return f"{mins} minutos"
    if mins == 0:
        return f"{horas} horas"
    return f"{horas} horas y {mins} minutos"

def primer_colectivo(origen, destino):
    resultados = buscar_viaje(origen, destino)
    return resultados[0] if resultados else None

def proximo_colectivo(origen, destino):
    ahora = datetime.now()
    hora_actual_min = ahora.hour * 60 + ahora.minute
    print(f"🕐 HORA ACTUAL: {ahora.strftime('%H:%M')}")
    
    resultados = buscar_viaje(origen, destino)
    for r in resultados:
        hora_origen_min = hora_a_minutos(r["hora_origen"])
        if hora_origen_min >= hora_actual_min:
            minutos_restantes = hora_origen_min - hora_actual_min
            print(f"  → PRÓXIMO: {r['hora_origen']} (en {minutos_restantes} minutos)")
            return r, minutos_restantes
    print(f"  → No hay más servicios hoy")
    return None, None

def ultimo_colectivo(origen, destino):
    resultados = buscar_viaje(origen, destino)
    if resultados:
        print(f"  → ÚLTIMO: {resultados[-1]['hora_origen']}")
        return resultados[-1]
    return None

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
# BÚSQUEDA DE HORARIOS (IDA Y VUELTA)
# ============================================

def buscar_viaje(origen, destino, hora_limite=None):
    print(f"🔍 BUSCANDO: {origen} -> {destino}")
    resultados = []
    
    orden_ida = ["parana", "viale", "tabossi", "sosa", "maria grande"]
    orden_vuelta = ["maria grande", "sosa", "tabossi", "viale", "parana"]
    
    if origen.lower() not in orden_ida or destino.lower() not in orden_ida:
        print(f"  → Localidad no válida")
        return []
    
    # IDA
    if orden_ida.index(origen.lower()) < orden_ida.index(destino.lower()):
        print(f"  → Buscando en IDA...")
        for s in servicios:
            if s["ida"] and origen.lower() in s["ida"] and destino.lower() in s["ida"]:
                hora_o = s["ida"][origen.lower()]
                hora_d = s["ida"][destino.lower()]
                if hora_o and hora_d and (hora_limite is None or hora_a_minutos(hora_o) >= hora_limite):
                    print(f"    → Encontrado: {hora_o} -> {hora_d} ({s['servicio']})")
                    resultados.append({"servicio": s["servicio"], "hora_origen": hora_o, "hora_destino": hora_d})
    
    # VUELTA
    if orden_vuelta.index(origen.lower()) < orden_vuelta.index(destino.lower()):
        print(f"  → Buscando en VUELTA...")
        for s in servicios:
            if s["vuelta"] and origen.lower() in s["vuelta"] and destino.lower() in s["vuelta"]:
                hora_o = s["vuelta"][origen.lower()]
                hora_d = s["vuelta"][destino.lower()]
                if hora_o and hora_d and (hora_limite is None or hora_a_minutos(hora_o) >= hora_limite):
                    print(f"    → Encontrado: {hora_o} -> {hora_d} ({s['servicio']})")
                    resultados.append({"servicio": s["servicio"], "hora_origen": hora_o, "hora_destino": hora_d})
    
    resultados.sort(key=lambda x: hora_a_minutos(x["hora_origen"]))
    print(f"  → {len(resultados)} resultados")
    return resultados

# ============================================
# WEBHOOK PRINCIPAL
# ============================================

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    print(f"\n📩 MENSAJE RECIBIDO: '{incoming_msg}' de {sender}")
    print("🔍 ANALIZANDO MENSAJE...")
    
    resp = MessagingResponse()
    msg = resp.message()
    
    if sender not in session:
        print("🆕 NUEVA SESIÓN")
        session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "ultima_fecha": None}
    
    contexto = session[sender]
    print(f"📌 CONTEXTO ACTUAL: {contexto}")
    
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
    # NUEVA CONSULTA (prioritaria)
    # ============================================
    print("🔍 Intentando extraer origen/destino...")
    origen, destino = extraer_origen_destino(incoming_msg)
    if origen and destino:
        print(f"✅ CASO: NUEVA CONSULTA - {origen} -> {destino}")
        
        fecha = interpretar_fecha(incoming_msg)
        
        if not es_dia_habil(fecha):
            print("  → DÍA NO HÁBIL")
            msg.body("⚠️ Solo tengo horarios de días hábiles por ahora.")
            return str(resp)
        
        contexto["ultimo_origen"] = origen
        contexto["ultimo_destino"] = destino
        contexto["ultima_fecha"] = fecha
        session[sender] = contexto
        print(f"  → Contexto actualizado: {origen} -> {destino}")
        
        # Primer colectivo
        if any(p in incoming_msg.lower() for p in ["primer", "primero", "temprano"]):
            print("  → ES CONSULTA DE PRIMER")
            if "mañana" in incoming_msg.lower() or "manana" in incoming_msg.lower():
                fecha = datetime.now() + timedelta(days=1)
                fecha_str = fecha.strftime("%d/%m/%Y")
            else:
                fecha_str = "hoy"
            primer = primer_colectivo(origen, destino)
            if primer:
                msg.body(f"🚌 El primer colectivo de {origen} a {destino} para {fecha_str} sale a las {primer['hora_origen']}.")
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} para {fecha_str}.")
            return str(resp)
        
        # Próximo colectivo
        if any(p in incoming_msg.lower() for p in ["próximo", "proximo", "siguiente"]):
            print("  → ES CONSULTA DE PRÓXIMO")
            prox, minutos = proximo_colectivo(origen, destino)
            if prox:
                if minutos == 0:
                    msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale ahora a las {prox['hora_origen']}.")
                else:
                    msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale en {minutos} minutos (a las {prox['hora_origen']}).")
            else:
                msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
            return str(resp)
        
        # Último colectivo
        if any(p in incoming_msg.lower() for p in ["último", "ultimo", "final"]):
            print("  → ES CONSULTA DE ÚLTIMO")
            ult = ultimo_colectivo(origen, destino)
            if ult:
                msg.body(f"🚌 El último colectivo de {origen} a {destino} sale a las {ult['hora_origen']}.")
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} hoy.")
            return str(resp)
        
        # Horarios normales
        hora_limite = extraer_hora_limite(incoming_msg)
        resultados = buscar_viaje(origen, destino, hora_limite)
        
        if resultados:
            fecha_str = fecha.strftime("%d/%m/%Y")
            if hora_limite:
                texto = f"🚌 Servicios de {origen} a {destino} después de {minutos_a_hora(hora_limite)}:\n"
            else:
                texto = f"🚌 Servicios de {origen} a {destino} para {fecha_str}:\n"
            for r in resultados[:8]:
                texto += f"• {r['hora_origen']} → {r['hora_destino']} ({r['servicio']})\n"
            texto += "\n😊 ¿Necesitas precio, duración, próximo o último?"
            msg.body(texto)
        else:
            msg.body(f"😕 No encontré servicios de {origen} a {destino}.")
        return str(resp)
    
    # ============================================
    # CONSULTAS SIN CONTEXTO
    # ============================================
    if not contexto["ultimo_origen"]:
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "dura", "tiempo", "próximo", "último"]):
            print("✅ CASO: CONSULTA SIN CONTEXTO")
            msg.body("📝 Primero decime de dónde a dónde querés viajar. Ej: 'Viale a Paraná'")
            return str(resp)
    
    # ============================================
    # SEGUIMIENTO CON CONTEXTO
    # ============================================
    if contexto["ultimo_origen"] and contexto["ultimo_destino"]:
        o = contexto["ultimo_origen"]
        d = contexto["ultimo_destino"]
        print(f"✅ CASO: SEGUIMIENTO - contexto {o}->{d}")
        
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "$"]):
            print("  → SUB-CASO: PRECIO")
            precio = obtener_precio(o, d)
            msg.body(f"💰 El pasaje de {o} a {d} cuesta ${precio}." if precio else f"😕 No tengo precio de {o} a {d}.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["dura", "tiempo", "demora"]):
            print("  → SUB-CASO: DURACIÓN")
            duracion = obtener_duracion(o, d)
            if duracion:
                msg.body(f"⏱️ El viaje de {o} a {d} dura {formatear_duracion(duracion)}.")
            else:
                msg.body(f"😕 No tengo información de la duración.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["próximo", "proximo", "siguiente"]):
            print("  → SUB-CASO: PRÓXIMO")
            prox, mins = proximo_colectivo(o, d)
            if prox:
                if mins == 0:
                    msg.body(f"🚌 El próximo colectivo de {o} a {d} sale ahora a las {prox['hora_origen']}.")
                else:
                    msg.body(f"🚌 El próximo colectivo de {o} a {d} sale en {mins} minutos (a las {prox['hora_origen']}).")
            else:
                msg.body(f"😕 No hay más servicios de {o} a {d} hoy.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["último", "ultimo", "final"]):
            print("  → SUB-CASO: ÚLTIMO")
            ult = ultimo_colectivo(o, d)
            if ult:
                msg.body(f"🚌 El último colectivo de {o} a {d} sale a las {ult['hora_origen']}.")
            else:
                msg.body(f"😕 No hay servicios de {o} a {d} hoy.")
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
# INICIO (VERSIÓN PRODUCCIÓN)
# ============================================

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
