import streamlit as st
import requests
from io import BytesIO
from collections import Counter
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

try:
    API_BASE_URL = st.secrets["API_BASE_URL"]
except:
    API_BASE_URL = "http://217.154.156.197:8003"

MODELS_ENDPOINT = f"{API_BASE_URL}/desInfo/models"
ANALYZE_ENDPOINT = f"{API_BASE_URL}/desInfo/generateReport"

CATEGORY_POINTS = {'FALSCH': 5, 'DELEGITIMIERUNG': 4, 'VERZERRUNG': 3, 'FRAME': 1, 'WAHR': 0}

SCORE_GRADES = {
    'A': (0.0, 0.4, 'wahr', 'Die Aussagen entsprechen nachprüfbaren Fakten und sind wahrheitsgetreu.'),
    'B': (0.5, 1.4, 'geframed', 'Die Aussagen enthalten wahre Kernaussagen, die durch normative Framings eingefärbt werden.'),
    'C': (1.5, 2.4, 'verzerrend', 'Die Aussagen enthalten formal richtige Kernaussagen, die durch Übertreibung, Verkürzung oder Kontextausblendung ein schiefes Bild erzeugen.'),
    'D': (2.5, 3.4, 'demokratisch dysfunktional', 'Die Aussagen enthalten substanzielle Falschbehauptungen und delegitimierende Elemente, die den demokratischen Diskurs belasten.'),
    'E': (3.5, 5.0, 'demokratisch destruktiv', 'Die Aussagen sind überwiegend falsch und delegitimierend, untergraben systematisch Vertrauen und demokratische Institutionen.')
}

CATEGORY_DESCRIPTIONS = {
    'FALSCH': 'Objektiv widerlegte Behauptungen. Es liegen belastbare Daten oder Ereignisprotokolle vor, die das Gegenteil zeigen.',
    'DELEGITIMIERUNG': 'Abwertung oder Untergrabung von Personen, Gruppen oder Institutionen. Sprachliche Diskreditierungen, Kampfbegriffe.',
    'VERZERRUNG': 'Formal richtige Kernaussagen, die durch Übertreibung, Verkürzung oder Kontextausblendung ein schiefes Bild erzeugen.',
    'FRAME': 'Sprachliche Deutungsrahmen, die neutrale Sachverhalte emotional oder normativ aufladen.',
    'WAHR': 'Sachlich zutreffende Aussagen, die überprüfbar sind und keinen überzogenen Frame enthalten.'
}

st.set_page_config(page_title="DESINFO Analyzer", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .block-container { 
        max-width: 1200px; 
        padding: 2rem; 
        background: white; 
        border-radius: 20px; 
        margin: 2rem auto;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    [data-testid="stSidebar"] { background: white; }
    h1, h2, h3, h4, h5, h6 { color: #1a1a1a !important; }
    .stButton>button {
        background: linear-gradient(135deg, #ffd93d 0%, #ffb800 100%);
        color: #1a1a1a;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        font-weight: 700;
        border-radius: 50px;
        width: 100%;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255, 217, 61, 0.4); }
    .stTextArea textarea { border: 2px solid #667eea; border-radius: 15px; }
    .category-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        margin: 0.3rem 0.2rem;
        color: white;
    }
    .badge-falsch { background: #dc3545; }
    .badge-delegitimierung { background: #fd7e14; }
    .badge-verzerrung { background: #ffc107; color: #000; }
    .badge-frame { background: #28a745; }
    .badge-wahr { background: #007bff; }
    .statement-card {
        background: #f8f9fa;
        border-left: 5px solid;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .score-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        color: white;
        margin: -3rem auto 2rem;
        max-width: 600px;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
    }
    .score-value { font-size: 6rem; font-weight: 800; }
    .score-grade { font-size: 2.5rem; font-weight: 700; color: #ffd93d; margin: 1rem 0; }
    .score-label { font-size: 1.8rem; font-weight: 600; }
    .metric-card {
        text-align: center;
        padding: 1.5rem 1rem;
        border-radius: 15px;
        color: white;
        margin: 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .metric-value { font-size: 2.5rem; font-weight: 800; }
    .metric-label { font-size: 1rem; font-weight: 600; }
    #MainMenu, footer { visibility: hidden; }
    .stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_models():
    try:
        response = requests.get(MODELS_ENDPOINT, timeout=10)
        if response.ok:
            return [m for m in response.json().get('models', []) if m.get('valid', False)]
    except: pass
    return []

def parse_statements(text):
    if '|' in text:
        return [s.strip() for s in text.split('|') if s.strip()]
    return [s.strip() for s in text.split('\n') if s.strip()]

def call_api(statements, model_id):
    try:
        response = requests.get(ANALYZE_ENDPOINT, params={"modelID": model_id, "text": "|".join(statements)}, timeout=120)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_summary(analysis_data):
    category_counts = Counter(item['kategorie'] for item in analysis_data)
    total_points = sum(CATEGORY_POINTS.get(item['kategorie'], 0) for item in analysis_data)
    total_statements = len(analysis_data)
    desinfo_score = total_points / total_statements if total_statements > 0 else 0
    grade = grade_label = grade_description = 'E'
    for g, (min_score, max_score, label, desc) in SCORE_GRADES.items():
        if min_score <= desinfo_score <= max_score:
            grade, grade_label, grade_description = g, label, desc
            break
    return {
        'total_statements': total_statements,
        'category_counts': dict(category_counts),
        'total_points': total_points,
        'desinfo_score': round(desinfo_score, 1),
        'grade': grade,
        'grade_label': grade_label,
        'grade_description': grade_description
    }

def get_category_color(category):
    colors_map = {
        'FALSCH': ('#dc3545', colors.HexColor('#dc3545')),
        'DELEGITIMIERUNG': ('#fd7e14', colors.HexColor('#fd7e14')),
        'VERZERRUNG': ('#ffc107', colors.HexColor('#ffc107')),
        'FRAME': ('#28a745', colors.HexColor('#28a745')),
        'WAHR': ('#007bff', colors.HexColor('#007bff'))
    }
    return colors_map.get(category, ('#6c757d', colors.grey))

def generate_pdf_report(analysis_data, summary, model_info=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2.5*cm, rightMargin=2.5*cm)
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, textColor=colors.black, spaceAfter=20, fontName='Helvetica-Bold')
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=16, textColor=colors.black, spaceAfter=10, fontName='Helvetica-Bold')
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=11, alignment=TA_JUSTIFY, fontName='Helvetica')
    italic_style = ParagraphStyle('Italic', parent=body_style, fontName='Helvetica-Oblique')
    
    elements.append(Paragraph("Vollständige Auswertung", title_style))
    elements.append(Spacer(1, 0.3*cm))
    line = Table([['']], colWidths=[16*cm])
    line.setStyle(TableStyle([('LINEABOVE', (0,0), (-1,0), 1, colors.grey)]))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    elements.append(Paragraph("Zusammenfassung", heading_style))
    total = summary['total_statements']
    elements.append(Paragraph(f"Die vorliegende Analyse untersucht {total} Aussagen nach ihrer faktischen Richtigkeit und kommunikativen Qualität.", body_style))
    elements.append(Spacer(1, 0.8*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    elements.append(Paragraph("Quantifizierung", heading_style))
    elements.append(Paragraph(f"Anzahl Aussagen gesamt: {total}", body_style))
    elements.append(Spacer(1, 0.3*cm))
    
    counts = summary['category_counts']
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        count = counts.get(cat, 0)
        percentage = (count / total * 100) if total > 0 else 0
        hex_color, _ = get_category_color(cat)
        elements.append(Paragraph(f'<font color="{hex_color}">■</font> {cat}: {count} ({percentage:.0f} %)', body_style))
    
    elements.append(Spacer(1, 0.8*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    elements.append(Paragraph("Scoring", heading_style))
    elements.append(Paragraph(f"<b>Desinfo-Score: {summary['desinfo_score']}</b><br/>{summary['grade']}: {summary['grade_label']}<br/><br/>{summary['grade_description']}", body_style))
    elements.append(Spacer(1, 0.8*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    elements.append(Paragraph("Einteilung", heading_style))
    for grade, (min_s, max_s, label, _) in SCORE_GRADES.items():
        elements.append(Paragraph(f"{grade}: {min_s} bis {max_s}: {label}", body_style))
    
    elements.append(PageBreak())
    elements.append(Paragraph("Vollständige Auswertung des Textes", title_style))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    for category in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        elements.append(Paragraph(f"<b>{category} ({len(cat_items)})</b>", heading_style))
        elements.append(Paragraph(CATEGORY_DESCRIPTIONS[category], italic_style))
        elements.append(Spacer(1, 0.5*cm))
        for idx, item in enumerate(cat_items, 1):
            hex_color, _ = get_category_color(category)
            symbol = '✓' if category == 'WAHR' else '■'
            elements.append(Paragraph(f'{idx}. <font color="{hex_color}">{symbol}</font> <b>"{item["aussage"]}"</b>', body_style))
            elements.append(Spacer(1, 0.2*cm))
            elements.append(Paragraph(f"– {item['begründung']}", body_style))
            elements.append(Spacer(1, 0.5*cm))
        elements.append(Spacer(1, 0.5*cm))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_docx_report(analysis_data, summary, model_info=None):
    doc = Document()
    doc.add_heading('Vollständige Auswertung', 0)
    doc.add_heading('Zusammenfassung', 1)
    doc.add_paragraph(f"Die vorliegende Analyse untersucht {summary['total_statements']} Aussagen nach ihrer faktischen Richtigkeit.")
    doc.add_heading('Quantifizierung', 1)
    doc.add_paragraph(f"Anzahl Aussagen gesamt: {summary['total_statements']}")
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        count = summary['category_counts'].get(cat, 0)
        percentage = (count / summary['total_statements'] * 100) if summary['total_statements'] > 0 else 0
        doc.add_paragraph(f"■ {cat}: {count} ({percentage:.0f} %)")
    doc.add_heading('Scoring', 1)
    doc.add_paragraph(f"Desinfo-Score: {summary['desinfo_score']}")
    doc.add_paragraph(f"{summary['grade']}: {summary['grade_label']}")
    doc.add_paragraph(summary['grade_description'])
    doc.add_heading('Einteilung', 1)
    for grade, (min_s, max_s, label, _) in SCORE_GRADES.items():
        doc.add_paragraph(f"{grade}: {min_s} bis {max_s}: {label}")
    doc.add_page_break()
    doc.add_heading('Vollständige Auswertung des Textes', 1)
    for category in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        doc.add_heading(f"{category} ({len(cat_items)})", 2)
        p = doc.add_paragraph(CATEGORY_DESCRIPTIONS[category])
        p.italic = True
        for idx, item in enumerate(cat_items, 1):
            symbol = '✓' if category == 'WAHR' else '■'
            p = doc.add_paragraph()
            p.add_run(f'{idx}. {symbol} ').bold = True
            p.add_run(f'"{item["aussage"]}"').bold = True
            doc.add_paragraph(f"– {item['begründung']}")
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

with st.sidebar:
    st.title("⚙️ Einstellungen")
    valid_models = fetch_models()
    if valid_models:
        st.subheader("AI Model")
        model_options = {f"{m['modelName']} ({m['provider']})": m for m in valid_models}
        selected_model_label = st.selectbox("Wähle ein Model:", options=list(model_options.keys()), index=0)
        st.session_state.selected_model = model_options[selected_model_label]
        with st.expander("ℹ️ Model Details"):
            model = st.session_state.selected_model
            st.write(f"**ID:** {model['modelID']}")
            st.write(f"**Name:** {model['modelName']}")
            st.write(f"**Provider:** {model['provider']}")
    st.divider()
    st.subheader("📚 Kategorien")
    st.markdown("- 🔴 **FALSCH** (5 Punkte)\n- 🟠 **DELEGITIMIERUNG** (4 Punkte)\n- 🟡 **VERZERRUNG** (3 Punkte)\n- 🟢 **FRAME** (1 Punkt)\n- 🔵 **WAHR** (0 Punkte)")
    if st.session_state.analysis_data is not None:
        st.divider()
        if st.button("🔄 Neue Analyse", use_container_width=True):
            st.session_state.analysis_data = None
            st.session_state.summary = None
            st.session_state.input_text = ""
            st.rerun()

if not valid_models:
    st.error("⚠️ Keine Models verfügbar.")
    st.stop()

st.markdown("""
<div style="text-align: center; color: white; padding: 2rem 0; margin: -2rem -2rem 2rem -2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px 20px 0 0;">
    <h1 style="font-size: 3.5rem; font-weight: 800; margin: 0; color: white !important;">DESINFO</h1>
    <p style="font-size: 1.5rem; color: #ffd93d; font-weight: 600; margin: 0.5rem 0;">Political Discourse Analyzer</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.analysis_data is None:
    st.header("📝 Politische Aussagen eingeben")
    st.markdown("*Eine Aussage pro Zeile oder mit | getrennt*")
    input_text = st.text_area("Text eingeben", height=350, placeholder="Beispiel:\nDiese Bundesregierung riskiert gerade den Dritten Weltkrieg.\nNehmen Sie Polen.", value=st.session_state.input_text, label_visibility="collapsed")
    st.session_state.input_text = input_text
    if st.button("🚀 Analyse starten", type="primary", disabled=not bool(input_text and input_text.strip())):
        if input_text and input_text.strip():
            statements = parse_statements(input_text)
            with st.spinner(f"🔍 Analysiere {len(statements)} Aussagen..."):
                result = call_api(statements, st.session_state.selected_model['modelID'])
                if result['success']:
                    st.session_state.analysis_data = result['data']
                    st.session_state.summary = calculate_summary(result['data'])
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ Fehler: {result['error']}")
    if input_text:
        st.info(f"📊 **{len(parse_statements(input_text))} Aussagen** werden analysiert")
else:
    analysis_data = st.session_state.analysis_data
    summary = st.session_state.summary
    st.markdown(f"""
    <div class="score-box">
        <div class="score-value">{summary['desinfo_score']}</div>
        <div class="score-grade">Grade {summary['grade']}</div>
        <div class="score-label">{summary['grade_label']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.header("📊 Quantifizierung")
    cols = st.columns(5)
    categories = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    for idx, cat in enumerate(categories):
        count = summary['category_counts'].get(cat, 0)
        percentage = (count / summary['total_statements'] * 100) if summary['total_statements'] > 0 else 0
        hex_color, _ = get_category_color(cat)
        with cols[idx]:
            st.markdown(f'<div class="metric-card" style="background: {hex_color};"><div class="metric-value">{count}</div><div class="metric-label">{cat}</div><div style="font-size: 0.9rem;">{percentage:.0f}%</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("📋 Detaillierte Ergebnisse")
    for category in categories:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        st.subheader(f"{category} ({len(cat_items)} Aussagen)")
        st.markdown(f"*{CATEGORY_DESCRIPTIONS[category]}*")
        for idx, item in enumerate(cat_items, 1):
            hex_color, _ = get_category_color(category)
            st.markdown(f'<div class="statement-card" style="border-left-color: {hex_color};"><div style="font-size: 1.1rem; font-weight: 700; margin-bottom: 0.8rem;">{idx}. "{item["aussage"]}"</div><span class="category-badge badge-{category.lower()}">{category}</span><span class="category-badge" style="background: #6c757d;">Punkte: {item["punkte"]}</span><div style="margin-top: 1rem;"><strong>Begründung:</strong> {item["begründung"]}</div></div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("📥 Report Download")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 PDF Report generieren", use_container_width=True):
            with st.spinner("Generiere PDF..."):
                pdf_buffer = generate_pdf_report(analysis_data, summary)
                st.download_button("⬇️ PDF herunterladen", pdf_buffer, f"DesInfo_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf", "application/pdf", use_container_width=True)
    with col2:
        if st.button("📝 DOCX Report generieren", use_container_width=True):
            with st.spinner("Generiere DOCX..."):
                docx_buffer = generate_docx_report(analysis_data, summary)
                st.download_button("⬇️ DOCX herunterladen", docx_buffer, f"DesInfo_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

st.markdown("---")
st.markdown('<div style="text-align: center; color: #666; padding: 1rem 0;"><p style="font-weight: 600;">Powered by <a href="https://www.democracy-intelligence.de" target="_blank" style="color: #667eea;">Democracy Intelligence</a></p><p style="font-size: 0.9rem;">DESINFO v2.3</p></div>', unsafe_allow_html=True)
