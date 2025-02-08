# Notwendige Bibliotheken importieren
import pandas as pd
import numpy as np
import streamlit as st
import io
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import locale
from pytz import timezone

# Seiten-Konfiguration MUSS als erstes kommen
st.set_page_config(
    page_title="Artikel Analyse",
    page_icon="📊",
    layout="wide"
)

# Styling
st.markdown("""
    <style>
        .main {
            padding: 2rem;
        }
        .stButton>button {
            width: 100%;
        }
        .reportview-container {
            margin-top: -2em;
        }
        .css-1d391kg {
            padding-top: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Session State Initialisierung
if 'inhaltsbericht_loaded' not in st.session_state:
    st.session_state.inhaltsbericht_loaded = False
if 'seitenaufrufe_loaded' not in st.session_state:
    st.session_state.seitenaufrufe_loaded = False

# Helper function für deutsche Zahlenformatierung
def format_german_number(number):
    """Formatiert Zahlen im deutschen Format ohne locale"""
    try:
        # Runden auf ganze Zahl und in String umwandeln
        number_str = f"{int(round(number)):,}"
        # Ersetze Kommas durch Punkte für deutsches Format
        return number_str.replace(",", ".")
    except (ValueError, TypeError):
        return "0"

def format_german_decimal(number, decimals=1):
    """Formatiert Dezimalzahlen im deutschen Format"""
    try:
        # Formatierung mit angegebener Dezimalstelle
        number_str = f"{number:.{decimals}f}"
        # Erst Tausender mit Punkten, dann Dezimalkomma
        whole, dec = number_str.split(".")
        whole = format_german_number(int(whole))
        return f"{whole},{dec}"
    except (ValueError, TypeError):
        return "0,0"

def format_german_date(date_str):
    """Konvertiert Datum ins deutsche Format"""
    try:
        date_obj = pd.to_datetime(date_str)
        # Timezone auf CET setzen
        cet = timezone('Europe/Berlin')
        date_obj = date_obj.tz_localize('UTC').tz_convert(cet)
        return date_obj.strftime('%d.%m.%Y')
    except:
        return date_str

@st.cache_data
def load_data(uploaded_file):
    """
    Lädt und cached die Daten aus der hochgeladenen CSV-Datei.
    """
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden der Datei: {str(e)}")
        return None

def upload_files():
    """
    Upload-Bereich in der Sidebar mit Expander für geladene Dateien
    """
    # Upload-Bereich in der Sidebar
    with st.sidebar:
        st.sidebar.markdown("### 📁 Daten-Upload")
        
        # Status für erfolgreiche Uploads
        inhaltsbericht_success = False
        seitenaufrufe_success = False
        
        # Container für Uploader wenn noch nicht erfolgreich geladen
        if not st.session_state.get('inhaltsbericht_loaded', False):
            st.markdown("#### 1️⃣ Inhaltsbericht")
            inhaltsbericht_file = st.file_uploader(
                "Inhaltsbericht-CSV",
                type=['csv'],
                key="inhaltsbericht",
                help="CSV-Datei mit dem Inhaltsbericht"
            )
            
            if inhaltsbericht_file is not None:
                inhaltsbericht_df = load_data(inhaltsbericht_file)
                if inhaltsbericht_df is not None:
                    inhaltsbericht_success = True
                    st.session_state.inhaltsbericht_loaded = True
                    st.session_state.inhaltsbericht_df = inhaltsbericht_df
                    st.success(f"✅ {len(inhaltsbericht_df)} Zeilen")
        
        if not st.session_state.get('seitenaufrufe_loaded', False):
            st.markdown("#### 2️⃣ Seitenaufrufe")
            seitenaufrufe_file = st.file_uploader(
                "Seitenaufrufe-CSV",
                type=['csv'],
                key="seitenaufrufe",
                help="CSV-Datei mit den Seitenaufrufen"
            )
            
            if seitenaufrufe_file is not None:
                seitenaufrufe_df = load_data(seitenaufrufe_file)
                if seitenaufrufe_df is not None:
                    seitenaufrufe_success = True
                    st.session_state.seitenaufrufe_loaded = True
                    st.session_state.seitenaufrufe_df = seitenaufrufe_df
                    st.success(f"✅ {len(seitenaufrufe_df)} Zeilen")
        
        # Wenn beide Dateien geladen sind, zeige Status im Expander
        if st.session_state.get('inhaltsbericht_loaded', False) and st.session_state.get('seitenaufrufe_loaded', False):
            with st.expander("📊 Geladene Dateien", expanded=True):
                st.markdown("**Inhaltsbericht**")
                st.markdown(f"✅ {len(st.session_state.inhaltsbericht_df)} Zeilen")
                if st.button("Inhaltsbericht neu laden", key="reload_inhalt"):
                    st.session_state.inhaltsbericht_loaded = False
                    st.experimental_rerun()
                
                st.markdown("---")
                
                st.markdown("**Seitenaufrufe**")
                st.markdown(f"✅ {len(st.session_state.seitenaufrufe_df)} Zeilen")
                if st.button("Seitenaufrufe neu laden", key="reload_seiten"):
                    st.session_state.seitenaufrufe_loaded = False
                    st.experimental_rerun()
            
            # Trennlinie für weitere Sidebar-Elemente
            st.sidebar.markdown("---")
    
    # Rückgabe der DataFrames
    inhaltsbericht_df = st.session_state.get('inhaltsbericht_df', None)
    seitenaufrufe_df = st.session_state.get('seitenaufrufe_df', None)
    
    return inhaltsbericht_df, seitenaufrufe_df

def add_time_analysis(df):
    """
    Fügt zeitliche Analysen zum DataFrame hinzu.
    """
    # Datum konvertieren
    df['Datum'] = pd.to_datetime(
        df['Erstellungs-/Aktualisierungsdatum'], 
        format='%d.%m.%Y, %H:%M:%S'
    )
    
    # Wochentagsanalyse (auf Deutsch)
    df['Wochentag'] = df['Datum'].dt.day_name()
    
    # Tageszeit-Analyse
    df['Stunde'] = df['Datum'].dt.hour
    df['Tageszeit'] = pd.cut(
        df['Stunde'],
        bins=[0, 6, 12, 18, 24],
        labels=['Nacht', 'Morgen', 'Mittag', 'Abend']
    )
    
    return df

def calculate_extended_metrics(df):
    """
    Berechnet erweiterte Performance-Metriken.
    """
    # Engagement Rate berechnen
    df['Engagement_Rate'] = (
        (df['Likes'] + df['Kommentare']) / 
        df['Seitenaufrufe'] * 100
    ).fillna(0)
    
    # Unique Visitor Rate berechnen
    df['Unique_Visitor_Rate'] = (
        df['Eindeutige Benutzer'] / 
        df['Seitenaufrufe'] * 100
    ).fillna(0)
    
    return df

def get_top_tageszeit(portal_data):
    """
    Ermittelt die Tageszeit mit den meisten Seitenaufrufen.
    """
    if portal_data.empty:
        return "Keine Daten"
        
    tageszeit_stats = portal_data.groupby('Tageszeit', observed=True)['Seitenaufrufe'].mean()
    if tageszeit_stats.empty or tageszeit_stats.isna().all():
        return "Keine Daten"
        
    return tageszeit_stats.fillna(0).idxmax()

@st.cache_data
def analyze_msn_data(inhaltsbericht_df, seitenaufrufe_df, portale=['HNA', '24vita']):
    """
    Analysiert Daten und aggregiert Seitenaufrufe.
    """
    # Filterung nach relevanten Portalen
    inhaltsbericht_df = inhaltsbericht_df[
        inhaltsbericht_df['Markenname'].isin(portale)
    ]
    
    # Spalten für die Verknüpfung vorbereiten
    inhaltsbericht_df['Dokument-ID'] = inhaltsbericht_df['Dokument-ID'].astype(str)
    seitenaufrufe_df['docID'] = seitenaufrufe_df['docID'].astype(str)
    
    # Seitenaufrufe pro Artikel aggregieren
    seitenaufrufe_agg = seitenaufrufe_df.groupby('docID', observed=True).agg({
        'Titel': 'first',
        'Seitenaufrufe': 'sum',
        'Eindeutige Benutzer': 'sum',
        'Likes': 'sum',
        'Kommentare': 'sum'
    }).reset_index()
    
    # Daten zusammenführen
    merged_data = pd.merge(
        inhaltsbericht_df,
        seitenaufrufe_agg,
        left_on='Dokument-ID',
        right_on='docID',
        how='left'
    )
    
    # Relevante Spalten auswählen
    result = merged_data[[
        'Markenname',
        'Feedname',
        'Inhaltstitel',
        'Dokument-ID',
        'Canonical URL',
        'Veröffentlichte URL',
        'Seitenaufrufe',
        'Eindeutige Benutzer',
        'Likes',
        'Kommentare',
        'Erstellungs-/Aktualisierungsdatum'
    ]].copy()
    
    # NaN-Werte durch 0 ersetzen
    numeric_columns = ['Seitenaufrufe', 'Eindeutige Benutzer', 'Likes', 'Kommentare']
    result[numeric_columns] = result[numeric_columns].fillna(0)
    
    # Zeitliche Analyse hinzufügen
    result = add_time_analysis(result)
    
    # Erweiterte Metriken berechnen
    result = calculate_extended_metrics(result)
    
    # Daten sortieren nach Seitenaufrufen (absteigend)
    result = result.sort_values('Seitenaufrufe', ascending=False)
    
    # Portal-spezifische Statistiken
    portal_stats = {}
    for portal in portale:
        portal_data = result[result['Markenname'] == portal]
        if not portal_data.empty:
            portal_stats[portal] = {
                'Artikel': len(portal_data),
                'Gesamtaufrufe': int(portal_data['Seitenaufrufe'].sum()),
                'Durchschnitt': portal_data['Seitenaufrufe'].mean(),
                'Top_Tageszeit': get_top_tageszeit(portal_data),
                'Durchschnittl_Engagement': portal_data['Engagement_Rate'].mean()
            }
        else:
            portal_stats[portal] = {
                'Artikel': 0,
                'Gesamtaufrufe': 0,
                'Durchschnitt': 0,
                'Top_Tageszeit': 'Keine Daten',
                'Durchschnittl_Engagement': 0
            }
    
    # Allgemeine Zusammenfassung
    summary = {
        'Gesamtzahl Artikel': len(result),
        'Artikel mit Aufrufen': len(result[result['Seitenaufrufe'] > 0]),
        'Gesamte Seitenaufrufe': int(result['Seitenaufrufe'].sum()),
        'Durchschnitt Seitenaufrufe': result['Seitenaufrufe'].mean(),
        'Gesamte Likes': int(result['Likes'].sum()),
        'Gesamte Kommentare': int(result['Kommentare'].sum()),
        'Durchschnittl_Engagement_Rate': result['Engagement_Rate'].mean()
    }
    
    return result, summary, portal_stats

def create_dashboard(result_df, summary, portal_stats):
    """
    Erstellt ein interaktives Dashboard mit den Analyseergebnissen.
    """
     
    # Horizontale Linie zur visuellen Trennung
    st.markdown("---")
           
    # Hauptbereich
    col1, col2 = st.columns(2)
    
    # Zusammenfassung Metriken
    with col1:
        st.subheader("📈 Wichtige Metriken")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        
        with metrics_col1:
            st.metric(
                "Gesamtaufrufe",
                format_german_number(filtered_df['Seitenaufrufe'].sum())
            )
        with metrics_col2:
            st.metric(
                "Durchschnitt/Artikel",
                format_german_number(filtered_df['Seitenaufrufe'].mean())
            )
        with metrics_col3:
            st.metric(
                "Engagement-Rate",
                f"{format_german_decimal(filtered_df['Engagement_Rate'].mean())}%"
            )
    
    # Tageszeit-Analyse
    with col2:
        st.subheader("⏰ Performance nach Tageszeit")
        tageszeit_data = filtered_df.groupby('Tageszeit', observed=True)['Seitenaufrufe'].mean()
        
        # Deutsche Formatierung für die Y-Achse
        fig_tageszeit = px.bar(
            tageszeit_data,
            title="Durchschnittliche Seitenaufrufe nach Tageszeit"
        )
        fig_tageszeit.update_layout(
            yaxis=dict(
                tickformat=".",
                separatethousands=True
            )
        )
        st.plotly_chart(fig_tageszeit, use_container_width=True)

    # Horizontale Linie zur visuellen Trennung
    st.markdown("---")
    
    # Artikel-Tabelle
    st.subheader("📑 Artikel-Übersicht")

    # Filter im Hauptbereich
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        selected_portal = st.selectbox(
            "Portal auswählen",
            ["Alle"] + list(portal_stats.keys())
        )
    
    with col_filter2:
        display_options = {
            "Top 5": 5,
            "Top 10": 10,
            "Alle": len(result_df)
        }
        selected_display = st.selectbox(
            "Anzahl Artikel",
            list(display_options.keys())
        )

    # Daten filtern
    if selected_portal != "Alle":
        filtered_df = result_df[result_df['Markenname'] == selected_portal]
    else:
        filtered_df = result_df
    
    displayed_df = filtered_df.head(display_options[selected_display])
    
    # Formatierte Tabelle mit Plotly
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Portal", "Titel", "Seitenaufrufe", "Engagement", "Tageszeit", "Datum"],
            font=dict(size=12, color='white'),
            fill_color='rgb(75, 75, 75)',
            align=['left', 'left', 'right', 'right', 'center', 'center']
        ),
        cells=dict(
            values=[
                displayed_df['Markenname'],
                displayed_df['Inhaltstitel'],
                displayed_df['Seitenaufrufe'].apply(format_german_number),
                displayed_df['Engagement_Rate'].apply(lambda x: f"{format_german_decimal(x)}%"),
                displayed_df['Tageszeit'],
                displayed_df['Erstellungs-/Aktualisierungsdatum'].apply(format_german_date)
            ],
            font=dict(size=11),
            align=['left', 'left', 'right', 'right', 'center', 'center']
        )
    )])
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Download-Bereich
    st.subheader("💾 Download")
    
    # Excel erstellen mit mehreren Sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Deutsche Zahlenformate für Excel
        workbook = writer.book
        german_number_format = workbook.add_format({'num_format': '#.##0'})
        german_percent_format = workbook.add_format({'num_format': '#.##0,0%'})
        
        # Detailanalyse Sheet
        filtered_df.to_excel(writer, sheet_name='Detailanalyse', index=False)
        worksheet = writer.sheets['Detailanalyse']
        
        # Formatierung der Zahlenkolumnen
        for col_num, col_name in enumerate(filtered_df.columns):
            if 'aufrufe' in col_name.lower():
                worksheet.set_column(col_num, col_num, None, german_number_format)
            elif 'rate' in col_name.lower():
                worksheet.set_column(col_num, col_num, None, german_percent_format)
        
        # Tageszeit-Analyse Sheet
        tageszeit_analyse = filtered_df.groupby(['Tageszeit'], observed=True).agg({
            'Seitenaufrufe': ['count', 'sum', 'mean'],
            'Engagement_Rate': 'mean'
        }).round(2)
        tageszeit_analyse.to_excel(writer, sheet_name='Tageszeit-Analyse')
    
    output.seek(0)
    
    st.download_button(
        label="📥 Excel-Report herunterladen",
        data=output,
        file_name=f"Analyse_{selected_portal}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )
    
def main():
    """
    Hauptfunktion für die Analyse App
    """
    # Haupttitel im Content-Bereich
    st.title("Artikel Analyse 📊")
    
    # Datei-Upload in Sidebar
    inhaltsbericht_df, seitenaufrufe_df = upload_files()
    
    if inhaltsbericht_df is not None and seitenaufrufe_df is not None:
        with st.spinner('Analyse wird durchgeführt...'):
            # Analyse durchführen
            result, summary, portal_stats = analyze_msn_data(inhaltsbericht_df, seitenaufrufe_df)
            
            # Dashboard erstellen
            create_dashboard(result, summary, portal_stats)
    else:
        st.info('👈 Bitte laden Sie beide CSV-Dateien in der Seitenleiste hoch, um die Analyse zu starten.')

if __name__ == "__main__":
    main()
