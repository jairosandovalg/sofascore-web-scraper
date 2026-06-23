import streamlit as st
import pandas as pd
import os
import subprocess
import sys
from streamlit_autorefresh import st_autorefresh

# --- INSTALACIÓN OPTIMIZADA Y CONTROLADA DE PLAYWRIGHT ---
@st.cache_resource
def iniciar_entorno_playwright():
    # Creamos un indicador visual elegante en la interfaz mientras descarga en segundo plano
    with st.spinner("🚀 Configurando el motor de navegación en la nube... Esto puede tomar 1 o 2 minutos en el primer inicio."):
        try:
            # Ejecuta la descarga de Chromium capturando los logs para no congelar la app
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"], 
                check=True, 
                capture_output=True
            )
            return True
        except Exception as e:
            st.error(f"Error al inicializar el navegador: {e}")
            return False

# Ejecutamos la función de caché antes de renderizar el resto del diseño
navegador_listo = iniciar_entorno_playwright()

# CONFIGURACIÓN DE LA INTERFAZ
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

# Solo habilitamos el autorefresh y el flujo si el navegador ya está descargado e instalado
if navegador_listo:
    st_autorefresh(interval=15 * 1000, key="datarefresh")

    archivo_datos = "analisis_live_apuestas.csv"

    # Botón manual de emergencia optimizado
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
            if not df.empty:
                if "Última Actualización" in df.columns:
                    ultima_hora = df["Última Actualización"].iloc[0]
                    st.success(f"🔄 Interfaz sincronizada en la nube. Último barrido: **{ultima_hora}**")
                
                st.subheader("🔥 Presión y Volumen de Ataque en Directo")
                columnas_mostrar = [
                    "Tiempo", "Local", "GL", "GV", "Visitante", 
                    "xG L", "xG V", "Córneres L", "Córneres V", 
                    "Remates Puerta L", "Remates Puerta V", "Remates Totales L", "Remates Totales V"
                ]
                columnas_validas = [col for col in columnas_mostrar if col in df.columns]
                st.dataframe(df[columnas_validas], use_container_width=True, height=600)
            else:
                st.info("⏳ Esperando encuentros en vivo...")
        except Exception as e:
            st.error("⏳ Archivo temporalmente ocupado, reintentando...")
    else:
        st.warning("⏳ Esperando la primera generación del archivo de datos...")
        
        if "auto_start_initiated" not in st.session_state:
            st.session_state["auto_start_initiated"] = True
            try:
                subprocess.Popen([sys.executable, "cron_scraper.py"], start_new_session=True)
            except Exception as e:
                st.error(f"No se pudo inicializar el motor: {e}")
else:
    st.info("Por favor, espera a que finalice la instalación interna en la consola de la derecha.")
