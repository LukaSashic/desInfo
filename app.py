import streamlit as st
import requests
import json
from datetime import datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

# === PAGE CONFIG (MUST BE FIRST) ===
st.set_page_config(
    page_title="DESINFO Analyse Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === STYLING ===
st.markdown("""
<style>
    /* Sidebar Fixes - READABLE TEXT */
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
    [data-testid="stSidebar"] h3 {
        color: white !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] p {
        color: rgba(255, 255, 255, 0.95) !important;
        font-size: 0.95rem !important;
    }
    
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stTextArea label,
    [data-testid="stSidebar"] .stSelectbox label {
        color: white !important;
        font-weight: 500 !important;
    }
    
    /* Main Content */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Report Container - Like PDF Report */
    .report-container {
        background: white;
        border-radius: 12px;
        padding: 2.5rem;
        box-shadow: 0 2px 20px rgba(0,0,0,0.08);
        margin: 2rem 0;
    }
    
    .report-header {
        border-bottom: 3px solid #667eea;
        padding-bottom: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .report-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: 0.5rem;
    }
    
    .report-subtitle {
        font-size: 1.1rem;
        color: #666;
        font-weight: 400;
    }
    
    /* Summary Box */
    .summary-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin: 2rem 0;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
    }
    
    .summary-title {
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .summary-content {
        font-size: 1.05rem;
        line-height: 1.7;
        opacity: 0.95;
    }
    
    /* Category Sections - Report Style */
    .report-section {
        margin: 2.5rem 0;
        page-break-inside: avoid;
    }
    
    .report-category-title {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .report-category-desc {
        font-size: 1rem;
        color: #555;
        margin-bottom: 1.5rem;
        font-style: italic;
        padding-left: 0.5rem;
    }
    
    .report-item {
        background: #f8f9fa;
        padding: 1.2rem;
        margin: 1rem 0;
        border-left: 4px solid;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    
    .report-item-number {
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #2d3748;
    }
    
    .report-item-text {
        font-size: 1rem;
        color: #4a5568;
        line-height: 1.6;
        padding-left: 1.5rem;
    }
    
    /* Stats Cards */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .stat-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        border-left: 4px solid;
        transition: transform 0.2s;
    }
    
    .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.3rem;
    }
    
    .stat-label {
        font-size: 0.95rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Buttons */
    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.8rem 1.5rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 1.05rem;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Alert Boxes */
    .stAlert {
        border-radius: 8px;
        border-left-width: 4px;
    }
</style>
""", unsafe_allow_html=True)

# === CONSTANTS ===
API_URL = "http://217.154.156.197:8003/desInfo/report"
DEFAULT_MODEL_ID = 1

CATEGORY_COLORS = {
    'FALSCH': '#ef4444',
    'DELEGITIMIERUNG': '#f97316',
    'VERZERRUNG': '#eab308',
    'FRAME': '#3b82f6',
    'WAHR': '#10b981'
}

CATEGORY_DESCRIPTIONS = {
    'FALSCH': 'Aussagen, die nachweislich falsch oder irreführend sind',
    'DELEGITIMIERUNG': 'Aussagen, die demokratische Institutionen oder Prozesse untergraben',
    'VERZERRUNG': 'Einseitige oder verzerrt dargestellte Informationen',
    'FRAME': 'Verwendung spezifischer Framings zur Beeinflussung',
    'WAHR': 'Aussagen, die faktisch korrekt und ausgewogen dargestellt sind'
}

CATEGORY_SYMBOLS = {
    'FALSCH': '✗',
    'DELEGITIMIERUNG': '⚠',
    'VERZERRUNG': '◐',
    'FRAME': '▣',
    'WAHR': '✓'
}

# === HELPER FUNCTIONS ===
def get_category_color(category):
    """Get color for category"""
    return CATEGORY_COLORS.get(category, '#6b7280')

def analyze_text(text, model_id=DEFAULT_MODEL_ID):
    """Call DESINFO API"""
    try:
        response = requests.get(
            API_URL,
            params={'modelID': model_id, 'text': text},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ API Fehler: {str(e)}")
        return None

def generate_summary(analysis_data):
    """Generate executive summary"""
    total = len(analysis_data)
    categories = {}
    
    for item in analysis_data:
        cat = item['kategorie']
        categories[cat] = categories.get(cat, 0) + 1
    
    problematic = categories.get('FALSCH', 0) + categories.get('DELEGITIMIERUNG', 0) + categories.get('VERZERRUNG', 0)
    problematic_pct = (problematic / total * 100) if total > 0 else 0
    
    if problematic_pct > 60:
        assessment = "stark problematisch"
        emoji = "🔴"
    elif problematic_pct > 30:
        assessment = "teilweise problematisch"
        emoji = "🟡"
    else:
        assessment = "weitgehend unproblematisch"
        emoji = "🟢"
    
    summary = f"{emoji} Die Analyse von {total} Aussagen zeigt: {problematic_pct:.1f}% der Aussagen sind {assessment}. "
    
    if categories.get('FALSCH', 0) > 0:
        summary += f"{categories['FALSCH']} Aussagen sind nachweislich falsch. "
    if categories.get('DELEGITIMIERUNG', 0) > 0:
        summary += f"{categories['DELEGITIMIERUNG']} Aussagen zielen auf Delegitimierung ab. "
    if categories.get('WAHR', 0) > 0:
        summary += f"{categories['WAHR']} Aussagen sind faktisch korrekt."
    
    return summary

def generate_pdf_report(analysis_data, summary):
    """Generate PDF report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=1
    )
    story.append(Paragraph("DESINFO Analyse Report", title_style))
    story.append(Paragraph(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 1*cm))
    
    # Summary
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        leftIndent=10,
        rightIndent=10,
        spaceAfter=20
    )
    story.append(Paragraph("<b>Zusammenfassung:</b>", styles['Heading2']))
    story.append(Paragraph(summary, summary_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Categories
    categories_grouped = {}
    for item in analysis_data:
        cat = item['kategorie']
        if cat not in categories_grouped:
            categories_grouped[cat] = []
        categories_grouped[cat].append(item)
    
    for category in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        if category in categories_grouped:
            cat_items = categories_grouped[category]
            
            cat_style = ParagraphStyle(
                f'Cat_{category}',
                parent=styles['Heading2'],
                textColor=colors.HexColor(CATEGORY_COLORS[category]),
                spaceAfter=10
            )
            story.append(Paragraph(f"{category} ({len(cat_items)})", cat_style))
            story.append(Paragraph(CATEGORY_DESCRIPTIONS[category], styles['Italic']))
            story.append(Spacer(1, 0.3*cm))
            
            for idx, item in enumerate(cat_items, 1):
                story.append(Paragraph(f"<b>{idx}. \"{item['aussage']}\"</b>", styles['Normal']))
                story.append(Paragraph(f"– {item['begründung']}", styles['Normal']))
                story.append(Spacer(1, 0.3*cm))
            
            story.append(Spacer(1, 0.5*cm))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_docx_report(analysis_data, summary):
    """Generate DOCX report"""
    doc = Document()
    
    # Title
    title = doc.add_heading('DESINFO Analyse Report', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    doc.add_paragraph()
    
    # Summary
    doc.add_heading('Zusammenfassung', 1)
    doc.add_paragraph(summary)
    doc.add_paragraph()
    
    # Categories
    categories_grouped = {}
    for item in analysis_data:
        cat = item['kategorie']
        if cat not in categories_grouped:
            categories_grouped[cat] = []
        categories_grouped[cat].append(item)
    
    for category in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        if category in categories_grouped:
            cat_items = categories_grouped[category]
            
            heading = doc.add_heading(f"{category} ({len(cat_items)})", 2)
            doc.add_paragraph(CATEGORY_DESCRIPTIONS[category]).italic = True
            
            for idx, item in enumerate(cat_items, 1):
                p = doc.add_paragraph()
                p.add_run(f"{idx}. \"{item['aussage']}\"").bold = True
                doc.add_paragraph(f"– {item['begründung']}")
            
            doc.add_paragraph()
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# === SIDEBAR ===
with st.sidebar:
    st.markdown("# 🔍 DESINFO")
    st.markdown("### Demokratie-Intelligenz Analyse Tool")
    
    st.markdown("---")
    
    st.markdown("### 📋 Anleitung")
    st.markdown("""
    **1.** Text in das Feld eingeben
    
    **2.** "Analyse starten" klicken
    
    **3.** Ergebnisse prüfen
    
    **4.** Report herunterladen (PDF/DOCX)
    """)
    
    st.markdown("---")
    
    st.markdown("### ℹ️ Kategorien")
    for cat, desc in CATEGORY_DESCRIPTIONS.items():
        symbol = CATEGORY_SYMBOLS[cat]
        st.markdown(f"**{symbol} {cat}**")
        st.markdown(f"*{desc}*")
        st.markdown("")
    
    st.markdown("---")
    st.markdown("**🌐 Democracy Intelligence**")
    st.markdown("Version 2.5")

# === MAIN CONTENT ===
st.markdown("""
<div class="main-header">
    <h1 style='margin: 0; font-size: 2.5rem;'>🔍 DESINFO Analyse Tool</h1>
    <p style='margin-top: 0.5rem; font-size: 1.1rem; opacity: 0.95;'>Demokratie-Intelligenz für politische Kommunikation</p>
</div>
""", unsafe_allow_html=True)

# === INPUT SECTION - PROMINENTLY PLACED ===
st.markdown("## 📝 Analyse starten")

with st.form(key="analysis_form"):
    text_input = st.text_area(
        "Text zur Analyse eingeben:",
        height=250,
        placeholder="Geben Sie hier den zu analysierenden Text ein (mehrere Aussagen möglich)...",
        help="Geben Sie politische Aussagen oder Texte zur Analyse ein. Mehrere Statements können durch Pipe (|) getrennt werden."
    )
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        # FIX #1: Analyse button is IMMEDIATELY available (no conditions)
        submit_button = st.form_submit_button(
            "🚀 Analyse starten",
            use_container_width=True
        )

# === ANALYSIS RESULTS ===
if submit_button:
    if not text_input or len(text_input.strip()) < 10:
        st.warning("⚠️ Bitte geben Sie mindestens 10 Zeichen Text ein.")
    else:
        with st.spinner("🔄 Analysiere Text..."):
            result = analyze_text(text_input)
            
            if result and isinstance(result, list) and len(result) > 0:
                # Store in session state
                st.session_state['analysis_result'] = result
                st.session_state['analysis_summary'] = generate_summary(result)
                st.success("✅ Analyse erfolgreich abgeschlossen!")
            else:
                st.error("❌ Keine Ergebnisse erhalten. Bitte versuchen Sie es erneut.")

# === DISPLAY RESULTS ===
if 'analysis_result' in st.session_state:
    analysis_data = st.session_state['analysis_result']
    summary = st.session_state['analysis_summary']
    
    st.markdown("---")
    
    # FIX #3: REPORT-STYLE DISPLAY (exactly like PDF report)
    st.markdown('<div class="report-container">', unsafe_allow_html=True)
    
    # Report Header
    st.markdown(f"""
    <div class="report-header">
        <div class="report-title">📊 Analyse Ergebnisse</div>
        <div class="report-subtitle">Erstellt am {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats Overview
    categories_count = {}
    for item in analysis_data:
        cat = item['kategorie']
        categories_count[cat] = categories_count.get(cat, 0) + 1
    
    st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
    for cat in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        if cat in categories_count:
            hex_color = get_category_color(cat)
            count = categories_count[cat]
            symbol = CATEGORY_SYMBOLS[cat]
            st.markdown(f"""
            <div class="stat-card" style="border-left-color: {hex_color};">
                <div class="stat-value" style="color: {hex_color};">{count}</div>
                <div class="stat-label">{symbol} {cat}</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Executive Summary
    st.markdown(f"""
    <div class="summary-box">
        <div class="summary-title">
            📋 Zusammenfassung
        </div>
        <div class="summary-content">
            {summary}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Detailed Results by Category
    st.markdown("## 📑 Detaillierte Ergebnisse")
    
    categories_grouped = {}
    for item in analysis_data:
        cat = item['kategorie']
        if cat not in categories_grouped:
            categories_grouped[cat] = []
        categories_grouped[cat].append(item)
    
    for category in ['FALSCH', 'DELEGITIMIERUNG', 'VERZERRUNG', 'FRAME', 'WAHR']:
        if category not in categories_grouped:
            continue
            
        cat_items = categories_grouped[category]
        hex_color = get_category_color(category)
        symbol = CATEGORY_SYMBOLS[category]
        
        st.markdown(f"""
        <div class="report-section">
            <div class="report-category-title" style="border-bottom-color: {hex_color}; color: {hex_color};">
                {symbol} {category} ({len(cat_items)})
            </div>
            <div class="report-category-desc">
                {CATEGORY_DESCRIPTIONS[category]}
            </div>
        """, unsafe_allow_html=True)
        
        for idx, item in enumerate(cat_items, 1):
            st.markdown(f"""
            <div class="report-item" style="border-left-color: {hex_color};">
                <div class="report-item-number">
                    {idx}. <span style="color: {hex_color};">{symbol}</span> <strong>"{item['aussage']}"</strong>
                </div>
                <div class="report-item-text">
                    – {item['begründung']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)  # Close report-container
    
    # Download Section
    st.markdown("---")
    st.markdown("## 📥 Report Download")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📄 PDF Report generieren", use_container_width=True, key="pdf_btn"):
            with st.spinner("🔄 Generiere PDF..."):
                pdf_buffer = generate_pdf_report(analysis_data, summary)
                st.download_button(
                    "⬇️ PDF herunterladen",
                    pdf_buffer,
                    f"DesInfo_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    "application/pdf",
                    use_container_width=True
                )
    
    with col2:
        if st.button("📝 DOCX Report generieren", use_container_width=True, key="docx_btn"):
            with st.spinner("🔄 Generiere DOCX..."):
                docx_buffer = generate_docx_report(analysis_data, summary)
                st.download_button(
                    "⬇️ DOCX herunterladen",
                    docx_buffer,
                    f"DesInfo_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )

# === FOOTER ===
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem 0;">
    <p style="font-weight: 600; margin-bottom: 0.5rem;">
        Powered by <a href="https://www.democracy-intelligence.de" target="_blank" style="color: #667eea; text-decoration: none;">Democracy Intelligence</a>
    </p>
    <p style="font-size: 0.9rem; margin: 0;">DESINFO v2.5 Final</p>
</div>
""", unsafe_allow_html=True)
