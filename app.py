import streamlit as st
import os
import subprocess
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

# ===========================================
# 📦 AUTO-INSTALACIÓN DE NAVEGADORES (MANTENER PARA LA NUBE)
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

# 💡 Corregido: Apuntamos a la URL real que no da Error 404
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
            stealth(page)
            
            st.write(f"🌍 Accediendo a la URL real: `{url_objetivo}` ...")
            page.goto(url_objetivo, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            st.write("🎯 Buscando y aplicando el filtro de partidos 'En vivo'...")
            
            # Intentamos hacer clic en el botón de filtro "En vivo" usando selectores de texto comunes
            # Sofascore suele tener un botón o pestaña que contiene el texto "En vivo" o "Live"
            filtro_live = page.get_by_text("En vivo", exact=True)
            
            if filtro_live.count() > 0:
                filtro_live.first.click()
                st.write("✅ Filtro 'En vivo' pulsado. Esperando actualización de la cartelera...")
                page.wait_for_timeout(4000)
            else:
                st.warning("⚠️ No se localizó el botón de texto plano 'En vivo'. Intentando capturar la pantalla por defecto...")

            st.success("🎉 Ciclo completado. Procesando captura de pantalla final...")
            
            # Tomamos la foto de la pantalla para verificar visualmente que cargaron los partidos en juego
            screenshot_bytes = page.screenshot(full_page=False)
            
            st.image(screenshot_bytes, caption="Cartelera real capturada desde el servidor", use_container_width=True)
            st.write(f"**Título actual de la ventana:** {page.title()}")
            
            browser.close()
            
    except Exception as err:
        st.error(f"❌ Ocurrió un inconveniente al interactuar con la página: {err}")
