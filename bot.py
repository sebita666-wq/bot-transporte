from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import re
import json
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_sesiones'
app.permanent_session_lifetime = timedelta(minutes=3)

print("🚀 BOT INICIADO - VERSIÓN CON NUEVOS HORARIOS")

# ============================================
# CONFIGURACIÓN
# ============================================
NUMERO_DUENIO = "whatsapp:+5493434727811"
STATS_FILE = 'estadisticas.json'

# ============================================
# HORARIOS ACTUALIZADOS (DESDE LA IMAGEN)
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
            return hora * 60 + minutos
    return None

def interpretar_fecha(mensaje):
    mensaje = mensaje.lower()
    hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if "hoy" in mensaje:
        return hoy
    if "mañana" in mensaje or "manana" in mensaje:
        return hoy + timedelta(days=1)
    
    dias_semana = {"lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
                   "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6}
    for dia_nombre, dia_num in dias_semana.items():
        if dia_nombre in mensaje:
            dias_para_summar = (dia_num - hoy.weekday() + 7) % 7
            return hoy + timedelta(days=dias_para_summar)
    
    return hoy

def obtener_tipo_dia(fecha):
    """Devuelve 'habiles', 'sabados' o 'domingos' según la fecha"""
    if fecha.weekday() < 5:  # Lunes a viernes
        return "habiles"
    elif fecha.weekday() == 5:  # Sábado
        return "sabados"
    else:  # Domingo
        return "domingos"

def buscar_tramos(origen, destino, tipo_dia, hora_limite=None, ruta=None):
    """Busca tramos que coincidan con origen, destino y tipo de día"""
    resultados = []
    
    for t in tramos:
        if t["origen"] == origen and t["destino"] == destino and t["dia"] == tipo_dia:
            if ruta is None or t.get("ruta") == ruta:
                hora_min = hora_a_minutos(t["hora_salida"])
                if hora_limite is None or hora_min >= hora_limite:
                    resultados.append(t)
    
    resultados.sort(key=lambda x: hora_a_minutos(x["hora_salida"]))
    return resultados

def obtener_precio(origen, destino):
    return precios.get((origen, destino))

def formatear_horarios(resultados):
    if not resultados:
        return None
    texto = ""
    for r in resultados[:8]:
        ruta_text = f" ({r['ruta']})" if r.get('ruta') else ""
        texto += f"• {r['hora_salida']}{ruta_text}\n"
    return texto

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
    
    if sender not in session:
        session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu"}
    
    contexto = session[sender]
    
    # ============================================
    # RESETEO
    # ============================================
    if any(p in incoming_msg.lower() for p in ["chau", "adiós", "adios", "bye"]):
        resetear_contexto(sender)
        msg.body(despedida())
        return str(resp)
    
    if "gracias" in incoming_msg.lower():
        resetear_contexto(sender)
        msg.body(despedida())
        return str(resp)
    
    if incoming_msg.lower() in ["menu", "reiniciar", "reset", "empezar", "inicio"]:
        resetear_contexto(sender)
        msg.body(mostrar_menu())
        return str(resp)
    
    # ============================================
    # OPCIONES NUMÉRICAS
    # ============================================
    if incoming_msg == "1":
        contexto["estado"] = "esperando_origen_horarios"
        session[sender] = contexto
        msg.body(preguntar_origen_destino("horarios"))
        return str(resp)
    
    if incoming_msg == "2":
        contexto["estado"] = "esperando_origen_precios"
        session[sender] = contexto
        msg.body(preguntar_origen_destino("precios"))
        return str(resp)
    
    if incoming_msg == "3":
        msg.body(mostrar_info_util())
        return str(resp)
    
    if incoming_msg == "4":
        msg.body(mostrar_faq())
        return str(resp)
    
    # ============================================
    # SALUDO
    # ============================================
    if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes", "ayuda"]:
        msg.body(mostrar_menu())
        return str(resp)
    
    # ============================================
    # PROCESAR SEGÚN ESTADO
    # ============================================
    
    # Estado: esperando origen para precios
    if contexto.get("estado") == "esperando_origen_precios":
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
    
    # Estado: esperando origen para horarios
    if contexto.get("estado") == "esperando_origen_horarios":
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
    origen, destino = extraer_origen_destino(incoming_msg)
    if origen and destino:
        fecha = interpretar_fecha(incoming_msg)
        tipo_dia = obtener_tipo_dia(fecha)
        
        # Detectar si es consulta de precio
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "$"]):
            precio = obtener_precio(origen, destino)
            if precio:
                msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
            else:
                msg.body(f"😕 No tengo precio de {origen} a {destino}.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            session[sender] = contexto
            return str(resp)
        
        # Si no es precio, asumimos horarios
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
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "dura", "tiempo"]):
            msg.body("📝 Primero decime de dónde a dónde querés viajar. Ej: 'De Viale a Parana'")
            return str(resp)
    
    # ============================================
    # SEGUIMIENTO CON CONTEXTO
    # ============================================
    if contexto["ultimo_origen"] and contexto["ultimo_destino"]:
        o = contexto["ultimo_origen"]
        d = contexto["ultimo_destino"]
        
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "$"]):
            precio = obtener_precio(o, d)
            msg.body(f"💰 El pasaje de {o} a {d} cuesta ${precio}." if precio else f"😕 No tengo precio de {o} a {d}.")
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["dura", "tiempo", "demora"]):
            # Podríamos agregar duración después
            msg.body(f"⏱️ La duración del viaje de {o} a {d} no está disponible aún.")
            return str(resp)
    
    # ============================================
    # INFORMACIÓN ÚTIL / FAQ
    # ============================================
    if any(p in incoming_msg.lower() for p in ["info", "telefono", "direccion"]):
        msg.body(mostrar_info_util())
        return str(resp)
    
    if any(p in incoming_msg.lower() for p in ["faq", "pregunta", "como", "cómo"]):
        msg.body(mostrar_faq())
        return str(resp)
    
    # ============================================
    # NO ENTENDIDO
    # ============================================
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
