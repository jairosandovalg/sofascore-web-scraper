import streamlit as st
import pandas as pd
import asyncio
import json
import time
from playwright.async_api import async_playwright
from playwright_stealth import stealth

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Detector de Anomalías - Live", page_icon="📈", layout="wide")
st.title("🚀 Fase 1: Conexión con Partidos en Vivo (Sofascore API)")
st.write("Este módulo conecta Streamlit con la API oculta de Sofascore mediante Playwright para capturar los eventos en directo.")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración")
ejecutar = st.sidebar.toggle("▶️ Escanear Partidos en Vivo (Loop 10s)", value=False)

# --- CONTENEDORES DE INTERFAZ ---
col1, col2 = st.columns(2)
metric_partidos = col1.empty()
metric_status = col2.empty()

log_box = st.container(border=True)
log_box.write("### 📄 Logs de Intercepción de Red")

st.write("### ⚽ Partidos en Directo Detectados")
tabla_partidos = st.empty()

# ===========================================
# 🤖 FUNCIÓN ASÍNCRONA: CAPTURAR API DE SOFASCORE
# ===========================================
async def capturar_partidos_en_vivo():
    json_data = None
    
    async with async_playwright() as p:
        log_box.write("🛰️ Iniciando navegador en segundo plano...")
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        stealth(page) # Evasión de bloqueos Cloudflare
        
        # 🧠 FUNCIÓN INTERNA: Captura las respuestas de red buscando el endpoint de eventos "live"
        async def interceptar_respuesta(response):
            nonlocal json_data
            # Buscamos la URL de la API de Sofascore que trae los partidos del día en vivo
            if "api/v1/sport/football/events/live" in response.url:
                try:
                    log_box.success("🎯 ¡API de Partidos en Vivo Detectada con éxito!")
                    text = await response.text()
                    json_data = json.loads(text)
                except Exception as e:
                    log_box.error(f"❌ Error al decodificar el JSON de la API: {e}")

        # Escuchar todas las respuestas de red del navegador
        page.on("response", interceptar_respuesta)
        
        try:
            log_box.write("🌍 Navegando a la sección en vivo de Sofascore...")
            # Vamos directo a la url de partidos en directo
            await page.goto("https://www.sofascore.com/es/futbol/en-vivo", timeout=60000, wait_until="commit")
            
            # Le damos 5 segundos para que cargue el script de la página y dispare la petición de red
            await page.wait_for_timeout(5000)
            
        except Exception as err:
            log_box.error(f"❌ Error durante la navegación: {err}")
        finally:
            await browser.close()
            
    return json_data

# ===========================================
# 🔄 BUCLE DE CONTROL (STREAMLIT LOOP)
# ===========================================
if ejecutar:
    metric_status.metric("Estado de la Conexión", "🟢 Conectado y Buscando...")
    
    # Ejecutar la captura asíncrona
    datos_api = asyncio.run(capturar_partidos_en_vivo())
    
    lista_procesada = []
    
    if datos_api and "events" in datos_api:
        # Recorremos el JSON puro enviado por Sofascore
        for evento in datos_api["events"]:
            try:
                id_partido = evento.get("id")
                competicion = evento.get("tournament", {}).get("name", "Desconocida")
                equipo_local = evento.get("homeTeam", {}).get("name", "Local")
                equipo_visita = evento.get("awayTeam", {}).get("name", "Visitante")
                
                # Datos del marcador en vivo
                marcador_local = evento.get("homeScore", {}).get("current", 0)
                marcador_visita = evento.get("awayScore", {}).get("current", 0)
                
                # Minuto actual del partido
                minuto = evento.get("status", {}).get("description", "Not Started")
                
                lista_procesada.append({
                    "ID Evento": id_partido,
                    "Competición": competicion,
                    "Partido": f"🏟️ {equipo_local} [{marcador_local}] vs [{marcador_visita}] {equipo_visita}",
                    "Tiempo / Estado": minuto
                })
            except Exception as item_err:
                continue

    # Actualizar la pantalla con los datos capturados
    if lista_procesada:
        df_partidos = pd.DataFrame(lista_procesada)
        tabla_partidos.dataframe(df_partidos, use_container_width=True, hide_index=True)
        metric_partidos.metric("Partidos en Vivo Capturados", len(df_partidos))
    else:
        metric_partidos.metric("Partidos en Vivo Capturados", 0)
        log_box.warning("⚠️ No se pudieron extraer partidos en este ciclo. Verificando bloqueos de IP...")

    # Pausa e inicio del siguiente ciclo
    st.write("⏱️ Esperando 10 segundos para actualizar la lista de partidos en directo...")
    time.sleep(10)
    st.rerun()

else:
    metric_status.metric("Estado de la Conexión", "🔴 Detenido")
    st.info("Activa el switch del Panel de Control para enlazar la aplicación con los eventos en directo.")
