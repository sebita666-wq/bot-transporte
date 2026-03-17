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

print("🚀 BOT INICIADO - VERSIÓN CON DATOS EXTERNOS (horarios.json y tarifas.json)")

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
# CARGAR DATOS DESDE ARCHIVOS JSON
# ============================================

def cargar_horarios():
    try:
        with open('horarios.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('habiles', []), data.get('sabados', []), data.get('domingos', [])
    except Exception as e:
        print(f"❌ Error cargando horarios.json: {e}")
        return [], [], []

def cargar_tarifas():
    try:
        with open('tarifas.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error cargando tarifas.json: {e}")
        return {"localidades": [], "matriz_precios": []}

# Cargar datos al iniciar
horarios_habiles, horarios_sabados, horarios_domingos = cargar_horarios()
tarifas_data = cargar_tarifas()
localidades = tarifas_data.get('localidades', [])
matriz_precios = tarifas_data.get('matriz_precios', [])

print(f"✅ Horarios cargados: hábiles={len(horarios_habiles)}, sábados={len(horarios_sabados)}, domingos={len(horarios_domingos)}")
print(f"✅ Tarifas cargadas: {len(localidades)} localidades")

# ============================================
# FUNCIONES DE NORMALIZACIÓN
# ============================================

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
# FUNCIÓN DE PRECIOS
# ============================================
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
# FUNCIONES DE RESPUESTA
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
    print(f"🚀 Bot listo en puerto {port} - VERSIÓN CON DATOS EXTERNOS")
    app.run(host='0.0.0.0', port=port, debug=False)
