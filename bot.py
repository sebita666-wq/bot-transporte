from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import pytz
import re
import json
import os
import traceback
import requests
from collections import Counter
import unicodedata

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=30)

os.environ['TZ'] = 'America/Argentina/Buenos_Aires'
try:
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
except:
    timezone = pytz.timezone('America/Argentina/Cordoba')

print("🚀 BOT INICIADO - VERSIÓN CON GRUPO")
print("✅ Anti-spam: 4 segundos")
print("✅ Límites IA: 20/día, 150/mes")
print("✅ Contexto: 5 minutos de memoria")

NUMERO_DUENIO = os.environ.get('NUMERO_DUENIO', "whatsapp:+5493434727811")
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_para_sesiones')

# ============================================
# Disco persistente para datos
# ============================================
DATA_DIR = '/data'
os.makedirs(DATA_DIR, exist_ok=True)

STATS_FILE = os.path.join(DATA_DIR, 'estadisticas.json')
SUGERENCIAS_FILE = os.path.join(DATA_DIR, 'sugerencias.json')
LIMITES_IA_FILE = os.path.join(DATA_DIR, 'limites_ia.json')

DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

app.secret_key = SECRET_KEY

# ============================================
# CONTROL DE LÍMITES DE IA POR USUARIO
# ============================================

def cargar_limites_ia():
    if os.path.exists(LIMITES_IA_FILE):
        with open(LIMITES_IA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "usuarios": {},
        "config": {
            "max_por_dia": 20,
            "max_por_mes": 150,
            "min_segundos_entre": 4,
            "reset_hora": 3
        }
    }

def guardar_limites_ia(data):
    with open(LIMITES_IA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def verificar_limite_ia(sender):
    limites = cargar_limites_ia()
    config = limites["config"]
    ahora = ahora_argentina()
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    
    if sender not in limites["usuarios"]:
        limites["usuarios"][sender] = {
            "consultas_hoy": 0,
            "consultas_mes": 0,
            "ultima_consulta": None,
            "historial_fechas": [],
            "bloqueado_hasta": None,
            "ultima_fecha_dia": fecha_hoy
        }
    
    user = limites["usuarios"][sender]
    
    if "bloqueado_hasta" not in user:
        user["bloqueado_hasta"] = None
    if "ultima_fecha_dia" not in user:
        user["ultima_fecha_dia"] = fecha_hoy
    if "historial_fechas" not in user:
        user["historial_fechas"] = []
    if "consultas_hoy" not in user:
        user["consultas_hoy"] = 0
    if "consultas_mes" not in user:
        user["consultas_mes"] = 0
    if "ultima_consulta" not in user:
        user["ultima_consulta"] = None
    
    if user["bloqueado_hasta"]:
        try:
            bloqueo_hasta = datetime.fromisoformat(user["bloqueado_hasta"])
            if ahora < bloqueo_hasta:
                minutos_restantes = int((bloqueo_hasta - ahora).total_seconds() / 60)
                guardar_limites_ia(limites)
                return False, f"⏰ *Límite temporal*\nPodés volver en {minutos_restantes} minutos. 😊"
            else:
                user["bloqueado_hasta"] = None
        except:
            user["bloqueado_hasta"] = None
    
    fechas_validas = []
    for fecha_str in user.get("historial_fechas", []):
        try:
            fecha_consulta = datetime.fromisoformat(fecha_str)
            if (ahora - fecha_consulta).days < 30:
                fechas_validas.append(fecha_str)
        except:
            pass
    user["historial_fechas"] = fechas_validas
    user["consultas_mes"] = len(fechas_validas)
    
    if user.get("ultima_fecha_dia") != fecha_hoy:
        user["consultas_hoy"] = 0
        user["ultima_fecha_dia"] = fecha_hoy
    
    if user.get("ultima_consulta"):
        try:
            ultima = datetime.fromisoformat(user["ultima_consulta"])
            segundos_diferencia = (ahora - ultima).total_seconds()
            if segundos_diferencia < config["min_segundos_entre"]:
                espera = int(config["min_segundos_entre"] - segundos_diferencia)
                guardar_limites_ia(limites)
                return False, f"⏳ Esperá {espera} segundos entre consultas. 😊"
        except:
            pass
    
    if user["consultas_hoy"] >= config["max_por_dia"]:
        user["bloqueado_hasta"] = (ahora + timedelta(hours=24)).isoformat()
        guardar_limites_ia(limites)
        return False, f"📊 Límite diario alcanzado ({config['max_por_dia']}). Volvé mañana. 😊"
    
    if user["consultas_mes"] >= config["max_por_mes"]:
        user["bloqueado_hasta"] = (ahora + timedelta(days=30)).isoformat()
        guardar_limites_ia(limites)
        return False, f"📅 Límite mensual alcanzado ({config['max_por_mes']}). Volvé el mes que viene. 😊"
    
    guardar_limites_ia(limites)
    return True, None

def registrar_consulta_ia(sender, exito=True):
    limites = cargar_limites_ia()
    ahora = ahora_argentina()
    
    if sender not in limites["usuarios"]:
        limites["usuarios"][sender] = {
            "consultas_hoy": 0,
            "consultas_mes": 0,
            "ultima_consulta": None,
            "historial_fechas": [],
            "bloqueado_hasta": None,
            "ultima_fecha_dia": ahora.strftime("%Y-%m-%d")
        }
    
    user = limites["usuarios"][sender]
    fecha_hoy = ahora.strftime("%Y-%m-%d")
    
    if user.get("ultima_fecha_dia") != fecha_hoy:
        user["consultas_hoy"] = 0
        user["ultima_fecha_dia"] = fecha_hoy
    
    if exito:
        user["consultas_hoy"] = user.get("consultas_hoy", 0) + 1
        ahora_str = ahora.isoformat()
        user["ultima_consulta"] = ahora_str
        if "historial_fechas" not in user:
            user["historial_fechas"] = []
        user["historial_fechas"].append(ahora_str)
        user["consultas_mes"] = len(user["historial_fechas"])
    
    guardar_limites_ia(limites)

def ahora_argentina():
    return datetime.now(timezone)

# ============================================
# PALABRAS PROHIBIDAS PARA IA
# ============================================

def normalizar_localidad(texto):
    if not texto:
        return None
    texto = texto.lower().strip()
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode()
    for loc in localidades:
        principal_sin_tilde = unicodedata.normalize('NFKD', loc["principal"].lower()).encode('ASCII', 'ignore').decode()
        if texto == principal_sin_tilde:
            return loc["principal"]
        for alias in loc["alias"]:
            alias_sin_tilde = unicodedata.normalize('NFKD', alias.lower()).encode('ASCII', 'ignore').decode()
            if texto == alias_sin_tilde:
                return loc["principal"]
    return None

def es_consulta_prohibida_para_ia(mensaje):
    m = mensaje.lower().strip()
    
    # Si el mensaje tiene dos palabras que son localidades, bloquear IA
    palabras = m.split()
    if len(palabras) == 2:
        if normalizar_localidad(palabras[0]) and normalizar_localidad(palabras[1]):
            print(f"🚫 CONSULTA PROHIBIDA para IA: posible horario sin formato (origen+destino)")
            return True
    
    palabras_precio = [
        "precio", "cuesta", "costo", "tarifa", "pasaje", "vale", 
        "$", "pesos", "sale", "cuánto", "cuanto", "valor"
    ]
    
    palabras_horario = [
        "horario", "pasa", "primer", "primero", "próximo", "proximo",
        "último", "ultimo", "cuándo", "cuando", "hora", "horas"
    ]
    
    palabras_sugerencia = [
        "sugerencia", "reclamo", "queja", "problema", "error",
        "falla", "falta", "sugiero", "propongo"
    ]
    
    palabras_faq = [
        "pago", "equipaje", "mascota", "perro", "gato", "bulto",
        "valija", "maleta", "menor", "niño", "nene", "bebe", "bebé",
        "descuento", "sube", "tarjeta", "qr", "mercadopago",
        "objeto perdido", "perdí", "olvidé", "asiento", "sentarme"
    ]
    
    palabras_info = [
        "terminal", "dirección", "direccion", "teléfono", "telefono",
        "contacto", "atienden", "web", "oficina"
    ]
    
    palabras_prohibidas = (palabras_precio + palabras_horario + 
                          palabras_sugerencia + palabras_faq + palabras_info)
    
    for palabra in palabras_prohibidas:
        if palabra in m:
            print(f"🚫 CONSULTA PROHIBIDA para IA: contiene '{palabra}'")
            return True
    
    return False

# ============================================
# VERIFICACIÓN DE CONTEXTO ACTIVO
# ============================================

def contexto_activo(ctx):
    if not ctx.get("ultimo_mensaje_time"):
        return False
    ahora = ahora_argentina()
    tiempo_transcurrido = (ahora - ctx["ultimo_mensaje_time"]).total_seconds()
    if tiempo_transcurrido > 300:
        print(f"⏰ Contexto expirado después de {int(tiempo_transcurrido)} segundos")
        return False
    return True

def limpiar_contexto(ctx):
    ctx["ultimo_origen"] = None
    ctx["ultimo_destino"] = None
    ctx["ultima_intencion"] = None
    ctx["ultimo_mensaje_time"] = None
    print("🧹 Contexto limpiado")
    return ctx

# ============================================
# ESTADÍSTICAS
# ============================================

def cargar_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "usuarios": {},
        "metricas": {
            "total_usuarios_unicos": 0,
            "total_mensajes": 0,
            "ultimo_reinicio": ahora_argentina().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

def guardar_stats(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def registrar_interaccion(sender, mensaje, tipo=None, consulta=None, horario=None):
    stats = cargar_stats()
    ahora = ahora_argentina().strftime("%Y-%m-%d %H:%M:%S")
    
    if sender not in stats["usuarios"]:
        stats["usuarios"][sender] = {
            "primer_contacto": ahora,
            "ultimo_contacto": ahora,
            "mensajes": 1,
            "consultas": [tipo] if tipo else [],
            "destinos_consultados": [],
            "horarios_consultados": []
        }
        stats["metricas"]["total_usuarios_unicos"] += 1
        print(f"📊 Nuevo usuario: {sender}")
    else:
        stats["usuarios"][sender]["ultimo_contacto"] = ahora
        stats["usuarios"][sender]["mensajes"] += 1
        if tipo and tipo not in stats["usuarios"][sender]["consultas"]:
            stats["usuarios"][sender]["consultas"].append(tipo)
        
        if "destinos_consultados" not in stats["usuarios"][sender]:
            stats["usuarios"][sender]["destinos_consultados"] = []
        if "horarios_consultados" not in stats["usuarios"][sender]:
            stats["usuarios"][sender]["horarios_consultados"] = []
    
    if consulta:
        stats["usuarios"][sender]["destinos_consultados"].append(consulta)
    if horario:
        stats["usuarios"][sender]["horarios_consultados"].append(horario)
    
    stats["metricas"]["total_mensajes"] += 1
    guardar_stats(stats)

def resumen_stats():
    stats = cargar_stats()
    ahora = ahora_argentina()
    hoy = ahora.strftime("%Y-%m-%d")
    semana = (ahora - timedelta(days=7)).strftime("%Y-%m-%d")
    
    usuarios_hoy = sum(1 for u in stats["usuarios"].values() if u["ultimo_contacto"].startswith(hoy))
    usuarios_semana = sum(1 for u in stats["usuarios"].values() if u["ultimo_contacto"][:10] >= semana)
    
    return {
        "total_usuarios": stats["metricas"]["total_usuarios_unicos"],
        "total_mensajes": stats["metricas"]["total_mensajes"],
        "usuarios_hoy": usuarios_hoy,
        "usuarios_semana": usuarios_semana,
        "ultimo_reinicio": stats["metricas"]["ultimo_reinicio"]
    }

def destinos_mas_frecuentes():
    stats = cargar_stats()
    destinos = []
    for usuario, datos in stats["usuarios"].items():
        destinos.extend(datos.get("destinos_consultados", []))
    contador = Counter(destinos)
    return contador.most_common(5)

def horarios_mas_consultados():
    stats = cargar_stats()
    horarios = []
    for usuario, datos in stats["usuarios"].items():
        horarios.extend(datos.get("horarios_consultados", []))
    contador = Counter(horarios)
    return contador.most_common(5)

# ============================================
# VALIDAR ARCHIVOS JSON
# ============================================

def validar_archivos_json():
    archivos = ['horarios.json', 'tarifas.json', 'feriados.json', 'duraciones.json']
    for archivo in archivos:
        if not os.path.exists(archivo):
            print(f"❌ ERROR: No se encuentra {archivo}")
            return False
    print("✅ Todos los JSON están presentes")
    return True

if not validar_archivos_json():
    print("❌ Faltan archivos")
    exit(1)

# ============================================
# CARGAR DATOS
# ============================================

def cargar_feriados():
    try:
        with open('feriados.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('feriados_2026', [])
    except:
        return []

FERIADOS_NACIONALES = cargar_feriados()

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

def cargar_horarios():
    try:
        with open('horarios.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('habiles', []), data.get('sabados', []), data.get('domingos', [])
    except:
        return [], [], []

def cargar_tarifas():
    try:
        with open('tarifas.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"localidades": [], "matriz_precios": [], "precios_especiales": {}}

def cargar_duraciones():
    try:
        with open('duraciones.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

horarios_habiles, horarios_sabados, horarios_domingos = cargar_horarios()
tarifas_data = cargar_tarifas()
localidades = tarifas_data.get('localidades', [])
matriz_precios = tarifas_data.get('matriz_precios', [])
precios_especiales = tarifas_data.get('precios_especiales', {})
duraciones = cargar_duraciones()

print(f"✅ Horarios cargados: hábiles={len(horarios_habiles)}, sábados={len(horarios_sabados)}, domingos={len(horarios_domingos)}")
print(f"✅ Tarifas cargadas: {len(localidades)} localidades")
print(f"🤖 DeepSeek IA: {'Habilitada' if DEEPSEEK_API_KEY else 'No configurada'}")

# ============================================
# FUNCIÓN DEEPSEEK CON CONTEXTO Y LÍMITES
# ============================================

def consultar_deepseek(mensaje, sender, contexto=None):
    if not DEEPSEEK_API_KEY:
        return None
    
    puede_usar, mensaje_limite = verificar_limite_ia(sender)
    if not puede_usar:
        return mensaje_limite
    
    mensaje_con_contexto = mensaje
    if contexto and contexto.get("ultimo_origen") and contexto.get("ultimo_destino"):
        contexto_texto = f"[CONTEXTO: El usuario está preguntando sobre viajes de {contexto['ultimo_origen']} a {contexto['ultimo_destino']}. Pregunta original: '{mensaje}']"
        mensaje_con_contexto = contexto_texto
        print(f"🧠 IA recibe contexto: {contexto['ultimo_origen']} → {contexto['ultimo_destino']}")
    
    try:
        mensajes = [
            {
                "role": "system",
                "content": """🚌 *Asistente de Transporte - Horarios de Colectivos* 🚌

🎯 Soy un asistente para consultas de colectivos en Entre Ríos.

📍 *Localidades con horarios:* Paraná, Viale, Tabossi, Sosa, María Grande.
📍 *Localidades adicionales (solo precios):* Aldea San Antonio, Genolet, Sauce, 3 Bocas, Quebracho, El Ramblón.

⚠️ *NORMA OBLIGATORIA:* 
BAJO NINGUNA CIRCUNSTANCIA inventes ni muestres horarios o precios. 
Si el usuario pregunta por horarios o precios sin usar el formato correcto, 
respondé: 'Para ver horarios usá el formato "De [origen] a [destino]". Ej: "De Viale a Parana"'

📋 *REGLAS:*
1️⃣ NO respondas sobre PRECIOS, HORARIOS, SUGERENCIAS o PREGUNTAS FRECUENTES (FAQ). 
2️⃣ Si el usuario pregunta por el CLIMA, actividades turísticas o de recreacion, respondé con información general.
3️⃣ Si el usuario pregunta si este bot es oficial, respondé: "No, es un proyecto independiente. Los horarios son orientativos. Si ves un error, escribí 'Hola' y luego la opción 5."
4️⃣ Respondé con EMOTICONES: 🚌 📍 💰 ✅ ❌ 😊 ⏰ 📅
5️⃣ Usá *negritas* con asteriscos
6️⃣ Sé BREVE y AMIGABLE
7️⃣ Si no sabés algo, decí: "No tengo esa información. Podés escribir 'Ayuda' para ver las opciones. 😊"
8️⃣ Siempre cerrá con una pregunta amigable"""
            }
        ]
        
        mensajes.append({"role": "user", "content": mensaje_con_contexto})
        
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
        data = {"model": "deepseek-chat", "messages": mensajes, "temperature": 0.7, "max_tokens": 500}
        
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            resultado = response.json()
            respuesta = resultado['choices'][0]['message']['content']
            registrar_consulta_ia(sender, exito=True)
            return respuesta
        else:
            registrar_consulta_ia(sender, exito=False)
            return None
    except Exception as e:
        registrar_consulta_ia(sender, exito=False)
        print(f"❌ Error DeepSeek: {e}")
        return None

# ============================================
# FAQ COMPLETO
# ============================================

def responder_faq(mensaje):
    m = mensaje.lower()
    if any(p in m for p in ["pago", "pagar", "sube", "tarjeta", "qr", "mercadopago"]):
        return ("💳 *Medios de pago*\n\nA partir de Febrero de 2026, el único medio de pago disponible es a través de la **red SUBE**.\nPodés pagar con:\n• Tarjeta SUBE\n• Tarjeta de débito o crédito\n• Mercado Pago QR\n\nTodos los pagos se realizan en la terminal antes de subir.")
    
    if any(p in m for p in ["equipaje", "valija", "bulto", "maleta"]):
        return ("🧳 *Límite de equipaje*\n\nPodés llevar hasta **2 bultos por persona** con un peso máximo total de **10 kg**.\nSi necesitás llevar más, consultanos con anticipación para evaluar disponibilidad en bodega.")
    
    if any(p in m for p in ["mascota", "perro", "gato"]):
        return ("🐕 *Mascotas a bordo*\n\n• Mascotas pequeñas viajan **en jaula o bolso transportador**, únicamente en **bodega**.\n• **Perros de asistencia** viajan sin restricciones.\n• No se permiten mascotas sueltas en el interior del colectivo.")
    
    if any(p in m for p in ["perdi", "objeto", "olvide"]):
        return ("📞 *Objetos perdidos*\n\nSi perdiste algo en un colectivo, comunicate al 📱 **343 456-7890**.\nTené a mano el día y horario del viaje para ayudarte a ubicarlo.")
    
    if any(p in m for p in ["descuento", "estudiante", "jubilado"]):
        return ("👨‍🎓 *Descuentos*\n\nEl descuento lo aplica directamente el **sistema SUBE**.\nNosotros no podemos gestionar ningún tipo de descuento.")
    
    if any(p in m for p in ["niño", "nene", "bebe", "menor"]):
        return ("👶 *Menores*\n\n• **Menores de 5 años** que viajen en el regazo de un adulto abonan un **seguro mínimo** ($1.852).\n• **A partir de los 5 años**, deben pagar pasaje completo.")
    
    if any(p in m for p in ["asiento", "sentarme", "lugar"]):
        return ("🪑 *Asignación de asientos*\n\nLa asignación de asientos es **por orden de llegada**.\nSi necesitás un lugar especial, avisale al chofer al subir.")
    
    return None

def mostrar_faq():
    return (
        "❓ *Preguntas frecuentes*\n\nEscribí la palabra clave que te interese:\n\n"
        "💰 *pago* – Medios de pago\n🧳 *equipaje* – Límite de bultos\n🐕 *mascota* – Cómo viajan\n"
        "👶 *menores* – Pasajes para niños\n📞 *objetos perdidos* – Dónde reclamar\n💺 *asiento* – Asignación\n\n"
        "➡️ Ej: 'pago', 'equipaje', 'mascota'"
    )

def mostrar_info_util():
    return (
        "📌 *Información útil*\n\n📍 *Terminal Paraná:* Av. Ramírez 1200\n"
        "📍 *Terminal María Grande:* San Martín 450\n📞 *Teléfono de contacto:* 343 456-7890\n"
        "⏰ *Atención:* Lun a Dom 6:00 a 22:00"
    )

def mostrar_menu_sugerencia():
    return (
        "📝 *Envío de sugerencias*\n\nEscribí tu mensaje en el siguiente formato:\n\n"
        "*Teléfono:* Tu número\n*Mensaje:* Tu sugerencia\n\n📌 *Ejemplo:*\n"
        "Teléfono: 3435123456\nMensaje: El horario de las 15:30 está mal\n\n✍️ *Escribí 'Cancelar' para volver.*"
    )

# ============================================
# NORMALIZACIÓN Y EXTRACCIÓN
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
    
    # Buscar formato "de X a Y" (el ÚNICO que aceptamos)
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
    
    print("❌ No se pudo extraer - formato incorrecto")
    return None, None

def pedir_formato_correcto():
    return "🤔 Para consultar horarios, usá el formato:\n• 'De [origen] a [destino]'\n\nEjemplo: 'De Viale a Parana'\n\n¿Querés intentarlo de nuevo? 😊"

def interpretar_fecha(mensaje):
    m = mensaje.lower().strip()
    hoy = ahora_argentina().replace(hour=0, minute=0, second=0, microsecond=0)
    
    match = re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', m)
    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        anio = int(match.group(3)) if match.group(3) else hoy.year
        if anio < 100:
            anio += 2000
        try:
            fecha = datetime(anio, mes, dia, tzinfo=hoy.tzinfo)
            if fecha < hoy:
                fecha = datetime(anio + 1, mes, dia, tzinfo=hoy.tzinfo)
            return fecha
        except:
            pass
    
    meses = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
    match = re.search(r'(\d{1,2})\s+de\s+([a-z]+)', m)
    if match:
        dia = int(match.group(1))
        mes = meses.get(match.group(2))
        if mes:
            try:
                fecha = datetime(hoy.year, mes, dia, tzinfo=hoy.tzinfo)
                if fecha < hoy:
                    fecha = datetime(hoy.year + 1, mes, dia, tzinfo=hoy.tzinfo)
                return fecha
            except:
                pass
    
    if "mañana" in m or "manana" in m:
        return hoy + timedelta(days=1)
    if "hoy" in m:
        return hoy
    return hoy

def hora_a_minutos(h):
    if not h:
        return None
    try:
        hh, mm = map(int, h.split(':'))
        return hh*60 + mm
    except:
        return None

def obtener_horarios_por_dia(tipo):
    if tipo == "habiles":
        return horarios_habiles
    if tipo == "sabados":
        return horarios_sabados
    return horarios_domingos

def buscar_horarios(origen, destino, tipo, hora_limite=None):
    resultados = {"R10": [], "R18": [], "R10+R18": []}
    
    for h in obtener_horarios_por_dia(tipo):
        if isinstance(h, dict) and h.get("origen") == origen and h.get("destino") == destino:
            if hora_limite is None or (hora_a_minutos(h["hora"]) and hora_a_minutos(h["hora"]) >= hora_limite):
                ruta = h.get("ruta", "R18")
                if ruta in resultados:
                    resultados[ruta].append(h["hora"])
    
    for r in resultados:
        resultados[r].sort(key=lambda x: hora_a_minutos(x) if hora_a_minutos(x) is not None else 9999)
    
    return resultados

def formatear_horarios(resultados, origen, destino, fecha_str):
    if not any(resultados.values()):
        return f"😕 No encontré servicios de {origen} a {destino} para {fecha_str}."
    
    duracion = duraciones.get(f"{origen}-{destino}")
    duracion_str = f" (aprox. {duracion} min)" if duracion else ""
    
    texto = f"🚌 Servicios de {origen} a {destino}{duracion_str} para {fecha_str}:\n\n"
    
    if resultados["R10+R18"]:
        texto += "🛣️ *Por Ruta 10 + Ruta 18:*\n" + "\n".join([f"• {h}" for h in resultados["R10+R18"]]) + "\n\n"
    if resultados["R10"]:
        texto += "🛣️ *Por Ruta 10:*\n" + "\n".join([f"• {h}" for h in resultados["R10"]]) + "\n\n"
    if resultados["R18"]:
        texto += "🛣️ *Por Ruta 18:*\n" + "\n".join([f"• {h}" for h in resultados["R18"]]) + "\n\n"
    
    texto += "😊 ¿Necesitas precio, próximo o último?"
    return texto

def obtener_precio(origen, destino):
    try:
        o_norm = normalizar_localidad(origen)
        d_norm = normalizar_localidad(destino)
        if not o_norm or not d_norm:
            return None
        clave = f"{o_norm}-{d_norm}"
        if clave in precios_especiales:
            return precios_especiales[clave]
        indices = {loc["principal"]: i for i, loc in enumerate(localidades)}
        return matriz_precios[indices[o_norm]][indices[d_norm]]
    except:
        return None

def detectar_intencion(m):
    ml = m.lower()
    if any(p in ml for p in ["primer", "primero"]):
        return "primer"
    if any(p in ml for p in ["próximo", "proximo", "siguiente"]):
        return "proximo"
    if any(p in ml for p in ["último", "ultimo", "final"]):
        return "ultimo"
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

def guardar_sugerencia(telefono, mensaje):
    try:
        sugerencias = []
        if os.path.exists(SUGERENCIAS_FILE):
            with open(SUGERENCIAS_FILE, 'r', encoding='utf-8') as f:
                sugerencias = json.load(f)
        sugerencias.append({
            "fecha": ahora_argentina().strftime("%Y-%m-%d %H:%M:%S"),
            "telefono": telefono,
            "mensaje": mensaje
        })
        with open(SUGERENCIAS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sugerencias, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def mostrar_menu():
    return (
        "👋 *Hola! Soy el asistente virtual* 🚌\n\n"
        "¿Qué querés hacer?\n\n"
        "🔹 1 → 📅 Ver horarios\n"
        "🔹 2 → 💰 Consultar precios\n"
        "🔹 3 → ℹ️ Información útil\n"
        "🔹 4 → ❓ Preguntas frecuentes\n"
        "🔹 5 → 📝 Enviar sugerencias\n"
        "🔹 6 → 📢 Unite al grupo de WhatsApp\n\n"
        "📝 *Ejemplos:*\n"
        "• 'De Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n\n"
        "💬 Escribí 'Ayuda' para más detalles.\n\n"
        "---\n\n"
        "⚠️ *AVISO IMPORTANTE:*  \n"
        "Este bot es un proyecto independiente y NO tiene relación oficial con ninguna empresa de transporte.  \n"
        "Los horarios son orientativos.\n\n"
        "📝 *¿Encontraste un error?*  \n"
        "Escribí *Hola*, luego elegí la opción *5* y enviá tu mensaje. Así ayudás a mejorar el bot para todos."
    )

def mostrar_grupo():
    return (
        "📢 *GRUPO COMUNITARIO DE WHATSAPP*\n\n"
        "Unite al grupo donde los pasajeros comparten información en tiempo real:\n\n"
        "⚠️ *Demoras*\n"
        "⚠️ *Colectivos rotos*\n"
        "⚠️ *Cambios de horarios*\n"
        "⚠️ *Y se ayudan entre viajeros*\n\n"
        "🔗 *Link de invitación:*\n"
        "https://chat.whatsapp.com/LbpAPHZs3PDKXXy9pRtY9X\n\n"
        "¡Entre todos nos mantenemos informados! 🚌"
    )

def no_entendido_inteligente(mensaje):
    m = mensaje.lower().strip()
    
    # Si el usuario escribió algo como "Viale Parana" (dos localidades sin formato)
    palabras = m.split()
    if len(palabras) == 2:
        loc1 = normalizar_localidad(palabras[0])
        loc2 = normalizar_localidad(palabras[1])
        if loc1 and loc2:
            return f"🤔 Para consultar horarios, usá el formato:\n• 'De {loc1} a {loc2}'\n\n¿Querés intentarlo de nuevo? 😊"
    
    return (
        "🤔 *No entendí lo que escribiste.*\n\n"
        "✅ *Frases que funcionan:*\n"
        "• 'De Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n\n"
        "💡 Escribí 'Ayuda' para más ejemplos."
    )

def mostrar_ayuda_detallada():
    return (
        "📘 *GUÍA DE USO - BOT DE HORARIOS*\n\n"
        "Este bot te permite consultar horarios y precios de colectivos de forma rápida por WhatsApp.\n\n"
        "🔹 *¿CÓMO SE USA?*\n"
        "1. Escribí *Hola* para ver el menú principal.\n"
        "2. Elegí una opción (1: horarios, 2: precios, etc.).\n"
        "3. O directamente escribí frases como los ejemplos de abajo.\n\n"
        "✅ *EJEMPLOS DE FRASES QUE FUNCIONAN:*\n"
        "• 'De Parana a Viale' (para ver horarios)\n"
        "• 'Precio de Parana a Maria Grande' (para ver precios)\n"
        "• 'Primer colectivo de Viale a Parana'\n"
        "• 'Próximo de Tabossi a Parana'\n"
        "• 'Último de Parana a Sosa el 17/03'\n\n"
        "📍 *LOCALIDADES CON HORARIOS:*\nParana • Viale • Tabossi • Sosa • Maria Grande\n\n"
        "📍 *LOCALIDADES ADICIONALES (SOLO PARA PRECIOS):*\nAldea San Antonio • Genolet • Sauce • 3 Bocas • Quebracho • El Ramblón\n\n"
        "⚠️ *IMPORTANTE:*\n"
        "Este bot es un proyecto NO OFICIAL. Los horarios son orientativos.\n"
        "Siempre consultá en la terminal antes de viajar.\n\n"
        "📝 *¿VES ALGÚN ERROR?*\n"
        "Escribí *Hola*, luego elegí la opción *5* (Enviar sugerencias) y contanos qué está mal.\n"
        "Así ayudás a mejorar el bot para todos.\n\n"
        "👋 *PARA VOLVER AL MENÚ:*\n"
        "Escribí *Hola* en cualquier momento.\n\n"
        "💬 *¿NECESITÁS AYUDA EN VIVO?*\n"
        "Escribí cualquier frase con 'ayuda' o volvé a escribir *Hola* para reiniciar."
    )

def despedida():
    return "😊 *¡Gracias por consultar!* Escribí 'Hola' para volver a empezar.\n\n⚠️ *Recordatorio:* Este bot es un proyecto NO OFICIAL. Los horarios son orientativos."

# ============================================
# WEBHOOK PRINCIPAL
# ============================================

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    if 'X-Forwarded-Proto' in request.headers:
        protocol = request.headers.get('X-Forwarded-Proto', 'http')
        host = request.headers.get('X-Forwarded-Host', request.host)
        request.url = f"{protocol}://{host}{request.path}"
    
    try:
        incoming_msg = request.values.get('Body', '').strip()
        sender = request.values.get('From', '')
        print(f"\n📩 MENSAJE: '{incoming_msg}' de {sender}")
        
        registrar_interaccion(sender, incoming_msg)
        
        resp = MessagingResponse()
        msg = resp.message()
        
        if sender not in session:
            session[sender] = {
                "ultimo_origen": None, "ultimo_destino": None, "estado": "menu",
                "intencion": None, "fecha_pendiente": None, "ultimo_mensaje_time": ahora_argentina()
            }
        ctx = session[sender]
        ctx["ultimo_mensaje_time"] = ahora_argentina()
        
        if not contexto_activo(ctx):
            ctx = limpiar_contexto(ctx)
            session[sender] = ctx
        
        # Comandos dueño
        if incoming_msg.lower() == "/estadisticas" and sender == NUMERO_DUENIO:
            r = resumen_stats()
            top_destinos = destinos_mas_frecuentes()
            top_horarios = horarios_mas_consultados()
            texto_destinos = "\n".join([f"• {d}: {c}" for d, c in top_destinos]) if top_destinos else "• (sin datos)"
            texto_horarios = "\n".join([f"• {h}: {c}" for h, c in top_horarios]) if top_horarios else "• (sin datos)"
            msg.body(f"📊 *ESTADÍSTICAS*\n\n👥 Usuarios únicos: {r['total_usuarios']}\n💬 Mensajes totales: {r['total_mensajes']}\n📅 Usuarios hoy: {r['usuarios_hoy']}\n\n🔥 *Destinos más consultados:*\n{texto_destinos}\n\n⏰ *Horarios más consultados:*\n{texto_horarios}")
            return str(resp)
        
        if incoming_msg.lower() == "/limites" and sender == NUMERO_DUENIO:
            limites = cargar_limites_ia()
            config = limites["config"]
            total_usuarios = len(limites["usuarios"])
            msg.body(f"📊 *LÍMITES IA*\n\n⚙️ Máx/día: {config['max_por_dia']}\n📅 Máx/mes: {config['max_por_mes']}\n⏱️ Anti-spam: {config['min_segundos_entre']}s\n👥 Usuarios: {total_usuarios}")
            return str(resp)
        
        if incoming_msg.lower() == "/sugerencias" and sender == NUMERO_DUENIO:
            if os.path.exists(SUGERENCIAS_FILE):
                with open(SUGERENCIAS_FILE, 'r', encoding='utf-8') as f:
                    sugerencias = json.load(f)
                if not sugerencias:
                    msg.body("📝 *No hay sugerencias registradas.*")
                else:
                    ultimas = sugerencias[-10:]
                    texto = "📝 *ÚLTIMAS SUGERENCIAS*\n\n" + "\n\n---\n\n".join([f"📅 {s['fecha']}\n📞 {s['telefono']}\n💬 {s['mensaje']}" for s in ultimas])
                    msg.body(texto)
            else:
                msg.body("📝 *No hay sugerencias registradas.*")
            return str(resp)
        
        # FAQ
        faq = responder_faq(incoming_msg)
        if faq:
            msg.body(faq)
            return str(resp)
        
        # Saludos y despedidas
        if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes"]:
            ctx = limpiar_contexto(ctx)
            session[sender] = ctx
            msg.body(mostrar_menu())
            return str(resp)
        
        if any(p in incoming_msg.lower() for p in ["chau", "adiós", "adios", "bye", "gracias"]):
            ctx = limpiar_contexto(ctx)
            session[sender] = ctx
            msg.body(despedida())
            return str(resp)
        
        if incoming_msg.lower() == "ayuda":
            msg.body(mostrar_ayuda_detallada())
            return str(resp)
        
        # Detectar palabras clave con contexto (limpiando signos de puntuación)
        mensaje_limpio = incoming_msg.lower().strip()
        mensaje_limpio = re.sub(r'[¿?!¡.,;:]', '', mensaje_limpio)
        
        # Precio con contexto
        if mensaje_limpio in ["precio"] and ctx.get("ultimo_origen") and ctx.get("ultimo_destino"):
            origen = ctx["ultimo_origen"]
            destino = ctx["ultimo_destino"]
            print(f"💰 Precio con contexto: {origen} → {destino}")
            precio = obtener_precio(origen, destino)
            if isinstance(precio, dict):
                msg.body(f"💰 {origen} → {destino}\n🛣️ Ruta 10: ${precio.get('ruta10', 'N/A')}\n🛣️ Ruta 18: ${precio.get('ruta18', 'N/A')}")
            elif precio:
                msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**")
            else:
                msg.body(f"😕 No tengo precio de {origen} a {destino}")
            registrar_interaccion(sender, incoming_msg, tipo="precio", consulta=f"{origen}→{destino}")
            return str(resp)
        
        # Próximo con contexto
        if mensaje_limpio in ["próximo", "proximo"] and ctx.get("ultimo_origen") and ctx.get("ultimo_destino"):
            origen = ctx["ultimo_origen"]
            destino = ctx["ultimo_destino"]
            fecha = ahora_argentina()
            tipo_dia = obtener_tipo_dia(fecha)
            hora_actual = fecha.hour * 60 + fecha.minute
            resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual)
            todos = [(h, r) for r in ["R10", "R18", "R10+R18"] for h in resultados[r]]
            todos.sort(key=lambda x: hora_a_minutos(x[0]))
            if todos:
                msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {todos[0][0]} por {todos[0][1]}")
                registrar_interaccion(sender, incoming_msg, tipo="proximo", consulta=f"{origen}→{destino}", horario=todos[0][0])
            else:
                msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy")
            return str(resp)
        
        # Primer con contexto
        if mensaje_limpio in ["primer", "primero"] and ctx.get("ultimo_origen") and ctx.get("ultimo_destino"):
            origen = ctx["ultimo_origen"]
            destino = ctx["ultimo_destino"]
            fecha = ahora_argentina()
            tipo_dia = obtener_tipo_dia(fecha)
            resultados = buscar_horarios(origen, destino, tipo_dia)
            primero = None
            for r in ["R10", "R18", "R10+R18"]:
                if resultados[r]:
                    if not primero or hora_a_minutos(resultados[r][0]) < hora_a_minutos(primero[0]):
                        primero = (resultados[r][0], r)
            if primero:
                msg.body(f"🚌 El primer colectivo de {origen} a {destino} sale a las {primero[0]} por {primero[1]}")
                registrar_interaccion(sender, incoming_msg, tipo="primer", consulta=f"{origen}→{destino}", horario=primero[0])
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} hoy")
            return str(resp)
        
        # Último con contexto
        if mensaje_limpio in ["último", "ultimo", "final"] and ctx.get("ultimo_origen") and ctx.get("ultimo_destino"):
            origen = ctx["ultimo_origen"]
            destino = ctx["ultimo_destino"]
            fecha = ahora_argentina()
            tipo_dia = obtener_tipo_dia(fecha)
            resultados = buscar_horarios(origen, destino, tipo_dia)
            ultimo = None
            for r in ["R10", "R18", "R10+R18"]:
                if resultados[r]:
                    if not ultimo or hora_a_minutos(resultados[r][-1]) > hora_a_minutos(ultimo[0]):
                        ultimo = (resultados[r][-1], r)
            if ultimo:
                msg.body(f"🚌 El último colectivo de {origen} a {destino} sale a las {ultimo[0]} por {ultimo[1]}")
                registrar_interaccion(sender, incoming_msg, tipo="ultimo", consulta=f"{origen}→{destino}", horario=ultimo[0])
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} hoy")
            return str(resp)
        
        # Opciones numéricas
        if incoming_msg == "1":
            ctx["estado"] = "esperando_origen_horarios"
            session[sender] = ctx
            msg.body("📝 Decime de dónde a dónde (ej: De Viale a Parana)")
            return str(resp)
        
        if incoming_msg == "2":
            ctx["estado"] = "esperando_origen_precios"
            session[sender] = ctx
            msg.body("📝 Decime de dónde a dónde (ej: De Viale a Parana)")
            return str(resp)
        
        if incoming_msg == "3":
            msg.body(mostrar_info_util())
            return str(resp)
        
        if incoming_msg == "4":
            msg.body(mostrar_faq())
            return str(resp)
        
        if incoming_msg == "5":
            ctx["estado"] = "esperando_sugerencia"
            session[sender] = ctx
            msg.body(mostrar_menu_sugerencia())
            return str(resp)
        
        if incoming_msg == "6":
            msg.body(mostrar_grupo())
            return str(resp)
        
        # Sugerencias
        if ctx.get("estado") == "esperando_sugerencia":
            if incoming_msg.lower() == "cancelar":
                ctx["estado"] = "menu"
                session[sender] = ctx
                msg.body(mostrar_menu())
                return str(resp)
            
            match_telefono = re.search(r'(?:tel[eé]fono:?)\s*(\d+)', incoming_msg, re.IGNORECASE)
            match_mensaje = re.search(r'(?:mensaje:?)\s*(.+?)(?:\s*(?:gracias|$))', incoming_msg, re.IGNORECASE)
            
            if match_telefono and match_mensaje:
                if guardar_sugerencia(match_telefono.group(1), match_mensaje.group(1)):
                    msg.body("✅ *¡Gracias por tu sugerencia!*")
                else:
                    msg.body("❌ Error al guardar")
                ctx["estado"] = "menu"
                session[sender] = ctx
                return str(resp)
            else:
                msg.body("📝 Formato incorrecto. Usá:\nTeléfono: 3435123456\nMensaje: tu texto\n\nEscribí 'Cancelar' para volver.")
                return str(resp)
        
        # Procesar precios
        if ctx.get("estado") == "esperando_origen_precios":
            origen, destino = extraer_origen_destino(incoming_msg)
            if origen and destino:
                precio = obtener_precio(origen, destino)
                if isinstance(precio, dict):
                    msg.body(f"💰 {origen} → {destino}\n🛣️ Ruta 10: ${precio.get('ruta10', 'N/A')}\n🛣️ Ruta 18: ${precio.get('ruta18', 'N/A')}")
                elif precio:
                    msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**")
                else:
                    msg.body(f"😕 No tengo precio de {origen} a {destino}")
                registrar_interaccion(sender, incoming_msg, tipo="precio", consulta=f"{origen}→{destino}")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                session[sender] = ctx
                return str(resp)
            else:
                if DEEPSEEK_API_KEY and not es_consulta_prohibida_para_ia(incoming_msg):
                    respuesta_ia = consultar_deepseek(incoming_msg, sender, ctx)
                    if respuesta_ia:
                        msg.body(respuesta_ia)
                        return str(resp)
                msg.body(no_entendido_inteligente(incoming_msg))
                return str(resp)
        
        # Procesar horarios
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
                    primero = None
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r]:
                            if not primero or hora_a_minutos(resultados[r][0]) < hora_a_minutos(primero[0]):
                                primero = (resultados[r][0], r)
                    if primero:
                        msg.body(f"🚌 El primer colectivo sale a las {primero[0]} por {primero[1]}")
                        registrar_interaccion(sender, incoming_msg, tipo="primer", consulta=f"{origen}→{destino}", horario=primero[0])
                    else:
                        msg.body(f"😕 No hay servicios para {fecha_str}")
                
                elif intencion == "proximo":
                    ahora = ahora_argentina()
                    hora_actual = ahora.hour*60 + ahora.minute
                    resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual)
                    todos = [(h, r) for r in ["R10", "R18", "R10+R18"] for h in resultados[r]]
                    todos.sort(key=lambda x: hora_a_minutos(x[0]))
                    if todos:
                        msg.body(f"🚌 El próximo colectivo sale a las {todos[0][0]} por {todos[0][1]}")
                        registrar_interaccion(sender, incoming_msg, tipo="proximo", consulta=f"{origen}→{destino}", horario=todos[0][0])
                    else:
                        msg.body(f"😕 No hay más servicios hoy")
                
                elif intencion == "ultimo":
                    ultimo = None
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r]:
                            if not ultimo or hora_a_minutos(resultados[r][-1]) > hora_a_minutos(ultimo[0]):
                                ultimo = (resultados[r][-1], r)
                    if ultimo:
                        msg.body(f"🚌 El último colectivo sale a las {ultimo[0]} por {ultimo[1]}")
                        registrar_interaccion(sender, incoming_msg, tipo="ultimo", consulta=f"{origen}→{destino}", horario=ultimo[0])
                    else:
                        msg.body(f"😕 No hay servicios para {fecha_str}")
                
                else:
                    msg.body(formatear_horarios(resultados, origen, destino, fecha_str))
                    registrar_interaccion(sender, incoming_msg, tipo="horarios", consulta=f"{origen}→{destino}")
                
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                ctx["intencion"] = None
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            else:
                # Si no se pudo extraer, pedir formato correcto
                msg.body(pedir_formato_correcto())
                return str(resp)
        
        # Consulta directa
        intencion = detectar_intencion(incoming_msg)
        fecha = interpretar_fecha(incoming_msg)
        origen, destino = extraer_origen_destino(incoming_msg)
        
        if origen and destino:
            tipo_dia = obtener_tipo_dia(fecha)
            ctx["ultimo_origen"] = origen
            ctx["ultimo_destino"] = destino
            session[sender] = ctx
            
            if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "$"]):
                precio = obtener_precio(origen, destino)
                if isinstance(precio, dict):
                    msg.body(f"💰 {origen} → {destino}\n🛣️ Ruta 10: ${precio.get('ruta10', 'N/A')}\n🛣️ Ruta 18: ${precio.get('ruta18', 'N/A')}")
                elif precio:
                    msg.body(f"💰 El pasaje cuesta **${precio}**")
                else:
                    msg.body(f"😕 No tengo precio")
                registrar_interaccion(sender, incoming_msg, tipo="precio", consulta=f"{origen}→{destino}")
                return str(resp)
            
            elif intencion:
                resultados = buscar_horarios(origen, destino, tipo_dia)
                fecha_str = fecha.strftime("%d/%m/%Y")
                
                if intencion == "primer":
                    primero = None
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r]:
                            if not primero or hora_a_minutos(resultados[r][0]) < hora_a_minutos(primero[0]):
                                primero = (resultados[r][0], r)
                    if primero:
                        msg.body(f"🚌 El primer colectivo el {fecha_str} sale a las {primero[0]} por {primero[1]}")
                        registrar_interaccion(sender, incoming_msg, tipo="primer", consulta=f"{origen}→{destino}", horario=primero[0])
                    else:
                        msg.body(f"😕 No hay servicios")
                
                elif intencion == "proximo":
                    ahora = ahora_argentina()
                    hora_actual = ahora.hour*60 + ahora.minute
                    resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual)
                    todos = [(h, r) for r in ["R10", "R18", "R10+R18"] for h in resultados[r]]
                    todos.sort(key=lambda x: hora_a_minutos(x[0]))
                    if todos:
                        msg.body(f"🚌 El próximo colectivo sale a las {todos[0][0]} por {todos[0][1]}")
                        registrar_interaccion(sender, incoming_msg, tipo="proximo", consulta=f"{origen}→{destino}", horario=todos[0][0])
                    else:
                        msg.body(f"😕 No hay más servicios hoy")
                
                elif intencion == "ultimo":
                    ultimo = None
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r]:
                            if not ultimo or hora_a_minutos(resultados[r][-1]) > hora_a_minutos(ultimo[0]):
                                ultimo = (resultados[r][-1], r)
                    if ultimo:
                        msg.body(f"🚌 El último colectivo el {fecha_str} sale a las {ultimo[0]} por {ultimo[1]}")
                        registrar_interaccion(sender, incoming_msg, tipo="ultimo", consulta=f"{origen}→{destino}", horario=ultimo[0])
                    else:
                        msg.body(f"😕 No hay servicios")
                
                return str(resp)
            
            else:
                hora_limite = extraer_hora_limite(incoming_msg)
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_limite)
                fecha_str = fecha.strftime("%d/%m/%Y")
                msg.body(formatear_horarios(resultados, origen, destino, fecha_str))
                registrar_interaccion(sender, incoming_msg, tipo="horarios", consulta=f"{origen}→{destino}")
                return str(resp)
        
        # Si no se pudo extraer en consulta directa, pedir formato correcto
        msg.body(pedir_formato_correcto())
        return str(resp)
    
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
        resp = MessagingResponse()
        resp.message().body("⚠️ Ocurrió un error. Por favor, intentá de nuevo.")
        return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Bot listo en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
