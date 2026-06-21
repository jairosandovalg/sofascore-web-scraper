import streamlit as st
import os
import subprocess
from playwright.sync_api import sync_playwright
# ✅ Corrección de importación para evitar el error 'module' object is not callable
from playwright_stealth import stealth_sync

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
st.set_page_config(page_title="Verificación Sofascore", page_icon="⚽", layout="wide")
st.title("⚽ Fase 1: Corrección de Ruta y Filtro Live")
st.info(status_instalacion)

url_objetivo = st.text_input("URL Base de Partidos:", "https://www.sofascore.com/es/futbol")
btn_conectar = st.button("🔌 Conectar, Filtrar 'En Vivo' y Tomar Captura")

# ===========================================
# ⚡ EJECUCIÓN SÍNCRONA DIRECTA
# ===========================================
if btn_conectar:
    st.write("⏳ Levantando navegador limpio en segundo plano...")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1400, "height": 900}
            )
            page = context.new_page()
            
            # ✅ Corrección de ejecución aplicando stealth_sync
            stealth_sync(page)
            
            st.write(f"🌍 Accediendo a la URL real: `{url_objetivo}` ...")
            page.goto(url_objetivo, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            st.write("🎯 Buscando y aplicando el filtro de partidos 'En vivo'...")
            
            # Buscamos el filtro "En vivo" o "Live" en la barra de navegación interna de Sofascore
            filtro_live = page.get_by_text("En vivo", exact=True)
            
            if filtro_live.count() > 0:
                filtro_live.first.click()
                st.write("✅ Filtro 'En vivo' pulsado. Esperando actualización de la cartelera...")
                page.wait_for_timeout(5000)
            else:
                st.warning("⚠️ No se localizó el botón de texto plano 'En vivo'. Tomando captura general...")

            st.success("🎉 Ciclo completado. Procesando captura de pantalla final...")
            
            # Tomamos la captura
            screenshot_bytes = page.screenshot(full_page=False)
            
            st.image(screenshot_bytes, caption="Cartelera real capturada desde el servidor", use_container_width=True)
            st.write(f"**Título actual de la ventana:** {page.title()}")
            
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Ocurrió un inconveniente al interactuar con la página: {err}")
