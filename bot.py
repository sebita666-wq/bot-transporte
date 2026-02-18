from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import re

app = Flask(__name__)

# ============================================
# HORARIOS CARGADOS (días hábiles)
# ============================================

servicios = [
    # 1M (solo vuelta desde Tabossi)
    {"servicio": "1M", "ida": None, "vuelta": {"origen": "Tabossi", "hora": "06:15", "viale": "06:30", "parana": "07:30"}},
    # 2M
    {"servicio": "2M", "ida": {"parana": "04:45", "viale": "05:50", "tabossi": "06:10", "sosa": "06:25", "maria grande": "06:45"}, "vuelta": {"origen": "Maria Grande", "hora": "06:45", "ruta": "R10", "parana": "08:15"}},
    # 3M
    {"servicio": "3M", "ida": {"parana": "05:45", "viale": "06:43", "tabossi": "07:00"}, "vuelta": {"origen": "Tabossi", "hora": "07:00", "viale": "07:20", "parana": "08:30"}},
    # 1M
    {"servicio": "1M", "ida": {"parana": "07:45", "maria grande": "09:10", "ruta": "R10"}, "vuelta": {"origen": "Maria Grande", "hora": "09:10", "sosa": "09:34", "tabossi": "09:48", "viale": "10:07", "parana": "11:15"}},
    # 2M
    {"servicio": "2M", "ida": {"parana": "08:45", "viale": "09:55"}, "vuelta": {"origen": "Viale", "hora": "11:00", "parana": "12:10"}},
    # 3M
    {"servicio": "3M", "ida": {"parana": "10:15", "maria grande": "11:40", "ruta": "R10"}, "vuelta": {"origen": "Maria Grande", "hora": "11:40", "sosa": "12:00", "tabossi": "12:20", "viale": "12:40", "parana": "13:45"}},
    # 1M
    {"servicio": "1M", "ida": {"parana": "11:40", "viale": "12:50"}, "vuelta": {"origen": "Viale", "hora": "13:30", "parana": "14:40"}},
    # 2T
    {"servicio": "2T", "ida": {"parana": "12:40", "viale": "13:40", "tabossi": "14:10", "sosa": "14:30", "maria grande": "14:50"}, "vuelta": {"origen": "Maria Grande", "hora": "14:50", "ruta": "R10", "parana": "16:15"}},
    # 3T
    {"servicio": "3T", "ida": {"parana": "14:00", "viale": "15:00"}, "vuelta": {"origen": "Viale", "hora": "15:15", "parana": "16:15"}},
    # 1T
    {"servicio": "1T", "ida": {"parana": "15:15", "viale": "16:20", "tabossi": "16:35"}, "vuelta": {"origen": "Tabossi", "hora": "16:40", "viale": "17:00", "parana": "18:10"}},
    # 3T
    {"servicio": "3T", "ida": {"parana": "16:30", "viale": "18:00", "tabossi": "18:20", "sosa": "18:40", "maria grande": "19:00", "ruta": "R10"}, "vuelta": {"origen": "Maria Grande", "hora": "18:00", "sosa": "18:20", "tabossi": "18:40", "viale": "19:00", "parana": "20:10"}},
    # 2T
    {"servicio": "2T", "ida": {"parana": "17:00", "viale": "18:10", "tabossi": "18:30", "sosa": "18:45", "maria grande": "19:00"}, "vuelta": {"origen": "Maria Grande", "hora": "19:00", "ruta": "R10", "parana": "20:30"}},
    # 1T
    {"servicio": "1T", "ida": {"parana": "19:30", "viale": "20:40"}, "vuelta": {"origen": "Viale", "hora": "21:00", "parana": "22:05"}},
    # 3T
    {"servicio": "3T", "ida": {"parana": "20:40", "viale": "21:50", "tabossi": "22:15", "sosa": "22:25", "maria grande": "22:40"}, "vuelta": {"origen": "Maria Grande", "hora": "22:45", "sosa": "22:55", "tabossi": "23:15", "viale": "23:40", "parana": "00:40"}},
    # 2T
    {"servicio": "2T", "ida": {"parana": "21:00", "viale": "22:00"}, "vuelta": {"origen": "Viale", "hora": "22:05", "parana": "23:05"}},
    # 1T (solo ida, termina en Viale)
    {"servicio": "1T", "ida": {"parana": "22:30", "viale": "23:30"}, "vuelta": None}
]

# ============================================
# FUNCIONES DE AYUDA
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

def extraer_origen_destino(mensaje):
    mensaje = mensaje.lower().strip()
    patron = r'de\s+(.+?)\s+a\s+(.+)'
    match = re.search(patron, mensaje)
    if not match:
        return None, None
    origen = match.group(1).strip().title()
    destino = match.group(2).strip().title()
    return origen, destino

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
    
    patron_fecha = r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})'
    match = re.search(patron_fecha, mensaje)
    if match:
        dia, mes, anio = map(int, match.groups())
        try:
            return datetime(anio, mes, dia)
        except:
            pass
    
    dias_semana = {
        "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
        "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
    }
    for dia_nombre, dia_num in dias_semana.items():
        if dia_nombre in mensaje:
            dias_para_summar = (dia_num - hoy.weekday() + 7) % 7
            if dias_para_summar == 0:
                return hoy
            return hoy + timedelta(days=dias_para_summar)
    
    return hoy

def es_dia_habil(fecha):
    return fecha.weekday() < 5

# ============================================
# FUNCIONES DE RESPUESTA DEL MENÚ
# ============================================

def mostrar_menu():
    return (
        "👋 Hola, soy el asistente de la empresa de transporte.\n\n"
        "Elegí una opción:\n\n"
        "1️⃣ Ver horarios\n"
        "2️⃣ Consultar precios\n"
        "3️⃣ Información útil\n"
        "4️⃣ Preguntas frecuentes\n\n"
        "O escribí directamente lo que necesitas, por ejemplo:\n"
        "• 'De Viale a Paraná'\n"
        "• 'Precio de Paraná a María Grande'"
    )

def preguntar_origen_destino(tipo):
    if tipo == "horarios":
        return "📝 Decime de dónde a dónde querés viajar para consultar horarios (ej: De Viale a Paraná)"
    else:
        return "📝 Decime de dónde a dónde querés viajar para consultar el precio (ej: De Viale a Paraná)"

def mostrar_info_util():
    return (
        "📌 *Información útil*\n\n"
        "📍 *Terminal Paraná:* Av. Ramírez 1200\n"
        "📍 *Terminal María Grande:* San Martín 450\n"
        "📞 *Teléfono:* 343 456-7890\n"
        "⏰ *Atención:* Lun a Vie 8 a 18hs\n"
        "🌐 *Web:* www.transporteviale.com.ar"
    )

def mostrar_faq():
    return (
        "❓ *Preguntas frecuentes*\n\n"
        "• *¿Cómo pago el boleto?*\n"
        "  Efectivo al subir (sencillo) o en terminal con tarjeta.\n\n"
        "• *¿Hay descuentos para estudiantes?*\n"
        "  Sí, 50% presentando certificado.\n\n"
        "• *¿Se puede llevar encomienda?*\n"
        "  Sí, hasta 10kg por pasajero.\n\n"
        "• *¿Los perros viajan?*\n"
        "  Sí, en jaula o bolso transportador."
    )

def despedida():
    return "😊 ¡Gracias por consultar! Si necesitás algo más, ya sabés dónde encontrarme. ¡Buen viaje!"

def no_entendido():
    return (
        "🤔 No entendí bien tu consulta.\n\n"
        "Podés escribir:\n"
        "• 'Hola' para ver el menú\n"
        "• 'De Viale a Paraná' para horarios\n"
        "• 'Precio de Paraná a María Grande'\n\n"
        "¿Probás de nuevo?"
    )

# ============================================
# FUNCIÓN DE PRECIOS
# ============================================

def obtener_precio(origen, destino):
    precios = {
        ("Viale", "Parana"): 1200,
        ("Parana", "Viale"): 1200,
        ("Tabossi", "Parana"): 1500,
        ("Parana", "Tabossi"): 1500,
        ("Sosa", "Parana"): 1800,
        ("Parana", "Sosa"): 1800,
        ("Maria Grande", "Parana"): 2000,
        ("Parana", "Maria Grande"): 2000,
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
    }
    return precios.get((origen, destino), None)

# ============================================
# BÚSQUEDA DE HORARIOS
# ============================================

def buscar_viaje(origen, destino, hora_limite=None):
    resultados = []
    
    for s in servicios:
        # Búsqueda en IDA
        if s["ida"] and "parana" in s["ida"]:
            ida = s["ida"]
            
            if origen.lower() == "parana" and destino.lower() != "parana":
                if destino.lower() in ida:
                    hora_origen = ida["parana"]
                    hora_destino = ida[destino.lower()]
                    if hora_origen and hora_destino:
                        minutos_origen = hora_a_minutos(hora_origen)
                        if hora_limite is None or minutos_origen >= hora_limite:
                            resultados.append({
                                "tipo": "ida",
                                "servicio": s["servicio"],
                                "origen": origen,
                                "hora_origen": hora_origen,
                                "destino": destino,
                                "hora_destino": hora_destino
                            })
            else:
                localidades_ida = ["parana", "viale", "tabossi", "sosa", "maria grande"]
                if origen.lower() in localidades_ida and destino.lower() in localidades_ida:
                    idx_origen = localidades_ida.index(origen.lower())
                    idx_destino = localidades_ida.index(destino.lower())
                    if idx_origen < idx_destino and origen.lower() in ida and destino.lower() in ida:
                        hora_origen = ida[origen.lower()]
                        hora_destino = ida[destino.lower()]
                        if hora_origen and hora_destino:
                            minutos_origen = hora_a_minutos(hora_origen)
                            if hora_limite is None or minutos_origen >= hora_limite:
                                resultados.append({
                                    "tipo": "ida",
                                    "servicio": s["servicio"],
                                    "origen": origen,
                                    "hora_origen": hora_origen,
                                    "destino": destino,
                                    "hora_destino": hora_destino
                                })
        
        # Búsqueda en VUELTA
        if s["vuelta"]:
            vuelta = s["vuelta"]
            
            if origen.lower() == "maria grande" and destino.lower() == "parana":
                if "origen" in vuelta and vuelta["origen"].lower() == "maria grande":
                    hora_origen = vuelta.get("hora")
                    hora_destino = vuelta.get("parana")
                    if hora_origen and hora_destino:
                        minutos_origen = hora_a_minutos(hora_origen)
                        if hora_limite is None or minutos_origen >= hora_limite:
                            resultados.append({
                                "tipo": "vuelta",
                                "servicio": s["servicio"],
                                "origen": origen,
                                "hora_origen": hora_origen,
                                "destino": destino,
                                "hora_destino": hora_destino
                            })
            elif origen.lower() == "sosa" and destino.lower() == "parana":
                if "sosa" in vuelta:
                    hora_origen = vuelta["sosa"]
                    hora_destino = vuelta["parana"]
                    if hora_origen and hora_destino:
                        minutos_origen = hora_a_minutos(hora_origen)
                        if hora_limite is None or minutos_origen >= hora_limite:
                            resultados.append({
                                "tipo": "vuelta",
                                "servicio": s["servicio"],
                                "origen": origen,
                                "hora_origen": hora_origen,
                                "destino": destino,
                                "hora_destino": hora_destino
                            })
            elif origen.lower() == "tabossi" and destino.lower() == "parana":
                if "tabossi" in vuelta:
                    hora_origen = vuelta["tabossi"]
                    hora_destino = vuelta["parana"]
                    if hora_origen and hora_destino:
                        minutos_origen = hora_a_minutos(hora_origen)
                        if hora_limite is None or minutos_origen >= hora_limite:
                            resultados.append({
                                "tipo": "vuelta",
                                "servicio": s["servicio"],
                                "origen": origen,
                                "hora_origen": hora_origen,
                                "destino": destino,
                                "hora_destino": hora_destino
                            })
            elif origen.lower() == "viale" and destino.lower() == "parana":
                if "viale" in vuelta:
                    hora_origen = vuelta["viale"]
                    hora_destino = vuelta["parana"]
                    if hora_origen and hora_destino:
                        minutos_origen = hora_a_minutos(hora_origen)
                        if hora_limite is None or minutos_origen >= hora_limite:
                            resultados.append({
                                "tipo": "vuelta",
                                "servicio": s["servicio"],
                                "origen": origen,
                                "hora_origen": hora_origen,
                                "destino": destino,
                                "hora_destino": hora_destino
                            })
    
    resultados.sort(key=lambda x: hora_a_minutos(x["hora_origen"]))
    return resultados

# ============================================
# WEBHOOK PRINCIPAL DE WHATSAPP
# ============================================

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    print(f"Mensaje de {sender}: {incoming_msg}")
    
    resp = MessagingResponse()
    msg = resp.message()
    
    # ============================================
    # OPCIONES NUMÉRICAS DEL MENÚ
    # ============================================
    if incoming_msg == "1":
        msg.body(preguntar_origen_destino("horarios"))
        return str(resp)
    
    if incoming_msg == "2":
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
    if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes", "menu"]:
        msg.body(mostrar_menu())
        return str(resp)
    
    # ============================================
    # CONSULTA DIRECTA DE HORARIOS
    # ============================================
    origen, destino = extraer_origen_destino(incoming_msg)
    if origen and destino:
        fecha_consulta = interpretar_fecha(incoming_msg)
        tipo_dia = "habiles" if es_dia_habil(fecha_consulta) else "finde"
        
        if tipo_dia == "finde":
            msg.body("⚠️ Por ahora solo tengo horarios de días hábiles. Estamos trabajando en sábados y domingos.")
            return str(resp)
        
        hora_limite = extraer_hora_limite(incoming_msg)
        resultados = buscar_viaje(origen, destino, hora_limite)
        
        if resultados:
            fecha_str = fecha_consulta.strftime("%d/%m/%Y")
            if hora_limite:
                hora_texto = minutos_a_hora(hora_limite)
                respuesta = f"🚌 Servicios de {origen} a {destino} para el {fecha_str} *después de las {hora_texto}*:\n\n"
            else:
                respuesta = f"🚌 Servicios de {origen} a {destino} para el {fecha_str}:\n\n"
            
            for r in resultados[:8]:
                respuesta += f"• {r['hora_origen']} → {r['hora_destino']} (Servicio {r['servicio']})\n"
            
            respuesta += "\n😊 ¿En qué más puedo ayudarte?"
            msg.body(respuesta)
        else:
            fecha_str = fecha_consulta.strftime("%d/%m/%Y")
            msg.body(f"😕 No encontré servicios de {origen} a {destino} para el {fecha_str}. ¿Probaste con otra combinación?")
        
        return str(resp)
    
    # ============================================
    # CONSULTA DIRECTA DE PRECIOS
    # ============================================
    if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "costo", "pasaje", "boleto", "$"]):
        origen, destino = extraer_origen_destino(incoming_msg)
        if origen and destino:
            precio = obtener_precio(origen, destino)
            if precio:
                msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
            else:
                msg.body(f"😕 No tengo el precio de {origen} a {destino}. Consultá en boletería.")
        else:
            msg.body("🤔 No entendí bien. Por favor, escribí algo como 'Precio de Viale a Paraná'")
        return str(resp)
    
    # ============================================
    # INFORMACIÓN ÚTIL
    # ============================================
    if any(p in incoming_msg.lower() for p in ["info", "informacion", "telefono", "contacto", "direccion"]):
        msg.body(mostrar_info_util())
        return str(resp)
    
    # ============================================
    # PREGUNTAS FRECUENTES
    # ============================================
    if any(p in incoming_msg.lower() for p in ["faq", "pregunta", "duda", "consulta", "como", "cómo", "funciona"]):
        msg.body(mostrar_faq())
        return str(resp)
    
    # ============================================
    # DESPEDIDA
    # ============================================
    if any(p in incoming_msg.lower() for p in ["gracias", "chau", "adiós", "adios", "hasta luego", "bye"]):
        msg.body(despedida())
        return str(resp)
    
    # ============================================
    # NO ENTENDIDO
    # ============================================
    msg.body(no_entendido())
    return str(resp)

# ============================================
# INICIO DEL SERVIDOR
# ============================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
