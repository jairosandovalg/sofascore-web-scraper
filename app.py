import streamlit as st
import pandas as pd
import os
import json
import subprocess
from playwright.sync_api import sync_playwright

# ===========================================
# 📦 AUTO-INSTALACIÓN DE NAVEGADORES
# ===========================================
try:
    import playwright
except ImportError:
    pass

@st.cache_resource
def verificar_e_instalar_browsers():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        return "✅ Motor de navegación validado en el sistema."
    except Exception as e:
        return f"⚠️ Nota de inicialización: {e}"

status_instalacion = verificar_e_instalar_browsers()

# ===========================================
# 💻 CONFIGURACIÓN DE LA PÁGINA STREAMLIT
# ===========================================
st.set_page_config(page_title="Extractor Live API", page_icon="⚽", layout="wide")
st.title("⚽ Fase 1: Extracción por Intercepción de Tráfico (Anti-403)")
st.info(status_instalacion)

# Usamos la URL raíz internacional, que tiene menor tasa de bloqueo inicial
url_objetivo = st.text_input("URL de Acceso Base:", "https://www.sofascore.com/es/")
btn_conectar = st.button("🛰️ Interceptar API de Partidos en Vivo")

# ===========================================
# ⚡ EJECUCIÓN SÍNCRONA Y FILTRADO DE RED
# ===========================================
if btn_conectar:
    st.write("⏳ Levantando contenedor de navegación camuflado...")
    json_capturado = None
    
    try:
        with sync_playwright() as p:
            # Forzamos argumentos que deshabilitan la detección automatizada
            browser = p.chromium.launch(
                headless=True, 
                args=[
                    "--no-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            # Forzamos una huella digital (fingerprint) de escritorio común
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="es-ES",
                timezone_id="America/Lima"
            )
            
            page = context.new_page()
            
            # 🧠 FUNCIÓN DE INTERCEPCIÓN: Escucha los datos puros que viajan por detrás
            def capturar_trafico(response):
                global json_capturado
                # Filtramos la URL de la API interna de Sofascore que contiene los eventos en directo
                if "api/v1/sport/football/events/live" in response.url:
                    try:
                        text_data = response.text()
                        json_capturado = json.loads(text_data)
                        st.success("🎯 ¡API de eventos en directo interceptada con éxito desde el tráfico de red!")
                    except Exception as json_err:
                        pass

            # Activamos el radar de respuestas de red
            page.on("response", capturar_trafico)
            
            st.write(f"🌍 Conectando de forma silenciosa a `{url_objetivo}` ...")
            page.goto(url_objetivo, timeout=60000, wait_until="networkidle")
            
            # Pausa humana de 5 segundos para permitir el flujo completo de peticiones asíncronas
            page.wait_for_timeout(5000)
            
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Error en el puente de comunicación: {err}")

    # ===========================================
    # 📊 PROCESAMIENTO Y RENDERIZADO DE RESULTADOS
    # ===========================================
    st.write("### 🎛️ Resultado del Análisis de Red")
    
    if json_capturado and "events" in json_capturado:
        partidos_en_vivo = []
        
        # Parseamos el JSON puro que obtuvimos de la red
        for evento in json_capturado["events"]:
            try:
                id_evento = evento.get("id")
                torneo = evento.get("tournament", {}).get("name", "Liga")
                local = evento.get("homeTeam", {}).get("name", "Local")
                visita = evento.get("awayTeam", {}).get("name", "Visitante")
                score_l = evento.get("homeScore", {}).get("current", 0)
                score_v = evento.get("awayScore", {}).get("current", 0)
                minuto = evento.get("status", {}).get("description", "Live")
                
                partidos_en_vivo.append({
                    "ID Evento": id_evento,
                    "Competición": torneo,
                    "Partido en Directo": f"🏟️ {local} ({score_l}) vs ({score_v}) {visita}",
                    "Minuto / Estado": minuto
                })
            except:
                continue
        
        if partidos_en_vivo:
            df_live = pd.DataFrame(partidos_en_vivo)
            st.write(f"✅ Se encontraron **{len(df_live)}** partidos activos en este instante.")
            st.dataframe(df_live, use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ El JSON se capturó vacío o no contiene eventos activos de fútbol en este momento.")
            
    else:
        st.error("❌ No se detectó la llamada de la API en este ciclo. Cloudflare mantiene el bloqueo 403. Espera unos segundos e intenta reconectar.")
