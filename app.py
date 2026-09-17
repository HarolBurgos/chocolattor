"""
Chocolattor Web v5
Calculadora de Costos para Chocolate
| AECID | Cooperacion Espanola | Ayuda en Accion
"""
import streamlit as st
import json, math, io
from datetime import datetime
from modelos import (MateriaPrima, InsumoMP, InsumoGeneral, CostoFijo,
                     OtroGasto, ItemFormulacion, Presentacion, calcular_tir)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, PageBreak, HRFlowable)
    RPDF = True
except ImportError:
    RPDF = False

try:
    import matplotlib.pyplot as plt
    MPL = True
except ImportError:
    MPL = False

# =============================================================================
#  CONFIGURACION
# =============================================================================
st.set_page_config(
    page_title="Chocolattor - Calculadora de Costos",
    page_icon="images/Icono.png" if __import__("os").path.exists("images/Icono.png") else "🍫",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background-color: #FFF8F2; }
section[data-testid="stSidebar"] { background-color: #006776 !important; }
section[data-testid="stSidebar"] * { color: #FFE8D6 !important; }
h1 { color: #E8490F !important; }
h2, h3 { color: #007A87 !important; }
.stButton > button {
    background-color: #F4A261 !important;
    color: #2C1A0E !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: bold !important;
}
.stButton > button:hover { background-color: #007A87 !important; color: white !important; }
[data-testid="metric-container"] {
    background: #F87C56; border: 1px solid #F4A261;
    border-radius: 8px; padding: 8px;
}
.info-box {
    background: #F87C56; border-left: 4px solid #007A87;
    padding: 10px 14px; border-radius: 4px;
    margin-bottom: 12px; font-size: .9em; color: #007A87;
}
/* Botones dentro del sidebar */
section[data-testid="stSidebar"] .stDownloadButton > button {
    background-color: #F4A261 !important;
    color: #2C1A0E !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: bold !important;
    width: 100% !important;
}
section[data-testid="stSidebar"] .stDownloadButton > button:hover {
    background-color: #007A87 !important;
    color: white !important;
}
section[data-testid="stSidebar"] .stButton > button {
    background-color: #F4A261 !important;
    color: #2C1A0E !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: bold !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #007A87 !important;
    color: white !important;
}
/* File uploader dentro del sidebar */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background-color: #2C1A0E !important;
    border: 2px dashed #F4A261 !important;
    border-radius: 8px !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] * {
    color: #FFE8D6 !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    background-color: #F4A261 !important;
    color: #2C1A0E !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: bold !important;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background-color: #2C1A0E !important;
}
/* Labels del sidebar */
section[data-testid="stSidebar"] label {
    color: #FFE8D6 !important;
}
section[data-testid="stSidebar"] small {
    color: #F4A261 !important;
}
.precio-box {
    background: #EDF7F6; border: 2px solid #007A87;
    border-radius: 10px; padding: 14px 20px;
    text-align: center; font-size: 1.3em;
    font-weight: bold; color: #007A87; margin: 10px 0;
}
.footer {
    text-align: center; color: #914B2B; font-size: .8em;
    margin-top: 30px; padding-top: 10px;
    border-top: 1px solid #F4A261;
}
</style>
""", unsafe_allow_html=True)

# =============================================================================
#  ESTADO DE SESION
# =============================================================================
def init():
    defaults = {"mps": [], "igs": [], "pres": [], "cfs": [],
                "pres_idx": 0, "mp_idx": 0}
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

def MPS():  return st.session_state.mps
def IGS():  return st.session_state.igs
def PRES(): return st.session_state.pres
def CFS():  return st.session_state.cfs
def TCF():  return sum(c.monto for c in CFS())

def pres_actual():
    ps = PRES()
    if not ps: return None
    idx = min(st.session_state.pres_idx, len(ps) - 1)
    return ps[idx]

# =============================================================================
#  GENERAR PDF
# =============================================================================
def generar_pdf():
    tcf = TCF(); mps = MPS(); igs = IGS(); pres = PRES(); cfs = CFS()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=1.8*cm, leftMargin=1.8*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    C_NAR  = colors.HexColor("#E8490F")
    C_TURQ = colors.HexColor("#007A87")
    C_HDR  = colors.HexColor("#FFE5CC")
    C_FILA = colors.HexColor("#FFF8F2")

    h1 = ParagraphStyle("h1", fontSize=18, textColor=C_NAR,
                         fontName="Helvetica-Bold", spaceAfter=4)
    h2 = ParagraphStyle("h2", fontSize=11, textColor=C_TURQ,
                         fontName="Helvetica-Bold", spaceAfter=6)
    no = ParagraphStyle("no", fontSize=9, fontName="Helvetica", spaceAfter=3)
    bo = ParagraphStyle("bo", fontSize=9, fontName="Helvetica-Bold")
    ft = ParagraphStyle("ft", fontSize=7, fontName="Helvetica",
                         textColor=colors.grey, alignment=TA_CENTER)

    def base_ts():
        return TableStyle([
            ("FONTNAME",  (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",  (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), C_HDR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_FILA, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0C8C0")),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ])

    def sep(): return HRFlowable(width="100%", thickness=1, color=C_NAR,
                                  spaceAfter=8, spaceBefore=4)

    s = []
    s += [Paragraph("CHOCOLATTOR", h1),
          Paragraph("Reporte General de Costos", h2),
          Paragraph("Generado: " + datetime.now().strftime("%d/%m/%Y %H:%M") +
                    "   |   ASOCACAO - Policarpa, Narino", no),
          sep()]

    # 1. Materias Primas
    s.append(Paragraph("1. Materias Primas del Cacao", h2))
    if mps:
        d = [["Materia Prima", "Batch kg", "Rendim %", "Costo/kg ($)", "Costo/g ($)", "Insumos"]]
        for mp in mps:
            d.append([mp.nombre, str(round(mp.batch_kg, 1)),
                      str(round(mp.rendimiento, 1)) + "%",
                      "$" + str(round(mp.costo_por_kg(), 1)),
                      "$" + str(round(mp.costo_por_gramo(), 4)),
                      str(len(mp.insumos))])
        t = Table(d, colWidths=[4.5*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm])
        t.setStyle(base_ts()); s.append(t)
        for mp in mps:
            if mp.insumos:
                s += [Spacer(1, 6), Paragraph("Insumos: " + mp.nombre, bo)]
                di = [["Insumo", "Cantidad", "Unidad", "C.Unit ($)", "C.Total ($)"]]
                for ins in mp.insumos:
                    di.append([ins.nombre, str(round(ins.cantidad, 1)), ins.unidad,
                                "$" + str(round(ins.costo_unit, 1)),
                                "$" + str(round(ins.costo_total(), 1))])
                t2 = Table(di, colWidths=[4*cm, 2.5*cm, 2*cm, 3*cm, 3*cm])
                t2.setStyle(base_ts()); s.append(t2)
    else:
        s.append(Paragraph("(Sin materias primas registradas)", no))
    s += [Spacer(1, 8), sep()]

    # 2. Presentaciones
    s.append(Paragraph("2. Resumen de Presentaciones", h2))
    if pres:
        d = [["Presentacion", "Peso g", "CV ($)", "CF ($)", "Costo Tot ($)",
              "IVA%", "Gan%", "Precio ($)"]]
        for p in pres:
            d.append([p.nombre, str(int(p.peso_g)),
                      "$" + str(round(p.costo_variable_unit(mps, igs), 1)),
                      "$" + str(round(p.costo_fijo_unit(tcf), 1)),
                      "$" + str(round(p.costo_total_unit(mps, igs, tcf), 1)),
                      str(round(p.iva_pct, 1)) + "%",
                      str(round(p.ganancia_pct, 1)) + "%",
                      "$" + str(round(p.precio_venta(mps, igs, tcf), 1))])
        t = Table(d, colWidths=[3.5*cm, 1.2*cm, 2*cm, 2*cm, 2.2*cm, 1.4*cm, 1.4*cm, 2*cm])
        t.setStyle(base_ts()); s.append(t)
    else:
        s.append(Paragraph("(Sin presentaciones)", no))
    s += [Spacer(1, 8), sep()]

    # 3. Formulacion
    s.append(Paragraph("3. Formulacion por Presentacion", h2))
    for p in pres:
        s += [Spacer(1, 6), Paragraph(p.nombre + " (" + str(int(p.peso_g)) + " g):", bo)]
        if not p.formulacion:
            s.append(Paragraph("(Sin formulacion)", no)); continue
        df = [["Ingrediente", "Prop %", "Gramos", "$/g", "Costo ($)"]]
        suma = 0.0
        for item in p.formulacion:
            g = (item.proporcion_pct / 100.0) * p.peso_g
            cpg = p.cpg(item.nombre, mps, igs)
            suma += item.proporcion_pct
            df.append([item.nombre, str(round(item.proporcion_pct, 1)) + "%",
                        str(round(g, 1)), "$" + str(round(cpg, 4)),
                        "$" + str(round(g * cpg, 4))])
        cvi = p.costo_variable_insumos(mps, igs)
        df.append(["TOTAL", str(round(suma, 1)) + "%",
                   str(int(p.peso_g)) + " g", "", "$" + str(round(cvi, 4))])
        tf = Table(df, colWidths=[4*cm, 2*cm, 2.5*cm, 2.5*cm, 2.5*cm])
        sty = base_ts()
        sty.add("FONTNAME", (0, len(df)-1), (-1, len(df)-1), "Helvetica-Bold")
        sty.add("BACKGROUND", (0, len(df)-1), (-1, len(df)-1), C_HDR)
        tf.setStyle(sty); s.append(tf)
    s += [Spacer(1, 8), sep()]

    # 4. Costos Fijos
    s.append(Paragraph("4. Costos Fijos Mensuales", h2))
    if cfs:
        dc = [["Nombre", "Categoria", "Monto ($)"]]
        for c in cfs:
            dc.append([c.nombre, c.categoria, "$" + str(round(c.monto, 1))])
        dc.append(["TOTAL", "", "$" + str(round(tcf, 1))])
        tc = Table(dc, colWidths=[6*cm, 4*cm, 4*cm])
        sty2 = base_ts()
        sty2.add("FONTNAME",   (0, len(dc)-1), (-1, len(dc)-1), "Helvetica-Bold")
        sty2.add("BACKGROUND", (0, len(dc)-1), (-1, len(dc)-1), C_HDR)
        tc.setStyle(sty2); s.append(tc)
    else:
        s.append(Paragraph("(Sin costos fijos)", no))
    s += [Spacer(1, 8), sep()]

    # 5. Punto de Equilibrio
    s.append(Paragraph("5. Punto de Equilibrio", h2))
    s.append(Paragraph("CF Mensuales: $" + str(round(tcf, 1)), no))
    if pres:
        dp = [["Presentacion", "Precio ($)", "CV ($)", "MC ($)", "PE Unid", "PE Ing ($)"]]
        for p in pres:
            pv = p.precio_venta(mps, igs, tcf)
            cvu = p.costo_variable_unit(mps, igs)
            mc = pv - cvu
            if mc > 0:
                pe_u = math.ceil(tcf / mc)
                dp.append([p.nombre, "$" + str(round(pv, 1)), "$" + str(round(cvu, 1)),
                            "$" + str(round(mc, 1)), str(int(pe_u)),
                            "$" + str(round(pe_u * pv, 1))])
            else:
                dp.append([p.nombre, "$" + str(round(pv, 1)), "$" + str(round(cvu, 1)),
                            "$" + str(round(mc, 1)), "N/A", "N/A"])
        tp = Table(dp, colWidths=[3.5*cm, 2*cm, 2*cm, 2*cm, 2.5*cm, 3*cm])
        tp.setStyle(base_ts()); s.append(tp)
    s.append(PageBreak())

    # 6. Flujo de Caja 12 meses
    s.append(Paragraph("6. Flujo de Caja Proyectado (12 meses)", h2))
    s.append(Paragraph("Basado en cantidades mensuales configuradas.", no))
    dfc = [["Mes", "Ingresos ($)", "CV ($)", "CF ($)", "Flujo Neto ($)", "Saldo ($)"]]
    saldo = 0.0
    for mes in range(1, 13):
        ing = sum(p.cantidad_mensual * p.precio_venta(mps, igs, tcf) for p in pres)
        cv  = sum(p.cantidad_mensual * p.costo_variable_unit(mps, igs) for p in pres)
        fn  = ing - cv - tcf; saldo += fn
        dfc.append([str(mes), "$"+str(round(ing,1)), "$"+str(round(cv,1)),
                    "$"+str(round(tcf,1)), "$"+str(round(fn,1)), "$"+str(round(saldo,1))])
    tfc = Table(dfc, colWidths=[1.5*cm, 3*cm, 2.5*cm, 2.5*cm, 3*cm, 3*cm])
    sfc = base_ts()
    for i, row in enumerate(dfc[1:], 1):
        try:
            if float(str(row[4]).replace("$", "").replace(",", "")) < 0:
                sfc.add("TEXTCOLOR", (4, i), (4, i), colors.red)
                sfc.add("FONTNAME",  (4, i), (4, i), "Helvetica-Bold")
        except Exception: pass
    tfc.setStyle(sfc); s.append(tfc)

    s += [Spacer(1, 20),
          HRFlowable(width="100%", thickness=0.5, color=colors.grey),
          Spacer(1, 4),
          Paragraph("Chocolattor v5 Web  |   Ayuda en Accion |  " +
                    "Agencia Española de Cooperación Internacional para el Desarrollo - AECID |  " +
                    datetime.now().strftime("%d/%m/%Y %H:%M"), ft)]
    doc.build(s)
    return buf.getvalue()

# =============================================================================
#  SIDEBAR
# =============================================================================
with st.sidebar:
    # Logo ASOCACAO
    import os
    logo_asoc = "images/Logo_asociacion.png"
    if os.path.exists(logo_asoc):
        st.image(logo_asoc, width=150)
    else:
        st.markdown("### ASOCACAO")
    st.markdown("## Chocolattor")
    st.markdown("*Calculadora de Costos*")
    st.divider()

    pagina = st.radio("", [
        "1. Materias Primas",
        "2. Insumos Generales",
        "3. Presentaciones",
        "4. Formulacion",
        "5. Costos Fijos",
        "6. Produccion Mensual",
        "7. Otros Gastos",
        "8. IVA y Ganancia",
        "9. Punto de Equilibrio",
        "10. TIR / VPN",
        "11. Flujo de Caja",
        "12. Graficas",
    ], label_visibility="collapsed")

    st.divider()

    # Precio actual
    p_act = pres_actual()
    if p_act:
        pv = p_act.precio_venta(MPS(), IGS(), TCF())
        st.markdown(f"""
        <div style='background:#2C1A0E;padding:10px;border-radius:8px;text-align:center;'>
        <div style='color:#F4A261;font-size:.8em;margin-bottom:4px;'>{p_act.nombre}</div>
        <div style='color:#FFE8D6;font-size:1.2em;font-weight:bold;'>Precio: ${pv:,.1f}</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("")

    st.divider()
    st.markdown("**Archivo**")

    # GUARDAR
    datos_guardar = json.dumps({
        "version": "5_web",
        "materias_primas":   [m.to_dict() for m in MPS()],
        "insumos_generales": [i.to_dict() for i in IGS()],
        "presentaciones":    [p.to_dict() for p in PRES()],
        "costos_fijos":      [c.to_dict() for c in CFS()],
    }, indent=4, ensure_ascii=False)

    st.download_button(
        label="Guardar calculo (.json)",
        data=datos_guardar,
        file_name="chocolattor_" + datetime.now().strftime("%Y%m%d_%H%M") + ".json",
        mime="application/json",
        use_container_width=True,
    )

    # CARGAR
    archivo = st.file_uploader("Cargar calculo (.json)", type=["json"])
    if archivo is not None:
        try:
            data = json.load(archivo)
            st.session_state.mps  = [MateriaPrima.from_dict(d)
                                      for d in data.get("materias_primas", [])]
            st.session_state.igs  = [InsumoGeneral.from_dict(d)
                                      for d in data.get("insumos_generales", [])]
            st.session_state.pres = [Presentacion.from_dict(d)
                                      for d in data.get("presentaciones", [])]
            st.session_state.cfs  = [CostoFijo.from_dict(d)
                                      for d in data.get("costos_fijos", [])]
            st.session_state.pres_idx = 0
            st.success("Cargado correctamente")
            st.rerun()
        except Exception as e:
            st.error("Error al cargar: " + str(e))

    # EXPORTAR PDF
    if RPDF:
        if st.button("Exportar PDF", use_container_width=True):
            try:
                pdf_bytes = generar_pdf()
                st.download_button(
                    label="Descargar PDF",
                    data=pdf_bytes,
                    file_name="chocolattor_reporte_" + datetime.now().strftime("%Y%m%d") + ".pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error("Error al generar PDF: " + str(e))
    else:
        st.caption("Para PDF: pip install reportlab")

    st.divider()
    st.caption("Una produccion de:\nFundación Ayuda en Acción | Agencia Española de Cooperacion \nInternacional para el Desarrollo")

# =============================================================================
#  UTILIDADES
# =============================================================================
def info(txt):
    st.markdown(f'<div class="info-box">ℹ️ {txt}</div>', unsafe_allow_html=True)

def pie():
    import os
    st.divider()
    tirilla = "images/Tirilla_OPC.png"
    if os.path.exists(tirilla):
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            st.image(tirilla, use_container_width=True)
    st.markdown("""<div class="footer">
    Chocolattor v5 Web | Una produccion de: Ayuda en Accion y La Agencia Espanola de Cooperación Internacional para el Desarrollo - AECID
    </div>""", unsafe_allow_html=True)

def selector_pres(key):
    ps = PRES()
    if not ps: return None
    nombres = [p.nombre for p in ps]
    idx = min(st.session_state.pres_idx, len(ps) - 1)
    nuevo = st.selectbox("Presentacion activa:", range(len(nombres)),
                         format_func=lambda i: nombres[i],
                         index=idx, key=key)
    st.session_state.pres_idx = nuevo
    return ps[nuevo]

# =============================================================================
#  1. MATERIAS PRIMAS
# =============================================================================
def p1():
    st.title("1. Materias Primas del Cacao")
    info("Crea cada MP (Licor, Manteca, Cocoa, Nibs u Otra), agrega sus insumos "
         "de batch y calcula el costo/kg. Quedaran disponibles en Formulacion.")

    mps = MPS()

    if mps:
        st.subheader("Materias Primas creadas")
        filas = [{"MP": mp.nombre,
                  "Batch kg": round(mp.batch_kg, 1),
                  "Rendim %": f"{mp.rendimiento:.1f}%",
                  "Costo/kg ($)": f"${mp.costo_por_kg():,.1f}",
                  "Costo/g ($)":  f"${mp.costo_por_gramo():,.4f}",
                  "N Insumos": len(mp.insumos)} for mp in mps]
        st.dataframe(filas, use_container_width=True, hide_index=True)

        nombres = [m.nombre for m in mps]
        idx = st.selectbox("Seleccionar MP para ver/editar:",
                           range(len(nombres)),
                           format_func=lambda i: nombres[i],
                           index=min(st.session_state.mp_idx, len(mps)-1),
                           key="mp_sel")
        st.session_state.mp_idx = idx
        mp = mps[idx]

        st.divider()
        st.subheader(f"Batch: {mp.nombre}")
        c1, c2, c3 = st.columns(3)
        mp.batch_kg    = c1.number_input("Batch (kg):", value=float(mp.batch_kg),
                                          min_value=0.1, step=1.0, key="mp_bat")
        mp.rendimiento = c2.number_input("Rendimiento (%):", value=float(mp.rendimiento),
                                          min_value=1.0, max_value=100.0,
                                          step=1.0, key="mp_ren")
        c3.metric("Costo por kg", f"${mp.costo_por_kg():,.1f}")

        if mp.insumos:
            filas_i = [{"Nombre": i.nombre, "Cantidad": i.cantidad, "Unidad": i.unidad,
                         "Costo Unit ($)": f"${i.costo_unit:,.1f}",
                         "Costo Total ($)": f"${i.costo_total():,.1f}"} for i in mp.insumos]
            st.dataframe(filas_i, use_container_width=True, hide_index=True)
            total_b = sum(i.costo_total() for i in mp.insumos)
            st.info(f"Total costo por batch: **${total_b:,.1f}**  |  "
                    f"Costo/kg: **${mp.costo_por_kg():,.1f}**")

            with st.expander("Eliminar un insumo"):
                del_i = st.selectbox("Insumo a eliminar:",
                                     [i.nombre for i in mp.insumos], key="del_ins")
                if st.button("Eliminar insumo", key="btn_del_ins"):
                    mp.insumos = [i for i in mp.insumos if i.nombre != del_i]
                    st.rerun()

        with st.expander("Agregar Insumo o gasto por Batch", expanded=not mp.insumos):
            c1, c2, c3, c4 = st.columns(4)
            nom_i  = c1.text_input("Nombre:", key="ins_nom")
            cant_i = c2.number_input("Cantidad:", min_value=0.0, step=0.5, key="ins_cant")
            uni_i  = c3.text_input("Unidad:", placeholder="kg, lb, gr...", key="ins_uni")
            cu_i   = c4.number_input("Costo Unitario ($):", min_value=0.0,
                                      step=1000.0, key="ins_cu")
            if st.button("Agregar Insumo", type="primary", key="btn_add_ins"):
                if not nom_i or cant_i <= 0 or cu_i < 0:
                    st.warning("Completa todos los campos.")
                else:
                    mp.insumos.append(InsumoMP(nom_i, cant_i, uni_i, cu_i))
                    st.success(f"'{nom_i}' agregado.")
                    st.rerun()

        if st.button("Eliminar esta Materia Prima", type="secondary", key="del_mp_btn"):
            mps.pop(idx)
            st.session_state.mp_idx = 0
            st.rerun()

    st.divider()
    st.subheader("Agregar Nueva Materia Prima")
    st.caption("Referencia: Licor 75-80% | Manteca 45-50% | Cocoa 50-55% | Nibs 80-85%")
    c1, c2, c3, c4 = st.columns(4)
    tipo  = c1.selectbox("Tipo:", MateriaPrima.TIPOS, key="mp_tipo")
    nom_m = c2.text_input("Nombre (si es Otra):", key="mp_nom")
    bat_m = c3.number_input("Batch (kg):", value=30.0, min_value=0.1,
                             step=1.0, key="mp_bat_new")
    ren_m = c4.number_input("Rendimiento (%):", value=75.0, min_value=1.0,
                             max_value=100.0, step=1.0, key="mp_ren_new")

    if st.button("Crear Materia Prima", type="primary", key="btn_crear_mp"):
        nombre_final = nom_m.strip() if tipo == "Otra" else tipo
        if not nombre_final:
            st.error("Escribe un nombre o selecciona un tipo.")
        elif any(m.nombre.lower() == nombre_final.lower() for m in mps):
            st.error(f"Ya existe '{nombre_final}'.")
        else:
            st.session_state.mps.append(MateriaPrima(nombre_final, bat_m, ren_m))
            st.success(f"'{nombre_final}' creada. Ahora agrega sus insumos de batch.")
            st.rerun()

# =============================================================================
#  2. INSUMOS GENERALES
# =============================================================================
def p2():
    st.title("2. Insumos Generales")
    info("Azucar, leche, lecitina y otros ingredientes adicionales. "
         "Unidades: kg, gr/g, lb, oz, ml, l/litros, unidad")

    igs = IGS()
    if igs:
        filas = [{"Nombre": i.nombre, "Cantidad": i.cantidad, "Unidad": i.unidad,
                  "Costo Total ($)": f"${i.costo_total:,.1f}",
                  "$/gramo": f"${i.costo_por_gramo():,.4f}"} for i in igs]
        st.dataframe(filas, use_container_width=True, hide_index=True)
        with st.expander("Eliminar insumo general"):
            del_ig = st.selectbox("Insumo:", [i.nombre for i in igs], key="del_ig")
            if st.button("Eliminar", key="btn_del_ig"):
                st.session_state.igs = [i for i in igs if i.nombre != del_ig]
                st.rerun()

    st.divider()
    st.subheader("Agregar Insumo General")
    c1, c2, c3, c4 = st.columns(4)
    nom_ig  = c1.text_input("Nombre:", key="ig_nom")
    cant_ig = c2.number_input("Cantidad:", min_value=0.0, step=0.5, key="ig_cant")
    uni_ig  = c3.text_input("Unidad:", placeholder="kg, gr, litros...", key="ig_uni")
    ct_ig   = c4.number_input("Costo Total ($):", min_value=0.0, step=1000.0, key="ig_ct")

    if st.button("Agregar Insumo General", type="primary", key="btn_add_ig"):
        if not nom_ig or cant_ig <= 0 or ct_ig < 0 or not uni_ig:
            st.warning("Completa todos los campos.")
        elif any(i.nombre.lower() == nom_ig.lower() for i in igs):
            st.error(f"Ya existe '{nom_ig}'.")
        else:
            nuevo = InsumoGeneral(nom_ig, cant_ig, uni_ig, ct_ig)
            st.session_state.igs.append(nuevo)
            st.success(f"'{nom_ig}' agregado. Costo/g: ${nuevo.costo_por_gramo():,.4f}")
            st.rerun()

# =============================================================================
#  3. PRESENTACIONES
# =============================================================================
def p3():
    st.title("3. Presentaciones de Producto")
    info("Cada presentacion es un producto terminado con nombre y peso. "
         "Ejemplo: 'Chocolatina Chitena 90g'")

    ps = PRES(); mps = MPS(); igs = IGS(); tcf = TCF()

    if ps:
        filas = []
        for p in ps:
            ctu = p.costo_total_unit(mps, igs, tcf)
            pv  = p.precio_venta(mps, igs, tcf)
            filas.append({"Presentacion": p.nombre,
                          "Peso g": int(p.peso_g),
                          "Costo Total ($)": f"${ctu:,.1f}",
                          "Precio Venta ($)": f"${pv:,.1f}",
                          "IVA %": f"{p.iva_pct:.1f}%",
                          "Ganancia %": f"{p.ganancia_pct:.1f}%",
                          "Prod/mes": int(p.cantidad_mensual)})
        st.dataframe(filas, use_container_width=True, hide_index=True)

        nombres = [p.nombre for p in ps]
        idx = st.selectbox("Presentacion activa (pasos siguientes):",
                           range(len(nombres)),
                           format_func=lambda i: nombres[i],
                           index=min(st.session_state.pres_idx, len(ps)-1),
                           key="pres_act")
        st.session_state.pres_idx = idx
        p_sel = ps[idx]
        pv = p_sel.precio_venta(mps, igs, tcf)
        ctu = p_sel.costo_total_unit(mps, igs, tcf)
        c1, c2, c3 = st.columns(3)
        c1.metric("Precio de Venta", f"${pv:,.1f}")
        c2.metric("Costo Total Unit.", f"${ctu:,.1f}")
        c3.metric("Margen", f"${pv - ctu:,.1f}")

        if st.button("Eliminar presentacion seleccionada", type="secondary"):
            ps.pop(idx)
            st.session_state.pres_idx = 0
            st.rerun()

    st.divider()
    st.subheader("Crear Nueva Presentacion")
    c1, c2 = st.columns(2)
    nom_p  = c1.text_input("Nombre:", placeholder="Chocolatina Chitena", key="pnom")
    peso_p = c2.number_input("Peso (g):", min_value=1.0, value=90.0, step=5.0, key="ppeso")

    if st.button("Crear Presentacion", type="primary", key="btn_crear_p"):
        if not nom_p:
            st.error("El nombre es requerido.")
        elif peso_p <= 0:
            st.error("El peso debe ser mayor a 0.")
        elif any(p.nombre.lower() == nom_p.lower() for p in ps):
            st.error(f"Ya existe '{nom_p}'.")
        else:
            st.session_state.pres.append(Presentacion(nom_p, peso_p))
            st.session_state.pres_idx = len(PRES()) - 1
            st.success(f"'{nom_p}' creada. Ahora configura su Formulacion (Paso 4).")
            st.rerun()

# =============================================================================
#  4. FORMULACION
# =============================================================================
def p4():
    st.title("4. Formulacion")
    if not PRES():
        st.warning("Crea una presentacion primero (Paso 3)."); return

    p = selector_pres("form_psel")
    if not p: return

    mps = MPS(); igs = IGS()
    info(f"Proporciones de ingredientes para **{p.nombre}** ({int(p.peso_g)} g). "
         "La suma de proporciones debe ser 100%.")

    suma = sum(item.proporcion_pct for item in p.formulacion)
    cvi  = p.costo_variable_insumos(mps, igs)
    c1, c2, c3 = st.columns(3)
    c1.metric("Peso presentacion", f"{int(p.peso_g)} g")
    c2.metric("Suma proporciones", f"{suma:.1f}%",
              delta="OK" if 99 <= suma <= 101 else "Debe ser 100%",
              delta_color="normal" if 99 <= suma <= 101 else "inverse")
    c3.metric("Costo variable insumos", f"${cvi:,.4f}")

    if p.formulacion:
        filas_f = []
        for item in p.formulacion:
            g   = (item.proporcion_pct / 100.0) * p.peso_g
            cpg = p.cpg(item.nombre, mps, igs)
            filas_f.append({"Ingrediente": item.nombre,
                             "Prop %": f"{item.proporcion_pct:.1f}%",
                             "Cantidad g": f"{g:.1f}",
                             "$/g": f"${cpg:.4f}",
                             "Costo Total ($)": f"${g * cpg:.4f}"})
        st.dataframe(filas_f, use_container_width=True, hide_index=True)

        with st.expander("Eliminar ingrediente"):
            del_f = st.selectbox("Ingrediente:", [i.nombre for i in p.formulacion],
                                 key="del_form")
            if st.button("Eliminar", key="btn_del_form"):
                p.formulacion = [i for i in p.formulacion if i.nombre != del_f]
                st.rerun()

    st.divider()
    st.subheader("Agregar / Reemplazar Ingrediente")
    opciones = [mp.nombre for mp in mps] + [ig.nombre for ig in igs]
    if not opciones:
        st.warning("Agrega Materias Primas e Insumos Generales primero."); return

    c1, c2 = st.columns(2)
    ing_sel = c1.selectbox("Ingrediente:", opciones, key="form_ing")
    prop    = c2.number_input("Proporcion (%):", min_value=0.0,
                               max_value=100.0, step=1.0, key="form_prop")

    cpg_prev = p.cpg(ing_sel, mps, igs)
    g_prev   = (prop / 100.0) * p.peso_g
    c3, c4 = st.columns(2)
    c3.metric("$/gramo del ingrediente", f"${cpg_prev:.4f}")
    c4.metric("Costo total en formulacion", f"${g_prev * cpg_prev:.4f}")

    if st.button("Agregar a Formulacion", type="primary", key="btn_add_form"):
        if not ing_sel or prop <= 0:
            st.warning("Selecciona ingrediente y define la proporcion.")
        else:
            p.formulacion = [i for i in p.formulacion if i.nombre != ing_sel]
            p.formulacion.append(ItemFormulacion(ing_sel, prop))
            st.success(f"'{ing_sel}' con {prop:.1f}% agregado.")
            st.rerun()

# =============================================================================
#  5. COSTOS FIJOS
# =============================================================================
def p5():
    st.title("5. Costos Fijos Mensuales")
    info("Gastos que no dependen del volumen: arriendo, nomina, servicios, depreciacion...")

    cfs = CFS(); tcf = TCF()
    st.metric("Total Costos Fijos Mensuales", f"${tcf:,.1f}")

    if cfs:
        filas = [{"Nombre": c.nombre, "Categoria": c.categoria,
                  "Monto ($)": f"${c.monto:,.1f}"} for c in cfs]
        st.dataframe(filas, use_container_width=True, hide_index=True)
        with st.expander("Eliminar costo fijo"):
            del_cf = st.selectbox("Costo:", [c.nombre for c in cfs], key="del_cf")
            if st.button("Eliminar", key="btn_del_cf"):
                st.session_state.cfs = [c for c in cfs if c.nombre != del_cf]
                st.rerun()

    st.divider()
    st.subheader("Agregar Costo Fijo")
    c1, c2, c3 = st.columns(3)
    nom_cf  = c1.text_input("Nombre:", key="cf_nom")
    cat_cf  = c2.selectbox("Categoria:", CostoFijo.CATEGORIAS, key="cf_cat")
    mont_cf = c3.number_input("Monto Mensual ($):", min_value=0.0,
                               step=10000.0, key="cf_mont")

    if st.button("Agregar Costo Fijo", type="primary", key="btn_add_cf"):
        if not nom_cf or mont_cf <= 0:
            st.warning("Nombre y monto son requeridos.")
        else:
            st.session_state.cfs.append(CostoFijo(nom_cf, mont_cf, cat_cf))
            st.success(f"'{nom_cf}' agregado.")
            st.rerun()

# =============================================================================
#  6. PRODUCCION MENSUAL
# =============================================================================
def p6():
    st.title("6. Produccion Mensual")
    if not PRES():
        st.warning("Crea una presentacion primero."); return

    p = selector_pres("prod_psel")
    if not p: return

    tcf = TCF(); mps = MPS(); igs = IGS()
    info(f"Cuantas unidades de **{p.nombre}** produces al mes. "
         "Costo Fijo Unitario = CF Totales / Unidades al mes.")

    cant = st.number_input("Unidades producidas por mes:",
                           min_value=0.0, value=float(p.cantidad_mensual),
                           step=10.0, key="prod_cant")
    p.cantidad_mensual = cant

    cfu = tcf / cant if cant > 0 else 0.0
    cvi = p.costo_variable_insumos(mps, igs)
    cog = p.costo_otros()
    cvu = cvi + cog
    ctu = cvu + cfu
    pv  = p.precio_venta(mps, igs, tcf)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CF Totales Mensual",   f"${tcf:,.1f}")
    c2.metric("Costo Fijo Unitario",  f"${cfu:,.1f}")
    c3.metric("Costo Variable Unit.", f"${cvu:,.1f}")
    c4.metric("Costo Total Unitario", f"${ctu:,.1f}")

    st.markdown(f'<div class="precio-box">Precio de Venta de {p.nombre}: ${pv:,.1f}</div>',
                unsafe_allow_html=True)

# =============================================================================
#  7. OTROS GASTOS
# =============================================================================
def p7():
    st.title("7. Otros Gastos Unitarios")
    if not PRES():
        st.warning("Crea una presentacion primero."); return

    p = selector_pres("og_psel")
    if not p: return

    tcf = TCF(); mps = MPS(); igs = IGS()
    info(f"Costos adicionales por unidad de **{p.nombre}**: "
         "empaque, embalaje, etiqueta, mercadeo...")

    cvi = p.costo_variable_insumos(mps, igs)
    cog = p.costo_otros()
    cfu = p.costo_fijo_unit(tcf)
    ctu = cvi + cog + cfu
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CV Insumos",        f"${cvi:,.1f}")
    c2.metric("Otros Gastos",      f"${cog:,.1f}")
    c3.metric("CF Unitario",       f"${cfu:,.1f}")
    c4.metric("Costo Total Unit.", f"${ctu:,.1f}")

    if p.otros_gastos:
        filas = [{"Nombre": g.nombre, "Costo Unitario ($)": f"${g.costo_unit:,.1f}"}
                 for g in p.otros_gastos]
        st.dataframe(filas, use_container_width=True, hide_index=True)
        st.info(f"Total otros gastos: **${p.costo_otros():,.1f}**")
        with st.expander("Eliminar gasto"):
            del_og = st.selectbox("Gasto:", [g.nombre for g in p.otros_gastos], key="del_og")
            if st.button("Eliminar", key="btn_del_og"):
                p.otros_gastos = [g for g in p.otros_gastos if g.nombre != del_og]
                st.rerun()

    st.divider()
    st.subheader("Agregar Gasto")
    c1, c2 = st.columns(2)
    nom_og = c1.text_input("Nombre:", placeholder="Empaque, Etiqueta...", key="og_nom")
    cu_og  = c2.number_input("Costo Unitario ($):", min_value=0.0,
                              step=100.0, key="og_cu")
    if st.button("Agregar Gasto", type="primary", key="btn_add_og"):
        if not nom_og or cu_og <= 0:
            st.warning("Completa todos los campos.")
        else:
            p.otros_gastos.append(OtroGasto(nom_og, cu_og))
            st.success(f"'{nom_og}' agregado.")
            st.rerun()

# =============================================================================
#  8. IVA Y GANANCIA
# =============================================================================
def p8():
    st.title("8. IVA y Ganancia")
    if not PRES():
        st.warning("Crea una presentacion primero."); return

    p = selector_pres("iva_psel")
    if not p: return

    tcf = TCF(); mps = MPS(); igs = IGS()
    ctu = p.costo_total_unit(mps, igs, tcf)
    info(f"Configura los margenes para **{p.nombre}**. "
         f"Costo Total Unitario: **${ctu:,.1f}**")

    c1, c2 = st.columns(2)
    iva = c1.number_input("% IVA:", min_value=0.0, max_value=100.0,
                           value=float(p.iva_pct), step=1.0, key="iva_v")
    gan = c2.number_input("% Ganancia:", min_value=0.0, max_value=500.0,
                           value=float(p.ganancia_pct), step=5.0, key="gan_v")
    p.iva_pct = iva; p.ganancia_pct = gan

    pv = p.precio_venta(mps, igs, tcf)
    mg = pv - ctu
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Costo Total Unit.", f"${ctu:,.1f}")
    c2.metric("IVA aplicado",      f"${ctu * iva / 100:,.1f}")
    c3.metric("Margen ($)",        f"${mg:,.1f}")
    c4.metric("PRECIO DE VENTA",   f"${pv:,.1f}")

    st.markdown(f'<div class="precio-box">Precio de Venta de {p.nombre}: ${pv:,.1f}</div>',
                unsafe_allow_html=True)

# =============================================================================
#  9. PUNTO DE EQUILIBRIO
# =============================================================================
def p9():
    st.title("9. Punto de Equilibrio")
    tcf = TCF(); mps = MPS(); igs = IGS()
    info(f"PE = Costos Fijos / Margen de Contribucion  |  "
         f"CF Mensuales Totales: **${tcf:,.1f}**")

    if not PRES():
        st.warning("No hay presentaciones creadas."); return

    filas = []; resultados = []
    for p in PRES():
        pv  = p.precio_venta(mps, igs, tcf)
        cvu = p.costo_variable_unit(mps, igs)
        mc  = pv - cvu
        if mc > 0:
            pe_u = math.ceil(tcf / mc)
            pe_i = pe_u * pv
            pu = f"{pe_u:,}"; pi = f"${pe_i:,.1f}"
        else:
            pe_u = float("inf"); pe_i = float("inf")
            pu = "N/A"; pi = "N/A"
        resultados.append((p, pv, cvu, mc, pe_u, pe_i))
        filas.append({"Presentacion": p.nombre,
                      "Precio ($)": f"${pv:,.1f}",
                      "CV Unit ($)": f"${cvu:,.1f}",
                      "MC ($)": f"${mc:,.1f}",
                      "PE Unid/mes": pu,
                      "PE Ingresos ($)": pi})

    st.dataframe(filas, use_container_width=True, hide_index=True)

    if MPL:
        validos = [(p, pv, cvu, mc, pe_u, pe_i) for p, pv, cvu, mc, pe_u, pe_i
                   in resultados if pe_u != float("inf")]
        if validos:
            p_g, pv_g, cvu_g, mc_g, pe_g, _ = validos[0]
            U = list(range(0, int(pe_g * 2) + 1))
            fig, ax = plt.subplots(figsize=(9, 4))
            ax.plot(U, [u * pv_g for u in U], color="#007A87", lw=2, label="Ingresos")
            ax.plot(U, [tcf + u * cvu_g for u in U], color="#E8490F", lw=2, label="Costos")
            ax.axvline(pe_g, color="#F4A261", ls="--", label=f"PE = {int(pe_g):,} und.")
            ax.fill_between(U, [u*pv_g for u in U], [tcf+u*cvu_g for u in U],
                            where=[u*pv_g >= tcf+u*cvu_g for u in U],
                            alpha=0.1, color="#007A87")
            ax.fill_between(U, [u*pv_g for u in U], [tcf+u*cvu_g for u in U],
                            where=[u*pv_g < tcf+u*cvu_g for u in U],
                            alpha=0.1, color="#E8490F")
            ax.set_title(f"Punto de Equilibrio — {p_g.nombre}")
            ax.set_xlabel("Unidades / mes"); ax.set_ylabel("$")
            ax.legend(); ax.grid(True, alpha=0.3)
            plt.tight_layout(); st.pyplot(fig); plt.close()

# =============================================================================
#  10. TIR / VPN
# =============================================================================
def p10():
    st.title("10. TIR / VPN — Evaluacion de Inversion")
    info("Evalua si el proyecto es financieramente viable.")
    if not PRES():
        st.warning("No hay presentaciones creadas."); return

    tcf = TCF(); mps = MPS(); igs = IGS()
    c1, c2, c3, c4 = st.columns(4)
    inv    = c1.number_input("Inversion Inicial ($):", min_value=0.0,
                              step=1000000.0, key="tir_inv")
    tasa_a = c2.number_input("Tasa descuento % anual:", min_value=0.0,
                              value=12.0, step=1.0, key="tir_tasa")
    meses  = c3.number_input("Periodos (meses):", min_value=1,
                              value=12, step=1, key="tir_mes")
    unid   = c4.number_input("Unidades/mes:", min_value=0.0,
                              step=10.0, key="tir_unid")

    pres_sel = st.selectbox("Presentacion:", [p.nombre for p in PRES()], key="tir_psel")
    p = next(x for x in PRES() if x.nombre == pres_sel)

    if st.button("Calcular TIR / VPN", type="primary", key="btn_tir"):
        if inv <= 0 or unid <= 0:
            st.warning("Ingresa la inversion y las unidades.")
        else:
            tasa_m = (1 + tasa_a / 100) ** (1/12) - 1
            pv_u   = p.precio_venta(mps, igs, tcf)
            cvu    = p.costo_variable_unit(mps, igs)
            fn     = unid * pv_u - unid * cvu - tcf
            flujos = [-inv] + [fn] * int(meses)
            vpn    = sum(fl / (1 + tasa_m) ** t for t, fl in enumerate(flujos))
            tir    = calcular_tir(flujos)
            tir_a  = (1 + tir) ** 12 - 1 if tir else None
            pb = None; acc = -inv
            for i in range(1, int(meses) + 1):
                acc += fn
                if acc >= 0 and pb is None: pb = i

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Flujo Neto Mensual", f"${fn:,.1f}")
            c2.metric("VPN", f"${vpn:,.1f}",
                      delta="VIABLE" if vpn > 0 else "NO VIABLE",
                      delta_color="normal" if vpn > 0 else "inverse")
            c3.metric("TIR Anual", f"{tir_a*100:.2f}%" if tir_a else "N/A")
            c4.metric("Payback",
                      f"{pb} mes(es)" if pb else f"No recupera en {int(meses)} meses",
                      delta_color="normal" if pb else "inverse")

            if MPL:
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
                ax1.bar(range(len(flujos)), flujos,
                        color=["#007A87" if fl >= 0 else "#E8490F" for fl in flujos])
                ax1.axhline(0, color="black", lw=0.8)
                ax1.set_title("Flujos por Periodo"); ax1.grid(True, alpha=0.3)
                acc_l = []; s = 0
                for fl in flujos: s += fl; acc_l.append(s)
                ax2.plot(range(len(acc_l)), acc_l, color="#F4A261", lw=2, marker="o")
                ax2.axhline(0, color="black", lw=0.8, ls="--")
                tir_txt = f"{tir_a*100:.1f}%" if tir_a else "N/A"
                ax2.set_title(f"Flujo Acumulado | VPN=${vpn:,.0f} | TIR={tir_txt}")
                ax2.grid(True, alpha=0.3)
                plt.tight_layout(); st.pyplot(fig); plt.close()

# =============================================================================
#  11. FLUJO DE CAJA
# =============================================================================
def p11():
    st.title("11. Flujo de Caja Proyectado")
    if not PRES():
        st.warning("No hay presentaciones creadas."); return

    tcf = TCF(); mps = MPS(); igs = IGS(); ps = PRES()
    c1, c2, c3 = st.columns(3)
    meses   = c1.number_input("Meses:", min_value=1, value=12, step=1, key="fc_mes")
    crec    = c2.number_input("Crecimiento/mes (%):", min_value=0.0,
                               value=0.0, step=0.5, key="fc_crec")
    saldo_i = c3.number_input("Saldo inicial ($):", min_value=0.0,
                               value=0.0, step=100000.0, key="fc_ini")

    st.subheader("Unidades vendidas / mes por presentacion")
    cols = st.columns(min(len(ps), 4))
    v_unids = {}
    for i, p in enumerate(ps):
        v_unids[p.nombre] = cols[i % 4].number_input(
            p.nombre, min_value=0.0,
            value=float(p.cantidad_mensual), step=10.0, key=f"fc_u_{i}")

    if st.button("Generar Flujo de Caja", type="primary", key="btn_fc"):
        filas = []; saldo = saldo_i
        ml = []; il = []; fnl = []; sl = []
        for mes in range(1, int(meses) + 1):
            factor = (1 + crec / 100) ** (mes - 1)
            ing = sum(v_unids.get(p.nombre, 0) * factor * p.precio_venta(mps, igs, tcf)
                      for p in ps)
            cv  = sum(v_unids.get(p.nombre, 0) * factor * p.costo_variable_unit(mps, igs)
                      for p in ps)
            fn = ing - cv - tcf; saldo += fn
            ml.append(mes); il.append(ing); fnl.append(fn); sl.append(saldo)
            filas.append({"Mes": mes,
                          "Ingresos ($)":   f"${ing:,.1f}",
                          "CV Total ($)":   f"${cv:,.1f}",
                          "CF ($)":         f"${tcf:,.1f}",
                          "Flujo Neto ($)": f"${fn:,.1f}",
                          "Saldo Acum ($)": f"${saldo:,.1f}"})

        st.dataframe(filas, use_container_width=True, hide_index=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Ingresos",   f"${sum(il):,.1f}")
        c2.metric("Total Flujo Neto", f"${sum(fnl):,.1f}",
                  delta_color="normal" if sum(fnl) >= 0 else "inverse")
        c3.metric("Saldo Final",      f"${sl[-1]:,.1f}",
                  delta_color="normal" if sl[-1] >= 0 else "inverse")

        if MPL:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
            ax1.bar(ml, fnl, color=["#007A87" if f >= 0 else "#E8490F" for f in fnl])
            ax1.axhline(0, color="black", lw=0.8)
            ax1.set_title("Flujo Neto Mensual"); ax1.grid(True, alpha=0.3)
            ax2.plot(ml, sl, color="#F4A261", lw=2, marker="o")
            ax2.axhline(0, color="black", lw=0.8, ls="--")
            ax2.fill_between(ml, sl, 0, where=[s >= 0 for s in sl],
                             alpha=0.15, color="#007A87")
            ax2.fill_between(ml, sl, 0, where=[s < 0 for s in sl],
                             alpha=0.15, color="#E8490F")
            ax2.set_title("Saldo Acumulado"); ax2.grid(True, alpha=0.3)
            plt.tight_layout(); st.pyplot(fig); plt.close()

# =============================================================================
#  12. GRAFICAS
# =============================================================================
def p12():
    st.title("12. Graficas y Reportes")
    if not MPL:
        st.error("Instala matplotlib: pip install matplotlib"); return
    if not PRES():
        st.warning("No hay presentaciones creadas."); return

    tcf = TCF(); mps = MPS(); igs = IGS(); ps = PRES()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Precios vs Costos", "Estructura Costos",
        "Margenes", "Costos Fijos", "Desglose CTU"])

    with tab1:
        noms = [p.nombre for p in ps]
        pvs  = [p.precio_venta(mps, igs, tcf) for p in ps]
        ctus = [p.costo_total_unit(mps, igs, tcf) for p in ps]
        cvus = [p.costo_variable_unit(mps, igs) for p in ps]
        fig, ax = plt.subplots(figsize=(max(6, len(noms)*2), 5))
        x = range(len(noms))
        ax.bar([i-.25 for i in x], pvs,  .25, label="Precio Venta",    color="#007A87")
        ax.bar([i     for i in x], ctus, .25, label="Costo Total",     color="#E8490F")
        ax.bar([i+.25 for i in x], cvus, .25, label="Costo Variable",  color="#F4A261")
        ax.set_xticks(list(x)); ax.set_xticklabels(noms, rotation=15, ha="right")
        ax.set_title("Precio vs Costos por Presentacion")
        ax.set_ylabel("$"); ax.legend(); ax.grid(True, alpha=0.3)
        plt.tight_layout(); st.pyplot(fig); plt.close()

    with tab2:
        p_act = pres_actual()
        if not p_act: st.info("Selecciona una presentacion activa en Paso 3."); return
        etiq = []; vals = []
        for item in p_act.formulacion:
            g = (item.proporcion_pct / 100) * p_act.peso_g
            ct = g * p_act.cpg(item.nombre, mps, igs)
            if ct > 0: etiq.append(item.nombre); vals.append(ct)
        for g in p_act.otros_gastos:
            if g.costo_unit > 0: etiq.append(g.nombre); vals.append(g.costo_unit)
        if vals:
            fig, ax = plt.subplots(figsize=(7, 5))
            pal = ["#007A87","#F4A261","#E8490F","#C44A0A","#3D1F00","#888"] * 5
            ax.pie(vals, labels=etiq, autopct="%1.1f%%",
                   colors=pal[:len(vals)], startangle=90)
            ax.set_title(f"Estructura Costos — {p_act.nombre}")
            plt.tight_layout(); st.pyplot(fig); plt.close()
        else:
            st.info("Sin costos registrados para esta presentacion.")

    with tab3:
        noms = [p.nombre for p in ps]
        mcs  = [p.margen_contrib(mps, igs, tcf) for p in ps]
        fig, ax = plt.subplots(figsize=(max(6, len(noms)*2), 5))
        ax.bar(noms, mcs, color=["#007A87" if m >= 0 else "#E8490F" for m in mcs])
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title("Margen de Contribucion por Presentacion")
        ax.set_ylabel("$ / unidad"); ax.set_xticklabels(noms, rotation=15, ha="right")
        ax.grid(True, alpha=0.3); plt.tight_layout(); st.pyplot(fig); plt.close()

    with tab4:
        cfs = CFS()
        if not cfs: st.info("Sin costos fijos registrados."); return
        cats = {}
        for c in cfs: cats[c.categoria] = cats.get(c.categoria, 0) + c.monto
        fig, ax = plt.subplots(figsize=(7, 5))
        pal = ["#007A87","#F4A261","#E8490F","#C44A0A","#3D1F00","#888"] * 4
        ax.pie(list(cats.values()), labels=list(cats.keys()),
               autopct="%1.1f%%", colors=pal[:len(cats)], startangle=90)
        ax.set_title("Distribucion Costos Fijos por Categoria")
        plt.tight_layout(); st.pyplot(fig); plt.close()

    with tab5:
        noms = [p.nombre for p in ps]
        cvi  = [p.costo_variable_insumos(mps, igs) for p in ps]
        cog  = [p.costo_otros() for p in ps]
        cfu  = [p.costo_fijo_unit(tcf) for p in ps]
        fig, ax = plt.subplots(figsize=(max(6, len(noms)*2), 5))
        ax.bar(noms, cvi, label="CV Insumos",  color="#007A87")
        ax.bar(noms, cog, bottom=cvi, label="Otros Gastos", color="#F4A261")
        ax.bar(noms, cfu, bottom=[a+b for a,b in zip(cvi, cog)],
               label="CF Unitario", color="#E8490F")
        ax.set_title("Desglose Costo Total Unitario"); ax.set_ylabel("$")
        ax.set_xticklabels(noms, rotation=15, ha="right")
        ax.legend(); ax.grid(True, alpha=0.3)
        plt.tight_layout(); st.pyplot(fig); plt.close()

# =============================================================================
#  ROUTER
# =============================================================================
if   pagina.startswith("1."):  p1()
elif pagina.startswith("2."):  p2()
elif pagina.startswith("3."):  p3()
elif pagina.startswith("4."):  p4()
elif pagina.startswith("5."):  p5()
elif pagina.startswith("6."):  p6()
elif pagina.startswith("7."):  p7()
elif pagina.startswith("8."):  p8()
elif pagina.startswith("9."):  p9()
elif pagina.startswith("10."): p10()
elif pagina.startswith("11."): p11()
elif pagina.startswith("12."): p12()

pie()
