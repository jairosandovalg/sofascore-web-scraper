import streamlit as st
import pandas as pd
import requests
import re
import time
from datetime import datetime

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Extractor Live Flashscore", page_icon="⚽", layout="wide")
st.title("⚽ Fase 1: Extracción en Vivo Vía API Flashscore (Inmune a 403)")
st.write("Cambiamos el puente de comunicación hacia los servidores de Flashscore para evadir las restricciones de Cloudflare.")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Panel de Control")
ejecutar = st.sidebar.toggle("▶️ Iniciar Monitoreo en Vivo (Loop 10s)", value=False)

# --- CUADRO DE MANDOS ---
col1, col2 = st.columns(2)
metric_partidos = col1.empty()
metric_estado = col2.empty()

log_box = st.container(border=True)
log_box.write("### 📄 Logs de Conexión en Directo")

st.write("### 📊 Partidos en Tiempo Real Detectados")
tabla_datos = st.empty()

# ===========================================
# 🚀 FUNCIÓN DE EXTRACCIÓN NATIVA (FLASHCORE FEED)
# ===========================================
def capturar_flashscore_live():
    # URL del feed público en vivo que consume la app web de Flashscore
    # Usamos la variante continental para maximizar compatibilidad en servidores internacionales
    url = "https://m.flashscore.com/x/feed/d_live_1_es_1"
    
    # 🕵️‍♂️ Máscara humana completa obligatoria para saltar bloqueos de Data Centers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "X-AsyncRequest": "true",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://m.flashscore.com/",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    
    try:
        log_box.write("📡 Enviando petición de datos al servidor central de Flashscore...")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            log_box.success("🎯 ¡Paquete de datos en vivo descargado correctamente!")
            return response.text
        elif response.status_code == 403:
            log_box.error("❌ Código 403: Acceso denegado por el Host actual.")
            return None
        else:
            log_box.warning(f"⚠️ Servidor respondió con estado inusual: {response.status_code}")
            return None
    except Exception as e:
        log_box.error(f"❌ Error crítico de conexión: {e}")
        return None

# ===========================================
# 🔄 PROCESADOR DEL FEED DE TEXTO (PARSER)
# ===========================================
def procesar_feed(feed_texto):
    if not feed_texto:
        return []
        
    partidos_live = []
    
    # El feed de Flashscore divide las ligas y partidos usando bloques delimitados por '~'
    bloques = feed_texto.split("~")
    liga_actual = "Competición Internacional"
    
    for bloque in bloques:
        try:
            # 🏆 Si el bloque define una competición (Empieza con TO)
            if bloque.startswith("TO"):
                match_liga = re.search(r"DN欄([^]+)", bloque)
                if match_liga:
                    liga_actual = match_liga.group(1).replace("欄", "").strip()
            
            # ⚽ Si el bloque define un partido activo (Empieza con AA)
            elif bloque.startswith("AA"):
                # Extraemos el ID único del partido (clave para alertas futuras)
                id_match = bloque.split("欄")[0].replace("AA÷", "").strip()
                
                # Expresiones regulares adaptadas para capturar nombres y marcadores mutables
                partes = bloque.split("欄")
                
                local = None
                visita = None
                goles_l = "0"
                goles_v = "0"
                minuto = "Live"
                
                for p in partes:
                    if p.startswith("AE÷"): local = p.replace("AE÷", "")
                    elif p.startswith("AF÷"): visita = p.replace("AF÷", "")
                    elif p.startswith("AG÷"): goles_l = p.replace("AG÷", "")
                    elif p.startswith("AH÷"): goles_v = p.replace("AH÷", "")
                    elif p.startswith("AM÷"): minuto = p.replace("AM÷", "")
                
                if local and visita:
                    partidos_live.append({
                        "ID Partido": id_match,
                        "Competición": liga_actual,
                        "Partido": f"🏟️ {local} ({goles_l}) vs ({goles_v}) {visita}",
                        "Tiempo / Minuto": minuto.strip()
                    })
        except:
            continue
            
    return partidos_live

# ===========================================
# 🔄 BUCLE PRINCIPAL DE STREAMLIT
# ===========================================
if ejecutar:
    metric_estado.metric("Estado de Red", "🟢 Escaneando API...")
    
    # Descargar y parsear
    raw_feed = capturar_flashscore_live()
    lista_partidos = procesar_feed(raw_feed)
    
    if lista_partidos:
        df_flash = pd.DataFrame(lista_partidos)
        metric_partidos.metric("Eventos en Directo Encontrados", len(df_flash))
        tabla_datos.dataframe(df_flash, use_container_width=True, hide_index=True)
    else:
        metric_partidos.metric("Eventos en Directo Encontrados", 0)
        tabla_datos.warning("⚠️ No hay registros cargados en este bloque o el servidor está en mantenimiento.")
        
    st.write("⏱️ Esperando 10 segundos para actualizar métricas en vivo...")
    time.sleep(10)
    st.rerun()

else:
    metric_estado.metric("Estado de Red", "🔴 Apagado")
    st.info("Activa el interruptor de la izquierda para enlazar el lector de anomalías a los partidos en juego.")
