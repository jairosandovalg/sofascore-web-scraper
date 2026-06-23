import streamlit as st
import pandas as pd
import os
import subprocess
import sys
from streamlit_autorefresh import st_autorefresh

# CONFIGURACIÓN DE LA INTERFAZ
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

# Refresco automático de la pantalla cada 15 segundos
st_autorefresh(interval=15 * 1000, key="datarefresh")

archivo_datos = "analisis_live_apuestas.csv"

# Botón manual de emergencia por si el automatizado se duerme
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🔄 Forzar Raspado Manual"):
        with st.spinner("Ejecutando escaneo manual..."):
            try:
                # Eliminamos la instalación manual pesada de playwright aquí para evitar bloqueos
                subprocess.run([sys.executable, "cron_scraper.py"], timeout=90, check=True)
                st.success("¡Completado!")
                st.rerun()
            except Exception as ex:
                st.error(f"Error en raspado: {ex}")

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
        st.error(f"⏳ Archivo de intercambio temporalmente ocupado. Reintentando...")
else:
    st.warning("⏳ Esperando la primera generación del archivo de datos...")
    st.info("Si el motor automático tarda demasiado en el primer inicio, presiona el botón 'Forzar Raspado Manual' de arriba a la derecha para inicializar el archivo base.")
    
    # Control estricto del arranque único en segundo plano
    if "auto_start_initiated" not in st.session_state:
        st.session_state["auto_start_initiated"] = True
        try:
            # Lanza el proceso una única vez sin bloquear el hilo principal de Streamlit
            subprocess.Popen([sys.executable, "cron_scraper.py"])
        except Exception as e:
            st.error(f"No se pudo inicializar el motor automático: {e}")
