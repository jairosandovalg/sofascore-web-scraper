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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from sqlalchemy import create_engine, text
import streamlit as str

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Sofascore Data Scraper", page_icon="⚽", layout="wide")
st.title("⚽ Extractor de Estadísticas en Tiempo Real (Sofascore)")
st.write("El script buscará partidos nuevos en la liga seleccionada y actualizará la base de datos cada 10 segundos.")

# ===========================================
# ⚙️ INICIALIZACIÓN CONFIGURADA DE SELENIUM (CACHED)
# ===========================================
@st.cache_resource
def iniciar_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--headless")  # RECOMENDADO PARA STREAMLIT (Sin interfaz gráfica)
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
    st.error(f"Error al inicializar el navegador Chrome: {e}")
    st.stop()

# --- Conexión SQL ---
usuario = "sa"
password = "SQL_72543174"
servidor = "DESKTOP-N3PD6L0"
base_datos = "BET"
table_name = "DataBet"

engine = create_engine(
    f"mssql+pyodbc://{usuario}:{password}@{servidor}/{base_datos}?driver=ODBC+Driver+17+for+SQL+Server"
)

# ===========================================
# 🌍 URLS DE TORNEOS DISPONIBLES
# ===========================================
urls_torneos = {
    "Premier League": "https://www.sofascore.com/es/torneo/futbol/england/premier-league/17#id:76986",
    "La Liga": "https://www.sofascore.com/es/torneo/futbol/spain/laliga/8#id:77559",
    "Bundesliga": "https://www.sofascore.com/es/torneo/futbol/germany/bundesliga/35#id:77333",
    "Serie A": "https://www.sofascore.com/es/torneo/futbol/italy/serie-a/23#id:76457",
    "Ligue 1": "https://www.sofascore.com/es/torneo/futbol/france/ligue-1/34#id:77356",
    "Brasileirao Betano": "https://www.sofascore.com/es/torneo/futbol/brazil/brasileirao-serie-a/325#id:72034",
    "Liga 1": "https://www.sofascore.com/es/torneo/futbol/peru/liga-1/406#id:70962",
    "Mozzart Bet Superliga" : "https://www.sofascore.com/es/torneo/futbol/serbia/mozzart-bet-superliga/210#id:76909"
}

# Selector de torneo en la barra lateral
torneo_seleccionado = st.sidebar.selectbox("Selecciona un Torneo:", list(urls_torneos.keys()))
url_actual = urls_torneos[torneo_seleccionado]

# Control de ejecución mediante botones
ejecutar = st.sidebar.toggle("▶️ Iniciar Automatización (Loop 10s)", value=False)

# Mapeo visual en Dashboard
col1, col2 = st.columns(2)
metric_nuevos = col1.empty()
metric_estado = col2.empty()
log_box = st.container(border=True)
log_box.write("### 📄 Logs de Extracción")

# ===========================================
# 🔄 BUCLE DE EJECUCIÓN CONTINUA
# ===========================================
if ejecutar:
    metric_estado.metric("Estado del Proceso", "🟢 Corriendo...")
    
    with st.spinner(f"Cargando torneo: {torneo_seleccionado}..."):
        try:
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

            # 🔗 EXTRAER ENLACES DE PARTIDOS
            data_partidos = []
            # Para fines de demostración rápida en el loop de Streamlit, limitamos el barrido de equipos o procesamos directo
            for d in data_equipos[:3]: # Limitado a los 3 primeros equipos para agilizar el refresco web, remover '[:3]' si deseas procesar todo
                try:
                    driver.set_page_load_timeout(30)
                    driver.get(d['enlace'])
                    secciones = driver.find_elements(By.XPATH, "//div[contains(@class,'card-component')]")
                    for sec in secciones:
                        partidos = sec.find_elements(By.XPATH, ".//a[contains(@href, '/football/match/')]")
                        for p in partidos:
                            data_partidos.append({"Equipo Base": d['equipo'], "Enlace Partido": p.get_attribute("href")})
                except Exception as e:
                    continue

            # 🧹 LIMPIAR DUPLICADOS
            if data_partidos:
                df_final = pd.DataFrame(data_partidos).drop_duplicates(subset=["Equipo Base", "Enlace Partido"])
            else:
                df_final = pd.DataFrame(columns=["Equipo Base", "Enlace Partido"])

            # 🧠 VERIFICAR CONTRA SQL SERVER
            try:
                query = f"SELECT [Equipo Base], [Enlace Partido] FROM dbo.{table_name}"
                df_existentes = pd.read_sql(query, engine)
                existentes = set(zip(df_existentes["Equipo Base"].astype(str), df_existentes["Enlace Partido"].astype(str)))
            except:
                existentes = set()

            df_final["Clave Unica"] = list(zip(df_final["Equipo Base"].astype(str), df_final["Enlace Partido"].astype(str)))
            df_nuevos = df_final[~df_final["Clave Unica"].isin(existentes)]
            
            metric_nuevos.metric("Partidos Nuevos Encontrados", len(df_nuevos))

            # 📊 PROCESAR PARTIDOS NUEVOS
            estadisticas = []
            if not df_nuevos.empty:
                data_partidos_nuevos = df_nuevos.to_dict('records')
                
                # Iteramos por los nuevos partidos encontrados
                for i, partido in enumerate(data_partidos_nuevos, start=1):
                    log_box.write(f"🔎 Procesando {i}/{len(data_partidos_nuevos)}: {partido['Enlace Partido']}")
                    
                    try:
                        driver.get(partido["Enlace Partido"])
                        time.sleep(2)
                    except:
                        continue

                    # --- Extracción de Campos de Encabezado ---
                    try: fecha = driver.find_elements(By.XPATH, "//span[@class='textStyle_display.micro c_neutrals.nLv3 lh_1']")[0].text
                    except: fecha = None
                    try: competicion = driver.find_element(By.XPATH, "//div[contains(@class,'d_flex') and contains(@class,'hover:bg_surface.s2')]//span[contains(@class,'textStyle_display.micro')]").text
                    except: competicion = None
                    try:
                        equipos_p = driver.find_elements(By.XPATH, "//bdi[contains(@class,'textStyle_display.medium')]")
                        local = equipos_p[0].text; visita = equipos_p[1].text
                    except: local, visita = None, None
                    try:
                        marcadores = driver.find_elements(By.XPATH, "//span[contains(@class,'textStyle_display.extraLarge') and contains(@class,'pos_relative')]")
                        marcador_local = marcadores[0].text; marcador_visita = marcadores[1].text
                    except: marcador_local = marcador_visita = None

                    # --- Marcador de Primer Tiempo (1T) ---
                    goles_1T_local, goles_1T_visita, texto = None, None, "DES 0 - 0"
                    try:
                        bloque = driver.find_element(By.XPATH, "//div[contains(@class,'mdDown:pb_sm') and contains(@class,'md:pb_md')]")
                        segundo_div = bloque.find_element(By.XPATH, "( .//div[contains(@class,'d_flex') and contains(@class,'py_md') and contains(@class,'px_lg') and contains(@class,'gap_lg') and contains(@class,'w_100%')] )[last()]")
                        span = segundo_div.find_element(By.XPATH, ".//span[contains(@class,'textStyle_display.micro') and contains(@class,'ta_center')]")
                        texto = span.text.strip()
                        numeros = re.findall(r'\d+', texto)
                        if len(numeros) == 2:
                            goles_1T_local, goles_1T_visita = map(int, numeros)
                    except: pass

                    # Función interna adaptada
                    def extraer_y_guardar(tipo_periodo):
                        summary = driver.find_elements(By.XPATH, "//div[contains(@class, 'bg_surface') and contains(@class, 's1') and contains(@class, 'px_sm')]")
                        for s in summary:
                            try: titulo = s.find_element(By.XPATH, ".//span[contains(@class, 'textStyle_display.medium')]").text
                            except: titulo = "Sin título"
                            
                            stats = s.find_elements(By.XPATH, ".//div[contains(@class, 'd_flex') and contains(@class, 'flex-d_column') and contains(@class, 'ai_center') and contains(@class, 'jc_center')]")
                            for st in stats:
                                try: local_val = st.find_element(By.XPATH, ".//div[contains(@class, 'jc_space-between')]//bdi[1]/span").text
                                except: local_val = None
                                try: nombre = st.find_element(By.XPATH, ".//div[contains(@class, 'jc_space-between')]//span[contains(@class, 'textStyle_assistive') and contains(@class, 'c_neutrals.nLv1')]").text
                                except: nombre = None
                                try: visita_val = st.find_element(By.XPATH, ".//div[contains(@class, 'jc_space-between')]//bdi[last()]/span").text
                                except: visita_val = None

                                estadisticas.append({
                                    "Enlace Partido": partido['Enlace Partido'], "Tiempo" : texto, "Fecha": fecha, "Competición": competicion,
                                    "Equipo Base": partido['Equipo Base'], "Equipo Local": local, "Equipo Visitante": visita,
                                    "Marcador Local": marcador_local, "Marcador Visitante": marcador_visita, "1T Marcador Local" : goles_1T_local,
                                    "1T Marcador Visita" : goles_1T_visita, "Bloque": titulo, "Métrica": nombre, "Valor Local": local_val,
                                    "Valor Visitante": visita_val, "Periodo": tipo_periodo
                                })

                    # --- Extracción General ---
                    try:
                        driver.find_element(By.XPATH, "//button[contains(@data-testid, 'tab-statistics')]").click()
                        time.sleep(2)
                        extraer_y_guardar("General")
                    except: pass

                    # --- Extracción 1T ---
                    try:
                        driver.find_element(By.XPATH, "//button[contains(@data-testid, 'tab-1ST')]").click()
                        time.sleep(2)
                        extraer_y_guardar("1er Tiempo")
                    except: pass

                # ===================================================
                # PROCESAMIENTO DF Y CARGA A BASE DE DATOS SQL SERVER
                # ===================================================
                if estadisticas:
                    df = pd.DataFrame(estadisticas)
                    df["Periodo"] = df["Periodo"].astype(str).str.lower().str.strip()
                    df = df[df["Periodo"].str.contains("general|tiempo", regex=True, na=False)]

                    # PIVOT GENERAL
                    df_general = df[df["Periodo"].str.contains("general", na=False)]
                    df_info = df_general[["Enlace Partido","Tiempo", "Fecha", "Competición", "Equipo Base", "Equipo Local", "Equipo Visitante", "Marcador Local", "Marcador Visitante", "1T Marcador Local", "1T Marcador Visita"]].drop_duplicates().reset_index(drop=True)
                    
                    if df_general["Métrica"].notna().any():
                        df_pivot_general = df_general.pivot_table(index=["Enlace Partido", "Tiempo","Fecha", "Competición", "Equipo Base", "Equipo Local", "Equipo Visitante", "Marcador Local","Marcador Visitante", "1T Marcador Local", "1T Marcador Visita"], columns="Métrica", values=["Valor Local", "Valor Visitante"], aggfunc="first")
                        df_pivot_general.columns = [f"{v}_{m}_General" for v, m in df_pivot_general.columns]
                        df_pivot_general = df_pivot_general.reset_index()
                    else:
                        df_pivot_general = pd.DataFrame(columns=df_info.columns)

                    df_pivot_general = pd.merge(df_info, df_pivot_general, on=["Enlace Partido", "Tiempo","Fecha", "Competición", "Equipo Base", "Equipo Local", "Equipo Visitante", "Marcador Local", "Marcador Visitante", "1T Marcador Local", "1T Marcador Visita"], how="left")

                    # PIVOT PRIMER TIEMPO
                    df_pt = df[df["Periodo"].str.contains("tiempo", na=False)]
                    if df_pt["Métrica"].notna().any():
                        df_pivot_pt = df_pt.pivot_table(index=["Enlace Partido", "Tiempo","Fecha", "Competición", "Equipo Base", "Equipo Local", "Equipo Visitante", "Marcador Local", "Marcador Visitante", "1T Marcador Local", "1T Marcador Visita"], columns="Métrica", values=["Valor Local", "Valor Visitante"], aggfunc="first")
                        df_pivot_pt.columns = [f"{v}_{m}_PT" for v, m in df_pivot_pt.columns]
                        df_pivot_pt = df_pivot_pt.reset_index()
                    else:
                        df_pivot_pt = df_pt[["Enlace Partido", "Tiempo","Fecha", "Competición", "Equipo Base", "Equipo Local", "Equipo Visitante", "Marcador Local", "Marcador Visitante", "1T Marcador Local", "1T Marcador Visita"]].drop_duplicates().reset_index(drop=True)

                    # UNIFICACIÓN FINAL Y ESCRITURA
                    df_final_db = pd.merge(df_pivot_general, df_pivot_pt, on=["Enlace Partido","Tiempo", "Fecha", "Competición", "Equipo Base", "Equipo Local", "Equipo Visitante", "Marcador Local", "Marcador Visitante", "1T Marcador Local", "1T Marcador Visita"], how="outer")
                    
                    df_final_db["Fecha"] = pd.to_datetime(df_final_db["Fecha"], errors="coerce", dayfirst=True)
                    df_final_db["Marcador Local"] = pd.to_numeric(df_final_db["Marcador Local"], errors="coerce")
                    df_final_db["Marcador Visitante"] = pd.to_numeric(df_final_db["Marcador Visitante"], errors="coerce")

                    with engine.begin() as conn:
                        df_final_db.to_sql(table_name, con=conn, schema="dbo", if_exists="append", index=False)
                        log_box.success(f"💾 Se insertaron {len(df_final_db)} registros nuevos en SQL Server.")
            else:
                log_box.info("✅ No hay partidos nuevos en este ciclo.")

        except Exception as main_err:
            log_box.error(f"⚠️ Error general en el bucle: {main_err}")

    # ===========================================
    # ⏳ CONTROL DEL REFRESCO AUTOMÁTICO (10 SEGUNDOS)
    # ===========================================
    st.write("⏱️ Esperando 10 segundos para la siguiente ejecución...")
    time.sleep(10)
    st.rerun()  # Reinicia el script y vuelve a evaluar/extraer

else:
    metric_estado.metric("Estado del Proceso", "🔴 Detenido")
    st.info("Activa el switch de la barra lateral para iniciar el raspado continuo.")
