import streamlit as st
import requests
from io import BytesIO
from collections import Counter
from datetime import datetime

# PDF Generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
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

LOGO_URL = "https://uzimkjbynnadffyvsohi.supabase.co/storage/v1/object/public/bilder/di_logo_300.png"

# Debug Mode
DEBUG_MODE = False  # Set to True to see debug output

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
# PAGE CONFIG - Force dark theme
# ============================================
st.set_page_config(
    page_title="DESINFO Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# MINIMAL CSS - Let Streamlit theme handle colors
# ============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
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
    
    /* Headers */
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        padding: 1rem 0 0.5rem 0;
        text-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }
    
    .subtitle {
        font-size: 1.3rem;
        text-align: center;
        font-weight: 400;
        margin-bottom: 2rem;
        opacity: 0.95;
    }
    
    /* Results Container */
    .results-container {
        background: white;
        border-radius: 20px;
        padding: 2.5rem;
        margin: 2rem 0;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    
    /* Score Box */
    .score-box {
        background: linear-gradient(135deg, #2c5f7d 0%, #1a3a4d 100%);
        border-radius: 20px;
        padding: 3rem 2rem;
        text-align: center;
        color: white;
        margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(44, 95, 125, 0.4);
    }
    
    .score-value {
        font-size: 6rem;
        font-weight: 800;
        margin: 0;
        color: white;
    }
    
    .score-grade {
        font-size: 2.5rem;
        font-weight: 700;
        margin: 1rem 0;
        color: #e91e8c;
    }
    
    .score-label {
        font-size: 1.8rem;
        font-weight: 600;
        color: white;
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
        border-bottom: 3px solid #2c5f7d;
    }
    
    .category-description {
        font-style: italic;
        color: #666;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: #f0f0f0;
        border-radius: 8px;
    }
    
    /* Section Title */
    .section-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    
    /* Hide Streamlit Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Debug Box */
    .debug-box {
        background: #f0f0f0;
        border: 2px solid #666;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        font-family: monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# HELPER FUNCTIONS
# ============================================

def debug_log(message):
    """Print debug message if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        st.sidebar.markdown(f'<div class="debug-box">🐛 {message}</div>', unsafe_allow_html=True)

@st.cache_data(ttl=300)
def fetch_models():
    """Lädt verfügbare Models von API"""
    try:
        debug_log(f"Fetching models from: {MODELS_ENDPOINT}")
        response = requests.get(MODELS_ENDPOINT, timeout=10)
        debug_log(f"Response status: {response.status_code}")
        
        if response.ok:
            data = response.json()
            models = [m for m in data.get('models', []) if m.get('valid', False)]
            debug_log(f"Found {len(models)} valid models")
            return models
        else:
            debug_log(f"API Error: {response.status_code}")
            return []
    except Exception as e:
        debug_log(f"Exception: {str(e)}")
        st.error(f"⚠️ Fehler beim Laden der Models: {e}")
        return []

def parse_statements(text: str) -> list:
    """Parse statements from text"""
    if '|' in text:
        statements = [s.strip() for s in text.split('|') if s.strip()]
    else:
        statements = [s.strip() for s in text.split('\n') if s.strip()]
    return statements

def call_api(statements: list, model_id: int) -> dict:
    """Call DESINFO API"""
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
    """Generate PDF report - NO LOGO"""
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

def get_docx_color(category: str) -> tuple:
    """Get RGB color tuple for DOCX (R, G, B values 0-255)"""
    color_map = {
        'FALSCH': (220, 53, 69),        # Red
        'DELEGITIMIERUNG': (253, 126, 20),  # Orange  
        'VERZERRUNG': (255, 193, 7),    # Yellow
        'FRAME': (40, 167, 69),         # Green
        'WAHR': (0, 123, 255)           # Blue
    }
    return color_map.get(category, (108, 117, 125))  # Default grey

def generate_docx_report(analysis_data: list, summary: dict, model_info: dict = None) -> BytesIO:
    """Generate DOCX report with colors"""
    doc = Document()
    
    doc.add_heading('Vollständige Auswertung', 0)
    doc.add_heading('Zusammenfassung', 1)
    
    total = summary['total_statements']
    summary_text = f"Die vorliegende Analyse untersucht {total} Aussagen nach ihrer faktischen Richtigkeit und kommunikativen Qualität."
    doc.add_paragraph(summary_text)
    
    doc.add_heading('Quantifizierung', 1)
    doc.add_paragraph(f"Anzahl Aussagen gesamt: {total}")
    
    # Add colored category counts
    counts = summary['category_counts']
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        count = counts.get(cat, 0)
        percentage = (count / total * 100) if total > 0 else 0
        
        # Create paragraph with colored bullet
        p = doc.add_paragraph()
        
        # Add colored bullet point
        bullet_run = p.add_run("■ ")
        r, g, b = get_docx_color(cat)
        bullet_run.font.color.rgb = RGBColor(r, g, b)
        bullet_run.font.size = Pt(12)
        
        # Add category text
        text_run = p.add_run(f"{cat}: {count} ({percentage:.0f} %)")
        text_run.font.size = Pt(11)
    
    doc.add_heading('Scoring', 1)
    
    # Score with colored background effect
    score_p = doc.add_paragraph()
    score_run = score_p.add_run(f"Desinfo-Score: {summary['desinfo_score']}")
    score_run.bold = True
    score_run.font.size = Pt(12)
    
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
        
        # Add colored category heading
        heading = doc.add_heading(level=2)
        heading_run = heading.add_run(f"{category} ({len(cat_items)})")
        r, g, b = get_docx_color(category)
        heading_run.font.color.rgb = RGBColor(r, g, b)
        
        # Category description
        desc_p = doc.add_paragraph(CATEGORY_DESCRIPTIONS[category])
        desc_p.italic = True
        
        # Statements with colored symbols
        for idx, item in enumerate(cat_items, 1):
            symbol = '✓' if category == 'WAHR' else '■'
            
            # Statement paragraph
            stmt_p = doc.add_paragraph()
            
            # Add colored symbol and number
            symbol_run = stmt_p.add_run(f'{idx}. {symbol} ')
            symbol_run.bold = True
            r, g, b = get_docx_color(category)
            symbol_run.font.color.rgb = RGBColor(r, g, b)
            
            # Add statement text
            stmt_run = stmt_p.add_run(f'"{item["aussage"]}"')
            stmt_run.bold = True
            
            # Add reasoning
            reason_p = doc.add_paragraph(f"– {item['begründung']}")
            reason_p.style.font.size = Pt(10)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ============================================
# SESSION STATE - Simple initialization
# ============================================
if 'analysis_data' not in st.session_state:
    st.session_state.analysis_data = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'input_text' not in st.session_state:
    st.session_state.input_text = ""

# ============================================
# LOAD MODELS FIRST
# ============================================
valid_models = fetch_models()

# Initialize selected_model with FIRST model if available
if 'selected_model' not in st.session_state:
    if valid_models and len(valid_models) > 0:
        st.session_state.selected_model = valid_models[0]
        debug_log(f"Initialized with model: {valid_models[0]['modelName']}")
    else:
        st.session_state.selected_model = None
        debug_log("No models available!")

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    if valid_models and len(valid_models) > 0:
        st.subheader("AI Model")
        
        # Create options dict
        model_options = {}
        for m in valid_models:
            label = f"{m['modelName']} ({m['provider']})"
            model_options[label] = m
        
        # Get current selection
        if st.session_state.selected_model:
            current_label = f"{st.session_state.selected_model['modelName']} ({st.session_state.selected_model['provider']})"
            try:
                current_index = list(model_options.keys()).index(current_label)
            except ValueError:
                current_index = 0
        else:
            current_index = 0
        
        debug_log(f"Current index: {current_index}")
        debug_log(f"Available options: {list(model_options.keys())}")
        
        # Selectbox
        selected_label = st.selectbox(
            "Wähle ein Model:",
            options=list(model_options.keys()),
            index=current_index
        )
        
        # Update session state
        st.session_state.selected_model = model_options[selected_label]
        
        with st.expander("ℹ️ Model Details"):
            model = st.session_state.selected_model
            st.write(f"**ID:** {model['modelID']}")
            st.write(f"**Name:** {model['modelName']}")
            st.write(f"**Provider:** {model['provider']}")
    else:
        st.error("⚠️ Keine Models verfügbar")
        st.info("API-Verbindung prüfen")
    
    st.divider()
    
    st.subheader("📚 Kategorien")
    st.markdown("""
    🔴 **FALSCH** (5 Punkte)  
    🟠 **DELEGITIMIERUNG** (4 Punkte)  
    🟡 **VERZERRUNG** (3 Punkte)  
    🟢 **FRAME** (1 Punkt)  
    🔵 **WAHR** (0 Punkte)
    """)
    
    if st.session_state.analysis_data is not None:
        st.divider()
        if st.button("🔄 Neue Analyse", use_container_width=True):
            st.session_state.analysis_data = None
            st.session_state.summary = None
            st.session_state.input_text = ""
            st.rerun()

# ============================================
# MAIN APP
# ============================================

if not valid_models or len(valid_models) == 0:
    st.error("⚠️ Keine Models verfügbar. Bitte API-Verbindung prüfen.")
    st.info(f"API Endpoint: {MODELS_ENDPOINT}")
    st.stop()

# Logo
st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" alt="Democracy Intelligence"></div>', unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🔍 DESINFO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Demokratie-Intelligenz für politische Kommunikation</div>', unsafe_allow_html=True)

# Main Content
if st.session_state.analysis_data is None:
    # INPUT MODE
    st.markdown("### 📝 Analyse starten")
    st.info("Geben Sie politische Aussagen ein (eine pro Zeile oder mit | getrennt)")
    
    # Use st.text_area directly - let Streamlit theme handle it
    input_text = st.text_area(
        "Text zur Analyse:",
        height=350,
        value=st.session_state.input_text,
        placeholder="",
        help="Geben Sie hier politische Aussagen ein.",
        key="main_textarea"
    )
    
    st.session_state.input_text = input_text
    
    # Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        analyze_button = st.button(
            "🚀 Analyse starten",
            use_container_width=True,
            type="primary",
            disabled=(not input_text or len(input_text.strip()) < 10)
        )
    
    # Handle analysis
    if analyze_button:
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
        statements = parse_statements(input_text)
        st.info(f"📊 **{len(statements)} Aussagen** werden analysiert")

else:
    # RESULTS MODE
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
    
    # Results in white container
    st.markdown('<div class="results-container">', unsafe_allow_html=True)
    
    # Quantification
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
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Detailed Results
    st.markdown('<div class="section-title">📋 Detaillierte Ergebnisse</div>', unsafe_allow_html=True)
    
    for category in categories:
        cat_items = [item for item in analysis_data if item['kategorie'] == category]
        if not cat_items:
            continue
        
        hex_color, _ = get_category_color(category)
        st.markdown(f'<div class="category-header" style="border-bottom-color: {hex_color};">{category} ({len(cat_items)} Aussagen)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="category-description">{CATEGORY_DESCRIPTIONS[category]}</div>', unsafe_allow_html=True)
        
        for idx, item in enumerate(cat_items, 1):
            st.markdown(f"""
            <div class="statement-card" style="border-left-color: {hex_color};">
                <div class="statement-title">{idx}. "{item['aussage']}"</div>
                <span class="category-badge badge-{category.lower()}">{category}</span>
                <span class="category-badge" style="background: #6c757d;">Punkte: {item.get('punkte', CATEGORY_POINTS.get(category, 0))}</span>
                <div class="statement-text" style="margin-top: 1rem;"><strong>Begründung:</strong> {item['begründung']}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Downloads
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
st.divider()
st.markdown("""
<div style="text-align: center; padding: 2rem 0;">
    <p style="font-size: 1.2rem; font-weight: 600;">
        Powered by <a href="https://www.democracy-intelligence.de" target="_blank" style="color: #e91e8c; text-decoration: none;">Democracy Intelligence</a>
    </p>
    <p style="font-size: 0.9rem; opacity: 0.8;">DESINFO v3.1 Robust - Theme-Based</p>
</div>
""", unsafe_allow_html=True)
