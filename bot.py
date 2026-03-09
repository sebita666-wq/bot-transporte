from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
import pytz
import re
import json
import os

app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=3)

# Configurar zona horaria de Argentina
os.environ['TZ'] = 'America/Argentina/Buenos_Aires'
try:
    timezone = pytz.timezone('America/Argentina/Buenos_Aires')
except:
    timezone = pytz.timezone('America/Argentina/Cordoba')

print("🚀 BOT INICIADO - CHECKPOINT 11 (RUTA 18 CORREGIDA + EXTRACCIÓN MEJORADA)")

# ============================================
# CONFIGURACIÓN (VERSIÓN PRODUCCIÓN)
# ============================================
NUMERO_DUENIO = os.environ.get('NUMERO_DUENIO', "whatsapp:+5493434727811")
SECRET_KEY = os.environ.get('SECRET_KEY', 'clave_secreta_para_sesiones')
STATS_FILE = 'estadisticas.json'

app.secret_key = SECRET_KEY

# ============================================
# FUNCIÓN PARA OBTENER HORA ARGENTINA
# ============================================
def ahora_argentina():
    return datetime.now(timezone)

# ============================================
# FERIADOS NACIONALES 2026 (se tratan como domingo)
# ============================================
FERIADOS_NACIONALES = [
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-03-24", "2026-04-02",
    "2026-04-03", "2026-05-01", "2026-05-25", "2026-06-15", "2026-06-20",
    "2026-07-09", "2026-08-17", "2026-10-12", "2026-11-23", "2026-12-08",
    "2026-12-25"
]

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
            "ultimo_reinicio": ahora_argentina().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

def guardar_estadisticas(stats):
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

def registrar_interaccion(sender, mensaje, tipo_consulta=None):
    stats = cargar_estadisticas()
    ahora = ahora_argentina().strftime("%Y-%m-%d %H:%M:%S")
    
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
    ahora = ahora_argentina()
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
# HORARIOS - DÍAS HÁBILES
# ============================================

tramos_habiles = [
    # 1. Tabossi 04:50 → Viale 05:10 → Parana 06:20
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "04:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "05:10", "ruta": "R18"},
    
    # 2. Tabossi 05:45 → Viale 06:05 → Parana 07:15
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "05:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "06:05", "ruta": "R18"},
    
    # 3. Parana 04:45 → Viale 05:50 → Tabossi 06:10 → Sosa 06:25 → Maria Grande 06:45 → (vuelve R10) → Parana 08:15
    {"origen": "Parana", "destino": "Viale", "hora_salida": "04:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "05:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "06:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "06:25", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "06:45", "ruta": "R10"},
    
    # 4. Parana 05:35 → Viale 06:45 → Tabossi 07:00 → (vuelve) Tabossi 07:00 → Viale 07:20 → Parana 08:30
    {"origen": "Parana", "destino": "Viale", "hora_salida": "05:35", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "06:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "07:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "07:20", "ruta": "R18"},
    
    # 5. Parana 06:40 → Aldea San Antonio 07:30 → Viale 07:50 → (vuelve) Viale 08:15 → Parana 09:25
    {"origen": "Parana", "destino": "Aldea San Antonio", "hora_salida": "06:40", "ruta": "R18"},
    {"origen": "Aldea San Antonio", "destino": "Viale", "hora_salida": "07:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "08:15", "ruta": "R18"},
    
    # 6. Parana 07:45 → (R10) → Maria Grande 09:10 → (vuelve) Sosa 09:25 → Tabossi 09:45 → Viale 10:05 → Parana 11:15
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "07:45", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "09:25", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "09:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:05", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "11:15", "ruta": "R18"},
    
    # 7. Parana 08:45 → Viale 09:55 → Tabossi 10:10 → (vuelve) Tabossi 10:25 → Viale 10:45 → Parana 11:55
    {"origen": "Parana", "destino": "Viale", "hora_salida": "08:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "09:55", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:25", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "10:45", "ruta": "R18"},
    
    # 8. Parana 10:00 → Viale 11:10 → (vuelve) Viale 12:00 → Parana 13:10
    {"origen": "Parana", "destino": "Viale", "hora_salida": "10:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:00", "ruta": "R18"},
    
    # 9. Parana 10:15 → (R10) → Maria Grande 11:40 → (vuelve) Sosa 11:55 → Tabossi 12:15 → Viale 12:35 → Aldea San Antonio 12:55 → Parana 13:45
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "10:15", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "11:55", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "12:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "12:35", "ruta": "R18"},
    {"origen": "Viale", "destino": "Aldea San Antonio", "hora_salida": "12:55", "ruta": "R18"},
    {"origen": "Aldea San Antonio", "destino": "Parana", "hora_salida": "13:45", "ruta": "R18"},
    
    # 10. Parana 12:15 → Viale 13:25 → (vuelve) Viale 13:30 → Parana 14:40
    {"origen": "Parana", "destino": "Viale", "hora_salida": "12:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:30", "ruta": "R18"},
    
    # 11. Parana 13:05 → Viale 14:15 → Tabossi 14:30 → Sosa 14:45 → Maria Grande 15:05 → (vuelve R10) → Parana 16:35
    {"origen": "Parana", "destino": "Viale", "hora_salida": "13:05", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "14:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "14:30", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "14:45", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "15:05", "ruta": "R10"},
    
    # 12. Parana 14:00 → Viale 15:10 → (vuelve) Viale 15:40 → Parana 16:50
    {"origen": "Parana", "destino": "Viale", "hora_salida": "14:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:40", "ruta": "R18"},
    
    # 13. Parana 15:30 → Viale 16:40 → Tabossi 16:55 → (vuelve) Tabossi 17:00 → Viale 17:30 → Parana 18:25
    {"origen": "Parana", "destino": "Viale", "hora_salida": "15:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "16:40", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "17:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:30", "ruta": "R18"},
    
    # 14. Parana 16:30 → (R10) → Maria Grande 18:00 → (vuelve) Sosa 18:15 → Tabossi 18:35 → Viale 18:55 → Parana 20:05
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "16:30", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "18:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "18:35", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "18:55", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:05", "ruta": "R18"},
    
    # 15. Parana 17:15 → Viale 18:25 → Tabossi 18:40 → Sosa 18:55 → Maria Grande 19:15 → (vuelve R10) → Parana 20:45
    {"origen": "Parana", "destino": "Viale", "hora_salida": "17:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "18:25", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "18:40", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "18:55", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "19:15", "ruta": "R10"},
    
    # 16. Parana 18:00 → Viale 19:10 → (vuelve) Viale 19:40 → Parana 20:50
    {"origen": "Parana", "destino": "Viale", "hora_salida": "18:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "19:40", "ruta": "R18"},
    
    # 17. Parana 19:30 → Viale 20:40 → (vuelve) Viale 21:10 → Parana 22:20
    {"origen": "Parana", "destino": "Viale", "hora_salida": "19:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "ruta": "R18"},
    
    # 18. Parana 20:45 → Viale 21:55 → Tabossi 22:10 → Sosa 22:25 → Maria Grande 22:45 → (vuelve) Sosa 23:00 → Tabossi 23:15 → Viale 23:30 → Parana 00:30
    {"origen": "Parana", "destino": "Viale", "hora_salida": "20:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "21:55", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "22:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "22:25", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "23:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "23:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "23:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "00:30", "ruta": "R18"},
    
    # 19. Parana 23:00 → Viale 00:10
    {"origen": "Parana", "destino": "Viale", "hora_salida": "23:00", "ruta": "R18"},
]

# ============================================
# HORARIOS - SÁBADOS
# ============================================

tramos_sabados = [
    # 1. Tabossi 06:15 → Viale 06:30 → Parana 07:30
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "06:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "06:30", "ruta": "R18"},
    
    # 2. Parana 04:45 → Viale 05:50 → Tabossi 06:10 → Sosa 06:25 → Maria Grande 06:45 → (vuelve R10) → Parana 08:15
    {"origen": "Parana", "destino": "Viale", "hora_salida": "04:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "05:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "06:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "06:25", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "06:45", "ruta": "R10"},
    
    # 3. Parana 05:35 → Viale 06:45 → Tabossi 06:55 → (vuelve) Tabossi 07:00 → Viale 07:20 → Parana 08:30
    {"origen": "Parana", "destino": "Viale", "hora_salida": "05:35", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "06:45", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "07:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "07:20", "ruta": "R18"},
    
    # 4. Parana 07:45 → (R10) → Maria Grande 11:40 → (vuelve) Sosa 12:00 → Tabossi 12:20 → Viale 12:40 → Parana 13:45
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "07:45", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "12:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "12:20", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "12:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:45", "ruta": "R18"},
    
    # 5. Parana 11:40 → Viale 12:50 → (vuelve) Viale 13:30 → Parana 14:40
    {"origen": "Parana", "destino": "Viale", "hora_salida": "11:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "13:30", "ruta": "R18"},
    
    # 6. Parana 12:30 → Viale 13:50 → Tabossi 14:10 → Sosa 14:30 → Maria Grande 14:50 → (vuelve R10) → Parana 16:15
    {"origen": "Parana", "destino": "Viale", "hora_salida": "12:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "13:50", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "14:10", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "14:30", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "14:50", "ruta": "R10"},
    
    # 7. Parana 14:00 → Viale 15:00 → (vuelve) Viale 15:15 → Parana 16:15
    {"origen": "Parana", "destino": "Viale", "hora_salida": "14:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "15:15", "ruta": "R18"},
    
    # 8. Parana 15:15 → Viale 16:20 → Tabossi 16:35 → (vuelve) Tabossi 16:40 → Viale 17:00 → Parana 18:10
    {"origen": "Parana", "destino": "Viale", "hora_salida": "15:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "16:20", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "16:40", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:00", "ruta": "R18"},
    
    # 9. Parana 17:00 → Viale 18:10 → Tabossi 18:30 → Sosa 18:45 → Maria Grande 19:05 → (vuelve R10) → Parana 20:30
    {"origen": "Parana", "destino": "Viale", "hora_salida": "17:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "18:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "18:30", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "18:45", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "19:05", "ruta": "R10"},
    
    # 10. Parana 16:30 → (R10) → Maria Grande 18:00 → (vuelve) Sosa 18:20 → Tabossi 18:40 → Viale 19:00 → Parana 20:10
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "16:30", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "18:20", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "18:40", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "19:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:10", "ruta": "R18"},
    
    # 11. Parana 19:30 → Viale 20:40 → (vuelve) Viale 21:10 → Parana 22:15
    {"origen": "Parana", "destino": "Viale", "hora_salida": "19:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "21:10", "ruta": "R18"},
    
    # 12. Parana 20:45 → Viale 21:55 → Tabossi 22:15 → Sosa 22:30 → Maria Grande 22:45 → (vuelve) Sosa 23:00 → Tabossi 23:15 → Viale 23:30 → Parana 00:30
    {"origen": "Parana", "destino": "Viale", "hora_salida": "20:45", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "21:55", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "22:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "22:30", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "23:00", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "23:15", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "23:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "00:30", "ruta": "R18"},
    
    # 13. Parana 23:00 → Viale 00:01
    {"origen": "Parana", "destino": "Viale", "hora_salida": "23:00", "ruta": "R18"},
]

# ============================================
# HORARIOS - DOMINGOS
# ============================================

tramos_domingos = [
    # 1. Parana 07:15 → Viale 08:30 → (vuelve) Viale 08:45 → Parana 09:55
    {"origen": "Parana", "destino": "Viale", "hora_salida": "07:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "08:45", "ruta": "R18"},
    
    # 2. Parana 07:45 → (R10) → Maria Grande 09:10 → (vuelve) Sosa 09:34 → Tabossi 09:48 → Viale 10:07 → Parana 11:35
    {"origen": "Parana", "destino": "Maria Grande", "hora_salida": "07:45", "ruta": "R10"},
    {"origen": "Maria Grande", "destino": "Sosa", "hora_salida": "09:34", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Tabossi", "hora_salida": "09:48", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "10:07", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "11:35", "ruta": "R18"},
    
    # 3. Parana 10:15 → Viale 11:45 → (vuelve) Viale 12:00 → Parana 13:10
    {"origen": "Parana", "destino": "Viale", "hora_salida": "10:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "12:00", "ruta": "R18"},
    
    # 4. Parana 12:30 → Viale 13:59 → Tabossi 14:15 → Sosa 14:30 → Maria Grande 14:50 → (vuelve R10) → Parana 16:25
    {"origen": "Parana", "destino": "Viale", "hora_salida": "12:30", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "13:59", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "14:15", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "14:30", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "14:50", "ruta": "R10"},
    
    # 5. Parana 15:15 → Viale 16:25 → Tabossi 16:45 → (vuelve) Tabossi 16:50 → Viale 17:10 → Parana 18:40
    {"origen": "Parana", "destino": "Viale", "hora_salida": "15:15", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "16:25", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "16:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "17:10", "ruta": "R18"},
    
    # 6. Parana 17:00 → Viale 18:29 → Tabossi 18:45 → Sosa 19:00 → Maria Grande 19:25 → (vuelve R10) → Parana 20:55
    {"origen": "Parana", "destino": "Viale", "hora_salida": "17:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "18:29", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Sosa", "hora_salida": "18:45", "ruta": "R18"},
    {"origen": "Sosa", "destino": "Maria Grande", "hora_salida": "19:00", "ruta": "R18"},
    {"origen": "Maria Grande", "destino": "Parana", "hora_salida": "19:25", "ruta": "R10"},
    
    # 7. Parana 19:00 → Viale 20:30 → (vuelve) Viale 20:45 → Parana 22:15
    {"origen": "Parana", "destino": "Viale", "hora_salida": "19:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "20:45", "ruta": "R18"},
    
    # 8. Parana 21:00 → Viale 22:10 → Tabossi 22:50 → (vuelve) Tabossi 22:50 → Viale 23:08 → Parana 00:05
    {"origen": "Parana", "destino": "Viale", "hora_salida": "21:00", "ruta": "R18"},
    {"origen": "Viale", "destino": "Tabossi", "hora_salida": "22:10", "ruta": "R18"},
    {"origen": "Tabossi", "destino": "Viale", "hora_salida": "22:50", "ruta": "R18"},
    {"origen": "Viale", "destino": "Parana", "hora_salida": "23:08", "ruta": "R18"},
]

# ============================================
# TABLA DE PRECIOS (ACTUALIZADA)
# ============================================

precios = {
    ("Parana", "Viale"): 6300,
    ("Viale", "Parana"): 6300,
    ("Parana", "Tabossi"): 7700,
    ("Tabossi", "Parana"): 7700,
    ("Parana", "Sosa"): 8000,
    ("Sosa", "Parana"): 8000,
    ("Parana", "Maria Grande"): 8400,
    ("Maria Grande", "Parana"): 8400,
    ("Parana", "Aldea San Antonio"): 3100,
    ("Aldea San Antonio", "Parana"): 3100,
    ("Viale", "Tabossi"): 1800,
    ("Tabossi", "Viale"): 1800,
    ("Viale", "Sosa"): 2100,
    ("Sosa", "Viale"): 2100,
    ("Viale", "Maria Grande"): 3400,
    ("Maria Grande", "Viale"): 3400,
    ("Viale", "Aldea San Antonio"): 2100,
    ("Aldea San Antonio", "Viale"): 2100,
    ("Tabossi", "Sosa"): 1800,
    ("Sosa", "Tabossi"): 1800,
    ("Tabossi", "Maria Grande"): 2100,
    ("Maria Grande", "Tabossi"): 2100,
    ("Tabossi", "Aldea San Antonio"): 3400,
    ("Aldea San Antonio", "Tabossi"): 3400,
    ("Sosa", "Maria Grande"): 1800,
    ("Maria Grande", "Sosa"): 1800,
    ("Sosa", "Aldea San Antonio"): 4100,
    ("Aldea San Antonio", "Sosa"): 4100,
    ("Maria Grande", "Aldea San Antonio"): 4900,
    ("Aldea San Antonio", "Maria Grande"): 4900,
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

# Lista de frases introductorias a eliminar
FRASES_INTRO = [
    "cual es el", "cual es la", "cual es",
    "podrias decirme", "podría decirme", "me podrias decir", "me podría decir",
    "quiero saber", "quisiera saber", "necesito saber",
    "decime", "contame", "dime", "dígame",
    "primer servicio", "primer colectivo", "primer",
    "último servicio", "último colectivo", "último", "ultimo",
    "próximo servicio", "próximo colectivo", "próximo", "proximo",
    "horarios de", "horario de", "hora de"
]

def limpiar_mensaje(mensaje):
    """Elimina frases introductorias del mensaje para facilitar la extracción"""
    mensaje_limpio = mensaje.lower()
    for frase in FRASES_INTRO:
        if frase in mensaje_limpio:
            mensaje_limpio = mensaje_limpio.replace(frase, " ")
    mensaje_limpio = re.sub(r'\s+', ' ', mensaje_limpio).strip()
    return mensaje_limpio

def detectar_intencion(mensaje):
    """Detecta si la consulta es sobre primer, próximo o último colectivo"""
    mensaje_lower = mensaje.lower()
    if any(p in mensaje_lower for p in ["primer", "primero", "primer servicio", "primer colectivo"]):
        return "primer"
    if any(p in mensaje_lower for p in ["próximo", "proximo", "siguiente", "próximo colectivo"]):
        return "proximo"
    if any(p in mensaje_lower for p in ["último", "ultimo", "final", "último servicio"]):
        return "ultimo"
    return None

def extraer_origen_destino(mensaje):
    mensaje_original = mensaje
    
    mensaje_limpio = limpiar_mensaje(mensaje)
    mensaje_limpio = normalizar_texto(mensaje_limpio)
    mensaje_limpio = re.sub(r'[¿?!¡.,;:\s]+$', '', mensaje_limpio)
    
    print(f"🧹 MENSAJE LIMPIO: '{mensaje_limpio}'")
    
    # Localidades válidas (incluyendo las de dos palabras)
    localidades_validas = [
        "parana", "viale", "tabossi", "sosa", "maria grande", 
        "aldea san antonio", "san antonio"
    ]
    
    palabras_temporales = ["mañana", "manana", "hoy", "para", "el", "la", "los", "las", "del", "dia", "jornada"]
    
    # Función para normalizar una localidad
    def normalizar_localidad(loc):
        loc_lower = loc.lower()
        for valida in localidades_validas:
            if valida in loc_lower:
                if valida == "maria grande" and "maria" in loc_lower and "grande" in loc_lower:
                    return "Maria Grande"
                if valida == "aldea san antonio" and ("aldea" in loc_lower and "san antonio" in loc_lower):
                    return "Aldea San Antonio"
                if valida == "san antonio" and "san antonio" in loc_lower and "aldea" not in loc_lower:
                    return "Aldea San Antonio"
                # Para localidades de una palabra
                if valida in ["parana", "viale", "tabossi", "sosa"]:
                    return valida.title()
        return None
    
    # Patrón para "de X a Y" donde X e Y pueden tener espacios
    patron_de_a = r'de\s+(.+?)\s+a\s+(.+)'
    match = re.search(patron_de_a, mensaje_limpio)
    
    if match:
        origen_raw = match.group(1).strip()
        destino_raw = match.group(2).strip()
        
        # Limpiar palabras temporales del destino
        for palabra in palabras_temporales:
            if palabra in destino_raw:
                partes = destino_raw.split(palabra)
                destino_raw = partes[0].strip()
                break
        
        origen = normalizar_localidad(origen_raw)
        destino = normalizar_localidad(destino_raw)
        
        if origen and destino:
            print(f"✅ EXTRAÍDO (patrón 'de a'): {origen} -> {destino}")
            return origen, destino
    
    # Patrón para "X a Y" (sin "de")
    patron_simple = r'^(.+?)\s+a\s+(.+)$'
    match = re.search(patron_simple, mensaje_limpio)
    
    if match:
        origen_raw = match.group(1).strip()
        destino_raw = match.group(2).strip()
        
        for palabra in palabras_temporales:
            if palabra in destino_raw:
                partes = destino_raw.split(palabra)
                destino_raw = partes[0].strip()
                break
        
        origen = normalizar_localidad(origen_raw)
        destino = normalizar_localidad(destino_raw)
        
        if origen and destino:
            print(f"✅ EXTRAÍDO (patrón 'a'): {origen} -> {destino}")
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
    hoy = ahora_argentina().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if "hoy" in mensaje:
        print(f"📅 FECHA: Hoy ({hoy.strftime('%d/%m/%Y')})")
        return hoy
    if "mañana" in mensaje or "manana" in mensaje:
        manana = hoy + timedelta(days=1)
        print(f"📅 FECHA: Mañana ({manana.strftime('%d/%m/%Y')})")
        return manana
    
    patron_fecha = r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.]?(\d{2,4})?'
    match = re.search(patron_fecha, mensaje)
    if match:
        dia = int(match.group(1))
        mes = int(match.group(2))
        anio = int(match.group(3)) if match.group(3) else hoy.year
        if anio < 100:
            anio += 2000
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

def es_feriado_nacional(fecha):
    fecha_str = fecha.strftime("%Y-%m-%d")
    return fecha_str in FERIADOS_NACIONALES

def obtener_tipo_dia(fecha):
    if es_feriado_nacional(fecha):
        print("📅 FERIADO NACIONAL - Se trata como domingo")
        return "domingos"
    if fecha.weekday() < 5:
        return "habiles"
    elif fecha.weekday() == 5:
        return "sabados"
    else:
        return "domingos"

def obtener_tramos_por_dia(tipo_dia):
    if tipo_dia == "habiles":
        return tramos_habiles
    elif tipo_dia == "sabados":
        return tramos_sabados
    else:
        return tramos_domingos

def buscar_servicios_completos(origen, destino, tipo_dia, hora_limite=None):
    """
    Busca servicios completos que permitan ir de origen a destino,
    considerando tanto viajes de ida como de vuelta.
    """
    print(f"🔍 BUSCANDO SERVICIOS COMPLETOS: {origen} -> {destino} | día: {tipo_dia}")
    tramos_dia = obtener_tramos_por_dia(tipo_dia)
    
    # Primero, buscar servicios que tengan un tramo directo
    resultados_directos = []
    for t in tramos_dia:
        if t["origen"] == origen and t["destino"] == destino:
            hora_min = hora_a_minutos(t["hora_salida"])
            if hora_limite is None or hora_min >= hora_limite:
                resultados_directos.append({
                    "hora_salida": t["hora_salida"],
                    "descripcion": f"{origen} → {destino}",
                    "ruta": t.get("ruta", "R18")
                })
    
    # Luego, buscar servicios que requieran múltiples tramos
    # Agrupar todos los tramos por hora de salida desde el origen
    servicios_por_hora = {}
    for t in tramos_dia:
        if t["origen"] == origen:
            clave = t["hora_salida"]
            if clave not in servicios_por_hora:
                servicios_por_hora[clave] = {
                    "hora_salida": t["hora_salida"],
                    "tramos": []
                }
            servicios_por_hora[clave]["tramos"].append(t)
    
    # Para cada servicio, construir el recorrido completo
    resultados_indirectos = []
    localidades_orden = ["Parana", "Aldea San Antonio", "Viale", "Tabossi", "Sosa", "Maria Grande"]
    
    for hora, servicio in servicios_por_hora.items():
        # Ordenar tramos por el orden de las localidades
        tramos_ordenados = sorted(servicio["tramos"], key=lambda x: localidades_orden.index(x["destino"]) if x["destino"] in localidades_orden else 999)
        
        # Verificar si el destino está en el recorrido
        destinos = [t["destino"] for t in tramos_ordenados]
        if destino in destinos:
            hora_min = hora_a_minutos(hora)
            if hora_limite is None or hora_min >= hora_limite:
                # Construir descripción del recorrido
                desc = f"{origen} → "
                destinos_unicos = []
                for d in destinos:
                    if d not in destinos_unicos and d != origen:
                        destinos_unicos.append(d)
                desc += " → ".join(destinos_unicos)
                
                resultados_indirectos.append({
                    "hora_salida": hora,
                    "descripcion": desc,
                    "ruta": "R18"  # Los servicios con múltiples tramos son R18
                })
    
    # Combinar y ordenar
    todos_resultados = resultados_directos + resultados_indirectos
    todos_resultados.sort(key=lambda x: hora_a_minutos(x["hora_salida"]))
    
    print(f"  → Total: {len(todos_resultados)} servicios encontrados")
    for r in todos_resultados:
        print(f"    → {r['hora_salida']}: {r['descripcion']} ({r['ruta']})")
    
    return todos_resultados

def obtener_precio(origen, destino):
    precio = precios.get((origen, destino))
    print(f"💰 PRECIO {origen}->{destino}: {precio}")
    return precio

def primer_colectivo(origen, destino, tipo_dia):
    print(f"🔍 BUSCANDO PRIMER COLECTIVO: {origen} -> {destino}")
    resultados = buscar_servicios_completos(origen, destino, tipo_dia)
    if resultados:
        print(f"  → PRIMERO: {resultados[0]['hora_salida']}")
        return resultados[0]
    print(f"  → No hay servicios")
    return None

def proximo_colectivo(origen, destino, tipo_dia):
    ahora = ahora_argentina()
    hora_actual_min = ahora.hour * 60 + ahora.minute
    print(f"🕐 HORA ACTUAL (Argentina): {ahora.strftime('%H:%M')} ({hora_actual_min} minutos)")
    resultados = buscar_servicios_completos(origen, destino, tipo_dia, hora_actual_min)
    if resultados:
        print(f"  → PRÓXIMO: {resultados[0]['hora_salida']}")
        return resultados[0]
    print(f"  → No hay más servicios hoy")
    return None

def ultimo_colectivo(origen, destino, tipo_dia):
    print(f"🔍 BUSCANDO ÚLTIMO COLECTIVO: {origen} -> {destino}")
    resultados = buscar_servicios_completos(origen, destino, tipo_dia)
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
        texto += f"• {r['hora_salida']}: {r['descripcion']}\n"
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
            "• 'Primer colectivo de Parana a Viale mañana'\n"
            "• 'Precio de Parana a Aldea San Antonio'")

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
            "• 'Primer colectivo de Parana a Viale mañana'\n"
            "• 'Precio de Parana a Aldea San Antonio'")

def resetear_contexto(sender):
    session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
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
        session[sender] = {"ultimo_origen": None, "ultimo_destino": None, "estado": "menu", "intencion": None, "fecha_pendiente": None}
    
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
        
        # ANTES de procesar, verificamos si el mensaje es sobre PRECIO
        if any(p in incoming_msg.lower() for p in ["precio", "cuesta", "vale", "$"]):
            print("  → El mensaje es de PRECIO, cambiando a estado esperando_origen_precios")
            contexto["estado"] = "esperando_origen_precios"
            session[sender] = contexto
            msg.body("📝 Decime de dónde a dónde querés saber el precio.")
            return str(resp)
        
        origen, destino = extraer_origen_destino(incoming_msg)
        if origen and destino:
            fecha = contexto.get("fecha_pendiente") or interpretar_fecha(incoming_msg)
            tipo_dia = obtener_tipo_dia(fecha)
            
            intencion = contexto.get("intencion")
            
            if intencion == "primer":
                primer = primer_colectivo(origen, destino, tipo_dia)
                if primer:
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    msg.body(f"🚌 El primer colectivo de {origen} a {destino} para el {fecha_str} sale a las {primer['hora_salida']}.")
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} para esa fecha.")
            elif intencion == "proximo":
                prox = proximo_colectivo(origen, destino, tipo_dia)
                if prox:
                    msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox['hora_salida']}.")
                else:
                    msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
            elif intencion == "ultimo":
                ult = ultimo_colectivo(origen, destino, tipo_dia)
                if ult:
                    msg.body(f"🚌 El último colectivo de {origen} a {destino} sale a las {ult['hora_salida']}.")
                else:
                    msg.body(f"😕 No hay servicios de {origen} a {destino} para hoy.")
            else:
                hora_limite = extraer_hora_limite(incoming_msg)
                resultados = buscar_servicios_completos(origen, destino, tipo_dia, hora_limite)
                if resultados:
                    fecha_str = fecha.strftime("%d/%m/%Y")
                    if hora_limite:
                        texto = f"🚌 Servicios de {origen} a {destino} después de {minutos_a_hora(hora_limite)} ({tipo_dia}):\n"
                    else:
                        texto = f"🚌 Servicios de {origen} a {destino} para {fecha_str} ({tipo_dia}):\n"
                    texto += formatear_horarios(resultados)
                    msg.body(texto)
                else:
                    msg.body(f"😕 No encontré servicios de {origen} a {destino} para {tipo_dia}.")
            
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            contexto["estado"] = "menu"
            contexto["intencion"] = None
            contexto["fecha_pendiente"] = None
            session[sender] = contexto
            return str(resp)
        else:
            msg.body("🤔 No entendí. Por favor, escribí algo como 'De Viale a Parana'")
            return str(resp)
    
    # ============================================
    # NUEVA CONSULTA DIRECTA
    # ============================================
    print("🔍 Intentando extraer origen/destino...")
    
    intencion = detectar_intencion(incoming_msg)
    fecha = interpretar_fecha(incoming_msg)
    
    origen, destino = extraer_origen_destino(incoming_msg)
    
    if origen and destino:
        print(f"✅ CONSULTA DIRECTA COMPLETA: {origen} -> {destino} | intención: {intencion} | fecha: {fecha.strftime('%d/%m/%Y')}")
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
            contexto["fecha_pendiente"] = fecha
            session[sender] = contexto
            return str(resp)
        
        if intencion == "primer":
            print("  → Es consulta de PRIMER")
            primer = primer_colectivo(origen, destino, tipo_dia)
            if primer:
                fecha_str = fecha.strftime("%d/%m/%Y")
                msg.body(f"🚌 El primer colectivo de {origen} a {destino} para el {fecha_str} sale a las {primer['hora_salida']}.")
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} para esa fecha.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            contexto["fecha_pendiente"] = fecha
            session[sender] = contexto
            return str(resp)
        
        if intencion == "proximo":
            print("  → Es consulta de PRÓXIMO")
            prox = proximo_colectivo(origen, destino, tipo_dia)
            if prox:
                msg.body(f"🚌 El próximo colectivo de {origen} a {destino} sale a las {prox['hora_salida']}.")
            else:
                msg.body(f"😕 No hay más servicios de {origen} a {destino} hoy.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            contexto["fecha_pendiente"] = fecha
            session[sender] = contexto
            return str(resp)
        
        if intencion == "ultimo":
            print("  → Es consulta de ÚLTIMO")
            ult = ultimo_colectivo(origen, destino, tipo_dia)
            if ult:
                msg.body(f"🚌 El último colectivo de {origen} a {destino} sale a las {ult['hora_salida']}.")
            else:
                msg.body(f"😕 No hay servicios de {origen} a {destino} hoy.")
            contexto["ultimo_origen"] = origen
            contexto["ultimo_destino"] = destino
            contexto["fecha_pendiente"] = fecha
            session[sender] = contexto
            return str(resp)
        
        # Horarios comunes
        print("  → Asumiendo consulta de HORARIOS")
        hora_limite = extraer_hora_limite(incoming_msg)
        resultados = buscar_servicios_completos(origen, destino, tipo_dia, hora_limite)
        if resultados:
            fecha_str = fecha.strftime("%d/%m/%Y")
            if hora_limite:
                texto = f"🚌 Servicios de {origen} a {destino} después de {minutos_a_hora(hora_limite)} ({tipo_dia}):\n"
            else:
                texto = f"🚌 Servicios de {origen} a {destino} para {fecha_str} ({tipo_dia}):\n"
            texto += formatear_horarios(resultados)
            msg.body(texto)
        else:
            msg.body(f"😕 No encontré servicios de {origen} a {destino} para {tipo_dia}.")
        contexto["ultimo_origen"] = origen
        contexto["ultimo_destino"] = destino
        session[sender] = contexto
        return str(resp)
    
    # Intención sin origen/destino
    if intencion and not origen:
        print(f"✅ INTENCIÓN DETECTADA SIN ORIGEN/DESTINO: {intencion}")
        
        if contexto.get("fecha_pendiente") and "mañana" not in incoming_msg.lower() and not re.search(r'\d{1,2}[/\-\.]\d{1,2}', incoming_msg):
            fecha = contexto["fecha_pendiente"]
            print(f"📅 MANTENIENDO FECHA ANTERIOR: {fecha.strftime('%d/%m/%Y')}")
        
        contexto["estado"] = "esperando_origen_horarios"
        contexto["intencion"] = intencion
        contexto["fecha_pendiente"] = fecha
        session[sender] = contexto
        msg.body("📝 Decime de dónde a dónde querés viajar.")
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
        fecha = ahora_argentina()
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
    app.run(host='0.0.0.0', port=port, debug=False)
