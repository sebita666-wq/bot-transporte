from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# ============================================
# HORARIOS - SOLO LOS ESENCIALES
# ============================================
# Formato: (origen, destino) -> [horarios]
horarios = {
    ("Parana", "Viale"): ["04:45", "05:35", "08:45", "10:00", "12:15", "13:05", "14:00", "15:30", "17:15", "18:00", "19:30", "20:45", "23:00"],
    ("Viale", "Parana"): ["05:10", "06:05", "07:20", "08:15", "10:25", "10:45", "12:00", "13:30", "15:40", "17:30", "19:40", "21:10", "00:30"],
    ("Parana", "Maria Grande"): ["07:45", "10:15", "16:30"],  # R10
    # Agregá los que necesites
}

@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    msg = request.values.get('Body', '').strip().lower()
    print(f"Mensaje: {msg}")
    
    resp = MessagingResponse()
    r = resp.message()
    
    if msg == "hola":
        r.body("👋 Bot de transporte. Escribí 'de parana a viale'")
        return str(resp)
    
    # Parseo simple
    if " de " in msg and " a " in msg:
        partes = msg.split(" de ")[1].split(" a ")
        if len(partes) == 2:
            o = partes[0].strip().title()
            d = partes[1].strip().title()
            
            if (o, d) in horarios:
                hs = "\n".join([f"• {h}" for h in horarios[(o, d)]])
                r.body(f"🚌 Horarios {o}→{d}:\n{hs}")
            else:
                r.body("😕 No tengo horarios para ese tramo")
            return str(resp)
    
    r.body("🤔 No entendí. Probá 'de parana a viale'")
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
