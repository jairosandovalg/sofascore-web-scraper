import os
import sys
import subprocess
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN DE RUTA LOCAL ABSOLUTA PARA PLAYWRIGHT ---
# Forzamos a Playwright a instalar y buscar el navegador dentro de la carpeta del proyecto
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.getcwd(), ".playwright-browsers")

@st.cache_resource
def inicializar_playwright_local():
    with st.spinner("🚀 Sincronizando motor Chromium y dependencias del sistema operativo Linux (Paso Único)..."):
        try:
            # 1. Instalar el binario de Chromium directamente en el directorio local del proyecto
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"], 
                check=True, 
                capture_output=True
            )
            
            # 2. Intentar inyectar las librerías compartidas de Linux (.so) que Chromium headless requiere
            # Se usa check=False para evitar que la aplicación colapse si el entorno de la nube restringe el comando
            subprocess.run(
                [sys.executable, "-m", "playwright", "install-deps"], 
                check=False, 
                capture_output=True
            )
            return True
        except Exception as e:
            st.error(f"Error crítico al inicializar el binario de Chromium o sus dependencias: {e}")
            return False

# Inicializar entorno (Navegador y Librerías del SO) antes de construir la interfaz de usuario
entorno_listo = inicializar_playwright_local()

# CONFIGURACIÓN DE LA INTERFAZ DE STREAMLIT
st.set_page_config(page_title="Radar Live 24/7", page_icon="⚽", layout="wide")
st.title("⚽ Monitor General In-Play (Actualización Automática 24/7)")

if entorno_listo:
    # Refresco automático de la pantalla del navegador cada 15 segundos
    st_autorefresh(interval=15 * 1000, key="datarefresh")

    # Configuración de nombres de archivo de intercambio
    nombre_script_raspador = "cron_scraper.py"
    archivo_datos = "analisis_live_apuestas.csv"

    # Fila superior de utilidades y botón manual de emergencia por si el automatizado se congela
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
                
                # Columnas mapeadas idénticas a la salida estructurada de tu raspador corregido
                columnas_mostrar = [
                    "Tiempo", "Local", "GL", "GV", "Visitante", 
                    "xG L", "xG V", "Córneres L", "Córneres V", 
                    "Remates Puerta L", "Remates Puerta V", "Remates Totales L", "Remates Totales V",
                    "Grandes Ocasiones L", "Grandes Ocasiones V", "TA L", "TA V", "TR L", "TR V",
                    "Posesión L", "Posesión V", "Precisión Pases L", "Precisión Pases V"
                ]
                
                # Filtrar solo aquellas columnas que efectivamente se generaron en el CSV
                columnas_validas = [col for col in columnas_mostrar if col in df.columns]
                
                # Rellenar valores nulos (partidos que recién empiezan sin métricas aún) con guiones
                df_filtrado = df[columnas_validas].fillna("-")
                
                st.dataframe(df_filtrado, use_container_width=True, height=600)
            else:
                st.info("⏳ Al momento no hay partidos en directo disponibles en la plataforma. Esperando encuentros...")
                
        except Exception as e:
            st.error("⏳ Archivo de intercambio de datos ocupado transitoriamente. Sincronizando en el siguiente ciclo...")
    else:
        st.warning("⏳ Esperando la primera generación del archivo de datos...")
        st.info("Si el motor automático tarda demasiado en el primer inicio, presiona el botón 'Forzar Raspado Manual' arriba a la derecha para inicializar el archivo base.")
        
        # Disparar hilo secundario persistente si no se ha iniciado antes en la sesión actual
        if "auto_start_initiated" not in st.session_state:
            st.session_state["auto_start_initiated"] = True
            try:
                subprocess.Popen([sys.executable, nombre_script_raspador], start_new_session=True)
            except Exception as e:
                st.error(f"No se pudo inicializar el motor en segundo plano: {e}")
else:
    st.error("El entorno en la nube no cuenta con los privilegios básicos requeridos para montar el navegador headless.")

# =====================================================================
# VISOR DE LOGS INTEGRADO AL FINAL ABSOLUTO DE LA APP
# =====================================================================
st.markdown("---")
st.subheader("🕵️‍♂️ Auditoría del Robot en Vivo (Logs)")
if os.path.exists("robot_ejecucion.log"):
    with open("robot_ejecucion.log", "r", encoding="utf-8") as f:
        lineas = f.readlines()
    # Muestra de forma segura el último bloque de texto para diagnosticar bloqueos
    st.code("".join(lineas[-15:]))
else:
    st.info("El archivo de registro de eventos aún no se ha generado en el servidor.")
