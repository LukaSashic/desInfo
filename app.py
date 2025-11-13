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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT

# DOCX Generation
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ============================================
# KONFIGURATION
# ============================================
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

CATEGORY_DESCRIPTIONS = {
    'FALSCH': 'Objektiv widerlegte Behauptungen. Es liegen belastbare Daten oder Ereignisprotokolle vor, die das Gegenteil zeigen. Keine Meinungen oder Prognosen; nur Tatsachenbehauptungen, die nachweislich nicht stimmen.',
    'DELEGITIMIERUNG': 'Abwertung oder Untergrabung von Personen, Gruppen oder Institutionen. Sprachliche Diskreditierungen, Kampfbegriffe oder systematische Diffamierungen.',
    'VERZERRUNG': 'Formal richtige Kernaussagen, die durch Übertreibung, Verkürzung oder Kontextausblendung ein schiefes Bild erzeugen.',
    'FRAME': 'Sprachliche Deutungsrahmen, die neutrale Sachverhalte emotional oder normativ aufladen, ohne sie faktisch falsch oder delegitimierend darzustellen.',
    'WAHR': 'Sachlich zutreffende Aussagen, die überprüfbar sind und keinen überzogenen Frame, keine Verzerrung oder Delegitimierung enthalten.'
}

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="DESINFO Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# CUSTOM CSS - Democracy Intelligence Style
# ============================================
st.markdown("""
<style>
    /* Import Democracy Intelligence Colors */
    :root {
        --primary-color: #1a1a2e;
        --secondary-color: #16213e;
        --accent-color: #0f3460;
        --highlight-color: #e94560;
        --text-light: #f1f1f1;
    }
    
    /* Main Container */
    .main {
        background-color: #ffffff;
    }
    
    /* Header */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--primary-color);
        text-align: center;
        padding: 2rem 0;
        margin-bottom: 2rem;
        border-bottom: 3px solid var(--highlight-color);
    }
    
    /* Subtitle */
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 3rem;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: var(--highlight-color);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 5px;
        transition: all 0.3s;
    }
    
    .stButton>button:hover {
        background-color: #d63851;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(233, 69, 96, 0.3);
    }
    
    /* Category Badges */
    .category-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.2rem;
    }
    
    .badge-falsch { background-color: #dc3545; color: white; }
    .badge-delegitimierung { background-color: #fd7e14; color: white; }
    .badge-verzerrung { background-color: #ffc107; color: #000; }
    .badge-frame { background-color: #28a745; color: white; }
    .badge-wahr { background-color: #007bff; color: white; }
    
    /* Statement Card */
    .statement-card {
        background-color: #f8f9fa;
        border-left: 4px solid var(--accent-color);
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Score Display */
    .score-display {
        text-align: center;
        padding: 3rem 2rem;
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        border-radius: 15px;
        color: white;
        margin: 2rem 0;
        box-shadow: 0 8px 16px rgba(0,0,0,0.2);
    }
    
    .score-value {
        font-size: 5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .score-grade {
        font-size: 2rem;
        font-weight: 600;
        margin: 1rem 0;
    }
    
    .score-label {
        font-size: 1.5rem;
        opacity: 0.9;
    }
    
    /* Metric Cards */
    .metric-card {
        text-align: center;
        padding: 2rem 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Input Area */
    .stTextArea textarea {
        border: 2px solid var(--accent-color);
        border-radius: 8px;
        font-size: 1rem;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: var(--secondary-color);
    }
    
    /* Provider Badges */
    .provider-badge {
        display: inline-block;
        padding: 0.3rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
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
        'FALSCH': '#dc3545',
        'DELEGITIMIERUNG': '#fd7e14',
        'VERZERRUNG': '#ffc107',
        'FRAME': '#28a745',
        'WAHR': '#007bff'
    }
    return colors_map.get(category, '#6c757d')

def generate_pdf_report(analysis_data: list, summary: dict, model_info: dict = None) -> BytesIO:
    """Generiert PDF Report - EXAKT wie das Beispiel-PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=2*cm, 
        bottomMargin=2*cm, 
        leftMargin=2.5*cm, 
        rightMargin=2.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom Styles - Exakt wie im PDF
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.black,
        spaceAfter=30,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    # ============================================
    # TITEL
    # ============================================
    title = Paragraph("Vollständige Auswertung", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*cm))
    
    # Horizontal line
    from reportlab.platypus import Table, TableStyle
    line_table = Table([['']], colWidths=[16*cm])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.grey),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # ============================================
    # ZUSAMMENFASSUNG
    # ============================================
    summary_heading = Paragraph("Zusammenfassung", heading_style)
    elements.append(summary_heading)
    
    total = summary['total_statements']
    counts = summary['category_counts']
    
    summary_text = f"""Die vorliegende Analyse untersucht {total} Aussagen nach ihrer faktischen Richtigkeit und kommunikativen Qualität. Das Ergebnis zeigt eine ausgeprägte Tendenz zu {summary['grade_label']}en Darstellungen."""
    
    summary_para = Paragraph(summary_text, body_style)
    elements.append(summary_para)
    elements.append(Spacer(1, 0.8*cm))
    
    # Horizontal line
    elements.append(line_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # ============================================
    # QUANTIFIZIERUNG
    # ============================================
    quant_heading = Paragraph("Quantifizierung", heading_style)
    elements.append(quant_heading)
    
    elements.append(Paragraph(f"<b>Anzahl Aussagen gesamt: {total}</b>", body_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Category breakdown mit farbigen Bullets
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        count = counts.get(cat, 0)
        percentage = (count / total * 100) if total > 0 else 0
        
        color_hex = get_category_color(cat).replace('#', '')
        bullet = f'<font color="#{color_hex}">■</font>'
        
        cat_text = f"{bullet} {cat}: {count} ({percentage:.0f} %)"
        elements.append(Paragraph(cat_text, body_style))
    
    elements.append(Spacer(1, 0.8*cm))
    
    # Horizontal line
    elements.append(line_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # ============================================
    # SCORING
    # ============================================
    score_heading = Paragraph("Scoring", heading_style)
    elements.append(score_heading)
    
    score_text = f"""<b>Desinfo-Score: {summary['desinfo_score']}</b><br/>
{summary['grade']}: {summary['grade_label']}<br/><br/>
{summary['grade_description']}"""
    
    elements.append(Paragraph(score_text, body_style))
    elements.append(Spacer(1, 0.8*cm))
    
    # Horizontal line
    elements.append(line_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # ============================================
    # EINTEILUNG
    # ============================================
    eint_heading = Paragraph("Einteilung", heading_style)
    elements.append(eint_heading)
    
    for grade, (min_s, max_s, label, _) in SCORE_GRADES.items():
        grade_line = f"{grade}: {min_s} bis {max_s}: {label}"
        elements.append(Paragraph(grade_line, body_style))
    
    # Page Break
    elements.append(PageBreak())
    
    # ============================================
    # VOLLSTÄNDIGE AUSWERTUNG DES TEXTES
    # ============================================
    full_heading = Paragraph("Vollständige Auswertung des Textes", title_style)
    elements.append(full_heading)
    elements.append(Spacer(1, 0.3*cm))
    elements.append(line_table)
    elements.append(Spacer(1, 0.8*cm))
    
    # Group by category
    categories_order = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    
    for category in categories_order:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        # Category header
        cat_title = Paragraph(f"<b>{category} ({len(cat_items)})</b>", heading_style)
        elements.append(cat_title)
        
        # Category description in italic
        cat_desc_style = ParagraphStyle(
            'CategoryDesc',
            parent=body_style,
            fontName='Helvetica-Oblique'
        )
        cat_desc = Paragraph(CATEGORY_DESCRIPTIONS.get(category, ''), cat_desc_style)
        elements.append(cat_desc)
        elements.append(Spacer(1, 0.5*cm))
        
        # Statements
        for idx, item in enumerate(cat_items, 1):
            # Statement with bullet
            symbol = '✓' if category == 'WAHR' else '■'
            stmt_text = f'{idx}. {symbol} <b>"{item["aussage"]}"</b>'
            elements.append(Paragraph(stmt_text, body_style))
            elements.append(Spacer(1, 0.2*cm))
            
            # Begründung
            beg_text = f"– {item['begründung']}"
            elements.append(Paragraph(beg_text, body_style))
            elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Spacer(1, 0.5*cm))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_docx_report(analysis_data: list, summary: dict, model_info: dict = None) -> BytesIO:
    """Generiert DOCX Report - EXAKT wie das PDF Format"""
    doc = Document()
    
    # Titel
    title = doc.add_heading('Vollständige Auswertung', 0)
    
    # Zusammenfassung
    doc.add_heading('Zusammenfassung', 1)
    
    total = summary['total_statements']
    summary_text = f"Die vorliegende Analyse untersucht {total} Aussagen nach ihrer faktischen Richtigkeit und kommunikativen Qualität. Das Ergebnis zeigt eine ausgeprägte Tendenz zu {summary['grade_label']}en Darstellungen."
    
    doc.add_paragraph(summary_text)
    
    # Quantifizierung
    doc.add_heading('Quantifizierung', 1)
    doc.add_paragraph(f"Anzahl Aussagen gesamt: {total}")
    
    counts = summary['category_counts']
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        count = counts.get(cat, 0)
        percentage = (count / total * 100) if total > 0 else 0
        p = doc.add_paragraph(f"■ {cat}: {count} ({percentage:.0f} %)")
    
    # Scoring
    doc.add_heading('Scoring', 1)
    doc.add_paragraph(f"Desinfo-Score: {summary['desinfo_score']}")
    doc.add_paragraph(f"{summary['grade']}: {summary['grade_label']}")
    doc.add_paragraph(summary['grade_description'])
    
    # Einteilung
    doc.add_heading('Einteilung', 1)
    for grade, (min_s, max_s, label, _) in SCORE_GRADES.items():
        doc.add_paragraph(f"{grade}: {min_s} bis {max_s}: {label}")
    
    # Vollständige Auswertung
    doc.add_page_break()
    doc.add_heading('Vollständige Auswertung des Textes', 1)
    
    # Categories
    categories_order = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    
    for category in categories_order:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        doc.add_heading(f"{category} ({len(cat_items)})", 2)
        
        desc_para = doc.add_paragraph(CATEGORY_DESCRIPTIONS.get(category, ''))
        desc_para.italic = True
        
        for idx, item in enumerate(cat_items, 1):
            symbol = '✓' if category == 'WAHR' else '■'
            p = doc.add_paragraph()
            p.add_run(f'{idx}. {symbol} ').bold = True
            p.add_run(f'"{item["aussage"]}"').bold = True
            
            doc.add_paragraph(f"– {item['begründung']}")
    
    # Save
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
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

# ============================================
# LOAD MODELS
# ============================================
valid_models = fetch_models()

if not valid_models:
    st.error("⚠️ Keine Models verfügbar. Bitte API-Verbindung prüfen.")
    st.info(f"API Endpoint: {MODELS_ENDPOINT}")
    st.stop()

# ============================================
# MAIN APP
# ============================================

# Header
st.markdown('<div class="main-header">DESINFO Political Discourse Analyzer</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Powered by Democracy Intelligence</div>', unsafe_allow_html=True)

# Model Selection (Compact at top)
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    model_options = {format_model_option(m): m for m in valid_models}
    selected_model_label = st.selectbox(
        "🤖 AI Model auswählen:",
        options=list(model_options.keys()),
        index=0
    )
    selected_model = model_options[selected_model_label]
    st.session_state.selected_model = selected_model

st.markdown("---")

# INPUT OR RESULTS
if st.session_state.analysis_data is None:
    st.header("📝 Text eingeben")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # FIX 1: Remove disabled parameter - button should always be enabled when text is present
        input_text = st.text_area(
            "Politische Aussagen eingeben (eine pro Zeile oder mit | getrennt):",
            height=300,
            placeholder="Beispiel:\nDiese Bundesregierung riskiert gerade den Dritten Weltkrieg.\nNehmen Sie Polen. Natürlich kann auch Polen für uns eine Gefahr sein.",
            key="text_input",
            value=st.session_state.input_text
        )
        
        # Update session state
        st.session_state.input_text = input_text
    
    with col2:
        if input_text:
            statements = parse_statements(input_text)
            st.metric("📊 Statements", len(statements))
        
        if st.button("📝 Beispiel laden", use_container_width=True):
            st.session_state.input_text = """Diese Bundesregierung riskiert gerade den Dritten Weltkrieg.|Nehmen Sie Polen. Natürlich kann auch Polen für uns eine Gefahr sein.|Nehmen wir die Nord Stream Sprengung, wo der Generalbundesanwalt hier einen gesuchten Täter nicht nach Deutschland ausliefert.|Das macht Polen nicht."""
            st.rerun()
    
    # Preview
    if input_text:
        with st.expander("👁️ Statements Preview"):
            statements = parse_statements(input_text)
            for i, stmt in enumerate(statements, 1):
                st.write(f"{i}. {stmt}")
    
    # Analyze Button - FIX 1: Always enabled if text present
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        # Button is now enabled as long as there's text
        analyze_btn = st.button(
            "🔍 Analyse starten",
            type="primary",
            use_container_width=True,
            disabled=not bool(input_text and input_text.strip())  # Only disabled if truly empty
        )
    
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
    
    st.success(f"✅ Analyse abgeschlossen mit {model_info['modelName']}!")
    
    # Score Display
    st.markdown(f"""
    <div class="score-display">
        <div class="score-value">{summary['desinfo_score']}</div>
        <div class="score-grade">Grade: {summary['grade']}</div>
        <div class="score-label">{summary['grade_label']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Categories
    st.header("📊 Quantifizierung")
    
    cols = st.columns(5)
    categories = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    
    for idx, cat in enumerate(categories):
        count = summary['category_counts'].get(cat, 0)
        percentage = (count / summary['total_statements'] * 100) if summary['total_statements'] > 0 else 0
        color = get_category_color(cat)
        
        with cols[idx]:
            st.markdown(f"""
            <div class="metric-card" style="background: {color};">
                <div style="font-size: 2.5rem; font-weight: bold;">{count}</div>
                <div style="font-size: 1rem; margin: 0.5rem 0;">{cat}</div>
                <div style="font-size: 0.9rem;">{percentage:.0f}%</div>
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
            st.markdown(f"*{CATEGORY_DESCRIPTIONS[category]}*")
            st.markdown("---")
            
            for idx, item in enumerate(cat_items, 1):
                st.markdown(f"""
                <div class="statement-card">
                    <h4>{idx}. "{item['aussage']}"</h4>
                    <span class="category-badge badge-{category.lower()}">{category}</span>
                    <span class="category-badge" style="background-color: #6c757d; color: white;">Punkte: {item['punkte']}</span>
                    <p style="margin-top: 1rem;"><strong>Begründung:</strong> {item['begründung']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Downloads
    st.markdown("---")
    st.header("📥 Report Download")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 PDF Report")
        if st.button("🔨 PDF generieren", key="gen_pdf", use_container_width=True):
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
        if st.button("🔨 DOCX generieren", key="gen_docx", use_container_width=True):
            with st.spinner("Generiere DOCX..."):
                docx_buffer = generate_docx_report(analysis_data, summary, model_info)
                st.download_button(
                    label="📥 DOCX herunterladen",
                    data=docx_buffer,
                    file_name=f"DESINFO_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
    
    # New Analysis Button
    st.markdown("---")
    if st.button("🔄 Neue Analyse starten", use_container_width=True):
        st.session_state.analysis_data = None
        st.session_state.summary = None
        st.session_state.input_text = ""
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem 0;">
    <p><strong>DESINFO Political Discourse Analyzer v2.0</strong></p>
    <p>Powered by <a href="https://www.democracy-intelligence.de" target="_blank" style="color: #e94560;">Democracy Intelligence</a></p>
</div>
""", unsafe_allow_html=True)
