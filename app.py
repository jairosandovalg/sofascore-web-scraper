import streamlit as st
import pandas as pd
import numpy as np
import asyncio
import time
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Sofascore Scraper Playwright", page_icon="⚽", layout="wide")
st.title("⚽ Extractor de Estadísticas en Tiempo Real (Playwright Pro)")
st.write("Esta versión utiliza Playwright Asíncrono + Stealth para evadir los bloqueos de Cloudflare en la nube.")

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

# --- DASHBOARD PRINCIPAL ---
col1, col2 = st.columns(2)
metric_filas = col1.empty()
metric_estado = col2.empty()

log_box = st.container(border=True)
log_box.write("### 📄 Logs del Navegador (Playwright Stealth)")

st.write("### 📊 Datos Extraídos en Vivo")
tabla_datos = st.empty()

tabla_datos.dataframe(st.session_state.datos_scraping, use_container_width=True)
metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))

# ===========================================
# 🤖 FUNCIÓN ASÍNCRONA DE SCRAPING CON PLAYWRIGHT
# ===========================================
async def correr_scraping_playwright(url_liga):
    estadisticas = []
    
    async with async_playwright() as p:
        log_box.write("🚀 Iniciando navegador invisible en la nube...")
        # Levantamos Chromium emulando un perfil totalmente humano
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox", 
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled"
        ])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        page = await context.new_page()
        # Activamos el modo Stealth para evadir Cloudflare
        await stealth_async(page)
        
        try:
            log_box.write(f"🌍 Accediendo a: **{torneo_seleccionado}**")
            await page.goto(url_liga, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000) # Pausa táctica humana
            
            # Esperamos dinámicamente a que los enlaces de equipos aparezcan
            log_box.write("🔎 Buscando estructura de equipos...")
            await page.wait_for_selector("a[href*='/team/']", timeout=15000)
            
            # Extraer los elementos del DOM
            enlaces_equipos = await page.query_selector_all("a[href*='/team/']")
            data_equipos = []
            
            for selector in enlaces_equipos:
                href = await selector.get_attribute("href")
                if 'football/team/' in href or '/team/html/' in href:
                    span = await selector.query_selector("span")
                    if span:
                        texto_equipo = await span.inner_text()
                        texto_equipo = texto_equipo.strip()
                        if texto_equipo and not texto_equipo.isdigit():
                            data_equipos.append({"equipo": texto_equipo, "enlace": "https://www.sofascore.com" + href if href.startswith("/") else href})
            
            # Limpieza rápida de duplicados
            df_eq_temp = pd.DataFrame(data_equipos).drop_duplicates(subset=["equipo"])
            data_equipos = df_eq_temp.to_dict('records') if not df_eq_temp.empty else []
            
            log_box.write(f"✅ ¡Se localizaron **{len(data_equipos)}** equipos únicos!")
            
            # 🔗 PASO 2: EXTRAER PARTIDOS DEL PRIMER EQUIPO DETECTADO
            if data_equipos:
                equipo_prueba = data_equipos[0]
                log_box.write(f"⚽ Entrando al perfil de: *{equipo_prueba['equipo']}*")
                await page.goto(equipo_prueba["enlace"], wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                
                await page.wait_for_selector("a[href*='/match/']", timeout=10000)
                enlaces_partidos = await page.query_selector_all("a[href*='/match/']")
                
                urls_partidos = []
                for p_selector in enlaces_partidos:
                    href_p = await p_selector.get_attribute("href")
                    if href_p and '/match/' in href_p:
                        full_url = "https://www.sofascore.com" + href_p if href_p.startswith("/") else href_p
                        urls_partidos.append(full_url)
                
                urls_partidos = list(set(urls_partidos)) # Unicos
                
                # 📊 PASO 3: ENTRAR AL PARTIDO Y EXTRAER MÉTRICAS
                if urls_partidos:
                    partido_url = urls_partidos[0]
                    log_box.write(f"🔎 Extrayendo estadísticas de: {partido_url}")
                    await page.goto(partido_url, wait_until="domcontentloaded")
                    await page.wait_for_timeout(4000)
                    
                    # Intentar capturar metadatos básicos
                    try:
                        bdis = await page.query_selector_all("bdi")
                        local = await bdis[0].inner_text() if len(bdis) > 0 else "Local"
                        visita = await bdis[1].inner_text() if len(bdis) > 1 else "Visitante"
                    except:
                        local, visita = "Local", "Visitante"
                        
                    # Clic en el botón de estadísticas si está presente
                    try:
                        btn_stats = await page.query_selector("button[data-testid='tab-statistics']")
                        if btn_stats:
                            await btn_stats.click()
                            await page.wait_for_timeout(2000)
                            
                            # Mapear bloques de métricas
                            bloques = await page.query_selector_all("div[class*='bg_surface']")
                            for b in bloques:
                                filas_stats = await b.query_selector_all("div[class*='d_flex'][class*='flex-d_column']")
                                for fila in filas_stats:
                                    try:
                                        span_metric = await fila.query_selector("span[class*='textStyle_assistive']")
                                        if span_metric:
                                            nombre_m = await span_metric.inner_text()
                                            spans_valores = await fila.query_selector_all("bdi span")
                                            local_v = await spans_valores[0].inner_text() if len(spans_valores) > 0 else None
                                            visita_v = await spans_valores[-1].inner_text() if len(spans_valores) > 0 else None
                                            
                                            estadisticas.append({
                                                "Fecha Extracción": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                                "Local": local.strip(), "Visitante": visita.strip(),
                                                "Métrica": nombre_m.strip(), "Local Valor": local_v, "Visitante Valor": visita_v
                                            })
                                    except: continue
                    except Exception as e:
                        log_box.warning(f"⚠️ Estructura interna de estadísticas no disponible o cambiada: {e}")
            
        except Exception as err:
            log_box.error(f"❌ Error interno en Playwright: {err}")
        finally:
            await browser.close()
            
    return estadisticas

# ===========================================
# 🔄 GESTOR DEL CICLO DEL BUCLE (STREAMLIT)
# ===========================================
if ejecutar:
    metric_estado.metric("Estado del Scraper", "🟢 Buscando datos...")
    
    # Ejecutamos el entorno asíncrono de Playwright
    nuevas_metricas = asyncio.run(correr_scraping_playwright(url_actual))
    
    if nuevas_metricas:
        df_nuevas = pd.DataFrame(nuevas_metricas)
        st.session_state.datos_scraping = pd.concat([st.session_state.datos_scraping, df_nuevas], ignore_index=True).drop_duplicates(subset=["Local", "Visitante", "Métrica"])
        log_box.success("✨ ¡Tabla de datos en vivo actualizada!")
    else:
        log_box.info("ℹ️ Ciclo completado sin nuevas filas parseadas.")
        
    # Re-pitar dataframe
    tabla_datos.dataframe(st.session_state.datos_scraping, use_container_width=True)
    metric_filas.metric("Filas en Memoria", len(st.session_state.datos_scraping))
    
    st.write("⏱️ Esperando 10 segundos para reiniciar ciclo con Playwright...")
    time.sleep(10)
    st.rerun()
else:
    metric_estado.metric("Estado del Scraper", "🔴 Detenido")
    st.info("Utiliza el switch de la barra izquierda para arrancar el scraping continuo.")
