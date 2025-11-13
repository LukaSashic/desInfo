import streamlit as st
import requests
from io import BytesIO
from collections import Counter
from datetime import datetime

# PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
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
ANALYZE_ENDPOINT = f"{API_BASE_URL}/desInfo/generateReport"  # KORRIGIERT!

LOGO_URL = "https://uzimkjbynnadffyvsohi.supabase.co/storage/v1/object/public/bilder/di_logo_300.png"

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
    'FALSCH': 'Objektiv widerlegte Behauptungen. Es liegen belastbare Daten oder Ereignisprotokolle vor, die das Gegenteil zeigen.',
    'DELEGITIMIERUNG': 'Abwertung oder Untergrabung von Personen, Gruppen oder Institutionen. Sprachliche Diskreditierungen, Kampfbegriffe oder systematische Diffamierungen.',
    'VERZERRUNG': 'Formal richtige Kernaussagen, die durch Übertreibung, Verkürzung oder Kontextausblendung ein schiefes Bild erzeugen.',
    'FRAME': 'Sprachliche Deutungsrahmen, die neutrale Sachverhalte emotional oder normativ aufladen.',
    'WAHR': 'Sachlich zutreffende Aussagen, die überprüfbar sind und keinen überzogenen Frame, keine Verzerrung oder Delegitimierung enthalten.'
}

# ============================================
# PAGE CONFIG
# ============================================
st.set_page_config(
    page_title="DESINFO Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS - FIXED VERSION
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Sidebar - READABLE WHITE TEXT */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 1rem;
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: white !important;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3 {
        color: white !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] p {
        color: rgba(255, 255, 255, 0.95) !important;
        font-size: 0.95rem !important;
    }
    
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stTextArea label {
        color: white !important;
        font-weight: 500 !important;
    }
    
    [data-testid="stSidebar"] .stExpander {
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
    
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.3) !important;
    }
    
    /* Main Container */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .block-container {
        max-width: 1400px;
        padding: 2rem 1rem;
    }
    
    /* Logo */
    .logo-container {
        text-align: center;
        padding: 1rem 0;
    }
    
    .logo-container img {
        max-width: 200px;
        height: auto;
    }
    
    /* Header */
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        color: white;
        text-align: center;
        padding: 1rem 0 0.5rem 0;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .subtitle {
        font-size: 1.5rem;
        color: #ffd93d;
        text-align: center;
        font-weight: 600;
        margin-bottom: 2rem;
    }
    
    /* White Content Box */
    .content-box {
        background: white;
        border-radius: 20px;
        padding: 2.5rem;
        margin: 1.5rem 0;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    
    /* Section Headers */
    .section-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #ffd93d 0%, #ffb800 100%);
        color: #1a1a1a;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        font-weight: 700;
        border-radius: 50px;
        transition: all 0.3s;
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 217, 61, 0.4);
    }
    
    .stButton>button:disabled {
        background: #cccccc;
        color: #666666;
        cursor: not-allowed;
    }
    
    /* Text Area */
    .stTextArea textarea {
        border: 2px solid #667eea;
        border-radius: 15px;
        font-size: 1rem;
        padding: 1rem;
    }
    
    /* Score Box */
    .score-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        color: white;
        margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
    }
    
    .score-value {
        font-size: 6rem;
        font-weight: 800;
        margin: 0;
    }
    
    .score-grade {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 1rem 0;
        color: #ffd93d;
    }
    
    .score-label {
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    /* Metric Cards */
    .metric-card {
        text-align: center;
        padding: 1.5rem 1rem;
        border-radius: 15px;
        color: white;
        margin: 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0.3rem 0;
    }
    
    .metric-label {
        font-size: 1rem;
        font-weight: 600;
    }
    
    .metric-percent {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Statement Card */
    .statement-card {
        background: #f8f9fa;
        border-left: 5px solid;
        padding: 1.5rem;
        margin: 1.5rem 0;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .statement-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 0.8rem;
    }
    
    .statement-text {
        font-size: 1rem;
        color: #333;
        line-height: 1.6;
    }
    
    /* Category Badges */
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
    
    /* Category Header */
    .category-header {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a1a;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #667eea;
    }
    
    .category-description {
        font-style: italic;
        color: #666;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: #f0f0f0;
        border-radius: 8px;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# ============================================
# HELPER FUNCTIONS
# ============================================

@st.cache_data(ttl=300)
def fetch_models():
    """Lädt verfügbare Models von API"""
    try:
        response = requests.get(MODELS_ENDPOINT, timeout=10)
        if response.ok:
            data = response.json()
            return [m for m in data.get('models', []) if m.get('valid', False)]
    except Exception as e:
        st.error(f"⚠️ Fehler beim Laden der Models: {e}")
    return []

def parse_statements(text: str) -> list:
    """Parse statements from text - supports | separator or newlines"""
    if '|' in text:
        statements = [s.strip() for s in text.split('|') if s.strip()]
    else:
        statements = [s.strip() for s in text.split('\n') if s.strip()]
    return statements

def call_api(statements: list, model_id: int) -> dict:
    """Call DESINFO API with correct endpoint"""
    text_param = "|".join(statements)
    params = {"modelID": model_id, "text": text_param}
    
    try:
        response = requests.get(ANALYZE_ENDPOINT, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        # Add punkte field if not present
        for item in data:
            if 'punkte' not in item:
                item['punkte'] = CATEGORY_POINTS.get(item['kategorie'], 0)
        
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}

def calculate_summary(analysis_data: list) -> dict:
    """Calculate summary statistics"""
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

def get_category_color(category: str) -> tuple:
    """Get hex and reportlab color for category"""
    color_map = {
        'FALSCH': ('#dc3545', colors.HexColor('#dc3545')),
        'DELEGITIMIERUNG': ('#fd7e14', colors.HexColor('#fd7e14')),
        'VERZERRUNG': ('#ffc107', colors.HexColor('#ffc107')),
        'FRAME': ('#28a745', colors.HexColor('#28a745')),
        'WAHR': ('#007bff', colors.HexColor('#007bff'))
    }
    return color_map.get(category, ('#6c757d', colors.grey))

def generate_pdf_report(analysis_data: list, summary: dict, model_info: dict = None) -> BytesIO:
    """Generate PDF report matching example format"""
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
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=24,
        leading=28,
        textColor=colors.black,
        spaceAfter=20,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=16,
        leading=20,
        textColor=colors.black,
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=11,
        leading=15,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    italic_style = ParagraphStyle(
        'Italic',
        parent=body_style,
        fontName='Helvetica-Oblique'
    )
    
    # Add Logo if available
    try:
        logo_response = requests.get(LOGO_URL, timeout=5)
        if logo_response.ok:
            logo_buffer = BytesIO(logo_response.content)
            logo = Image(logo_buffer, width=4*cm, height=4*cm)
            logo.hAlign = 'LEFT'
            elements.append(logo)
            elements.append(Spacer(1, 0.5*cm))
    except:
        pass
    
    # Title
    elements.append(Paragraph("Vollständige Auswertung", title_style))
    elements.append(Spacer(1, 0.3*cm))
    
    # Line
    line = Table([['']], colWidths=[16*cm])
    line.setStyle(TableStyle([('LINEABOVE', (0,0), (-1,0), 1, colors.grey)]))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    # Summary
    elements.append(Paragraph("Zusammenfassung", heading_style))
    total = summary['total_statements']
    
    summary_text = f"Die vorliegende Analyse untersucht {total} Aussagen nach ihrer faktischen Richtigkeit und kommunikativen Qualität. Das Ergebnis zeigt eine ausgeprägte Tendenz zu {summary['grade_label']}en Darstellungen."
    
    elements.append(Paragraph(summary_text, body_style))
    elements.append(Spacer(1, 0.8*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    # Quantification
    elements.append(Paragraph("Quantifizierung", heading_style))
    elements.append(Paragraph(f"Anzahl Aussagen gesamt: {total}", body_style))
    elements.append(Spacer(1, 0.3*cm))
    
    counts = summary['category_counts']
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        count = counts.get(cat, 0)
        percentage = (count / total * 100) if total > 0 else 0
        hex_color, _ = get_category_color(cat)
        cat_text = f'<font color="{hex_color}">■</font> {cat}: {count} ({percentage:.0f} %)'
        elements.append(Paragraph(cat_text, body_style))
    
    elements.append(Spacer(1, 0.8*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    # Scoring
    elements.append(Paragraph("Scoring", heading_style))
    score_text = f"<b>Desinfo-Score: {summary['desinfo_score']}</b><br/>{summary['grade']}: {summary['grade_label']}<br/><br/>{summary['grade_description']}"
    elements.append(Paragraph(score_text, body_style))
    elements.append(Spacer(1, 0.8*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    # Grade Scale
    elements.append(Paragraph("Einteilung", heading_style))
    for grade, (min_s, max_s, label, _) in SCORE_GRADES.items():
        elements.append(Paragraph(f"{grade}: {min_s} bis {max_s}: {label}", body_style))
    
    elements.append(PageBreak())
    
    # Detailed Results
    elements.append(Paragraph("Vollständige Auswertung des Textes", title_style))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(line)
    elements.append(Spacer(1, 0.8*cm))
    
    categories_order = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    
    for category in categories_order:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        elements.append(Paragraph(f"<b>{category} ({len(cat_items)})</b>", heading_style))
        elements.append(Paragraph(CATEGORY_DESCRIPTIONS[category], italic_style))
        elements.append(Spacer(1, 0.5*cm))
        
        for idx, item in enumerate(cat_items, 1):
            hex_color, _ = get_category_color(category)
            symbol = '✓' if category == 'WAHR' else '■'
            
            stmt_text = f'{idx}. <font color="{hex_color}">{symbol}</font> <b>"{item["aussage"]}"</b>'
            elements.append(Paragraph(stmt_text, body_style))
            elements.append(Spacer(1, 0.2*cm))
            
            beg_text = f"– {item['begründung']}"
            elements.append(Paragraph(beg_text, body_style))
            elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Spacer(1, 0.5*cm))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_docx_report(analysis_data: list, summary: dict, model_info: dict = None) -> BytesIO:
    """Generate DOCX report"""
    doc = Document()
    
    doc.add_heading('Vollständige Auswertung', 0)
    doc.add_heading('Zusammenfassung', 1)
    
    total = summary['total_statements']
    summary_text = f"Die vorliegende Analyse untersucht {total} Aussagen nach ihrer faktischen Richtigkeit und kommunikativen Qualität."
    doc.add_paragraph(summary_text)
    
    doc.add_heading('Quantifizierung', 1)
    doc.add_paragraph(f"Anzahl Aussagen gesamt: {total}")
    
    counts = summary['category_counts']
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        count = counts.get(cat, 0)
        percentage = (count / total * 100) if total > 0 else 0
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
    
    categories_order = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    
    for category in categories_order:
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
# SIDEBAR - WITH READABLE WHITE TEXT
# ============================================
with st.sidebar:
    st.markdown("# ⚙️ Einstellungen")
    
    # Load Models
    valid_models = fetch_models()
    
    if valid_models:
        st.markdown("### AI Model")
        model_options = {f"{m['modelName']} ({m['provider']})": m for m in valid_models}
        selected_model_label = st.selectbox(
            "Wähle ein Model:",
            options=list(model_options.keys()),
            index=0
        )
        st.session_state.selected_model = model_options[selected_model_label]
        
        with st.expander("ℹ️ Model Details"):
            model = st.session_state.selected_model
            st.write(f"**ID:** {model['modelID']}")
            st.write(f"**Name:** {model['modelName']}")
            st.write(f"**Provider:** {model['provider']}")
    
    st.markdown("---")
    
    st.markdown("### 📚 Kategorien")
    st.markdown("""
    - 🔴 **FALSCH** (5 Punkte)
    - 🟠 **DELEGITIMIERUNG** (4 Punkte)
    - 🟡 **VERZERRUNG** (3 Punkte)
    - 🟢 **FRAME** (1 Punkt)
    - 🔵 **WAHR** (0 Punkte)
    """)
    
    if st.session_state.analysis_data is not None:
        st.markdown("---")
        if st.button("🔄 Neue Analyse", use_container_width=True):
            st.session_state.analysis_data = None
            st.session_state.summary = None
            st.session_state.input_text = ""
            st.rerun()

# ============================================
# MAIN APP
# ============================================

if not valid_models:
    st.error("⚠️ Keine Models verfügbar. Bitte API-Verbindung prüfen.")
    st.stop()

# Logo
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" alt="Democracy Intelligence Logo"></div>', unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">DESINFO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Demokratie-Intelligenz für politische Kommunikation</div>', unsafe_allow_html=True)

# Main Content
if st.session_state.analysis_data is None:
    # INPUT MODE
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">📝 Analyse starten</div>', unsafe_allow_html=True)
    st.markdown('<p style="color: #666; text-align: center; margin-bottom: 1.5rem;">Geben Sie politische Aussagen ein (eine pro Zeile oder mit | getrennt)</p>', unsafe_allow_html=True)
    
    # Form with always-visible button (FIX #2)
    with st.form(key="analysis_form"):
        input_text = st.text_area(
            "Text zur Analyse:",
            height=350,
            placeholder="Beispiel:\nDeutschland zerstört Demokratie in Serbien\nDie Regierung plant den Dritten Weltkrieg",
            value=st.session_state.input_text,
            help="Geben Sie hier politische Aussagen ein, die Sie analysieren möchten."
        )
        
        st.session_state.input_text = input_text
        
        # Button is ALWAYS visible (FIX #2)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit_button = st.form_submit_button(
                "🚀 Analyse starten",
                use_container_width=True,
                type="primary"
            )
    
    # Handle form submission
    if submit_button:
        if not input_text or len(input_text.strip()) < 10:
            st.warning("⚠️ Bitte geben Sie mindestens 10 Zeichen Text ein.")
        else:
            statements = parse_statements(input_text)
            model_id = st.session_state.selected_model['modelID']
            model_name = st.session_state.selected_model['modelName']
            
            with st.spinner(f"🔍 Analysiere {len(statements)} Aussagen mit {model_name}..."):
                result = call_api(statements, model_id)
                
                if result['success']:
                    st.session_state.analysis_data = result['data']
                    st.session_state.summary = calculate_summary(result['data'])
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ API Fehler: {result['error']}")
    
    # Preview
    if input_text:
        st.markdown("---")
        statements = parse_statements(input_text)
        st.info(f"📊 **{len(statements)} Aussagen** werden analysiert")
    
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # RESULTS MODE - REPORT STYLE (FIX #3)
    analysis_data = st.session_state.analysis_data
    summary = st.session_state.summary
    model_info = st.session_state.selected_model
    
    # Score Display
    st.markdown(f"""
    <div class="score-box">
        <div class="score-value">{summary['desinfo_score']}</div>
        <div class="score-grade">Grade {summary['grade']}</div>
        <div class="score-label">{summary['grade_label']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quantification
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Quantifizierung</div>', unsafe_allow_html=True)
    
    cols = st.columns(5)
    categories = ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']
    
    for idx, cat in enumerate(categories):
        count = summary['category_counts'].get(cat, 0)
        percentage = (count / summary['total_statements'] * 100) if summary['total_statements'] > 0 else 0
        hex_color, _ = get_category_color(cat)
        
        with cols[idx]:
            st.markdown(f"""
            <div class="metric-card" style="background: {hex_color};">
                <div class="metric-value">{count}</div>
                <div class="metric-label">{cat}</div>
                <div class="metric-percent">{percentage:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Detailed Results - REPORT STYLE (FIX #3)
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Detaillierte Ergebnisse</div>', unsafe_allow_html=True)
    
    for category in categories:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        # Category Header
        hex_color, _ = get_category_color(category)
        st.markdown(f'<div class="category-header" style="border-bottom-color: {hex_color};">{category} ({len(cat_items)} Aussagen)</div>', unsafe_allow_html=True)
        
        # Category Description
        st.markdown(f'<div class="category-description">{CATEGORY_DESCRIPTIONS[category]}</div>', unsafe_allow_html=True)
        
        # Statements
        for idx, item in enumerate(cat_items, 1):
            st.markdown(f"""
            <div class="statement-card" style="border-left-color: {hex_color};">
                <div class="statement-title">{idx}. "{item['aussage']}"</div>
                <span class="category-badge badge-{category.lower()}">{category}</span>
                <span class="category-badge" style="background: #6c757d;">Punkte: {item.get('punkte', CATEGORY_POINTS.get(category, 0))}</span>
                <div class="statement-text" style="margin-top: 1rem;"><strong>Begründung:</strong> {item['begründung']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Downloads
    st.markdown('<div class="content-box">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📥 Report Download</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 PDF Report generieren", use_container_width=True):
            with st.spinner("Generiere PDF..."):
                pdf_buffer = generate_pdf_report(analysis_data, summary, model_info)
                st.download_button(
                    label="⬇️ PDF herunterladen",
                    data=pdf_buffer,
                    file_name=f"DesInfo_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
    
    with col2:
        if st.button("📝 DOCX Report generieren", use_container_width=True):
            with st.spinner("Generiere DOCX..."):
                docx_buffer = generate_docx_report(analysis_data, summary, model_info)
                st.download_button(
                    label="⬇️ DOCX herunterladen",
                    data=docx_buffer,
                    file_name=f"DesInfo_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
    
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: white; padding: 2rem 0;">
    <p style="font-size: 1.2rem; font-weight: 600;">
        Powered by <a href="https://www.democracy-intelligence.de" target="_blank" style="color: #ffd93d; text-decoration: none;">Democracy Intelligence</a>
    </p>
    <p style="font-size: 0.9rem; opacity: 0.8;">DESINFO v2.6 Final - Alle Fixes implementiert</p>
</div>
""", unsafe_allow_html=True)
