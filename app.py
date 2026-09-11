import streamlit as st
import pandas as pd
import json
import datetime
import io

# Importaciones para generación de PDF con ReportLab
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Configuración de la página
st.set_page_config(page_title="App Educativa de Contabilidad", layout="wide")

st.title("📚 Sistema Contable Educativo")
st.write("Herramienta pedagógica para registración manual, gestión de padrones y valuación de inventarios por PPP.")

# ==========================================
# INICIALIZACIÓN DE ESTADOS (SESSION STATE)
# ==========================================

def inicializar_estados():
    if "alumno_nombre" not in st.session_state:
        st.session_state.alumno_nombre = "Alumno Demo"
    if "alumno_curso" not in st.session_state:
        st.session_state.alumno_curso = "5° Año - Contabilidad"

    if "plan_cuentas" not in st.session_state:
        st.session_state.plan_cuentas = [
            "1.1.01 Caja",
            "1.1.02 Banco Nación c/c",
            "1.2.01 Deudores por Ventas (Clientes)",
            "1.3.01 Mercaderías (Stock)",
            "2.1.01 Proveedores",
            "2.1.02 Obligaciones a Pagar",
            "3.1.01 Capital Social",
            "4.1.01 Ventas",
            "5.1.01 Costo de Mercaderías Vendidas (CMV)",
            "5.1.02 Gastos Generales"
        ]

    if "padron_terceros" not in st.session_state:
        st.session_state.padron_terceros = []

    if "libro_diario" not in st.session_state:
        st.session_state.libro_diario = []

    if "submayores" not in st.session_state:
        st.session_state.submayores = {
            "Clientes": [],
            "Proveedores": [],
            "Stock_Fisico": [],
            "Stock_Valorizado": {}
        }

inicializar_estados()

# ==========================================
# SIDEBAR: DATOS DEL ALUMNO Y GUARDADO
# ==========================================
st.sidebar.header("🎓 Datos del Estudiante")

# NOTA EDUCIONAL: Por ahora editable. En el producto final se deshabilita con disabled=True 
# o se obtiene directamente del login/autenticación del alumno.
st.session_state.alumno_nombre = st.sidebar.text_input(
    "Nombre del Alumno", 
    value=st.session_state.alumno_nombre,
    help="Modificable en etapa de prueba. Se bloqueará en el entorno de evaluación."
)

st.session_state.alumno_curso = st.sidebar.text_input(
    "Curso / División / Materia", 
    value=st.session_state.alumno_curso
)

st.sidebar.divider()

st.sidebar.header("💾 Guardar / Cargar Trabajo")

def serializar_fecha(o):
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()

datos_exportar = {
    "alumno_nombre": st.session_state.alumno_nombre,
    "alumno_curso": st.session_state.alumno_curso,
    "plan_cuentas": st.session_state.plan_cuentas,
    "padron_terceros": st.session_state.padron_terceros,
    "libro_diario": st.session_state.libro_diario,
    "submayores": st.session_state.submayores
}

json_str = json.dumps(datos_exportar, default=serializar_fecha, indent=2)

st.sidebar.download_button(
    label="📥 Guardar Avance (Descargar .json)",
    data=json_str,
    file_name=f"practica_{st.session_state.alumno_nombre.replace(' ', '_')}.json",
    mime="application/json",
    help="Descargá este archivo para no perder lo que registraste."
)

archivo_cargado = st.sidebar.file_uploader("📤 Cargar Avance previo (.json)", type=["json"])

if archivo_cargado is not None:
    try:
        datos_recuperados = json.load(archivo_cargado)
        
        for renglon in datos_recuperados.get("libro_diario", []):
            if isinstance(renglon.get("Fecha"), str):
                renglon["Fecha"] = datetime.date.fromisoformat(renglon["Fecha"])
                
        for clave, movs in datos_recuperados.get("submayores", {}).items():
            if isinstance(movs, list):
                for m in movs:
                    if isinstance(m.get("Fecha"), str):
                        m["Fecha"] = datetime.date.fromisoformat(m["Fecha"])
            elif isinstance(movs, dict):
                for art, registros in movs.items():
                    for r in registros:
                        if isinstance(r.get("Fecha"), str):
                            r["Fecha"] = datetime.date.fromisoformat(r["Fecha"])

        st.session_state.alumno_nombre = datos_recuperados.get("alumno_nombre", st.session_state.alumno_nombre)
        st.session_state.alumno_curso = datos_recuperados.get("alumno_curso", st.session_state.alumno_curso)
        st.session_state.plan_cuentas = datos_recuperados.get("plan_cuentas", st.session_state.plan_cuentas)
        st.session_state.padron_terceros = datos_recuperados.get("padron_terceros", [])
        st.session_state.libro_diario = datos_recuperados.get("libro_diario", [])
        st.session_state.submayores = datos_recuperados.get("submayores", st.session_state.submayores)
        
        st.sidebar.success("¡Avance cargado con éxito!")
    except Exception as e:
        st.sidebar.error("Error al leer el archivo JSON.")

st.sidebar.divider()

# ==========================================
# FUNCIONES AUXILIARES PARA GENERACIÓN DE PDF
# ==========================================

def obtener_encabezado_pdf(styles):
    """Genera el bloque visual de identificación del alumno para los reportes."""
    style_header_label = ParagraphStyle('HLabel', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#1E293B'))
    style_header_val = ParagraphStyle('HVal', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#0F172A'))
    style_header_right = ParagraphStyle('HRight', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, alignment=2, textColor=colors.HexColor('#64748B'))

    fecha_emision = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    header_data = [
        [
            Paragraph(f"<b>Estudiante:</b> {st.session_state.alumno_nombre}", style_header_label),
            Paragraph(f"<b>Emisión:</b> {fecha_emision}", style_header_right)
        ],
        [
            Paragraph(f"<b>Curso/Materia:</b> {st.session_state.alumno_curso}", style_header_label),
            Paragraph("Sistema de Practicantes Contables", style_header_right)
        ]
    ]

    table_header = Table(header_data, colWidths=[350, 190])
    table_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))

    return [
        table_header,
        Spacer(1, 5),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceAfter=15)
    ]

def generar_pdf_libro_diario(asientos):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, alignment=1, spaceAfter=10)
    style_normal = ParagraphStyle('NormStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9)
    style_right = ParagraphStyle('RightStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, alignment=2)
    
    elements = []
    elements.extend(obtener_encabezado_pdf(styles))
    elements.append(Paragraph("LIBRO DIARIO GENERAL", style_title))
    elements.append(Spacer(1, 10))

    data = [["Fecha / Detalle", "Cuenta / Imputación", "Debe ($)", "Haber ($)"]]

    for a in asientos:
        data.append([
            f"Asiento N° {a['Asiento']}\n{a['Fecha']}",
            f"<b>Operación:</b> {a['Operación']}",
            "", ""
        ])
        for r in a['Renglones']:
            debe_str = f"${r['Monto']:,.2f}" if r['Tipo'] == "Debe" else ""
            haber_str = f"${r['Monto']:,.2f}" if r['Tipo'] == "Haber" else ""
            cuenta_fmt = r['Cuenta'] if r['Tipo'] == "Debe" else f"&nbsp;&nbsp;&nbsp;&nbsp;a {r['Cuenta']}"
            
            data.append([
                "",
                Paragraph(cuenta_fmt, style_normal),
                Paragraph(debe_str, style_right),
                Paragraph(haber_str, style_right)
            ])
            
        tercero_str = f" | Tercero: {a['Tercero']}" if a['Tercero'] != "N/A" else ""
        data.append([
            "",
            Paragraph(f"<i>Según: {a['Concepto']}{tercero_str}</i>", style_normal),
            "", ""
        ])

    table = Table(data, colWidths=[100, 270, 90, 90])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (2,0), (3,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generar_pdf_tabla_generica(titulo, df, orientacion="portrait"):
    buffer = io.BytesIO()
    pagesize = landscape(letter) if orientacion == "landscape" else letter
    doc = SimpleDocTemplate(buffer, pagesize=pagesize, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, alignment=1, spaceAfter=10)
    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontName='Helvetica', fontSize=8)
    style_header = ParagraphStyle('Header', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)

    elements = []
    elements.extend(obtener_encabezado_pdf(styles))
    elements.append(Paragraph(titulo, style_title))
    elements.append(Spacer(1, 10))

    headers = [Paragraph(str(col), style_header) for col in df.columns]
    table_data = [headers]

    for _, row in df.iterrows():
        row_data = []
        for val in row:
            if isinstance(val, (float, int)):
                val_str = f"${val:,.2f}" if isinstance(val, float) else str(val)
            else:
                val_str = str(val) if pd.notnull(val) else ""
            row_data.append(Paragraph(val_str, style_cell))
        table_data.append(row_data)

    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#94A3B8')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# MENÚ NAVEGACIÓN
# ==========================================
menu = st.sidebar.radio(
    "Navegación",
    [
        "1. Padrones y Plan de Cuentas",
        "2. Carga de Asientos (Libro Diario)",
        "3. Libro Mayor y Submayores",
        "4. Ficha de Stock PPP",
        "5. Sumas y Saldos"
    ]
)

# ==========================================
# MÓDULO 1: PADRONES Y PLAN DE CUENTAS
# ==========================================
if menu == "1. Padrones y Plan de Cuentas":
    st.header("⚙️ Configuración Inicial: Padrones y Cuentas")
    
    tab_padron, tab_cuentas = st.tabs(["👥 Padrón de Clientes / Proveedores", "📑 Plan de Cuentas"])

    with tab_padron:
        st.subheader("Alta de Cliente o Proveedor")
        with st.form("form_tercero", clear_on_submit=True):
            col_t1, col_t2 = st.columns(2)
            tipo_tercero = col_t1.selectbox("Tipo de Entidad", ["Cliente", "Proveedor"])
            nombre = col_t2.text_input("Razón Social / Nombre", placeholder="Ej: Distribuidora Tucumán S.R.L.")

            col_t3, col_t4, col_t5 = st.columns(3)
            cuit = col_t3.text_input("CUIT / DNI", placeholder="20-30405060-7")
            domicilio = col_t4.text_input("Domicilio Comercial", placeholder="Ej: Av. San Martín 450")
            condicion_pago = col_t5.selectbox("Condición Habitual", [
                "Contado / Efectivo",
                "Cuenta Corriente 30 días",
                "Cuenta Corriente 60 días",
                "Transferencia Bancaria"
            ])

            if st.form_submit_button("Guardar en Padrón"):
                if not nombre or not cuit:
                    st.error("El nombre y el CUIT son obligatorios.")
                else:
                    st.session_state.padron_terceros.append({
                        "Tipo": tipo_tercero,
                        "Nombre": nombre,
                        "CUIT": cuit,
                        "Domicilio": domicilio,
                        "Condicion": condicion_pago
                    })
                    st.success(f"{tipo_tercero} '{nombre}' registrado correctamente.")

        st.subheader("📋 Padrón Registrado")
        if st.session_state.padron_terceros:
            st.dataframe(pd.DataFrame(st.session_state.padron_terceros), use_container_width=True)
        else:
            st.info("Aún no hay clientes o proveedores registrados.")

    with tab_cuentas:
        st.subheader("Agregar Nueva Cuenta Contable")
        with st.form("form_nueva_cuenta", clear_on_submit=True):
            col_c1, col_c2 = st.columns([1, 3])
            codigo = col_c1.text_input("Código de Cuenta", placeholder="Ej: 1.1.03")
            nombre_cuenta = col_c2.text_input("Nombre de la Cuenta", placeholder="Ej: Valores a Depositar")

            if st.form_submit_button("Agregar Cuenta al Plan"):
                if not codigo or not nombre_cuenta:
                    st.error("El código y nombre son obligatorios.")
                else:
                    nueva_cuenta_str = f"{codigo} {nombre_cuenta}"
                    if nueva_cuenta_str not in st.session_state.plan_cuentas:
                        st.session_state.plan_cuentas.append(nueva_cuenta_str)
                        st.session_state.plan_cuentas.sort()
                        st.success(f"Cuenta '{nueva_cuenta_str}' agregada.")

        st.dataframe(pd.DataFrame({"Cuentas Disponibles": st.session_state.plan_cuentas}), use_container_width=True)

# ==========================================
# MÓDULO 2: LIBRO DIARIO
# ==========================================
elif menu == "2. Carga de Asientos (Libro Diario)":
    st.header("📝 Registración de Asientos Contables")

    lista_clientes = [t["Nombre"] for t in st.session_state.padron_terceros if t.get("Tipo") == "Cliente"]
    lista_proveedores = [t["Nombre"] for t in st.session_state.padron_terceros if t.get("Tipo") == "Proveedor"]

    st.subheader("📄 Datos del Comprobante y Operación")
    col_op1, col_op2, col_op3 = st.columns(3)
    fecha = col_op1.date_input("Fecha de operación")
    tipo_operacion = col_op2.selectbox("Tipo de Operación", ["Compra", "Venta", "Cobro", "Pago", "Otra Operación"])
    concepto = col_op3.text_input("Comprobante / Detalle", placeholder="Ej: Factura A N° 0001-00000123")

    tercero_operacion = "N/A"
    if tipo_operacion in ["Venta", "Cobro"]:
        if lista_clientes:
            tercero_operacion = st.selectbox(
                "Seleccionar Cliente",
                ["Sin especificar"] + lista_clientes,
                key=f"sel_cliente_{tipo_operacion}"
            )
        else:
            st.warning("⚠️ No hay Clientes registrados en el Padrón (Módulo 1).")
            tercero_operacion = "Sin especificar"
    elif tipo_operacion in ["Compra", "Pago"]:
        if lista_proveedores:
            tercero_operacion = st.selectbox(
                "Seleccionar Proveedor",
                ["Sin especificar"] + lista_proveedores,
                key=f"sel_prov_{tipo_operacion}"
            )
        else:
            st.warning("⚠️ No hay Proveedores registrados en el Padrón (Módulo 1).")
            tercero_operacion = "Sin especificar"

    st.divider()

    with st.form("form_asiento_montos", clear_on_submit=True):
        st.subheader("1️⃣ Imputación al DEBE")
        col_d1, col_d2 = st.columns([3, 2])
        cuenta_debe = col_d1.selectbox("Cuenta al DEBE", st.session_state.plan_cuentas, key="cuenta_d")
        monto_debe = col_d2.number_input("Monto Debe ($)", min_value=0.0, step=100.0, key="monto_d")

        st.subheader("2️⃣ Imputación al HABER")
        col_h1, col_h2 = st.columns([3, 2])
        cuenta_haber = col_h1.selectbox("Cuenta al HABER", st.session_state.plan_cuentas, key="cuenta_h")
        monto_haber = col_h2.number_input("Monto Haber ($)", min_value=0.0, step=100.0, key="monto_h")

        st.divider()

        st.subheader("📦 Control de Inventario (Opcional)")
        col_st1, col_st2, col_st3, col_st4 = st.columns(4)
        mov_stock = col_st1.selectbox("Movimiento de Stock", ["Ninguno", "Entrada (Compra)", "Salida (Venta)"])
        art_stock = col_st2.text_input("Nombre del Artículo", placeholder="Ej: Resma A4")
        cant_stock = col_st3.number_input("Cantidad (Unidades)", min_value=0, step=1)
        pu_stock = col_st4.number_input("Precio Unitario Compra ($)", min_value=0.0, step=10.0, help="Solo para Entradas por Compra")

        submitted = st.form_submit_button("Registrar Asiento Contable")

        if submitted:
            if monto_debe <= 0 or monto_haber <= 0:
                st.error("Error: Los montos deben ser mayores a $0.")
            elif monto_debe != monto_haber:
                st.error(f"Error de Partida Doble: El Debe (${monto_debe:,.2f}) no coincide con el Haber (${monto_haber:,.2f}).")
            elif cuenta_debe == cuenta_haber:
                st.error("Error: Las cuentas al Debe y al Haber no pueden ser iguales.")
            else:
                num_asiento = len(st.session_state.libro_diario) + 1

                asiento_obj = {
                    "Asiento": num_asiento,
                    "Fecha": fecha,
                    "Operación": tipo_operacion,
                    "Concepto": concepto,
                    "Tercero": tercero_operacion,
                    "Renglones": [
                        {"Tipo": "Debe", "Cuenta": cuenta_debe, "Monto": monto_debe},
                        {"Tipo": "Haber", "Cuenta": cuenta_haber, "Monto": monto_haber}
                    ]
                }
                
                st.session_state.libro_diario.append(asiento_obj)

                if tercero_operacion not in ["N/A", "Sin especificar"]:
                    if tipo_operacion in ["Venta", "Cobro"]:
                        st.session_state.submayores["Clientes"].append({
                            "Fecha": fecha, "Cliente": tercero_operacion, "Concepto": concepto,
                            "Debe (Deuda)": monto_debe if "Clientes" in cuenta_debe else 0.0,
                            "Haber (Pago)": monto_haber if "Clientes" in cuenta_haber else 0.0
                        })
                    elif tipo_operacion in ["Compra", "Pago"]:
                        st.session_state.submayores["Proveedores"].append({
                            "Fecha": fecha, "Proveedor": tercero_operacion, "Concepto": concepto,
                            "Debe (Pago)": monto_debe if "Proveedores" in cuenta_debe else 0.0,
                            "Haber (Deuda)": monto_haber if "Proveedores" in cuenta_haber else 0.0
                        })

                if mov_stock != "Ninguno" and art_stock and cant_stock > 0:
                    historial_sf = [m for m in st.session_state.submayores["Stock_Fisico"] if m["Artículo"] == art_stock]
                    stock_f_prev = historial_sf[-1]["Stock Final"] if historial_sf else 0
                    
                    e_sf = cant_stock if mov_stock == "Entrada (Compra)" else 0
                    s_sf = cant_stock if mov_stock == "Salida (Venta)" else 0
                    stock_f_nuevo = stock_f_prev + e_sf - s_sf

                    st.session_state.submayores["Stock_Fisico"].append({
                        "Fecha": fecha, "Artículo": art_stock, "Movimiento": mov_stock,
                        "Entrada": e_sf, "Salida": s_sf, "Stock Final": stock_f_nuevo
                    })

                    fichas = st.session_state.submayores["Stock_Valorizado"]
                    if art_stock not in fichas:
                        fichas[art_stock] = []

                    historial_art = fichas[art_stock]
                    cant_saldo_prev = historial_art[-1]["Saldo Cantidad"] if historial_art else 0
                    monto_saldo_prev = historial_art[-1]["Saldo Total"] if historial_art else 0.0
                    ppp_prev = historial_art[-1]["Saldo PPP"] if historial_art else 0.0

                    if mov_stock == "Entrada (Compra)":
                        e_cant = cant_stock
                        e_pu = pu_stock
                        e_total = e_cant * e_pu
                        s_cant, s_pu, s_total = 0, 0.0, 0.0

                        cant_saldo_n = cant_saldo_prev + e_cant
                        monto_saldo_n = monto_saldo_prev + e_total
                        ppp_n = monto_saldo_n / cant_saldo_n if cant_saldo_n > 0 else 0.0
                    else:
                        e_cant, e_pu, e_total = 0, 0.0, 0.0
                        s_cant = cant_stock
                        s_pu = ppp_prev
                        s_total = s_cant * s_pu

                        cant_saldo_n = max(0, cant_saldo_prev - s_cant)
                        monto_saldo_n = max(0.0, monto_saldo_prev - s_total)
                        ppp_n = ppp_prev if cant_saldo_n > 0 else 0.0

                    historial_art.append({
                        "Fecha": fecha, "Concepto": concepto,
                        "E. Cant": e_cant, "E. PU": e_pu, "E. Total": e_total,
                        "S. Cant": s_cant, "S. PU": s_pu, "S. Total": s_total,
                        "Saldo Cantidad": cant_saldo_n, "Saldo PPP": ppp_n, "Saldo Total": monto_saldo_n
                    })

                st.success(f"Asiento N° {num_asiento} registrado con éxito.")

    col_tit, col_btn = st.columns([3, 1])
    col_tit.subheader("📖 Libro Diario General (Formato Tradicional)")
    
    if st.session_state.libro_diario:
        pdf_diario = generar_pdf_libro_diario(st.session_state.libro_diario)
        col_btn.download_button(
            label="📄 Exportar Libro Diario (PDF)",
            data=pdf_diario,
            file_name=f"Libro_Diario_{st.session_state.alumno_nombre.replace(' ', '_')}.pdf",
            mime="application/pdf"
        )

        for asito in st.session_state.libro_diario:
            with st.container():
                st.markdown(f"**------------------- Asiento N° {asito['Asiento']} ({asito['Fecha']}) -------------------**")
                
                for renglon in asito["Renglones"]:
                    if renglon["Tipo"] == "Debe":
                        col_c, col_d, col_h = st.columns([5, 2, 2])
                        col_c.write(f"**{renglon['Cuenta']}**")
                        col_d.write(f"${renglon['Monto']:,.2f}")
                        col_h.write("")

                for renglon in asito["Renglones"]:
                    if renglon["Tipo"] == "Haber":
                        col_c, col_d, col_h = st.columns([5, 2, 2])
                        col_c.write(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;a **{renglon['Cuenta']}**", unsafe_allow_html=True)
                        col_d.write("")
                        col_h.write(f"${renglon['Monto']:,.2f}")

                tercero_str = f" | Tercero: {asito['Tercero']}" if asito['Tercero'] != "N/A" else ""
                st.caption(f"*Según: {asito['Concepto']}{tercero_str}*")
                st.divider()
    else:
        st.info("Sin asientos registrados.")

# ==========================================
# MÓDULO 3: LIBRO MAYOR Y SUBMAYORES
# ==========================================
elif menu == "3. Libro Mayor y Submayores":
    st.header("📊 Libro Mayor General y Submayores Auxiliares")

    tab_mayor, tab_sub_c, tab_sub_p, tab_sub_stk = st.tabs([
        "Libro Mayor General", "Submayor Clientes", "Submayor Proveedores", "Stock Físico (Unidades)"
    ])

    with tab_mayor:
        cuenta_sel = st.selectbox("Seleccionar Cuenta", st.session_state.plan_cuentas)
        if st.session_state.libro_diario:
            renglones_flat = []
            for a in st.session_state.libro_diario:
                for r in a["Renglones"]:
                    if r["Cuenta"] == cuenta_sel:
                        renglones_flat.append({
                            "Asiento": a["Asiento"],
                            "Fecha": a["Fecha"],
                            "Operación": a["Operación"],
                            "Concepto": a["Concepto"],
                            "Tercero": a["Tercero"],
                            "Debe": r["Monto"] if r["Tipo"] == "Debe" else 0.0,
                            "Haber": r["Monto"] if r["Tipo"] == "Haber" else 0.0
                        })

            if renglones_flat:
                df_cuenta = pd.DataFrame(renglones_flat)
                t_debe = df_cuenta["Debe"].sum()
                t_haber = df_cuenta["Haber"].sum()
                
                pdf_mayor = generar_pdf_tabla_generica(f"LIBRO MAYOR: {cuenta_sel}", df_cuenta)
                st.download_button("📄 Exportar Mayor de Cuenta (PDF)", pdf_mayor, f"Mayor_{cuenta_sel}.pdf", "application/pdf")
                
                st.dataframe(df_cuenta, use_container_width=True)

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Debe", f"${t_debe:,.2f}")
                c2.metric("Total Haber", f"${t_haber:,.2f}")
                c3.metric("Saldo", f"${t_debe - t_haber:,.2f}")
            else:
                st.info("Sin movimientos en esta cuenta.")

    with tab_sub_c:
        lista_c = list(set([m["Cliente"] for m in st.session_state.submayores["Clientes"]]))
        if lista_c:
            cliente_sel = st.selectbox("Seleccionar Cliente a Visualizar", lista_c)
            movs_cli = [m for m in st.session_state.submayores["Clientes"] if m["Cliente"] == cliente_sel]
            
            df_c = pd.DataFrame(movs_cli)
            df_c["Saldo Acumulado"] = (df_c["Debe (Deuda)"] - df_c["Haber (Pago)"]).cumsum()

            pdf_sub_c = generar_pdf_tabla_generica(f"SUBMAYOR DE CLIENTE: {cliente_sel}", df_c)
            st.download_button("📄 Exportar Submayor Cliente (PDF)", pdf_sub_c, f"Submayor_Cliente_{cliente_sel}.pdf", "application/pdf")

            st.dataframe(df_c, use_container_width=True)
            st.metric("Saldo Pendiente del Cliente", f"${df_c['Saldo Acumulado'].iloc[-1]:,.2f}")
        else:
            st.info("Sin registros en submayor de clientes.")

    with tab_sub_p:
        lista_p = list(set([m["Proveedor"] for m in st.session_state.submayores["Proveedores"]]))
        if lista_p:
            prov_sel = st.selectbox("Seleccionar Proveedor a Visualizar", lista_p)
            movs_prov = [m for m in st.session_state.submayores["Proveedores"] if m["Proveedor"] == prov_sel]
            
            df_p = pd.DataFrame(movs_prov)
            df_p["Saldo Acumulado"] = (df_p["Haber (Deuda)"] - df_p["Debe (Pago)"]).cumsum()

            pdf_sub_p = generar_pdf_tabla_generica(f"SUBMAYOR DE PROVEEDOR: {prov_sel}", df_p)
            st.download_button("📄 Exportar Submayor Proveedor (PDF)", pdf_sub_p, f"Submayor_Proveedor_{prov_sel}.pdf", "application/pdf")

            st.dataframe(df_p, use_container_width=True)
            st.metric("Saldo Deuda con Proveedor", f"${df_p['Saldo Acumulado'].iloc[-1]:,.2f}")
        else:
            st.info("Sin registros en submayor de proveedores.")

    with tab_sub_stk:
        if st.session_state.submayores["Stock_Fisico"]:
            df_sf = pd.DataFrame(st.session_state.submayores["Stock_Fisico"])
            pdf_sub_stk = generar_pdf_tabla_generica("SUBMAYOR DE STOCK FISICO", df_sf)
            st.download_button("📄 Exportar Stock Físico (PDF)", pdf_sub_stk, "Stock_Fisico.pdf", "application/pdf")
            st.dataframe(df_sf, use_container_width=True)
        else:
            st.info("Sin registros de movimientos físicos de stock.")

# ==========================================
# MÓDULO 4: FICHA DE STOCK VALORIZADA (PPP)
# ==========================================
elif menu == "4. Ficha de Stock PPP":
    st.header("📈 Ficha de Stock Valorizada - Método PPP")

    fichas = st.session_state.submayores["Stock_Valorizado"]

    if fichas:
        art_sel = st.selectbox("Seleccionar Artículo", list(fichas.keys()))
        df_art = pd.DataFrame(fichas[art_sel])

        if not df_art.empty:
            df_display = df_art.copy()
            
            columnas_multinivel = pd.MultiIndex.from_tuples([
                ("Datos Operación", "Fecha"),
                ("Datos Operación", "Concepto"),
                ("ENTRADAS", "Cant."),
                ("ENTRADAS", "P. Unitario"),
                ("ENTRADAS", "Total"),
                ("SALIDAS", "Cant."),
                ("SALIDAS", "P. Unitario"),
                ("SALIDAS", "Total"),
                ("EXISTENCIAS", "Cant."),
                ("EXISTENCIAS", "$ PPP"),
                ("EXISTENCIAS", "Total Valorizado")
            ])
            
            df_display.columns = columnas_multinivel

            col_f1, col_f2 = st.columns([3, 1])
            col_f1.subheader(f"Ficha de Valuación: {art_sel}")

            pdf_ficha = generar_pdf_tabla_generica(f"FICHA DE STOCK PPP: {art_sel}", df_art, orientacion="landscape")
            col_f2.download_button("📄 Exportar Ficha (PDF)", pdf_ficha, f"Ficha_PPP_{art_sel}.pdf", "application/pdf")

            st.dataframe(
                df_display.style.format({
                    ("ENTRADAS", "Cant."): "{:,.0f}",
                    ("ENTRADAS", "P. Unitario"): "${:,.2f}",
                    ("ENTRADAS", "Total"): "${:,.2f}",
                    ("SALIDAS", "Cant."): "{:,.0f}",
                    ("SALIDAS", "P. Unitario"): "${:,.2f}",
                    ("SALIDAS", "Total"): "${:,.2f}",
                    ("EXISTENCIAS", "Cant."): "{:,.0f}",
                    ("EXISTENCIAS", "$ PPP"): "${:,.2f}",
                    ("EXISTENCIAS", "Total Valorizado"): "${:,.2f}"
                }),
                use_container_width=True
            )

            ultimo_reg = df_art.iloc[-1]
            m1, m2, m3 = st.columns(3)
            m1.metric("Stock Actual", f"{int(ultimo_reg['Saldo Cantidad'])} u.")
            m2.metric("Precio Promedio Ponderado ($PPP)", f"${ultimo_reg['Saldo PPP']:,.2f}")
            m3.metric("Valor Total del Inventario", f"${ultimo_reg['Saldo Total']:,.2f}")
    else:
        st.info("No hay artículos registrados con valuación de stock PPP.")

# ==========================================
# MÓDULO 5: BALANCE DE SUMAS Y SALDOS
# ==========================================
elif menu == "5. Sumas y Saldos":
    st.header("⚖️ Balance de Comprobación de Sumas y Saldos")

    if st.session_state.libro_diario:
        resumen = []

        for cuenta in st.session_state.plan_cuentas:
            debe = 0.0
            haber = 0.0
            for a in st.session_state.libro_diario:
                for r in a["Renglones"]:
                    if r["Cuenta"] == cuenta:
                        if r["Tipo"] == "Debe":
                            debe += r["Monto"]
                        else:
                            haber += r["Monto"]

            if debe > 0 or haber > 0:
                resumen.append({
                    "Cuenta": cuenta,
                    "Sumas Debe": debe,
                    "Sumas Haber": haber,
                    "Saldo Deudor": debe - haber if debe > haber else 0.0,
                    "Saldo Acreedor": haber - debe if haber > debe else 0.0
                })

        if resumen:
            df_resumen = pd.DataFrame(resumen)

            col_b1, col_b2 = st.columns([3, 1])
            col_b1.subheader("Balance General de Comprobación")

            pdf_balance = generar_pdf_tabla_generica("BALANCE DE COMPROBACION DE SUMAS Y SALDOS", df_resumen)
            col_b2.download_button("📄 Exportar Balance (PDF)", pdf_balance, "Balance_Sumas_y_Saldos.pdf", "application/pdf")

            st.dataframe(df_resumen, use_container_width=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Debe", f"${df_resumen['Sumas Debe'].sum():,.2f}")
            c2.metric("Total Haber", f"${df_resumen['Sumas Haber'].sum():,.2f}")
            c3.metric("Total Acreedor", f"${df_resumen['Saldo Acreedor'].sum():,.2f}")
            c4.metric("Total Deudor", f"${df_resumen['Saldo Deudor'].sum():,.2f}")