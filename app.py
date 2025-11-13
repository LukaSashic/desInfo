import streamlit as st
import requests
import urllib.parse
from pathlib import Path
import json
from datetime import datetime
from io import BytesIO
from collections import Counter

# PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# DOCX Generation
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ============================================
# KONFIGURATION
# ============================================
# Für Streamlit Cloud: Nutze st.secrets
try:
    API_BASE_URL = st.secrets["API_BASE_URL"]
except:
    API_BASE_URL = "http://217.154.156.197:8003"

MODELS_ENDPOINT = f"{API_BASE_URL}/desInfo/models"
ANALYZE_ENDPOINT = f"{API_BASE_URL}/desInfo/generateReport"

# Kategorie Scoring
CATEGORY_POINTS = {
    'FALSCH': 5,
    'DELEGITIMIERUNG': 4,
    'VERZERRUNG': 3,
    'FRAME': 1,
    'WAHR': 0
}

# Score-Grade Mapping
SCORE_GRADES = {
    'A': (0.0, 0.4, 'wahr', 'Die Aussagen entsprechen nachprüfbaren Fakten und sind wahrheitsgetreu.'),
    'B': (0.5, 1.4, 'geframed', 'Die Aussagen enthalten wahre Kernaussagen, die durch normative Framings eingefärbt werden.'),
    'C': (1.5, 2.4, 'verzerrend', 'Die Aussagen enthalten formal richtige Kernaussagen, die durch Übertreibung, Verkürzung oder Kontextausblendung ein schiefes Bild erzeugen.'),
    'D': (2.5, 3.4, 'demokratisch dysfunktional', 'Die Aussagen enthalten substanzielle Falschbehauptungen und delegitimierende Elemente, die den demokratischen Diskurs belasten.'),
    'E': (3.5, 5.0, 'demokratisch destruktiv', 'Die Aussagen sind überwiegend falsch und delegitimierend, untergraben systematisch Vertrauen und demokratische Institutionen.')
}

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="DESINFO Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS
# ============================================
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    .category-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.9rem;
        margin: 0.2rem;
    }
    .badge-falsch { background-color: #ff4444; color: white; }
    .badge-delegitimierung { background-color: #ff8800; color: white; }
    .badge-verzerrung { background-color: #ffbb33; color: white; }
    .badge-frame { background-color: #00C851; color: white; }
    .badge-wahr { background-color: #0099CC; color: white; }
    
    .statement-card {
        background-color: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .provider-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-left: 0.5rem;
    }
    .provider-openai { background-color: #10a37f; color: white; }
    .provider-claude { background-color: #d97757; color: white; }
    .provider-google { background-color: #4285f4; color: white; }
    .provider-perplexity { background-color: #8b5cf6; color: white; }
    .provider-huggingface { background-color: #ffd21e; color: black; }
</style>
""", unsafe_allow_html=True)

# ============================================
# HELPER FUNCTIONS
# ============================================

@st.cache_data(ttl=300)
def fetch_models():
    """Lädt Models von API"""
    try:
        response = requests.get(MODELS_ENDPOINT, timeout=10)
        if response.ok:
            data = response.json()
            return [m for m in data.get('models', []) if m.get('valid', False)]
    except Exception as e:
        st.error(f"⚠️ Fehler beim Laden der Models: {e}")
    return []

def format_model_option(model: dict) -> str:
    return f"{model['modelName']} ({model['provider']})"

def get_provider_badge_class(provider: str) -> str:
    provider_map = {
        'OpenAI': 'provider-openai',
        'Claude.ai': 'provider-claude',
        'Google': 'provider-google',
        'Perplexity': 'provider-perplexity',
        'Huggingface': 'provider-huggingface'
    }
    return provider_map.get(provider, 'provider-huggingface')

def parse_statements(text: str) -> list:
    if '|' in text:
        statements = [s.strip() for s in text.split('|') if s.strip()]
    else:
        statements = [s.strip() for s in text.split('\n') if s.strip()]
    return statements

def call_api(statements: list, model_id: int) -> dict:
    text_param = "|".join(statements)
    params = {"modelID": model_id, "text": text_param}
    
    try:
        response = requests.get(ANALYZE_ENDPOINT, params=params, timeout=120)
        response.raise_for_status()
        return {"success": True, "data": response.json(), "url": response.url}
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_summary(analysis_data: list) -> dict:
    category_counts = Counter(item['kategorie'] for item in analysis_data)
    total_points = sum(CATEGORY_POINTS.get(item['kategorie'], 0) for item in analysis_data)
    total_statements = len(analysis_data)
    desinfo_score = total_points / total_statements if total_statements > 0 else 0
    
    grade = 'E'
    grade_label = ''
    grade_description = ''
    
    for g, (min_score, max_score, label, desc) in SCORE_GRADES.items():
        if min_score <= desinfo_score <= max_score:
            grade = g
            grade_label = label
            grade_description = desc
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

def get_category_color(category: str) -> str:
    colors_map = {
        'FALSCH': '#ff4444',
        'DELEGITIMIERUNG': '#ff8800',
        'VERZERRUNG': '#ffbb33',
        'FRAME': '#00C851',
        'WAHR': '#0099CC'
    }
    return colors_map.get(category, '#6c757d')

def generate_pdf_report(analysis_data: list, summary: dict, model_info: dict = None) -> BytesIO:
    """Generiert PDF Report - SIMPLIFIED VERSION für Streamlit Cloud"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Titel
    title = Paragraph("DESINFO Analyse Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.5*cm))
    
    # Summary
    elements.append(Paragraph("Zusammenfassung", styles['Heading1']))
    summary_text = f"Analysiert: {summary['total_statements']} Aussagen | DESINFO-Score: {summary['desinfo_score']} ({summary['grade']})"
    elements.append(Paragraph(summary_text, styles['Normal']))
    elements.append(Spacer(1, 1*cm))
    
    # Categories
    for category in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        elements.append(Paragraph(f"{category} ({len(cat_items)})", styles['Heading2']))
        
        for item in cat_items:
            elements.append(Paragraph(f"<b>{item['aussage']}</b>", styles['Normal']))
            elements.append(Paragraph(item['begründung'], styles['Normal']))
            elements.append(Spacer(1, 0.5*cm))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_docx_report(analysis_data: list, summary: dict, model_info: dict = None) -> BytesIO:
    """Generiert DOCX Report"""
    doc = Document()
    
    doc.add_heading('DESINFO Analyse Report', 0)
    doc.add_paragraph(f"Analysiert: {summary['total_statements']} Aussagen")
    doc.add_paragraph(f"DESINFO-Score: {summary['desinfo_score']} (Grade {summary['grade']})")
    
    for category in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        doc.add_heading(f"{category} ({len(cat_items)})", 1)
        
        for item in cat_items:
            doc.add_paragraph(f'"{item["aussage"]}"', style='Intense Quote')
            doc.add_paragraph(item['begründung'])
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ============================================
# SESSION STATE
# ============================================
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = None

# ============================================
# LOAD MODELS
# ============================================
valid_models = fetch_models()

if not valid_models:
    st.error("⚠️ Keine Models verfügbar. Bitte API-Verbindung prüfen.")
    st.info(f"API Endpoint: {MODELS_ENDPOINT}")
    st.stop()

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.title("⚙️ Einstellungen")
    
    model_options = {format_model_option(m): m for m in valid_models}
    selected_model_label = st.selectbox("AI Model:", options=list(model_options.keys()), index=0)
    selected_model = model_options[selected_model_label]
    st.session_state.selected_model = selected_model
    
    with st.expander("ℹ️ Model Details"):
        st.write(f"**ID:** {selected_model['modelID']}")
        st.write(f"**Name:** {selected_model['modelName']}")
        st.write(f"**Provider:** {selected_model['provider']}")
    
    st.divider()
    st.subheader("📚 Kategorien")
    st.markdown("""
    - 🔴 **FALSCH** (5 Punkte)
    - 🟠 **DELEGITIMIERUNG** (4 Punkte)
    - 🟡 **VERZERRUNG** (3 Punkte)
    - 🟢 **FRAME** (1 Punkt)
    - 🔵 **WAHR** (0 Punkte)
    """)
    
    if st.button("🔄 Neue Analyse"):
        st.session_state.analysis_data = None
        st.session_state.summary = None
        st.rerun()

# ============================================
# MAIN APP
# ============================================
st.markdown('<div class="main-header">📊 DESINFO Political Discourse Analyzer</div>', unsafe_allow_html=True)

if st.session_state.selected_model:
    model = st.session_state.selected_model
    badge_class = get_provider_badge_class(model['provider'])
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 1rem;">
        Analysiere mit: <strong>{model['modelName']}</strong>
        <span class="provider-badge {badge_class}">{model['provider']}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# INPUT
if st.session_state.analysis_data is None:
    st.header("1️⃣ Text eingeben")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        input_text = st.text_area(
            "Politische Aussagen eingeben:",
            height=300,
            placeholder="Eine Aussage pro Zeile oder mit | getrennt",
            key="input_text"
        )
    
    with col2:
        if input_text:
            statements = parse_statements(input_text)
            st.metric("Statements", len(statements))
        
        if st.button("📝 Beispiel laden"):
            st.session_state.example_loaded = """Diese Bundesregierung riskiert gerade den Dritten Weltkrieg.|Nehmen Sie Polen. Natürlich kann auch Polen für uns eine Gefahr sein.|Das macht Polen nicht."""
            st.rerun()
    
    if 'example_loaded' in st.session_state:
        input_text = st.session_state.example_loaded
        del st.session_state.example_loaded
    
    if input_text:
        with st.expander("👁️ Statements Preview"):
            statements = parse_statements(input_text)
            for i, stmt in enumerate(statements, 1):
                st.write(f"{i}. {stmt}")
    
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        analyze_btn = st.button("🔍 Analyse starten", type="primary", use_container_width=True, disabled=not input_text)
    
    if analyze_btn and input_text:
        statements = parse_statements(input_text)
        model_id = st.session_state.selected_model['modelID']
        model_name = st.session_state.selected_model['modelName']
        
        with st.spinner(f"🔍 Analysiere mit {model_name}..."):
            result = call_api(statements, model_id)
            
            if result['success']:
                st.session_state.analysis_data = result['data']
                st.session_state.summary = calculate_summary(result['data'])
                st.balloons()
                st.rerun()
            else:
                st.error(f"❌ Fehler: {result['error']}")

# RESULTS
else:
    analysis_data = st.session_state.analysis_data
    summary = st.session_state.summary
    model_info = st.session_state.selected_model
    
    st.success(f"✅ Analyse abgeschlossen!")
    
    # Score Display
    st.header("📊 DESINFO-Score")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white;">
            <h1 style="font-size: 4rem; margin: 0;">{summary['desinfo_score']}</h1>
            <h2 style="margin: 0.5rem 0;">Grade: {summary['grade']}</h2>
            <h3 style="font-weight: normal; margin: 0;">{summary['grade_label']}</h3>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Categories
    st.header("📋 Quantifizierung")
    cols = st.columns(5)
    categories = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    
    for idx, cat in enumerate(categories):
        count = summary['category_counts'].get(cat, 0)
        percentage = (count / summary['total_statements'] * 100) if summary['total_statements'] > 0 else 0
        color = get_category_color(cat)
        
        with cols[idx]:
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; background: {color}; border-radius: 10px; color: white;">
                <h2 style="margin: 0; font-size: 2rem;">{count}</h2>
                <p style="margin: 0.5rem 0 0 0;">{cat}</p>
                <p style="margin: 0; font-size: 0.9rem;">{percentage:.0f}%</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Detailed Results
    st.header("📋 Detaillierte Ergebnisse")
    
    for category in categories:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        with st.expander(f"{category} ({len(cat_items)} Aussagen)"):
            for idx, item in enumerate(cat_items, 1):
                st.markdown(f"""
                <div class="statement-card">
                    <h4>{idx}. "{item['aussage']}"</h4>
                    <span class="category-badge badge-{category.lower()}">{category}</span>
                    <span class="category-badge" style="background-color: #6c757d;">Punkte: {item['punkte']}</span>
                    <p style="margin-top: 1rem;"><strong>Begründung:</strong> {item['begründung']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Downloads
    st.markdown("---")
    st.header("📥 Report Download")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 PDF Report")
        if st.button("🔨 PDF generieren", key="gen_pdf"):
            with st.spinner("Generiere PDF..."):
                pdf_buffer = generate_pdf_report(analysis_data, summary, model_info)
                st.download_button(
                    label="📥 PDF herunterladen",
                    data=pdf_buffer,
                    file_name=f"DESINFO_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    with col2:
        st.subheader("📝 DOCX Report")
        if st.button("🔨 DOCX generieren", key="gen_docx"):
            with st.spinner("Generiere DOCX..."):
                docx_buffer = generate_docx_report(analysis_data, summary, model_info)
                st.download_button(
                    label="📥 DOCX herunterladen",
                    data=docx_buffer,
                    file_name=f"DESINFO_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p>DESINFO Political Discourse Analyzer v2.0</p>
</div>
""", unsafe_allow_html=True)