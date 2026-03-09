from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import pytz
import re
import json
import os

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=3)

# --- Zona Horaria ---
os.environ['TZ'] = 'America/Argentina/Buenos_Aires'
try:
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
    print("✅ Zona horaria: Argentina")
except:
    timezone = pytz.timezone('America/Argentina/Cordoba')
    print("⚠️ Zona horaria: Córdoba (fallback)")

def ahora_argentina():
    return datetime.now(timezone)

# --- Configuración ---
NUMERO_DUENIO = os.environ.get('NUMERO_DUENIO', "whatsapp:+5493434727811")
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_para_sesiones')
STATS_FILE = 'estadisticas.json'
app.secret_key = SECRET_KEY

# --- Horarios (TODOS los tramos, sin filtrar por ruta) ---
tramos_habiles = [
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "04:50"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "05:10"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "05:45"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "06:05"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "04:45"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "05:50"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "06:10"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "06:25"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "05:35"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "06:45"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "07:00"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "07:20"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "07:45"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "09:25"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "09:45"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:05"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "11:15"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "08:45"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "09:55"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:25"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "10:45"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "10:00"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:00"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "10:15"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "11:55"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "12:15"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "12:35"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "12:15"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:30"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "13:05"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "14:15"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "14:30"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "14:45"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "14:00"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:40"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "15:30"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "16:40"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "17:00"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:30"},
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "16:30"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "18:15"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "18:35"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "18:55"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:05"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "17:15"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "18:25"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "18:40"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "18:55"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "19:15"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "18:00"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "19:40"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "19:30"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "20:45"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "21:55"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "22:10"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "22:25"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "23:00"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "23:15"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "23:30"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "00:30"},
    {"origen": "Parana", "destino": "Viale", "hora_salida": "23:00"},
]

# --- Funciones Básicas ---
def hora_a_minutos(h):
    if not h: return None
    hh, mm = map(int, h.split(':'))
    return hh*60 + mm

def extraer_origen_destino(mensaje):
    m = mensaje.lower()
    m = re.sub(r'[¿?!¡.,;]', '', m).strip()
    patron = r'de\s+(.+?)\s+a\s+(.+)'
    match = re.search(patron, m)
    if not match:
        patron = r'^(.+?)\s+a\s+(.+)$'
        match = re.search(patron, m)
    if match:
        o_raw = match.group(1).strip()
        d_raw = match.group(2).strip()
        localidades = ["parana", "viale", "tabossi", "sosa", "maria grande", "aldea san antonio"]
        for loc in localidades:
            if loc in o_raw: o = loc.title()
            if loc in d_raw: d = loc.title()
        if 'o' in locals() and 'd' in locals():
            return o, d
    return None, None

def buscar_tramos(origen, destino):
    resultados = []
    for t in tramos_habiles:
        if t["origen"] == origen and t["destino"] == destino:
            resultados.append(t["hora_salida"])
    return sorted(resultados, key=hora_a_minutos)

# --- Webhook Principal ---
@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    print(f"\n📩 Mensaje: '{incoming_msg}' de {sender}")

    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg.lower() == "hola":
        msg.body("👋 Hola! Soy el bot de transporte. Escribí por ejemplo: 'De Parana a Viale'")
        return str(resp)

    origen, destino = extraer_origen_destino(incoming_msg)

    if origen and destino:
        horarios = buscar_tramos(origen, destino)
        if horarios:
            respuesta = f"🚌 Horarios de {origen} a {destino}:\n" + "\n".join([f"• {h}" for h in horarios[:8]])
            msg.body(respuesta)
        else:
            msg.body(f"😕 No encontré horarios de {origen} a {destino}.")
    else:
        msg.body("🤔 No entendí. Probá con 'De Parana a Viale'.")

    return str(resp)

# --- Inicio ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Iniciando bot en puerto {port} con DEBUG ACTIVADO")
    app.run(host='0.0.0.0', port=port, debug=True)
