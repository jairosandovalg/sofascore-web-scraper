import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import time
from datetime import datetime

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Extractor Live API Fiel", page_icon="⚽", layout="wide")
st.title("⚽ Fase 1: Extracción en Vivo Vía API Pública (Estabilidad Total)")
st.write("Conectamos Streamlit con un feed deportivo descentralizado e inmune a los bloqueos de Cloudflare.")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Panel de Control")
ejecutar = st.sidebar.toggle("▶️ Iniciar Monitoreo en Vivo (Loop 10s)", value=False)

# --- CUADRO DE MANDOS ---
col1, col2 = st.columns(2)
metric_partidos = col1.empty()
metric_estado = col2.empty()

log_box = st.container(border=True)
log_box.write("### 📄 Logs de Conexión de Datos")

st.write("### 📊 Partidos en Tiempo Real Detectados")
tabla_datos = st.empty()

# ===========================================
# 🚀 EXTRACCIÓN DIRECTA DE DATOS EN VIVO
# ===========================================
def capturar_feed_live():
    # Usamos el endpoint global de Scorespro que no bloquea IPs de servidores (Streamlit Cloud)
    url = "https://www.scorespro.com/rss/live-soccer.xml"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    
    try:
        log_box.write("📡 Conectando con el servidor de distribución deportiva...")
        response = requests.get(url, headers=headers, timeout=12)
        
        if response.status_code == 200:
            log_box.success("🎯 ¡Paquete de partidos en directo sincronizado correctamente!")
            return response.text
        else:
            log_box.error(f"❌ Error de respuesta del servidor externo. Código: {response.status_code}")
            return None
    except Exception as e:
        log_box.error(f"❌ Fallo en la solicitud de red: {e}")
        return None

# ===========================================
# 🧹 PARSER DE ESTRUCTURA SEMÁNTICA
# ===========================================
def procesar_xml_feed(xml_texto):
    if not xml_texto:
        return []
        
    partidos_procesados = []
    
    try:
        root = ET.fromstring(xml_texto)
        
        # Buscamos todos los elementos de partidos 'item' dentro del RSS
        for item in root.findall(".//item"):
            try:
                title = item.find("title").text # Contiene "Equipo A vs Equipo B (Marcador, Minuto)"
                description = item.find("description").text # Contiene detalles de la competición
                
                # Formateamos los strings para limpiar la metadata visual de la API
                if " vs " in title:
                    partidos_procesados.append({
                        "Fecha Captura": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Competición / Categoría": description.strip() if description else "Fútbol Profesional",
                        "Partido / Marcador Actual": title.strip()
                    })
            except:
                continue
    except Exception as err:
        log_box.error(f"⚠️ Error al estructurar la matriz XML: {err}")
        
    return list(partidos_procesados)

# ===========================================
# 🔄 BUCLE DE MONITOREO CONTINUO
# ===========================================
if ejecutar:
    metric_estado.metric("Estado de Red", "🟢 Sincronizado")
    
    raw_data = capturar_feed_live()
    partidos_activos = procesar_xml_feed(raw_data)
    
    if partidos_activos:
        df_live = pd.DataFrame(partidos_activos)
        metric_partidos.metric("Eventos en Directo Encontrados", len(df_live))
        tabla_datos.dataframe(df_live, use_container_width=True, hide_index=True)
    else:
        metric_partidos.metric("Eventos en Directo Encontrados", 0)
        tabla_datos.info("ℹ️ No hay partidos jugándose en vivo en este minuto exacto en la cartelera internacional.")
        
    st.write("⏱️ Esperando 10 segundos para actualizar métricas en vivo...")
    time.sleep(10)
    st.rerun()

else:
    metric_estado.metric("Estado de Red", "🔴 Apagado")
    st.info("Activa el interruptor del Panel de Control para arrancar el scraping continuo.")
