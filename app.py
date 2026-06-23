import streamlit as st
import pandas as pd
import os
from streamlit_autorefresh import st_autorefresh
import threading
import subprocess
import sys

# ====================================================================
# 🚀 CONTROL NATIVO DE HILOS PARA SCRAPER 24/7 EN SEGUNDO PLANO
# ====================================================================
def arrancar_scraper_background():
    try:
        # CORRECCIÓN CRÍTICA: NO usar st.write aquí adentro.
        # Ejecutamos la instalación en silencio dentro del subproceso secundario
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        
        # Iniciar el script cron de manera asíncrona y aislada
        subprocess.Popen(
            [sys.executable, "cron_scraper.py"],
            stdout=None,
            stderr=None,
            start_new_session=True
        )
    except Exception as e:
        print(f"❌ Error crítico en el hilo conductor: {e}")

# Verificamos si el hilo ya ha sido lanzado en esta sesión del contenedor
if "scraper_inicializado" not in st.session_state:
    st.session_state["scraper_inicializado"] = True
    threading.Thread(target=arrancar_scraper_background, daemon=True).start()

# ====================================================================
# 💻 CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT
# ====================================================================
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

# Refresco automático de la pantalla cada 10 segundos
st_autorefresh(interval=10 * 1000, key="datarefresh")

archivo_datos = "analisis_live_apuestas.csv"

# ====================================================================
# 📊 CONTROL Y DESPLIEGUE DE LA MATRIZ DE DATOS
# ====================================================================
if os.path.exists(archivo_datos):
    try:
        df = pd.read_csv(archivo_datos)
        
        if not df.empty and "Última Actualización" in df.columns:
            ultima_hora = df["Última Actualización"].iloc[0]
            st.success(f"🔄 Interfaz sincronizada en la nube. Último barrido del robot: **{ultima_hora}**")
            
            st.subheader("🔥 Presión y Volumen de Ataque en Directo")
            
            columnas_mostrar = [
                "Tiempo", "Local", "GL", "GV", "Visitante", 
                "xG L", "xG V", "Córneres L", "Córneres V", 
                "Remates Puerta L", "Remates Puerta V", "Remates Totales L", "Remates Totales V",
                "Grandes Ocasiones L", "Grandes Ocasiones V", "TA L", "TA V", "TR L", "TR V",
                "Posesión L", "Posesión V", "Precisión Pases L", "Precisión Pases V"
            ]
            
            columnas_validas = [col for col in columnas_mostrar if col in df.columns]
            st.dataframe(df[columnas_validas], width='stretch', height=600)
        else:
            st.info("⏳ Al momento no hay partidos en directo disponibles en Flashscore. Esperando encuentros...")
            
    except Exception as e:
        st.error(f"⏳ Archivo de intercambio temporalmente ocupado. Reintentando en 10s...")
else:
    st.warning("⏳ Inicializando el motor de raspado automatizado en el servidor Cloud...")
    st.info("El script `cron_scraper.py` ha sido despertado en segundo plano. Tomará aproximadamente 60-90 segundos en completar su primer barrido.")
