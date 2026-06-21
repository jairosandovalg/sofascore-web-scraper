import pandas as pd
import numpy as np
import time
import re
from datetime import datetime
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import streamlit as st

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Sofascore Scraper Pro", page_icon="⚽", layout="wide")
st.title("⚽ Extractor de Estadísticas en Tiempo Real (Sofascore)")
st.write("Esta versión incorpora configuraciones avanzadas anti-bloqueo (User-Agent y evasión de Cloudflare) para la nube.")

# ===========================================
# ⚙️ INICIALIZACIÓN DE SELENIUM (MEDIDAS ANTI-DETECCIÓN)
# ===========================================
@st.cache_resource
def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless=new")             
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")               
    options.add_argument("--disable-dev-shm-usage")    
    options.add_argument("--disable-extensions")
    
    # 🕵️‍♂️ MÁSCARA ANTI-BOTS: Definimos un agente de usuario de una computadora real
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    # ❌ Desactivamos la propiedad que le avisa a las webs que estamos usando Selenium
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    
    # Inyectamos un script para borrar rastro de automatización en Javascript
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
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
# 🌍 URLS DE TORNEOS DISPONIBLES
# ===========================================
urls_torneos = {
    "Copa Mundial": "https://www.sofascore.com/es/football/tournament/world/world-championship/16#id:58210",
    "Premier League": "https://www.sofascore.com/es/torneo/futbol/england/premier-league/17#id:76986",
    "La Liga": "https://www.sofascore.com/es/torneo/futbol/spain/laliga/8#id:77559"
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

tabla_datos.dataframe(st.session_state.datos_scraping, use_container_width=True)
metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))

# ===========================================
# 🔄 BUCLE DE EJECUCIÓN (REFRESCO CADA 10 SEGUNDOS)
# ===========================================
if ejecutar:
    metric_estado.metric("Estado del Scraper", "🟢 Buscando datos...")
    
    try:
        # 🛡️ Paso intermedio de simulación humana: ir a la raíz para generar cookies limpias
        log_box.write("⏳ Calentando el motor del navegador...")
        driver.get("https://www.sofascore.com/")
        time.sleep(3)
        
        log_box.write(f"🌍 Accediendo a la liga: **{torneo_seleccionado}**...")
        driver.get(url_actual)
        
        # ⏳ Espera explícita para la tabla
        wait = WebDriverWait(driver, 20)
        try:
            # Buscamos cualquier link de equipo válido en la tabla
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/team/')]")))
        except TimeoutException:
            log_box.warning("⚠️ Cloudflare o retraso de red detectado. Intentando buscar elementos alternativos...")

        # ⚽ EXTRAER EQUIPOS
        equipos = driver.find_elements(By.XPATH, "//a[contains(@href, '/team/')]")
        data_equipos = []
        
        for e in equipos:
            try:
                enlace = e.get_attribute("href")
                if 'football/team/' in enlace or '/team/html/' in enlace:
                    equipo_texto = e.find_element(By.XPATH, ".//span").text.strip()
                    if equipo_texto and not equipo_texto.isdigit():
                        data_equipos.append({"equipo": equipo_texto, "enlace": enlace})
            except:
                continue
        
        if data_equipos:
            df_eq_temp = pd.DataFrame(data_equipos).drop_duplicates(subset=["equipo"])
            data_equipos = df_eq_temp.to_dict('records')
        else:
            data_equipos = []

        log_box.write(f"✅ ¡Se localizaron **{len(data_equipos)}** equipos únicos!")

        # 🔗 EXTRAER PARTIDOS POR EQUIPO
        if data_equipos:
            data_partidos = []
            # Analizar el primer equipo de la lista para agilizar la prueba visual
            for d in data_equipos[:1]: 
                try:
                    log_box.write(f"⚽ Buscando partidos de: *{d['equipo']}*")
                    driver.get(d['enlace'])
                    time.sleep(3)
                    
                    secciones = driver.find_elements(By.XPATH, "//div[contains(@class,'card-component')]")
                    for sec in secciones:
                        partidos = sec.find_elements(By.XPATH, ".//a[contains(@href, '/match/')]")
                        for p in partidos:
                            enlace_partido = p.get_attribute("href")
                            if enlace_partido:
                                data_partidos.append({"Equipo Base": d['equipo'], "Enlace Partido": enlace_partido})
                except:
                    continue

            if data_partidos:
                df_partidos = pd.DataFrame(data_partidos).drop_duplicates()
                log_box.write(f"📋 Enlaces de partidos encontrados: {len(df_partidos)}")

                # 📊 EXTRAER MÉTRICAS
                estadisticas = []
                partido_prueba = df_partidos.iloc[0]
                
                log_box.write(f"🔎 Extrayendo métricas de partido: {partido_prueba['Enlace Partido']}")
                driver.get(partido_prueba["Enlace Partido"])
                time.sleep(3)

                # --- Raspar Información Básica ---
                try: fecha = driver.find_elements(By.XPATH, "//span[@class='textStyle_display.micro c_neutrals.nLv3 lh_1']")[0].text
                except: fecha = None
                try: competicion = driver.find_element(By.XPATH, "//div[contains(@class,'d_flex')]//span[contains(@class,'textStyle_display.micro')]").text
                except: competicion = None
                try:
                    eq_p = driver.find_elements(By.XPATH, "//bdi")
                    local, visita = eq_p[0].text, eq_p[1].text
                except: local, visita = "Local", "Visitante"

                # --- Extraer Estadísticas ---
                try:
                    btn_stats = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@data-testid, 'tab-statistics')]"))
                    )
                    btn_stats.click()
                    time.sleep(2)
                    
                    summary = driver.find_elements(By.XPATH, "//div[contains(@class, 'bg_surface')]")
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
                                    "Métrica": nombre, "Local Valor": local_val, "Visitante Valor": visita_val
                                })
                            except: continue
                except:
                    pass

                if estadisticas:
                    df_nuevos_datos = pd.DataFrame(estadisticas)
                    st.session_state.datos_scraping = pd.concat([st.session_state.datos_scraping, df_nuevos_datos], ignore_index=True).drop_duplicates(subset=["Fecha Partido", "Local", "Visitante", "Métrica"])
                    log_box.success("✨ ¡Métricas recopiladas con éxito!")
            else:
                log_box.warning("⚠️ No se pudieron estructurar sub-enlaces de partidos.")
        else:
            log_box.error("❌ La estructura fue bloqueada por el Host. Reintentando en el próximo ciclo...")
            
    except Exception as e:
        log_box.error(f"❌ Error en la ejecución: {e}")

    # Forzar actualización en pantalla
    tabla_datos.dataframe(st.session_state.datos_scraping, use_container_width=True)
    metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))
    
    st.write("⏱️ Esperando 10 segundos para iniciar un nuevo barrido automático...")
    time.sleep(10)
    st.rerun()

else:
    metric_estado.metric("Estado del Scraper", "🔴 Detenido")
    st.info("Utiliza el switch de la barra izquierda para arrancar el scraping continuo.")
