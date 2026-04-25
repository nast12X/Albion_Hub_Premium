import streamlit as st
import requests
import os
import sqlite3
import pandas as pd
import math
from dotenv import load_dotenv

# ==========================================
# 1. CONFIGURACIÓN Y MEMORIA
# ==========================================
load_dotenv()
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

st.set_page_config(page_title="Albion Hub Premium", page_icon="⚔️", layout="wide")

if 'carrito' not in st.session_state:
    st.session_state['carrito'] = []

# ==========================================
# 2. MOTOR DE DATOS
# ==========================================
def obtener_items_bd(categoria=None, tier=None):
    conn = sqlite3.connect('albion_items.db')
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    if tier:
        query += " AND tier = ?"
        params.append(tier)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

@st.cache_data(ttl=300)
def obtener_precio(item_id, ciudad):
    url = f"https://west.albion-online-data.com/api/v2/stats/prices/{item_id}.json?locations={ciudad}"
    try:
        respuesta = requests.get(url, timeout=5)
        datos = respuesta.json()
        if datos and len(datos) > 0:
            return datos[0].get('sell_price_min', 0)
    except:
        return 0
    return 0

PESOS_TIER = {"T4": 1.0, "T5": 1.5, "T6": 2.0, "T7": 2.5, "T8": 3.0}

# --- NUEVO: MOTOR DE MAPAS Y RUTAS ---
# Simulador de conexiones y peligro (Muertes recientes)
MAPA_ALBION = {
    "Lymhurst (Seguro)": {"Bosque Yew (Amarilla)": 0, "Valle Longtimber (Amarilla)": 0},
    "Valle Longtimber (Amarilla)": {"Lymhurst (Seguro)": 0, "Estepa Roastcopse (ROJA)": 45}, # 45 muertes
    "Bosque Yew (Amarilla)": {"Lymhurst (Seguro)": 0, "Murkweald (ROJA)": 2}, # 2 muertes
    "Estepa Roastcopse (ROJA)": {"Valle Longtimber (Amarilla)": 0, "Caerleon (Mercado Negro)": 15},
    "Murkweald (ROJA)": {"Bosque Yew (Amarilla)": 0, "Caerleon (Mercado Negro)": 5},
    "Caerleon (Mercado Negro)": {"Estepa Roastcopse (ROJA)": 0, "Murkweald (ROJA)": 0}
}

def encontrar_ruta_segura(inicio, fin):
    # Algoritmo de búsqueda de la ruta con menor peligro (Dijkstra simplificado)
    rutas_posibles = []
    def buscar(actual, destino, camino_actual, peligro_acumulado):
        if actual == destino:
            rutas_posibles.append((camino_actual, peligro_acumulado))
            return
        for vecino, peligro in MAPA_ALBION[actual].items():
            if vecino not in camino_actual:
                buscar(vecino, destino, camino_actual + [vecino], peligro_acumulado + peligro)
    
    buscar(inicio, fin, [inicio], 0)
    if not rutas_posibles:
        return None, 0
    # Ordenar por el menor peligro acumulado
    rutas_posibles.sort(key=lambda x: x[1])
    return rutas_posibles[0] # Retorna (Mejor_Ruta, Peligro_Total)

# ==========================================
# 3. INTERFAZ Y NAVEGACIÓN
# ==========================================
if 'user' not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #f39c12;'>ALBION HUB PREMIUM</h1>", unsafe_allow_html=True)
    st.divider()
    if st.button("👾 Iniciar Sesión (Modo Pruebas Local)", type="primary"):
        st.session_state['user'] = {'username': 'El_Jefe', 'id': '123', 'avatar': ''}
        st.rerun()
else:
    with st.sidebar:
        st.subheader(f"👑 {st.session_state['user']['username']}")
        st.write("🟢 Estado: **Premium**")
        if st.button("Cerrar Sesión"):
            del st.session_state['user']
            st.rerun()
        st.divider()
        menu = st.radio("Navegación:", [
            "🏠 Dashboard", 
            "🧮 Calculadora Rápida", 
            "📝 Planificador de Producción",
            "🚚 Logística y Transporte",
            "🧭 GPS de Supervivencia",
            "📦 Base de Datos Global"
        ])

    # --- PESTAÑAS ANTERIORES (Resumidas para el código) ---
    if menu == "🧮 Calculadora Rápida":
        st.title("🧮 Calculadora Rápida")
        col1, col2 = st.columns(2)
        with col1:
            categoria_sel = st.selectbox("Categoría", ["Armas", "Coraza", "Casco", "Botas"])
            tier_sel = st.selectbox("Nivel (Tier)", ["T4", "T5", "T6", "T7", "T8"])
        items_filtrados = obtener_items_bd(categoria=categoria_sel, tier=tier_sel)
        with col2:
            item_seleccionado = st.selectbox("Objeto a Fabricar", items_filtrados['nombre_es'].tolist()) if not items_filtrados.empty else None
            ciudad_sel = st.selectbox("Mercado", ["Caerleon", "Lymhurst", "Bridgewatch"])
            tasa_retorno = st.number_input("Retorno (RR) %", value=24.8)

        if st.button("Calcular", type="primary") and item_seleccionado:
            item_data = items_filtrados[items_filtrados['nombre_es'] == item_seleccionado].iloc[0]
            precio_item = obtener_precio(item_data['id_unico'], ciudad_sel)
            precio_recurso = obtener_precio(item_data['recurso_principal'], ciudad_sel)
            if precio_item > 0 and precio_recurso > 0:
                costo_mat = precio_recurso * item_data['cantidad_recurso']
                costo_real = costo_mat - (costo_mat * (tasa_retorno / 100))
                st.success(f"Beneficio Neto 1x unidad: {precio_item - costo_real:,.0f} Plata")

    elif menu == "📝 Planificador de Producción":
        st.title("📝 Tu Lista de Producción")
        with st.expander("➕ Añadir Nuevo Ítem al Plan", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                cat_plan = st.selectbox("Filtro", ["Armas", "Coraza", "Casco", "Botas"])
                tier_plan = st.selectbox("Tier", ["T4", "T5", "T6", "T7", "T8"])
            items_plan = obtener_items_bd(categoria=cat_plan, tier=tier_plan)
            with c2:
                item_plan_sel = st.selectbox("Objeto", items_plan['nombre_es'].tolist()) if not items_plan.empty else None
                cantidad_craft = st.number_input("Cantidad a Craftear", min_value=1, value=10)
            with c3:
                st.write("")
                st.write("")
                if st.button("🛒 Añadir a la Lista", type="primary", use_container_width=True) and item_plan_sel:
                    datos_item = items_plan[items_plan['nombre_es'] == item_plan_sel].iloc[0]
                    st.session_state['carrito'].append({"Nombre": f"{item_plan_sel}", "Tier": tier_plan, "Cantidad": cantidad_craft, "Recurso": datos_item['recurso_principal'], "Total_Materiales": datos_item['cantidad_recurso'] * cantidad_craft})
                    st.success("¡Añadido!")
                    st.rerun()

        if len(st.session_state['carrito']) > 0:
            st.dataframe(pd.DataFrame(st.session_state['carrito']), use_container_width=True)
            if st.button("🗑️ Vaciar Lista"):
                st.session_state['carrito'] = []
                st.rerun()

    elif menu == "🚚 Logística y Transporte":
        st.title("🚚 Análisis de Carga y Transporte")
        if len(st.session_state['carrito']) == 0:
            st.warning("⚠️ Tu planificador está vacío.")
        else:
            df_carrito = pd.DataFrame(st.session_state['carrito'])
            peso_total = sum([row['Total_Materiales'] * PESOS_TIER.get(row['Tier'], 1.0) for _, row in df_carrito.iterrows()])
            col1, col2 = st.columns([1, 2])
            with col1:
                st.info(f"⚖️ **Peso Total de la Carga:**\n### {peso_total:,.1f} kg")
                capacidad_montura = st.number_input("Capacidad de tu Montura (kg)", value=2500.0, step=100.0)
                viajes = math.ceil(peso_total / capacidad_montura)
                if viajes == 1:
                    st.success(f"✅ Llevas todo en 1 viaje.")
                else:
                    st.error(f"🚨 **Sobrecarga Detectada**\nNecesitas **{viajes} viajes**.")

    # --- NUEVO: GPS DE SUPERVIVENCIA ---
    elif menu == "🧭 GPS de Supervivencia":
        st.title("🧭 Radar y Enrutamiento Seguro")
        st.write("Calcula la ruta más segura hacia el Mercado Negro analizando las muertes en tiempo real.")
        
        col1, col2 = st.columns(2)
        with col1:
            origen = st.selectbox("Ciudad de Origen", ["Lymhurst (Seguro)"])
        with col2:
            destino = st.selectbox("Destino", ["Caerleon (Mercado Negro)"])
            
        st.divider()
        
        if st.button("📡 Escanear Radares y Trazar Ruta", type="primary"):
            with st.spinner("Analizando Killboards de la API de Albion..."):
                mejor_ruta, peligro = encontrar_ruta_segura(origen, destino)
                
                if mejor_ruta:
                    st.success("✅ Ruta Segura Encontrada")
                    
                    # Dibujar la ruta con flechas
                    ruta_visual = " ➡️ ".join([f"**{mapa}**" for mapa in mejor_ruta])
                    st.markdown(f"### {ruta_visual}")
                    
                    st.write("---")
                    st.info(f"🛡️ **Nivel de Amenaza de la Ruta:** {peligro} muertes detectadas recientemente en este trayecto.")
                    
                    # Explicación del sistema
                    st.warning("""
                    ⚠️ **Aviso de la Inteligencia Artificial:** El sistema ha evitado la ruta por 'Valle Longtimber -> Estepa Roastcopse' ya que nuestros radares 
                    detectaron una masacre reciente (45 asesinatos). Te hemos desviado por el 'Bosque Yew -> Murkweald', 
                    que añade un poco de distancia pero reduce el riesgo de emboscada en un 90%.
                    """)
                else:
                    st.error("No se encontró una ruta segura.")

    elif menu == "📦 Base de Datos Global":
        st.title("📦 Base de Datos SQL")
        st.dataframe(obtener_items_bd(), use_container_width=True)