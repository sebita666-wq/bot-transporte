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

print("🚀 BOT INICIADO - VERSIÓN HÍBRIDA (DeepSeek IA + Lógica Estándar)")

NUMERO_DUENIO = os.environ.get('NUMERO_DUENIO', "whatsapp:+5493434727811")
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_para_sesiones')
STATS_FILE = 'estadisticas.json'
SUGERENCIAS_FILE = 'sugerencias.json'

# DeepSeek API Key (desde variable de entorno)
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

app.secret_key = SECRET_KEY

def ahora_argentina():
    return datetime.now(timezone)

# ============================================
# VALIDAR ARCHIVOS JSON
# ============================================
def validar_archivos_json():
    archivos = ['horarios.json', 'tarifas.json', 'feriados.json', 'duraciones.json']
    for archivo in archivos:
        if not os.path.exists(archivo):
            print(f"❌ ERROR: No se encuentra el archivo {archivo}")
            return False
    print("✅ Todos los archivos JSON están presentes")
    return True

if not validar_archivos_json():
    print("❌ No se puede iniciar el bot. Faltan archivos.")
    exit(1)

# ============================================
# CARGAR FERIADOS DESDE JSON
# ============================================
def cargar_feriados():
    try:
        with open('feriados.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('feriados_2026', [])
    except Exception as e:
        print(f"❌ Error cargando feriados.json: {e}")
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
        return {"localidades": [], "matriz_precios": [], "precios_especiales": {}}

def cargar_duraciones():
    try:
        with open('duraciones.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error cargando duraciones.json: {e}")
        return {}

horarios_habiles, horarios_sabados, horarios_domingos = cargar_horarios()
tarifas_data = cargar_tarifas()
localidades = tarifas_data.get('localidades', [])
matriz_precios = tarifas_data.get('matriz_precios', [])
precios_especiales = tarifas_data.get('precios_especiales', {})
duraciones = cargar_duraciones()

print(f"✅ Horarios cargados: hábiles={len(horarios_habiles)}, sábados={len(horarios_sabados)}, domingos={len(horarios_domingos)}")
print(f"✅ Tarifas cargadas: {len(localidades)} localidades, {len(precios_especiales)} precios especiales")
print(f"✅ Duraciones cargadas: {len(duraciones)} tramos")
print(f"🤖 DeepSeek IA: {'Habilitada' if DEEPSEEK_API_KEY else 'No configurada'}")

# ============================================
# FUNCIÓN PARA CONSULTAR DEEPSEEK (IA CON PROMPT MEJORADO)
# ============================================
def consultar_deepseek(mensaje, historial=None):
    """Envía una consulta a DeepSeek y devuelve la respuesta con formato amigable"""
    if not DEEPSEEK_API_KEY:
        print("⚠️ DeepSeek no configurado")
        return None
    
    try:
        # Preparar mensajes para la API con PROMPT MEJORADO
        mensajes = [
            {
                "role": "system",
                "content": """🚌 *Asistente de Transporte - Empresa de Viajes* 🚌

🎯 Soy un asistente para consultas de colectivos en Entre Ríos.

📍 *Localidades que conozco:*
Paraná, Viale, Tabossi, Sosa, María Grande, Aldea San Antonio, Genolet, Sauce, 3 Bocas, Quebracho, El Ramblón.

📋 *REGLAS IMPORTANTES:*

1️⃣ Respondé SIEMPRE con EMOTICONES para hacer la conversación más amigable y cálida.
   - 🚌 para colectivos
   - 📍 para ubicaciones
   - 💰 para precios
   - ✅ para confirmaciones
   - ❌ para errores
   - 😊 para saludos y despedidas
   - ⏰ para horarios
   - 📅 para fechas
   - 🤔 cuando no entiendas algo

2️⃣ Usá NEGRITAS con *texto* para destacar información importante.

3️⃣ Usá SALTOS DE LÍNEA cada 2 o 3 oraciones para mejorar la legibilidad.

4️⃣ Si te preguntan por HORARIOS ESPECÍFICOS (ej: "De Parana a Viale"), sugerí usar el comando exacto para obtener información precisa.

5️⃣ Sé BREVE y AMIGABLE. No respondas con textos extremadamente largos.

6️⃣ Si NO SABÉS algo, decí: "No tengo esa información. Te recomiendo consultar en la terminal o con el administrador. 😊"

7️⃣ Si el usuario pregunta algo gracioso o fuera de contexto (ej: "ir a la luna"), respondé con humor pero aclarando que tu función es ayudar con el transporte local.

💡 *EJEMPLO DE RESPUESTA IDEAL:*
🚌 *Paraná → Viale*
⏰ Horarios: 04:45, 05:35, 06:40, 08:45, 10:00...
💰 *Precio:* $7.500
📍 ¿Necesitas algo más? 😊

👍 Siempre cerrá con una pregunta amigable o un emoticón positivo."""
            }
        ]
        
        # Agregar historial reciente si existe
        if historial:
            mensajes.extend(historial[-5:])  # últimos 5 mensajes para contexto
        
        # Agregar mensaje actual
        mensajes.append({"role": "user", "content": mensaje})
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": mensajes,
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            resultado = response.json()
            return resultado['choices'][0]['message']['content']
        elif response.status_code == 402:
            print("⚠️ Sin saldo en DeepSeek (Error 402)")
            return None
        else:
            print(f"❌ Error DeepSeek: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error consultando DeepSeek: {e}")
        return None

# ============================================
# FUNCIONES PARA SUGERENCIAS / RECLAMOS
# ============================================
def guardar_sugerencia(telefono, mensaje):
    """Guarda una sugerencia o reclamo en el archivo sugerencias.json"""
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
    except Exception as e:
        print(f"❌ Error guardando sugerencia: {e}")
        return False

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

        # Verificar si es un precio especial
        clave = f"{o_norm}-{d_norm}"
        if clave in precios_especiales:
            return precios_especiales[clave]

        # Si no, matriz normal
        indices = {loc["principal"]: i for i, loc in enumerate(localidades)}
        return matriz_precios[indices[o_norm]][indices[d_norm]]
    except:
        return None

# ============================================
# FUNCIÓN DE DURACIÓN
# ============================================
def obtener_duracion(origen, destino):
    """Devuelve la duración en minutos entre dos localidades."""
    clave = f"{origen}-{destino}"
    return duraciones.get(clave)

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
    """
    Busca horarios y los separa por tipo de ruta:
    - R10: viajes directos Paraná ↔ María Grande
    - R18: viajes tradicionales por todas las localidades
    - R10+R18: viajes mixtos (Paraná → María Grande por R10, luego a Sosa/Tabossi por R18)
    """
    resultados = {"R10": [], "R18": [], "R10+R18": []}
    
    for h in obtener_horarios_por_dia(tipo):
        if h["origen"] == origen and h["destino"] == destino:
            if hora_limite is None or hora_a_minutos(h["hora"]) >= hora_limite:
                ruta = h["ruta"]
                if ruta in resultados:
                    resultados[ruta].append(h["hora"])
    
    # Ordenar cada lista por hora
    for r in resultados:
        resultados[r].sort(key=hora_a_minutos)
    
    return resultados

def formatear_horarios(resultados, origen, destino, fecha_str):
    """
    Formatea la respuesta de horarios de manera clara para el pasajero,
    separando por tipo de ruta.
    """
    if not any(resultados.values()):
        return f"😕 No encontré servicios de {origen} a {destino} para {fecha_str}."
    
    duracion = obtener_duracion(origen, destino)
    duracion_str = f" (aprox. {duracion} min)" if duracion else ""
    
    texto = f"🚌 Servicios de {origen} a {destino}{duracion_str} para {fecha_str}:\n\n"
    
    if resultados["R10+R18"]:
        texto += "🛣️ *Por Ruta 10 + Ruta 18:*\n"
        texto += "\n".join([f"• {h}" for h in resultados["R10+R18"]]) + "\n\n"
    
    if resultados["R10"]:
        texto += "🛣️ *Por Ruta 10:*\n"
        texto += "\n".join([f"• {h}" for h in resultados["R10"]]) + "\n\n"
    
    if resultados["R18"]:
        texto += "🛣️ *Por Ruta 18:*\n"
        texto += "\n".join([f"• {h}" for h in resultados["R18"]]) + "\n\n"
    
    texto += "😊 ¿Necesitas precio, próximo o último?"
    return texto

# ============================================
# FUNCIONES DE RESPUESTA
# ============================================
def mostrar_menu():
    return (
        "🚌 *FASE DE PRUEBA* - Los horarios son orientativos.\n\n"
        "👋 *Hola! Soy el asistente virtual de la Empresa de viajes* 🚌\n\n"
        "¿Qué querés hacer hoy?\n\n"
        "🔹 *1* → Ver horarios de colectivos\n"
        "🔹 *2* → Consultar precios de pasajes\n"
        "🔹 *3* → Información útil (terminales, teléfono)\n"
        "🔹 *4* → Preguntas frecuentes (equipaje, mascotas, etc.)\n"
        "🔹 *5* → 📝 Enviar sugerencia / reclamo\n\n"
        "📝 *También podés escribir directamente:*\n"
        "• 'De Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n"
        "• 'Próximo de Tabossi a Parana'\n"
        "• 'Último de Parana a Sosa el 17/03'\n\n"
        "💬 *Escribí 'Ayuda' si querés más detalles.*"
    )

def mostrar_menu_sugerencia():
    return (
        "📝 *Envío de sugerencias / reclamos*\n\n"
        "Por favor, escribí tu mensaje en el siguiente formato:\n\n"
        "*Teléfono:* Tu número\n"
        "*Mensaje:* Tu sugerencia o reclamo\n\n"
        "📌 *Ejemplo:*\n"
        "Teléfono: 3435123456\n"
        "Mensaje: El colectivo de las 15:30 siempre llega tarde\n\n"
        "✍️ *Escribí 'Cancelar' para volver al menú.*"
    )

def mostrar_ayuda_detallada():
    return (
        "📘 *GUÍA DE USO DEL BOT*\n\n"
        "✅ *EJEMPLOS:*\n"
        "• 'De Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n"
        "• 'Próximo de Tabossi a Parana'\n"
        "• 'Último de Parana a Sosa el 17/03'\n"
        "• 'Horarios de Parana a Tabossi después de las 15'\n\n"
        
        "🛣️ *RUTAS:*\n"
        "• *Ruta 18:* Paraná → Viale → Tabossi → Sosa → María Grande\n"
        "• *Ruta 10:* Paraná ↔ María Grande (directo)\n"
        "• *Ruta 10 + 18:* Paraná → María Grande (R10) → Sosa/Tabossi (R18)\n\n"
        
        "📍 *LOCALIDADES:*\n"
        "Parana, Viale, Tabossi, Sosa, Maria Grande, Aldea San Antonio, Genolet, Sauce, 3 Bocas, Quebracho, El Ramblón, Paraje de las Piedras, Arroyo Carmona, Sauce Montrull\n\n"
        
        "❌ *ERRORES COMUNES:*\n"
        "• 'Parana Viale' → falta 'a'\n"
        "• 'Quiero ir a Viale' → falta origen\n"
        "• 'Primero' → falta origen/destino\n\n"
        
        "💡 *TIP:* Usá 'De X a Y' o 'X a Y'\n"
        "📅 Fechas: '17/03' o '17 de marzo'\n"
        "👋 Escribí 'Hola' para volver al menú."
    )

def no_entendido_inteligente(mensaje):
    m = mensaje.lower().strip()
    
    # Detectar si el mensaje contiene una localidad conocida pero sin formato
    localidades_conocidas = ["parana", "viale", "tabossi", "sosa", "maria grande", "genolet", "sauce", "3 bocas", "quebracho", "el ramblon", "aldea san antonio"]
    
    tiene_localidad = any(loc in m for loc in localidades_conocidas)
    
    if "precio" in m and not tiene_localidad:
        return (
            "🤔 *Para consultar un precio, necesito el origen y destino.*\n\n"
            "✍️ *Escribí por ejemplo:*\n"
            "• 'Precio de Parana a Viale'\n"
            "• 'Cuánto sale de Tabossi a Parana'\n"
            "• '$ de Sosa a Maria Grande'"
        )
    
    if any(p in m for p in ["primer", "próximo", "ultimo"]) and not tiene_localidad:
        return (
            "🤔 *Para buscar el primer, próximo o último colectivo, necesito el origen y destino.*\n\n"
            "✍️ *Escribí por ejemplo:*\n"
            "• 'Primer colectivo de Viale a Parana'\n"
            "• 'Próximo de Tabossi a Parana'\n"
            "• 'Último de Parana a Sosa'"
        )
    
    if tiene_localidad and " a " not in m:
        return (
            f"🤔 *Veo que mencionaste '{mensaje}', pero faltaría la palabra 'a'.*\n\n"
            "✍️ *Probá con:*\n"
            f"• 'De {mensaje} a ...'\n"
            f"• '{mensaje} a ...'"
        )
    
    if "ayuda" in m or "como" in m:
        return mostrar_ayuda_detallada()
    
    # Mensaje genérico si no aplica ninguna de las anteriores
    return (
        "🤔 *Ups! No entendí lo que escribiste.*\n\n"
        "✅ *Frases que funcionan:*\n"
        "• 'De Parana a Viale'\n"
        "• 'Precio de Parana a Maria Grande'\n"
        "• 'Primer colectivo de Viale a Parana'\n"
        "• 'Próximo de Tabossi a Parana'\n"
        "• 'Último de Parana a Sosa el 17/03'\n\n"
        "💡 *Escribí 'Ayuda' para ver la guía completa.*"
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
        "➡️ Ej: 'pago', 'equipaje', 'mascota', 'reclamo'"
    )

def mostrar_info_util():
    return (
        "📌 *Información útil*\n\n"
        "📍 *Terminal Paraná:* Av. Ramírez 1200\n"
        "📍 *Terminal María Grande:* San Martín 450\n"
        "📍 *Terminal Viale:* (pendiente)\n\n"
        "📞 *Teléfono de contacto:* 343 456-7890\n"
        "⏰ *Atención:* Lun a Dom 6:00 a 22:00\n\n"
        "🌐 *Web:* (próximamente)"
    )

def despedida():
    return (
        "😊 *¡Gracias por consultar!*\n\n"
        "Si necesitás algo más, escribí 'Hola' para empezar de nuevo."
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
    
    if any(p in m for p in ["reclamo", "problema", "queja"]):
        return ("📝 *Reclamos y sugerencias*\n\n"
                "Para enviar un reclamo o sugerencia, escribí *5* en el menú principal y seguí las instrucciones.\n\n"
                "También podés acercarte a cualquiera de nuestras terminales o escribirnos a este mismo WhatsApp.\n"
                "Tu opinión nos ayuda a mejorar.")
    
    return None

# ============================================
# ESTADÍSTICAS MEJORADAS
# ============================================
def cargar_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
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
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=2)

def registrar_interaccion(sender, mensaje, tipo=None, consulta=None, horario=None):
    """Registra interacción del usuario con estadísticas mejoradas"""
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
        
        # Verificar y crear las claves si no existen (para usuarios viejos)
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
    
    usuarios_hoy = sum(
        1 for u in stats["usuarios"].values()
        if u["ultimo_contacto"].startswith(hoy)
    )
    
    usuarios_semana = sum(
        1 for u in stats["usuarios"].values()
        if u["ultimo_contacto"][:10] >= semana
    )
    
    return {
        "total_usuarios": stats["metricas"]["total_usuarios_unicos"],
        "total_mensajes": stats["metricas"]["total_mensajes"],
        "usuarios_hoy": usuarios_hoy,
        "usuarios_semana": usuarios_semana,
        "ultimo_reinicio": stats["metricas"]["ultimo_reinicio"]
    }

def destinos_mas_frecuentes():
    """Devuelve los 5 destinos más consultados"""
    stats = cargar_stats()
    destinos = []
    for usuario, datos in stats["usuarios"].items():
        destinos.extend(datos.get("destinos_consultados", []))
    contador = Counter(destinos)
    return contador.most_common(5)

def horarios_mas_consultados():
    """Devuelve los 5 horarios más consultados"""
    stats = cargar_stats()
    horarios = []
    for usuario, datos in stats["usuarios"].items():
        horarios.extend(datos.get("horarios_consultados", []))
    contador = Counter(horarios)
    return contador.most_common(5)

# ============================================
# WEBHOOK PRINCIPAL (CON MODO HÍBRIDO)
# ============================================
@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    # ============================================
    # FORZAR LA URL CORRECTA PARA RENDER (PROXY)
    # ============================================
    if 'X-Forwarded-Proto' in request.headers:
        protocol = request.headers.get('X-Forwarded-Proto', 'http')
        host = request.headers.get('X-Forwarded-Host', request.host)
        request.url = f"{protocol}://{host}{request.path}"
    
    try:
        incoming_msg = request.values.get('Body', '').strip()
        sender = request.values.get('From', '')
        print(f"\n📩 MENSAJE RECIBIDO: '{incoming_msg}' de {sender}")

        # Registrar interacción básica (sin tipo aún)
        registrar_interaccion(sender, incoming_msg)

        resp = MessagingResponse()
        msg = resp.message()

        if sender not in session:
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
        ctx = session[sender]

        # ============================================
        # COMANDO DUEÑO - ESTADÍSTICAS MEJORADAS
        # ============================================
        if incoming_msg.lower() == "/estadisticas" and sender == NUMERO_DUENIO:
            print("✅ Comando: estadísticas")
            r = resumen_stats()
            top_destinos = destinos_mas_frecuentes()
            top_horarios = horarios_mas_consultados()
            
            texto_destinos = "\n".join([f"• {d}: {c}" for d, c in top_destinos]) if top_destinos else "• (sin datos)"
            texto_horarios = "\n".join([f"• {h}: {c}" for h, c in top_horarios]) if top_horarios else "• (sin datos)"
            
            msg.body(
                f"📊 *ESTADÍSTICAS*\n\n"
                f"👥 Usuarios únicos: {r['total_usuarios']}\n"
                f"💬 Mensajes totales: {r['total_mensajes']}\n"
                f"📅 Usuarios hoy: {r['usuarios_hoy']}\n"
                f"📆 Usuarios última semana: {r['usuarios_semana']}\n"
                f"🔄 Último reinicio: {r['ultimo_reinicio']}\n\n"
                f"🔥 *Destinos más consultados:*\n{texto_destinos}\n\n"
                f"⏰ *Horarios más consultados:*\n{texto_horarios}"
            )
            return str(resp)

        # ============================================
        # COMANDO DUEÑO - VER SUGERENCIAS
        # ============================================
        if incoming_msg.lower() == "/sugerencias" and sender == NUMERO_DUENIO:
            print("✅ Comando: ver sugerencias")
            if os.path.exists(SUGERENCIAS_FILE):
                with open(SUGERENCIAS_FILE, 'r', encoding='utf-8') as f:
                    sugerencias = json.load(f)
                
                if not sugerencias:
                    msg.body("📝 *No hay sugerencias registradas.*\n\n😊 *Para volver al menú escribí 'Hola'*")
                else:
                    ultimas = sugerencias[-10:]
                    texto = "📝 *ÚLTIMAS SUGERENCIAS*\n\n"
                    for s in ultimas:
                        fecha_formateada = s['fecha'].replace('-', '/').replace('  ', ' ')
                        texto += f"📅 {fecha_formateada}\n"
                        texto += f"📞 {s['telefono']}\n"
                        texto += f"💬 {s['mensaje']}\n\n---\n\n"
                    texto += "😊 *Para volver al menú escribí 'Hola'*"
                    msg.body(texto)
            else:
                msg.body("📝 *No hay sugerencias registradas.*\n\n😊 *Para volver al menú escribí 'Hola'*")
            return str(resp)

        # ============================================
        # DESPEDIDA
        # ============================================
        if any(p in incoming_msg.lower() for p in ["chau", "adiós", "adios", "bye", "gracias"]):
            print("✅ Despedida")
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
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
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "esperando_origen_horarios", "intencion": None, "fecha_pendiente": None}
            msg.body("📝 Decime de dónde a dónde querés viajar (ej: De Viale a Parana)")
            return str(resp)
        if incoming_msg == "2":
            print("✅ Opción 2: Precios")
            session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "esperando_origen_precios", "intencion": None, "fecha_pendiente": None}
            msg.body("📝 Decime de dónde a dónde querés viajar (ej: De Viale a Parana)")
            return str(resp)
        if incoming_msg == "3":
            print("✅ Opción 3: Información útil")
            msg.body(mostrar_info_util())
            return str(resp)
        if incoming_msg == "4":
            print("✅ Opción 4: Preguntas frecuentes")
            msg.body(mostrar_faq())
            return str(resp)
        if incoming_msg == "5":
            print("✅ Opción 5: Sugerencias / Reclamos")
            ctx["estado"] = "esperando_sugerencia"
            session[sender] = ctx
            msg.body(mostrar_menu_sugerencia())
            return str(resp)

        # ============================================
        # PROCESAR SUGERENCIA / RECLAMO
        # ============================================
        if ctx.get("estado") == "esperando_sugerencia":
            if incoming_msg.lower() == "cancelar":
                ctx["estado"] = "menu"
                session[sender] = ctx
                msg.body(mostrar_menu())
                return str(resp)
            
            lineas = incoming_msg.split('\n')
            telefono = None
            mensaje_texto = None
            
            for linea in lineas:
                linea = linea.strip()
                if linea.lower().startswith("teléfono:") or linea.lower().startswith("telefono:"):
                    telefono = linea.split(':', 1)[1].strip()
                elif linea.lower().startswith("mensaje:"):
                    mensaje_texto = linea.split(':', 1)[1].strip()
            
            if not telefono or not mensaje_texto:
                import re
                match_telefono = re.search(r'(?:tel[eé]fono:?)\s*(\d+)', incoming_msg, re.IGNORECASE)
                match_mensaje = re.search(r'(?:mensaje:?)\s*(.+?)(?:\s*(?:gracias|$))', incoming_msg, re.IGNORECASE)
                if match_telefono:
                    telefono = match_telefono.group(1)
                if match_mensaje:
                    mensaje_texto = match_mensaje.group(1).strip()
            
            if telefono and mensaje_texto:
                if guardar_sugerencia(telefono, mensaje_texto):
                    msg.body("✅ *¡Gracias por tu sugerencia!*\n\nCon ello nos ayudas a mejorar día a día.\n\nPara comenzar de nuevo escribe *Hola*")
                else:
                    msg.body("❌ *Error al guardar la sugerencia.*\nPor favor, intentá de nuevo más tarde.")
                ctx["estado"] = "menu"
                session[sender] = ctx
                return str(resp)
            else:
                msg.body("📝 *Formato incorrecto.*\n\nUsá el formato:\nTeléfono: tu número\nMensaje: tu sugerencia o reclamo\n\nEscribí 'Cancelar' para volver.")
                return str(resp)

        # ============================================
        # SALUDO
        # ============================================
        if incoming_msg.lower() in ["hola", "buenos dias", "buenas tardes"]:
            print("✅ Saludo")
            msg.body(mostrar_menu())
            return str(resp)

        if incoming_msg.lower() == "ayuda":
            print("✅ Ayuda detallada")
            msg.body(mostrar_ayuda_detallada())
            return str(resp)

        # ============================================
        # PROCESAR SEGÚN ESTADO
        # ============================================
        if ctx.get("estado") == "esperando_origen_precios":
            print("🔍 Estado: esperando origen para PRECIO")
            origen, destino = extraer_origen_destino(incoming_msg)
            if origen and destino:
                precio = obtener_precio(origen, destino)
                if isinstance(precio, dict):
                    msg.body(f"💰 El pasaje de {origen} a {destino} tiene dos precios:\n\n🛣️ Ruta 10: $8.580\n🛣️ Ruta 18: $9.900")
                elif precio:
                    msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {origen} a {destino}.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                session[sender] = ctx
                return str(resp)
            else:
                # Intentar con IA si no se pudo extraer
                if DEEPSEEK_API_KEY:
                    respuesta_ia = consultar_deepseek(incoming_msg)
                    if respuesta_ia:
                        msg.body(respuesta_ia)
                        return str(resp)
                msg.body(no_entendido_inteligente(incoming_msg))
                return str(resp)

        if ctx.get("estado") == "esperando_origen_horarios":
            print("🔍 Estado: esperando origen para HORARIOS")
            origen, destino = extraer_origen_destino(incoming_msg)
            if origen and destino:
                fecha = ctx.get("fecha_pendiente") or interpretar_fecha(incoming_msg)
                tipo_dia = obtener_tipo_dia(fecha)
                intencion = ctx.get("intencion")
                hora_limite = extraer_hora_limite(incoming_msg) if not intencion else None
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_limite)
                fecha_str = fecha.strftime("%d/%m/%Y")

                if intencion == "primer":
                    if any(resultados.values()):
                        primer = "99:99"
                        ruta = ""
                        for r in ["R10", "R18", "R10+R18"]:
                            if resultados[r] and hora_a_minutos(resultados[r][0]) < hora_a_minutos(primer):
                                primer, ruta = resultados[r][0], r
                        msg.body(f"🚌 El primer colectivo de {origen} a {destino} el {fecha_str} sale a las {primer} por {ruta}.")
                    else:
                        msg.body(f"😕 No hay servicios de {origen} a {destino} para {fecha_str}.")
                
                elif intencion == "proximo":
                    ahora = ahora_argentina()
                    hora_actual = ahora.hour*60 + ahora.minute
                    resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual)
                    if any(resultados.values()):
                        todos = []
                        for r in ["R10", "R18", "R10+R18"]:
                            for h in resultados[r]:
                                todos.append((h, r))
                        todos.sort(key=lambda x: hora_a_minutos(x[0]))
                        
                        if todos:
                            prox_hora, prox_ruta = todos[0]
                            msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox_hora} por {prox_ruta}.")
                        else:
                            msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                    else:
                        msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                
                elif intencion == "ultimo":
                    if any(resultados.values()):
                        ult = "00:00"
                        ruta = ""
                        for r in ["R10", "R18", "R10+R18"]:
                            if resultados[r] and hora_a_minutos(resultados[r][-1]) > hora_a_minutos(ult):
                                ult, ruta = resultados[r][-1], r
                        msg.body(f"🚌 El último colectivo de {origen} a {destino} el {fecha_str} sale a las {ult} por {ruta}.")
                    else:
                        msg.body(f"😕 No hay servicios de {origen} a {destino} para {fecha_str}.")
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
                # Intentar con IA si no se pudo extraer
                if DEEPSEEK_API_KEY:
                    respuesta_ia = consultar_deepseek(incoming_msg)
                    if respuesta_ia:
                        msg.body(respuesta_ia)
                        return str(resp)
                msg.body(no_entendido_inteligente(incoming_msg))
                return str(resp)

        # ============================================
        # NUEVA CONSULTA DIRECTA (MODO HÍBRIDO)
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
                if isinstance(precio, dict):
                    msg.body(f"💰 El pasaje de {origen} a {destino} tiene dos precios:\n\n🛣️ Ruta 10: $8.580\n🛣️ Ruta 18: $9.900")
                elif precio:
                    msg.body(f"💰 El pasaje de {origen} a {destino} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {origen} a {destino}.")
                registrar_interaccion(sender, incoming_msg, tipo="precio", consulta=f"{origen}→{destino}")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            
            # PRIORIDAD 2: PRIMER
            elif intencion == "primer":
                print("  → Es consulta de PRIMER")
                resultados = buscar_horarios(origen, destino, tipo_dia)
                if any(resultados.values()):
                    primer = "99:99"
                    ruta = ""
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r] and hora_a_minutos(resultados[r][0]) < hora_a_minutos(primer):
                            primer, ruta = resultados[r][0], r
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    msg.body(f"🚌 El primer colectivo de {origen} a {destino} el {fecha_str} sale a las {primer} por {ruta}.")
                    registrar_interaccion(sender, incoming_msg, tipo="primer", consulta=f"{origen}→{destino}", horario=primer)
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} para esa fecha.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            
            # PRIORIDAD 3: PRÓXIMO
            elif intencion == "proximo":
                print("  → Es consulta de PRÓXIMO")
                ahora = ahora_argentina()
                hora_actual = ahora.hour*60 + ahora.minute
                resultados = buscar_horarios(origen, destino, tipo_dia, hora_actual)
                if any(resultados.values()):
                    todos = []
                    for r in ["R10", "R18", "R10+R18"]:
                        for h in resultados[r]:
                            todos.append((h, r))
                    todos.sort(key=lambda x: hora_a_minutos(x[0]))
                    
                    if todos:
                        prox_hora, prox_ruta = todos[0]
                        msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox_hora} por {prox_ruta}.")
                        registrar_interaccion(sender, incoming_msg, tipo="proximo", consulta=f"{origen}→{destino}", horario=prox_hora)
                    else:
                        msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                else:
                    msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)
            
            # PRIORIDAD 4: ÚLTIMO
            elif intencion == "ultimo":
                print("  → Es consulta de ÚLTIMO")
                resultados = buscar_horarios(origen, destino, tipo_dia)
                if any(resultados.values()):
                    ult = "00:00"
                    ruta = ""
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r] and hora_a_minutos(resultados[r][-1]) > hora_a_minutos(ult):
                            ult, ruta = resultados[r][-1], r
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    msg.body(f"🚌 El último colectivo de {origen} a {destino} el {fecha_str} sale a las {ult} por {ruta}.")
                    registrar_interaccion(sender, incoming_msg, tipo="ultimo", consulta=f"{origen}→{destino}", horario=ult)
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} para esa fecha.")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
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
                registrar_interaccion(sender, incoming_msg, tipo="horarios", consulta=f"{origen}→{destino}")
                ctx["ultimo_origen"] = origen
                ctx["ultimo_destino"] = destino
                ctx["estado"] = "menu"
                ctx["fecha_pendiente"] = fecha
                session[sender] = ctx
                return str(resp)

        # ============================================
        # INTENCIÓN SIN ORIGEN/DESTINO - DERIVAR A IA
        # ============================================
        if intencion and not origen:
            print(f"✅ Intención detectada sin origen/destino: {intencion}")
            # Intentar con IA primero
            if DEEPSEEK_API_KEY:
                respuesta_ia = consultar_deepseek(incoming_msg)
                if respuesta_ia:
                    msg.body(respuesta_ia)
                    return str(resp)
            # Fallback al flujo normal
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
        # CONSULTA SIN CONTEXTO - DERIVAR A IA
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
                if isinstance(precio, dict):
                    msg.body(f"💰 El pasaje de {o} a {d} tiene dos precios:\n\n🛣️ Ruta 10: $8.580\n🛣️ Ruta 18: $9.900")
                elif precio:
                    msg.body(f"💰 El pasaje de {o} a {d} cuesta **${precio}**.")
                else:
                    msg.body(f"😕 No tengo precio de {o} a {d}.")
                registrar_interaccion(sender, incoming_msg, tipo="precio", consulta=f"{o}→{d}")
                return str(resp)
            
            if any(p in incoming_msg.lower() for p in ["primer", "primero"]):
                print("  → SUB-CASO: PRIMER (con contexto)")
                resultados = buscar_horarios(o, d, tipo_dia)
                if any(resultados.values()):
                    primer = "99:99"
                    ruta = ""
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r] and hora_a_minutos(resultados[r][0]) < hora_a_minutos(primer):
                            primer, ruta = resultados[r][0], r
                    msg.body(f"🚌 El primer colectivo de {o} a {d} sale a las {primer} por {ruta}.")
                    registrar_interaccion(sender, incoming_msg, tipo="primer", consulta=f"{o}→{d}", horario=primer)
                else:
                    msg.body(f"😕 No hay servicios de {o} a {d} hoy.")
                return str(resp)
            
            if any(p in incoming_msg.lower() for p in ["próximo", "proximo", "siguiente"]):
                print("  → SUB-CASO: PRÓXIMO (con contexto)")
                ahora = ahora_argentina()
                hora_actual = ahora.hour*60 + ahora.minute
                resultados = buscar_horarios(o, d, tipo_dia, hora_actual)
                if any(resultados.values()):
                    todos = []
                    for r in ["R10", "R18", "R10+R18"]:
                        for h in resultados[r]:
                            todos.append((h, r))
                    todos.sort(key=lambda x: hora_a_minutos(x[0]))
                    
                    if todos:
                        prox_hora, prox_ruta = todos[0]
                        msg.body(f"🚌 El próximo colectivo de {o} a {d} sale a las {prox_hora} por {prox_ruta}.")
                        registrar_interaccion(sender, incoming_msg, tipo="proximo", consulta=f"{o}→{d}", horario=prox_hora)
                    else:
                        msg.body(f"😕 No hay más servicios de {o} a {d} hoy.")
                else:
                    msg.body(f"😕 No hay más servicios de {o} a {d} hoy.")
                return str(resp)
            
            if any(p in incoming_msg.lower() for p in ["último", "ultimo", "final"]):
                print("  → SUB-CASO: ÚLTIMO (con contexto)")
                resultados = buscar_horarios(o, d, tipo_dia)
                if any(resultados.values()):
                    ult = "00:00"
                    ruta = ""
                    for r in ["R10", "R18", "R10+R18"]:
                        if resultados[r] and hora_a_minutos(resultados[r][-1]) > hora_a_minutos(ult):
                            ult, ruta = resultados[r][-1], r
                    msg.body(f"🚌 El último colectivo de {o} a {d} sale a las {ult} por {ruta}.")
                    registrar_interaccion(sender, incoming_msg, tipo="ultimo", consulta=f"{o}→{d}", horario=ult)
                else:
                    msg.body(f"😕 No hay servicios de {o} a {d} hoy.")
                return str(resp)

        # ============================================
        # NO ENTENDIDO - DERIVAR A IA
        # ============================================
        print("❌ No entendido, intentando con IA...")
        if DEEPSEEK_API_KEY:
            respuesta_ia = consultar_deepseek(incoming_msg)
            if respuesta_ia:
                msg.body(respuesta_ia)
                return str(resp)
        msg.body(no_entendido_inteligente(incoming_msg))
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
    print(f"🚀 Bot listo en puerto {port} - VERSIÓN HÍBRIDA CON PROMPT MEJORADO")
    app.run(host='0.0.0.0', port=port, debug=False)
