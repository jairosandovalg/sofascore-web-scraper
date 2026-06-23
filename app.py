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
        # Se elimina el comando subprocess.run de instalación para evitar bloqueos
        # Ejecuta el script cron usando el intérprete de Python del entorno actual
        subprocess.Popen([sys.executable, "cron_scraper.py"])
    except Exception as e:
        print(f"❌ Error al inicializar el proceso del Scraper: {e}")

# Verificamos si el hilo ya ha sido lanzado en esta sesión del contenedor
if "scraper_inicializado" not in st.session_state:
    st.session_state["scraper_inicializado"] = True
    threading.Thread(target=arrancar_scraper_background, daemon=True).start()

# Verificamos si el hilo ya ha sido lanzado en esta sesión del contenedor
if "scraper_inicializado" not in st.session_state:
    st.session_state["scraper_inicializado"] = True
    # Lanzamos el proceso en un hilo daemon para que no bloquee el cierre de la app principal
    threading.Thread(target=arrancar_scraper_background, daemon=True).start()

# ====================================================================
# 💻 CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT
# ====================================================================
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

# 🔄 Configuración del Refresco Automático de la Interfaz (Cada 10 segundos)
st_autorefresh(interval=10 * 1000, key="datarefresh")

archivo_datos = "analisis_live_apuestas.csv"

# ====================================================================
# 📊 CONTROL Y DESPLIEGUE DE LA MATRIZ DE DATOS
# ====================================================================
if os.path.exists(archivo_datos):
    try:
        # Leer la base de datos actualizada en segundo plano por el cron_scraper
        df = pd.read_csv(archivo_datos)
        
        # Validación de seguridad: Comprobar que el archivo no esté vacío o siendo sobreescrito
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
            
            # Asegurar que solo se muestren columnas existentes para evitar KeyErrors accidentales
            columnas_validas = [col for col in columnas_mostrar if col in df.columns]
            
            # Despliegue de tabla interactiva y ordenable
            st.dataframe(df[columnas_validas], use_container_width=True, height=600)
        else:
            st.info("⏳ El archivo de datos está siendo actualizado por el Scraper. Esperando próximo refresco...")
            
    except Exception as e:
        st.error(f"⏳ Archivo temporalmente bloqueado (I/O Concurrency). Reintentando en 10s...")
else:
    st.warning("⏳ Inicializando el motor de raspado automatizado en el servidor Cloud...")
    st.info("El script `cron_scraper.py` ha sido despertado en segundo plano. Tomará aproximadamente 60-90 segundos en completar su primer barrido de partidos en directo y generar el archivo de intercambio.")
