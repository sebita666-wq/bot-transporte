import sys
import os
import pytest
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot import (
    normalizar_localidad,
    extraer_origen_destino,
    interpretar_fecha,
    obtener_tipo_dia,
    hora_a_minutos,
    detectar_intencion,
    extraer_hora_limite
)

# ============================================
# TESTS DE NORMALIZACIÓN
# ============================================
def test_normalizar_localidad():
    assert normalizar_localidad("Parana") == "Paraná"
    assert normalizar_localidad("Paraná") == "Paraná"
    assert normalizar_localidad("Maria Grande") == "María Grande"
    assert normalizar_localidad("María Grande") == "María Grande"
    assert normalizar_localidad("Sosa") == "Estación Sosa"
    assert normalizar_localidad("Est. Sosa") == "Estación Sosa"
    assert normalizar_localidad("Tabossi") == "Tabossi"
    assert normalizar_localidad("Viale") == "Viale"
    assert normalizar_localidad("Genolet") == "Genolet"
    assert normalizar_localidad("San Benito") == "Genolet"
    assert normalizar_localidad("Colonia Avellaneda") == "Genolet"
    assert normalizar_localidad("Ciudad Inexistente") is None

# ============================================
# TESTS DE EXTRACCIÓN ORIGEN/DESTINO
# ============================================
def test_extraer_origen_destino_formato_de():
    assert extraer_origen_destino("De Parana a Viale") == ("Paraná", "Viale")
    assert extraer_origen_destino("de tabossi a parana") == ("Tabossi", "Paraná")
    assert extraer_origen_destino("De Maria Grande a Sosa") == ("María Grande", "Estación Sosa")

def test_extraer_origen_destino_formato_simple():
    assert extraer_origen_destino("Parana a Viale") == ("Paraná", "Viale")
    assert extraer_origen_destino("tabossi a parana") == ("Tabossi", "Paraná")

def test_extraer_origen_destino_con_intencion():
    assert extraer_origen_destino("Cual es el primer colectivo de Parana a Viale") == ("Paraná", "Viale")
    assert extraer_origen_destino("El ultimo de Tabossi a Parana") == ("Tabossi", "Paraná")
    assert extraer_origen_destino("Proximo de Sosa a Maria Grande") == ("Estación Sosa", "María Grande")

def test_extraer_origen_destino_con_fecha():
    assert extraer_origen_destino("De Parana a Viale el 17/03") == ("Paraná", "Viale")
    assert extraer_origen_destino("Tabossi a Parana 20/03/2026") == ("Tabossi", "Paraná")

def test_extraer_origen_destino_invalidos():
    assert extraer_origen_destino("Hola") == (None, None)
    assert extraer_origen_destino("Parana Viale") == (None, None)
    assert extraer_origen_destino("Quiero ir a Viale") == (None, None)

# ============================================
# TESTS DE FECHA
# ============================================
def test_interpretar_fecha_formato_ddmmaaaa():
    fecha = interpretar_fecha("17/03/2026")
    assert fecha.strftime("%d/%m/%Y") == "17/03/2026"

def test_interpretar_fecha_formato_ddmm():
    # Este test puede fallar si hoy no es 2026, pero lo ajustamos
    fecha = interpretar_fecha("17/03")
    assert fecha.strftime("%d/%m") == "17/03"

def test_interpretar_fecha_formato_texto():
    fecha = interpretar_fecha("17 de marzo")
    assert fecha.strftime("%d/%m") in ["17/03", "17/03/2026"]

def test_interpretar_fecha_manana():
    fecha = interpretar_fecha("mañana")
    assert fecha.date() > datetime.now().date()

def test_interpretar_fecha_hoy():
    fecha = interpretar_fecha("hoy")
    assert fecha.date() == datetime.now().date()

# ============================================
# TESTS DE TIPO DE DÍA
# ============================================
def test_obtener_tipo_dia_feriado():
    from bot import FERIADOS_NACIONALES
    if FERIADOS_NACIONALES:
        fecha_feriado = datetime.strptime(FERIADOS_NACIONALES[0], "%Y-%m-%d")
        assert obtener_tipo_dia(fecha_feriado) == "domingos"

def test_obtener_tipo_dia_lunes():
    # 16/03/2026 es lunes
    fecha = datetime(2026, 3, 16)
    assert obtener_tipo_dia(fecha) == "habiles"

def test_obtener_tipo_dia_sabado():
    # 21/03/2026 es sábado
    fecha = datetime(2026, 3, 21)
    assert obtener_tipo_dia(fecha) == "sabados"

def test_obtener_tipo_dia_domingo():
    # 22/03/2026 es domingo
    fecha = datetime(2026, 3, 22)
    assert obtener_tipo_dia(fecha) == "domingos"

# ============================================
# TESTS DE UTILIDADES
# ============================================
def test_hora_a_minutos():
    assert hora_a_minutos("04:45") == 285
    assert hora_a_minutos("23:30") == 1410
    assert hora_a_minutos("00:00") == 0
    assert hora_a_minutos("") is None

def test_detectar_intencion():
    assert detectar_intencion("primer colectivo") == "primer"
    assert detectar_intencion("primero") == "primer"
    assert detectar_intencion("próximo") == "proximo"
    assert detectar_intencion("proximo") == "proximo"
    assert detectar_intencion("siguiente") == "proximo"
    assert detectar_intencion("último") == "ultimo"
    assert detectar_intencion("ultimo") == "ultimo"
    assert detectar_intencion("final") == "ultimo"
    assert detectar_intencion("hola") is None

def test_extraer_hora_limite():
    assert extraer_hora_limite("después de las 15") == 900
    assert extraer_hora_limite("despues de las 17:30") == 1050
    assert extraer_hora_limite("a partir de las 8") == 480
    assert extraer_hora_limite("hola") is None

# ============================================
# TEST DE CARGA DE ARCHIVOS (opcional)
# ============================================
def test_archivos_json_existen():
    archivos = ['horarios.json', 'tarifas.json', 'feriados.json', 'duraciones.json']
    for archivo in archivos:
        assert os.path.exists(archivo), f"Falta el archivo {archivo}"
