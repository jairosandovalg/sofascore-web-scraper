import os
import sys
import subprocess
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

# Refresco automático de la pantalla del navegador cada 15 segundos
st_autorefresh(interval=15 * 1000, key="datarefresh")

nombre_script_raspador = "cron_scraper.py"
archivo_datos = "analisis_live_apuestas.csv"

# Fila superior de utilidades y botón manual de emergencia
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🔄 Forzar Raspado Manual", use_container_width=True):
        with st.spinner("Ejecutando escaneo manual..."):
            try:
                resultado = subprocess.run(
                    [sys.executable, nombre_script_raspador], 
                    timeout=90, 
                    capture_output=True, 
                    text=True,
                    check=True
                )
                st.success("¡Raspado completado con éxito!")
                st.rerun()
            except subprocess.TimeoutExpired:
                st.error("Error: El raspado manual superó el tiempo límite asignado de 90 segundos.")
            except subprocess.CalledProcessError as e:
                st.error("Error en el script de raspado:")
                st.code(e.stderr if e.stderr else e.output)

# DESPLIEGUE DEL TABLERO DE DATOS
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
            df_filtrado = df[columnas_validas].fillna("-")
            st.dataframe(df_filtrado, use_container_width=True, height=600)
        else:
            st.info("⏳ Al momento no hay partidos en directo disponibles en la plataforma. Esperando encuentros...")
            
    except Exception as e:
        st.error("⏳ Archivo de intercambio de datos ocupado transitoriamente. Sincronizando en el siguiente ciclo...")
else:
    st.warning("⏳ Esperando la primera generación del archivo de datos...")
    st.info("Si el motor automático tarda demasiado en el primer inicio, presiona el botón 'Forzar Raspado Manual' arriba a la derecha para inicializar el archivo base.")
    
    if "auto_start_initiated" not in st.session_state:
        st.session_state["auto_start_initiated"] = True
        try:
            subprocess.Popen([sys.executable, nombre_script_raspador], start_new_session=True)
        except Exception as e:
            st.error(f"No se pudo inicializar el motor en segundo plano: {e}")

# =====================================================================
# VISOR DE LOGS INTEGRADO AL FINAL ABSOLUTO DE LA APP
# =====================================================================
st.markdown("---")
st.subheader("🕵️‍♂️ Auditoría del Robot en Vivo (Logs)")
if os.path.exists("robot_ejecucion.log"):
    with open("robot_ejecucion.log", "r", encoding="utf-8") as f:
        lineas = f.readlines()
    st.code("".join(lineas[-15:]))
else:
    st.info("El archivo de registro de eventos aún no se ha generado en el servidor.")
