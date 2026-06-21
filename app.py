import pandas as pd
import numpy as np
import time
import re
from datetime import datetime
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import streamlit as st

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Sofascore Scraper Test", page_icon="⚽", layout="wide")
st.title("⚽ Prueba de Web Scraping en Tiempo Real (Sofascore)")
st.write("Esta versión ejecuta el scraping en la nube y muestra los resultados directamente en la pantalla usando la memoria de Streamlit.")

# ===========================================
# ⚙️ INICIALIZACIÓN DE SELENIUM (PAQUETES NATIVOS DE LINUX)
# ===========================================
@st.cache_resource
def iniciar_driver():
    options = webdriver.ChromeOptions()
    
    # 📌 Opciones críticas para correr en contenedores Linux/Nube sin interfaz gráfica
    options.add_argument("--headless=new")             # Formato moderno para headless en Selenium 4
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")               # Evita restricciones de seguridad de Docker
    options.add_argument("--disable-dev-shm-usage")    # Evita caídas por falta de memoria RAM compartida
    options.add_argument("--disable-extensions")
    
    # Dejamos que Selenium Manager (nativo de Selenium 4) encuentre Chromium solo.
    # Solo añadimos el servicio básico sin rutas forzadas.
    service = Service()
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver

try:
    driver = iniciar_driver()
except Exception as e:
    st.error(f"Error al inicializar Chrome en el servidor: {e}")
    st.stop()

# ===========================================
# 🧠 MEMORIA TEMPORAL DE LA SESIÓN
# ===========================================
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

# --- BARRA LATERAL (SIDEBAR) ---
st.sidebar.header("⚙️ Panel de Control")
torneo_seleccionado = st.sidebar.selectbox("Selecciona un Torneo:", list(urls_torneos.keys()))
url_actual = urls_torneos[torneo_seleccionado]

ejecutar = st.sidebar.toggle("▶️ Iniciar Web Scraping (Loop 10s)", value=False)

if st.sidebar.button("🧹 Borrar Datos de la Pantalla"):
    st.session_state.datos_scraping = pd.DataFrame()
    st.rerun()

# --- CUADRO DE MANDOS PRINCIPAL (DASHBOARD) ---
col1, col2 = st.columns(2)
metric_filas = col1.empty()
metric_estado = col2.empty()

log_box = st.container(border=True)
log_box.write("### 📄 Logs del Navegador en la Nube")

st.write("### 📊 Datos Extraídos en Vivo")
tabla_datos = st.empty()

# Renderizado inicial del DataFrame en memoria
tabla_datos.dataframe(st.session_state.datos_scraping, use_container_width=True)
metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))

# ===========================================
# 🔄 BUCLE DE EJECUCIÓN (REFRESCO CADA 10 SEGUNDOS)
# ===========================================
if ejecutar:
    metric_estado.metric("Estado del Scraper", "🟢 Buscando datos...")
    
    try:
        log_box.write(f"🌍 Accediendo a la liga: **{torneo_seleccionado}**...")
        driver.get(url_actual)
        time.sleep(4)
        
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
        
        log_box.write(f"✅ Se localizaron {len(data_equipos)} equipos en la tabla.")

        # 🔗 EXTRAER PARTIDOS (Limitado a los 2 primeros equipos para agilizar pruebas en la nube)
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
            log_box.write(f"📋 Analizando enlaces de partidos... Encontrados: {len(df_partidos)}")

            # 📊 EXTRAER MÉTRICAS INTERNAS DEL PRIMER PARTIDO DISPONIBLE
            estadisticas = []
            partido_prueba = df_partidos.iloc[0]
            
            log_box.write(f"🔎 Extrayendo métricas de: {partido_prueba['Enlace Partido']}")
            driver.get(partido_prueba["Enlace Partido"])
            time.sleep(4)

            # --- Raspar Información Básica ---
            try: fecha = driver.find_elements(By.XPATH, "//span[@class='textStyle_display.micro c_neutrals.nLv3 lh_1']")[0].text
            except: fecha = None
            try: competicion = driver.find_element(By.XPATH, "//div[contains(@class,'d_flex') and contains(@class,'hover:bg_surface.s2')]//span[contains(@class,'textStyle_display.micro')]").text
            except: competicion = None
            try:
                eq_p = driver.find_elements(By.XPATH, "//bdi[contains(@class,'textStyle_display.medium')]")
                local, visita = eq_p[0].text, eq_p[1].text
            except: local, visita = "Local", "Visitante"

            # --- Navegar a la pestaña de estadísticas internas ---
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
                                "Fecha Extracción": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "Fecha Partido": fecha, "Competición": competicion, "Local": local, "Visitante": visita,
                                "Métrica": ... if 'nombre' not in locals() else nombre, "Local Valor": local_val, "Visitante Valor": visita_val
                            })
                        except: continue
            except:
                log_box.warning("⚠️ Pestaña de estadísticas no disponible en este evento por el momento.")

            # Acumular en st.session_state si se obtuvieron datos nuevos
            if estadisticas:
                df_nuevos_datos = pd.DataFrame(estadisticas)
                st.session_state.datos_scraping = pd.concat([st.session_state.datos_scraping, df_nuevos_datos], ignore_index=True).drop_duplicates(subset=["Fecha Partido", "Local", "Visitante", "Métrica"])
                log_box.success("✨ ¡Tabla actualizada correctamente con nuevas métricas!")
            
    except Exception as e:
        log_box.error(f"❌ Error en la ejecución de la nube: {e}")

    # Forzar la actualización de los componentes visuales en pantalla
    tabla_datos.dataframe(st.session_state.datos_scraping, use_container_width=True)
    metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))
    
    # Pausa de control y relanzamiento del ciclo completo
    st.write("⏱️ Esperando 10 segundos para iniciar un nuevo barrido automático...")
    time.sleep(10)
    st.rerun()

else:
    metric_estado.metric("Estado del Scraper", "🔴 Detenido")
    st.info("Utiliza el switch de la barra izquierda para arrancar el scraping continuo.")
