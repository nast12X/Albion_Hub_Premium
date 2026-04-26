import streamlit as st
import pandas as pd
import sqlite3
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Albion Hub Premium v5.0", layout="wide", page_icon="👑")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS Y FUNCIONES ---
def obtener_items():
    conn = sqlite3.connect('albion_items.db')
    df = pd.read_sql_query("SELECT * FROM items", conn)
    conn.close()
    return df

def obtener_spec_usuario(discord_id, nombre_item):
    conn = sqlite3.connect('albion_items.db')
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT spec_nivel FROM user_specs WHERE discord_id=? AND nombre_item=?", (discord_id, nombre_item))
        res = cursor.fetchone()
        conn.close()
        return res[0] if res else 0
    except:
        conn.close()
        return 0

def guardar_specs(discord_id, df_specs):
    conn = sqlite3.connect('albion_items.db')
    cursor = conn.cursor()
    for _, row in df_specs.iterrows():
        cursor.execute('INSERT OR REPLACE INTO user_specs (discord_id, nombre_item, spec_nivel) VALUES (?, ?, ?)', 
                       (discord_id, row['Ítem'], row['Nivel de Spec']))
    conn.commit()
    conn.close()

def get_image(item_id, size=150):
    if not item_id or item_id == "None":
        return "https://render.albiononline.com/v1/item/T4_TRASH.png?size=150"
    return f"https://render.albiononline.com/v1/item/{item_id}.png?size={size}"

# --- MÓDULO 3: API DEL MERCADO NEGRO ---
@st.cache_data(ttl=60) # Se actualiza cada 60 segundos
def escanear_mercado_negro():
    # Escaneamos 3 items de alta demanda en el BM (Black Market)
    url = "https://west.albion-online-data.com/api/v2/stats/prices/T6_ARMOR_LEATHER_SET2,T6_HEAD_LEATHER_SET3,T6_MAIN_SWORD.json?locations=Black Market"
    try:
        respuesta = requests.get(url, timeout=5).json()
        resultados = []
        for item in respuesta:
            if item['sell_price_min'] > 0:
                resultados.append({"ID": item['item_id'], "Precio BM": item['sell_price_min']})
        return pd.DataFrame(resultados)
    except:
        return pd.DataFrame()

# --- MÓDULO 1: EL MEGA GPS (Algoritmo BFS de Búsqueda de Rutas) ---
MAPAS_ALBION = {
    # Continente Real
    "Lymhurst": ["Bosque Yew (Am)", "Valle Longtimber (Am)"],
    "Bosque Yew (Am)": ["Lymhurst", "Murkweald (ROJA)"],
    "Valle Longtimber (Am)": ["Lymhurst", "Estepa Roastcopse (ROJA)"],
    "Estepa Roastcopse (ROJA)": ["Valle Longtimber (Am)", "Caerleon (Mercado Negro)"],
    "Murkweald (ROJA)": ["Bosque Yew (Am)", "Caerleon (Mercado Negro)"],
    "Caerleon (Mercado Negro)": ["Estepa Roastcopse (ROJA)", "Murkweald (ROJA)"],
    # Zona Negra (Outlands)
    "Portal Lymhurst (Negra)": ["Awake Wood (T5)", "Oasis de Fuego (T6)"],
    "Awake Wood (T5)": ["Portal Lymhurst (Negra)", "Arthur's Rest"],
    "Oasis de Fuego (T6)": ["Portal Lymhurst (Negra)", "Arthur's Rest"],
    "Arthur's Rest": ["Awake Wood (T5)", "Oasis de Fuego (T6)", "Zona Profunda T8"],
    "Zona Profunda T8": ["Arthur's Rest", "Hideout del Gremio"]
}

def encontrar_ruta(inicio, fin):
    visitados = []
    cola = [[inicio]]
    if inicio == fin: return [inicio]
    while cola:
        camino = cola.pop(0)
        nodo = camino[-1]
        if nodo not in visitados:
            vecinos = MAPAS_ALBION.get(nodo, [])
            for vecino in vecinos:
                nuevo_camino = list(camino)
                nuevo_camino.append(vecino)
                cola.append(nuevo_camino)
                if vecino == fin: return nuevo_camino
            visitados.append(nodo)
    return []

# --- INTERFAZ LATERAL ---
with st.sidebar:
    st.title("🛡️ Albion Hub")
    if 'user' not in st.session_state:
        st.session_state['user'] = "El Jefe"
        st.session_state['discord_id'] = "123456"
    st.write(f"👑 Usuario: **{st.session_state['user']}**")
    menu = st.radio("Módulos Operativos:", ["🏠 Dashboard", "🎯 Mis Specs", "🧮 Calculadora Pro", "📝 Planificador", "🧭 Mega GPS"])

# ==========================================
# SECCIONES DE LA APLICACIÓN
# ==========================================

if menu == "🏠 Dashboard":
    st.title("📈 Centro de Mando: Mercado Negro")
    st.write("Escaneando órdenes de compra en tiempo real en Caerleon...")
    
    df_bm = escanear_mercado_negro()
    if not df_bm.empty:
        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        for i, row in df_bm.iterrows():
            if i < 3:
                with cols[i]:
                    st.image(get_image(row['ID']), width=80)
                    st.metric(label=f"Demanda BM: {row['ID']}", value=f"{row['Precio BM']:,} Plata")
    else:
        st.warning("No se pudo conectar a los servidores de Albion Data Project en este momento.")

elif menu == "🎯 Mis Specs":
    st.title("🎯 Base de Datos de Maestrías")
    df_items = obtener_items()
    nombres_unicos = df_items['nombre_es'].drop_duplicates().tolist() if not df_items.empty else []
    datos_tabla = [{"Ítem": n, "Nivel de Spec": obtener_spec_usuario(st.session_state['discord_id'], n)} for n in nombres_unicos]
    
    df_editado = st.data_editor(pd.DataFrame(datos_tabla), use_container_width=True)
    if st.button("💾 Guardar Mis Specs", type="primary"):
        guardar_specs(st.session_state['discord_id'], df_editado)
        st.success("¡Maestrías sincronizadas!")

elif menu == "🧮 Calculadora Pro":
    st.title("🧮 Calculadora de Crafteo Visual")
    df_items = obtener_items()
    
    if df_items.empty: st.stop()

    col1, col2 = st.columns(2)
    with col1: 
        item_nombre = st.selectbox("Objeto", df_items['nombre_es'].drop_duplicates().tolist())
        tier = st.selectbox("Tier", ["T4", "T5", "T6", "T7", "T8"], index=2)
    with col2:
        usar_foco = st.toggle("⚡ Usar Foco (Incrementa RR)")
        precio_venta = st.number_input("Precio de Venta Esperado", value=50000)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.image(get_image(f"{tier}_LEATHER"), width=80)
        precio_mat = st.number_input("Precio Material", value=2500)
    with c2:
        st.image(get_image(f"{tier}_JOURNAL_HUNTER_EMPTY"), width=80)
        precio_diario_vacio = st.number_input("Diario Vacío", value=1500)
        precio_diario_lleno = st.number_input("Diario Lleno", value=6500)
    with c3:
        st.image(get_image(f"T4_TRASH"), width=80)
        precio_artefacto = st.number_input("Precio Artefacto (Si requiere)", value=0)

    # Matemáticas
    rr = 43.5 if usar_foco else 15.2
    costo_mat = (precio_mat * 16) + precio_diario_vacio + precio_artefacto
    ahorro = (precio_mat * 16) * (rr / 100)
    costo_real = costo_mat - ahorro
    profit = (precio_venta + precio_diario_lleno) - costo_real

    if profit > 0: st.success(f"💰 PROFIT UNITARIO: +{profit:,.0f} Plata")
    else: st.error(f"📉 PÉRDIDA: {profit:,.0f} Plata")

elif menu == "📝 Planificador":
    st.title("🛒 Planificador de Producción Masivo")
    st.write("MÓDULO 2: Integración de Diarios y Artefactos a la lista de compras.")
    
    df_items = obtener_items()
    lista_items = df_items['nombre_es'].drop_duplicates().tolist() if not df_items.empty else ["Vacío"]

    if 'plan_data' not in st.session_state:
        st.session_state['plan_data'] = pd.DataFrame({"Fabricar": [True, False], "Ítem": [lista_items[0], lista_items[0]], "Cantidad": [10, 0], "Precio Venta": [50000, 0], "Costo Material (x1)": [2500, 0], "Usa Artefacto": [False, False]})

    df_plan = st.data_editor(st.session_state['plan_data'], num_rows="dynamic", use_container_width=True)
    st.session_state['plan_data'] = df_plan

    if st.button("📊 Generar Manifiesto de Compras", type="primary"):
        st.divider()
        st.subheader("📋 Lista de Compras Exacta")
        
        mats_totales = 0
        diarios_totales = 0
        art_totales = 0
        
        for index, row in df_plan.iterrows():
            if row['Fabricar'] and row['Cantidad'] > 0:
                mats_totales += (16 * row['Cantidad'])
                diarios_totales += row['Cantidad'] # Asumimos 1 diario por item para simplificar
                if row['Usa Artefacto']: art_totales += row['Cantidad']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"🪵 **Materiales Base:**\n### {mats_totales:,}")
        with col2:
            st.warning(f"📘 **Diarios Vacíos a Comprar:**\n### {diarios_totales:,}")
        with col3:
            st.error(f"🔮 **Artefactos a Comprar:**\n### {art_totales:,}")
            
        st.success("Tus trabajadores ya pueden ir al mercado a comprar esto exactamente.")

elif menu == "🧭 Mega GPS":
    st.title("🧭 Mega GPS Logístico (Royal & Outlands)")
    st.write("MÓDULO 1: Selecciona tu origen y destino para encontrar la ruta más segura.")
    
    c1, c2 = st.columns(2)
    mapas_disponibles = list(MAPAS_ALBION.keys())
    with c1: origen = st.selectbox("Punto de Partida", mapas_disponibles, index=0)
    with c2: destino = st.selectbox("Destino", mapas_disponibles, index=5)
    
    if st.button("📡 Trazar Ruta"):
        ruta = encontrar_ruta(origen, destino)
        if ruta:
            st.success("✅ Ruta Encontrada:")
            ruta_formateada = " ➡️ ".join([f"**{mapa}**" for mapa in ruta])
            st.markdown(f"### {ruta_formateada}")
            
            peligro = sum([1 for m in ruta if "ROJA" in m or "Negra" in m or "T8" in m])
            if peligro > 0:
                st.warning(f"⚠️ Alerta: Cruzarás {peligro} zonas de letalidad (PvP Full Loot).")
        else:
            st.error("❌ No hay conexión segura entre estos mapas.")