import streamlit as st
import pandas as pd
import os
import subprocess
import sys
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN DE RUTA LOCAL ABSOLUTA PARA PLAYWRIGHT ---
# Forzamos a Playwright a instalar y buscar el navegador dentro de la carpeta del proyecto
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), ".playwright-browsers")

@st.cache_resource
def inicializar_playwright_local():
    with st.spinner("🚀 Configurando entorno Chromium local en la nube (Paso Único)..."):
        try:
            # Instalamos el binario directamente en el directorio local del proyecto
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"], 
                check=True, 
                capture_output=True
            )
            return True
        except Exception as e:
            st.error(f"Error al inicializar el binario de Chromium: {e}")
            return False

# Inicializar entorno antes de construir la UI
entorno_listo = inicializar_playwright_local()

# CONFIGURACIÓN DE LA INTERFAZ
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

if entorno_listo:
    # Refresco automático de la pantalla cada 15 segundos
    st_autorefresh(interval=15 * 1000, key="datarefresh")

    archivo_datos = "analisis_live_apuestas.csv"

    # Botón manual de emergencia por si el automatizado se duerme
    col1, col2 = st.columns([8, 2])
    with col2:
        if st.button("🔄 Forzar Raspado Manual", use_container_width=True):
            with st.spinner("Ejecutando escaneo manual..."):
                try:
                    resultado = subprocess.run(
                        [sys.executable, "cron_scraper.py"], 
                        timeout=90, 
                        capture_output=True, 
                        text=True,
                        check=True
                    )
                    st.success("¡Raspado completado con éxito!")
                    st.rerun()
                except subprocess.TimeoutExpired:
                    st.error("Error: El raspado manual superó el tiempo límite.")
                except subprocess.CalledProcessError as e:
                    st.error(f"Error en el script de raspado:")
                    st.code(e.stderr if e.stderr else e.output)

    # DESPLIEGUE DE DATOS
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
                st.dataframe(df[columnas_validas], use_container_width=True, height=600)
            else:
                st.info("⏳ Al momento no hay partidos en directo disponibles. Esperando encuentros...")
                
        except Exception as e:
            st.error(f"⏳ Archivo de intercambio temporalmente ocupado. Sincronizando...")
    else:
        st.warning("⏳ Esperando la primera generación del archivo de datos...")
        st.info("Si el motor automático tarda demasiado en el primer inicio, presiona el botón 'Forzar Raspado Manual' de arriba a la derecha para inicializar el archivo base.")
        
        if "auto_start_initiated" not in st.session_state:
            st.session_state["auto_start_initiated"] = True
            try:
                subprocess.Popen([sys.executable, "cron_scraper.py"], start_new_session=True)
            except Exception as e:
                st.error(f"No se pudo inicializar el motor automático: {e}")
else:
    st.error("El entorno no se pudo inicializar correctamente.")
