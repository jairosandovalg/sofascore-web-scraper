import pandas as pd
import numpy as np
import time
import re
from datetime import datetime
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import streamlit as st

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Sofascore Scraper Test", page_icon="⚽", layout="wide")
st.title("⚽ Prueba de Web Scraping en Tiempo Real (Sofascore)")
st.write("Esta versión ejecuta el scraping y muestra los resultados directamente en la pantalla sin usar bases de datos.")

# ===========================================
# ⚙️ INICIALIZACIÓN DE SELENIUM (CACHED)
# ===========================================
@st.cache_resource
def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless")  # Corre en segundo plano sin abrir ventanas molestas
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver

try:
    driver = iniciar_driver()
except Exception as e:
    st.error(f"Error al inicializar Chrome: {e}")
    st.stop()

# ===========================================
# 🧠 MEMORÍA TEMPORAL DE STREAMLIT
# ===========================================
# Creamos un DataFrame vacío en la memoria de la sesión si no existe
if "datos_scraping" not in st.session_state:
    st.session_state.datos_scraping = pd.DataFrame()

# ===========================================
# 🌍 URLS DE TORNEOS
# ===========================================
urls_torneos = {
    "Mozzart Bet Superliga" : "https://www.sofascore.com/es/torneo/futbol/serbia/mozzart-bet-superliga/210#id:76909",
    "Premier League": "https://www.sofascore.com/es/torneo/futbol/england/premier-league/17#id:76986",
    "La Liga": "https://www.sofascore.com/es/torneo/futbol/spain/laliga/8#id:77559",
    "Liga 1 (Perú)": "https://www.sofascore.com/es/torneo/futbol/peru/liga-1/406#id:70962"
}

# Sidebar
torneo_seleccionado = st.sidebar.selectbox("Selecciona un Torneo:", list(urls_torneos.keys()))
url_actual = urls_torneos[torneo_seleccionado]

ejecutar = st.sidebar.toggle("▶️ Iniciar Web Scraping (Loop 10s)", value=False)

# Botón para limpiar la pantalla
if st.sidebar.button("🧹 Borrar Datos Mostrados"):
    st.session_state.datos_scraping = pd.DataFrame()
    st.rerun()

# Dashboard principal
col1, col2 = st.columns(2)
metric_filas = col1.empty()
metric_estado = col2.empty()

log_box = st.container(border=True)
log_box.write("### 📄 Logs del Navegador")

st.write("### 📊 Datos Extraídos en Vivo")
tabla_datos = st.empty() # Contenedor para la tabla de resultados

# Mostrar datos acumulados actualmente
tabla_datos.dataframe(st.session_state.datos_scraping)
metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))

# ===========================================
# 🔄 BUCLE DE SCRAPING (CADA 10 SEGUNDOS)
# ===========================================
if ejecutar:
    metric_estado.metric("Estado", "🟢 Buscando datos...")
    
    try:
        log_box.write(f"🌍 Accediendo a la liga: {torneo_seleccionado}...")
        driver.get(url_actual)
        time.sleep(3)
        
        # ⚽ EXTRAER EQUIPOS
        equipos = driver.find_elements(By.XPATH, "//a[contains(@href, 'football/team/')]")
        data_equipos = []
        for e in equipos:
            try:
                equipo = e.find_element(By.XPATH, ".//span[contains(@class, 'textStyle_table.medium')]").text
                enlace = e.get_attribute("href")
                data_equipos.append({"equipo": equipo, "enlace": enlace})
            except:
                continue
        
        log_box.write(f"✅ Se encontraron {len(data_equipos)} equipos.")

        # 🔗 EXTRAER PARTIDOS (Limitado a los 2 primeros equipos para que la prueba sea rápida)
        data_partidos = []
        for d in data_equipos[:2]: 
            try:
                driver.get(d['enlace'])
                time.sleep(2)
                secciones = driver.find_elements(By.XPATH, "//div[contains(@class,'card-component')]")
                for sec in secciones:
                    partidos = sec.find_elements(By.XPATH, ".//a[contains(@href, '/football/match/')]")
                    for p in partidos:
                        data_partidos.append({"Equipo Base": d['equipo'], "Enlace Partido": p.get_attribute("href")})
            except:
                continue

        if data_partidos:
            df_partidos = pd.DataFrame(data_partidos).drop_duplicates()
            log_box.write(f"📋 Analizando {len(df_partidos)} enlaces de partidos...")

            # 📊 EXTRAER DATOS DEL PRIMER PARTIDO DETECTADO COMO PRUEBA
            estadisticas = []
            partido_prueba = df_partidos.iloc[0] # Tomamos el primero para ver que funcione el scraping interno
            
            log_box.write(f"🔎 Extrayendo métricas de: {partido_prueba['Enlace Partido']}")
            driver.get(partido_prueba["Enlace Partido"])
            time.sleep(3)

            # --- Raspar info básica ---
            try: fecha = driver.find_elements(By.XPATH, "//span[@class='textStyle_display.micro c_neutrals.nLv3 lh_1']")[0].text
            except: fecha = None
            try: competicion = driver.find_element(By.XPATH, "//div[contains(@class,'d_flex') and contains(@class,'hover:bg_surface.s2')]//span[contains(@class,'textStyle_display.micro')]").text
            except: competicion = None
            try:
                eq_p = driver.find_elements(By.XPATH, "//bdi[contains(@class,'textStyle_display.medium')]")
                local, visita = eq_p[0].text, eq_p[1].text
            except: local, visita = "Local", "Visitante"

            # --- Intentar raspar algunas estadísticas generales si la pestaña existe ---
            try:
                driver.find_element(By.XPATH, "//button[contains(@data-testid, 'tab-statistics')]").click()
                time.sleep(2)
                
                summary = driver.find_elements(By.XPATH, "//div[contains(@class, 'bg_surface') and contains(@class, 's1')]")
                for s in summary:
                    stats = s.find_elements(By.XPATH, ".//div[contains(@class, 'd_flex') and contains(@class, 'flex-d_column')]")
                    for st in stats:
                        try:
                            nombre = st.find_element(By.XPATH, ".//span[contains(@class, 'textStyle_assistive')]").text
                            local_val = st.find_element(By.XPATH, ".//bdi[1]/span").text
                            visita_val = st.find_element(By.XPATH, ".//bdi[last()]/span").text
                            
                            estadisticas.append({
                                "Fecha": fecha, "Competición": competicion, "Local": local, "Visitante": visita,
                                "Métrica": nombre, "Local Valor": local_val, "Visitante Valor": visita_val
                            })
                        except: continue
            except:
                log_box.warning("⚠️ Pestaña de estadísticas no disponible o diferente formato.")

            # Si logramos raspar algo, lo acumulamos en la memoria de Streamlit
            if estadisticas:
                df_nuevos_datos = pd.DataFrame(estadisticas)
                # Concatenamos los nuevos datos a los que ya teníamos guardados en la sesión
                st.session_state.datos_scraping = pd.concat([st.session_state.datos_scraping, df_nuevos_datos], ignore_index=True).drop_duplicates()
                log_box.success("✨ ¡Nuevos datos agregados con éxito!")
            
    except Exception as e:
        log_box.error(f"❌ Error en este ciclo: {e}")

    # Refrescar componentes visuales
    tabla_datos.dataframe(st.session_state.datos_scraping)
    metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))
    
    # Espera de 10 segundos y reinicio automático
    st.write("⏱️ Esperando 10 segundos para el siguiente ciclo...")
    time.sleep(10)
    st.rerun()

else:
    metric_estado.metric("Estado", "🔴 Detenido")
    st.info("Activa el switch en la barra lateral izquierda para iniciar el scraping.")
