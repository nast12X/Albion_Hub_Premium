import streamlit as st
import pandas as pd
import sqlite3

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Albion Hub Premium v4.0", layout="wide", page_icon="⚔️")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1f2937; padding: 15px; border-radius: 10px; border: 1px solid #374151; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE BASE DE DATOS Y API ---
def obtener_items():
    conn = sqlite3.connect('albion_items.db')
    df = pd.read_sql_query("SELECT * FROM items", conn)
    conn.close()
    return df

def obtener_spec_usuario(discord_id, nombre_item):
    conn = sqlite3.connect('albion_items.db')
    cursor = conn.cursor()
    # Evitar error si la tabla no existe aún
    try:
        cursor.execute("SELECT spec_nivel FROM user_specs WHERE discord_id=? AND nombre_item=?", (discord_id, nombre_item))
        resultado = cursor.fetchone()
        conn.close()
        return resultado[0] if resultado else 0
    except:
        conn.close()
        return 0

def guardar_specs(discord_id, df_specs):
    conn = sqlite3.connect('albion_items.db')
    cursor = conn.cursor()
    for index, row in df_specs.iterrows():
        cursor.execute('''INSERT OR REPLACE INTO user_specs (discord_id, nombre_item, spec_nivel) 
                          VALUES (?, ?, ?)''', (discord_id, row['Ítem'], row['Nivel de Spec']))
    conn.commit()
    conn.close()

def get_image(item_id, size=150):
    if not item_id or item_id == "None":
        return "https://render.albiononline.com/v1/item/T4_TRASH.png?size=150"
    return f"https://render.albiononline.com/v1/item/{item_id}.png?size={size}"

# --- INTERFAZ LATERAL ---
with st.sidebar:
    st.title("🛡️ Panel Premium")
    if 'user' not in st.session_state:
        st.session_state['user'] = "The Gonza"
        st.session_state['discord_id'] = "123456"
        st.session_state['rol'] = "Premium"
    
    st.write(f"Usuario: **{st.session_state['user']}**")
    menu = st.radio("Secciones", ["🏠 Dashboard", "🎯 Mis Specs", "🧮 Calculadora Pro", "📝 Planificador Excel"])

# --- SECCIONES ---

if menu == "🎯 Mis Specs":
    st.title("🎯 Base de Datos de Maestrías (Specs)")
    df_items = obtener_items()
    nombres_unicos = df_items['nombre_es'].drop_duplicates().tolist() if not df_items.empty else []
    
    datos_tabla = [{"Ítem": n, "Nivel de Spec": obtener_spec_usuario(st.session_state['discord_id'], n)} for n in nombres_unicos]
    df_specs = pd.DataFrame(datos_tabla)
    
    st.info("Edita tus niveles y presiona Guardar.")
    df_editado = st.data_editor(df_specs, use_container_width=True, num_rows="dynamic")
    
    if st.button("💾 Guardar Mis Specs", type="primary"):
        guardar_specs(st.session_state['discord_id'], df_editado)
        st.success("¡Tus maestrías se han guardado!")

elif menu == "🧮 Calculadora Pro":
    st.title("🧮 Calculadora Visual")
    df_items = obtener_items()
    
    if df_items.empty:
        st.error("Base de datos vacía.")
        st.stop()

    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1: item_nombre = st.selectbox("Objeto", df_items['nombre_es'].drop_duplicates().tolist())
    with col_sel2: tier = st.selectbox("Tier", ["T4", "T5", "T6", "T7", "T8"], index=2)
    with col_sel3: encantamiento = st.selectbox("Encantamiento", [".0", ".1", ".2", ".3", ".4"])

    spec_actual = obtener_spec_usuario(st.session_state['discord_id'], item_nombre)
    st.caption(f"🧠 *Tu Spec para {item_nombre} es nivel: **{spec_actual}***")
    st.divider()

    enc_sufijo = f"@{encantamiento[-1]}" if encantamiento != ".0" else ""
    c_img1, c_img2, c_img3 = st.columns(3)
    
    with c_img1:
        st.image(get_image(f"{tier}_ARMOR_LEATHER_SET2{enc_sufijo}"), width=100)
        precio_venta = st.number_input("Precio Venta", value=50000)
    with c_img2:
        st.image(get_image(f"{tier}_LEATHER{enc_sufijo}"), width=100)
        precio_mat = st.number_input("Precio Material (1 ud)", value=2500)
    with c_img3:
        st.image(get_image(f"{tier}_JOURNAL_HUNTER_EMPTY"), width=100)
        precio_diario_vacio = st.number_input("Diario Vacío", value=1500)
        retorno_diario = st.number_input("Diario Lleno", value=6500)

    st.divider()
    usar_foco = st.toggle("⚡ Usar Foco")
    rr = 43.5 if usar_foco else 15.2
    
    costo_materiales = (precio_mat * 16) + precio_diario_vacio
    ahorro = (precio_mat * 16) * (rr / 100)
    costo_final = costo_materiales - ahorro
    profit = (precio_venta + retorno_diario) - costo_final

    if profit > 0:
        st.success(f"💰 PROFIT NETO: +{profit:,.0f} Plata")
    else:
        st.error(f"📉 PÉRDIDA NETA: {profit:,.0f} Plata")

# --- NUEVO: PLANIFICADOR TIPO EXCEL (Puntos 3 y 4) ---
elif menu == "📝 Planificador Excel":
    st.title("📝 Planificador de Producción en Masa")
    st.write("Añade los ítems que deseas craftear. El sistema leerá tus Specs automáticamente.")
    
    df_items = obtener_items()
    if df_items.empty:
        st.warning("No hay ítems en la base de datos.")
        st.stop()
        
    lista_items = df_items['nombre_es'].drop_duplicates().tolist()

    # Crear tabla vacía en memoria si no existe
    if 'plan_data' not in st.session_state:
        st.session_state['plan_data'] = pd.DataFrame({
            "Fabricar": [True, False, False],
            "Ítem": [lista_items[0], lista_items[0], lista_items[0]],
            "Cantidad": [10, 0, 0],
            "Precio Venta": [50000, 0, 0],
            "Costo Material (x1)": [2500, 0, 0],
            "Usar Foco": [False, False, False]
        })

    # Configurar el editor de datos (La tabla interactiva)
    config_columnas = {
        "Ítem": st.column_config.SelectboxColumn("Objeto a Fabricar", options=lista_items, required=True),
        "Cantidad": st.column_config.NumberColumn("Cant.", min_value=0, step=1),
        "Precio Venta": st.column_config.NumberColumn("Venta (Plata)", min_value=0),
        "Costo Material (x1)": st.column_config.NumberColumn("Costo Mat.", min_value=0)
    }

    df_plan = st.data_editor(
        st.session_state['plan_data'], 
        column_config=config_columnas, 
        num_rows="dynamic", 
        use_container_width=True
    )
    st.session_state['plan_data'] = df_plan

    if st.button("📊 Generar Reporte de Producción", type="primary"):
        st.divider()
        st.subheader("📋 Resumen Financiero")
        
        profit_total_global = 0
        materiales_totales = 0
        
        resultados = []
        for index, row in df_plan.iterrows():
            if row['Fabricar'] and row['Cantidad'] > 0:
                item_seleccionado = row['Ítem']
                cantidad = row['Cantidad']
                p_venta = row['Precio Venta']
                p_mat = row['Costo Material (x1)']
                foco = row['Usar Foco']
                
                # Auto-detectar Spec
                spec = obtener_spec_usuario(st.session_state['discord_id'], item_seleccionado)
                rr = 43.5 if foco else 15.2
                
                # Matemáticas (Asumimos 16 recursos por item por defecto en la demo)
                recursos_base = 16 * cantidad
                materiales_totales += recursos_base
                
                costo_bruto = (p_mat * 16) * cantidad
                ahorro = costo_bruto * (rr / 100)
                costo_real = costo_bruto - ahorro
                ingreso = p_venta * cantidad
                profit_fila = ingreso - costo_real
                
                profit_total_global += profit_fila
                
                resultados.append({
                    "Ítem": item_seleccionado,
                    "Cant.": cantidad,
                    "Spec": spec,
                    "RR%": rr,
                    "Costo Real": costo_real,
                    "Ingreso Bruto": ingreso,
                    "Profit Neto": profit_fila
                })
        
        if resultados:
            df_resultados = pd.DataFrame(resultados)
            
            # Formatear números para que se vean como dinero
            st.dataframe(df_resultados.style.format({
                "Costo Real": "{:,.0f}", 
                "Ingreso Bruto": "{:,.0f}", 
                "Profit Neto": "{:,.0f}"
            }), use_container_width=True)
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.success(f"### 🚀 PROFIT TOTAL ESTIMADO:\n### {profit_total_global:,.0f} Plata")
            with col_r2:
                st.info(f"### 📦 Materiales Brutos a Comprar:\n### {materiales_totales:,} Unidades")
                st.caption("*(No incluye la devolución de recursos durante el crafteo)*")
        else:
            st.warning("Selecciona la casilla 'Fabricar' y pon una cantidad mayor a 0.")

elif menu == "🏠 Dashboard":
    st.title("🏠 Dashboard")
    st.write("Bienvenido. Navega por el menú lateral.")