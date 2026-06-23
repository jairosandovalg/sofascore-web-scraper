import streamlit as st
import pandas as pd
import os
from streamlit_autorefresh import st_autorefresh
import threading
import subprocess
import os

# Función para arrancar el cron_scraper en segundo plano dentro del servidor cloud
def arrancar_scraper_background():
    if not os.path.exists("scraper_activo.txt"):
        with open("scraper_activo.txt", "w") as f:
            f.write("running")
        # Ejecuta el script de python de forma independiente y asíncrona
        subprocess.Popen(["python", "cron_scraper.py"])

# Lanzar el hilo persistente si no está corriendo
threading.Thread(target=arrancar_scraper_background, daemon=True).start()

st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

# 🔄 Configuración del Refresco Automático de la Interfaz (Cada 10 segundos lee el CSV)
st_autorefresh(interval=10 * 1000, key="datarefresh")

archivo_datos = "analisis_live_apuestas.csv"

if os.path.exists(archivo_datos):
    try:
        # Leer la base de datos actualizada en segundo plano por el cron_scraper
        df = pd.read_csv(archivo_datos)
        
        # Muestra la última hora en la que el robot inyectó datos
        ultima_hora = df["Última Actualización"].iloc[0] if "Última Actualización" in df.columns else "Desconocida"
        st.success(f"🔄 Interfaz sincronizada. Datos del servidor actualizados por última vez a las: **{ultima_hora}**")
        
        # Estructura del panel interactivo
        st.subheader("🔥 Presión y Volumen de Ataque en Directo")
        
        columnas_mostrar = [
            "Tiempo", "Local", "GL", "GV", "Visitante", 
            "xG L", "xG V", "Córneres L", "Córneres V", 
            "Remates Puerta L", "Remates Puerta V", "Remates Totales L", "Remates Totales V",
            "Grandes Ocasiones L", "Grandes Ocasiones V", "TA L", "TA V", "TR L", "TR V",
            "Posesión L", "Posesión V", "Precisión Pases L", "Precisión Pases V"
        ]
        
        # Despliegue de tabla ordenable
        st.dataframe(df[columnas_mostrar], use_container_width=True, height=600)
        
    except Exception as e:
        st.error(f"⏳ Intentando leer el archivo de intercambio... (El scraper podría estar escribiendo en él): {e}")
else:
    st.warning("⏳ Esperando que el extractor genere el primer archivo de datos dinámicos ('analisis_live_apuestas.csv')...")
    st.info("Asegúrate de ejecutar 'python cron_scraper.py' en una terminal paralela para iniciar la captura de datos.")
