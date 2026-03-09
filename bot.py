from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# ============================================
# HORARIOS (SOLO IDA, DÍAS HÁBILES, SIN RUTAS)
# ============================================
horarios = {
    ("Parana", "Viale"): ["04:45", "05:35", "08:45", "10:00", "12:15", "13:05", "14:00", "15:30", "17:15", "18:00", "19:30", "20:45", "23:00"],
    ("Viale", "Parana"): ["05:10", "06:05", "07:20", "08:15", "10:25", "10:45", "12:00", "13:30", "15:40", "17:30", "19:40", "21:10", "00:30"],
    ("Parana", "Maria Grande"): ["07:45", "10:15", "16:30"],
    ("Maria Grande", "Parana"): ["06:45", "14:50", "19:15"],
    ("Parana", "Tabossi"): ["04:45", "05:35", "08:45", "12:15", "15:30", "17:15", "20:45"],
    ("Tabossi", "Parana"): ["06:20", "07:15", "08:30", "11:55", "14:40", "18:25"],
}

# ============================================
# FUNCIÓN DE EXTRACCIÓN SIMPLE
# ============================================

def extraer_origen_destino(mensaje):
    mensaje = mensaje.lower().strip()
    print(f"🧹 Mensaje: {mensaje}")
    
    # Caso 1: "de x a y" (con o sin espacio adelante)
    if "de " in mensaje and " a " in mensaje:
        partes = mensaje.split("de ", 1)
        if len(partes) > 1:
            resto = partes[1]
            partes2 = resto.split(" a ")
            if len(partes2) == 2:
                origen = partes2[0].strip()
                destino = partes2[1].strip()
                return origen.title(), destino.title()
    
    # Caso 2: "x a y" (sin "de")
    if " a " in mensaje:
        partes = mensaje.split(" a ")
        if len(partes) == 2:
            origen = partes[0].strip()
            destino = partes[1].strip()
            # Verificar que no sea parte de otra frase
            if origen and destino:
                return origen.title(), destino.title()
    
    return None, None

# ============================================
# WEBHOOK PRINCIPAL
# ============================================
@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', '')
    
    print(f"📩 Mensaje de {sender}: {incoming_msg}")
    
    resp = MessagingResponse()
    msg = resp.message()
    
    if incoming_msg.lower() == "hola":
        msg.body("👋 Hola, soy el bot de transporte. Escribí por ejemplo: 'De Parana a Viale'")
        return str(resp)
    
    origen, destino = extraer_origen_destino(incoming_msg)
    
    if origen and destino:
        clave = (origen, destino)
        if clave in horarios:
            lista = "\n".join([f"• {h}" for h in horarios[clave]])
            msg.body(f"🚌 Horarios de {origen} a {destino}:\n{lista}")
        else:
            msg.body(f"😕 No tengo horarios de {origen} a {destino}")
    else:
        msg.body("🤔 No entendí. Probá con 'De Parana a Viale'")
    
    return str(resp)

# ============================================
# INICIO
# ============================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
