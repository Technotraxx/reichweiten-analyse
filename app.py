# Notwendige Bibliotheken importieren
import pandas as pd
import streamlit as st
import io
from datetime import datetime
from pytz import timezone

# Neue GermanFormatter Klasse einfügen
class GermanFormatter:
    @staticmethod
    def format_number(number, decimals=0, as_percentage=False):
        """
        Formatiert Zahlen im deutschen Format.
        - Bei decimals=0 wird als Ganzzahl mit Tausender-Trennzeichen formatiert.
        - Bei decimals>0 wird das Komma als Dezimaltrennzeichen genutzt.
        - Bei as_percentage=True wird ein Prozentzeichen angehängt.
        """
        try:
            if decimals == 0:
                formatted = f"{int(round(number)):,}".replace(",", ".")
            else:
                number_str = f"{number:.{decimals}f}"
                whole, dec = number_str.split(".")
                whole = f"{int(round(float(whole))):,}".replace(",", ".")
                formatted = f"{whole},{dec}"
            if as_percentage:
                formatted = f"{formatted}%"
            return formatted
        except (ValueError, TypeError):
            return "0" if decimals == 0 else f"0,{ '0'*decimals }"

    @staticmethod
    def format_date(date_input, include_time=False):
        """
        Konvertiert ein Datum in das deutsche Format.
        Wenn include_time True ist, wird auch die Uhrzeit ausgegeben.
        """
        try:
            # Falls date_input ein Unix-Timestamp (als int, float oder als Ziffernstring) ist:
            if isinstance(date_input, (int, float)) or (isinstance(date_input, str) and date_input.isdigit()):
                timestamp = int(date_input)
                if timestamp > 1e11:  # Vermutlich in Millisekunden
                    timestamp = timestamp / 1000
                date_obj = pd.to_datetime(timestamp, unit='s')
            else:
                date_obj = pd.to_datetime(date_input)
            # Zeitzone auf Europe/Berlin setzen
            cet = timezone('Europe/Berlin')
            if date_obj.tzinfo is None:
                date_obj = date_obj.tz_localize('UTC')
            date_obj = date_obj.tz_convert(cet)
            format_str = '%d.%m.%Y, %H:%M:%S' if include_time else '%d.%m.%Y'
            return date_obj.strftime(format_str)
        except Exception:
            return str(date_input)

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

# --- Die alten Funktionen zur deutschen Formatierung wurden entfernt ---
# (format_german_number, format_german_decimal, format_german_date, convert_unix_timestamp, convert_date)
# Stattdessen wird nun die zentrale GermanFormatter Klasse verwendet.

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
    Upload-Bereich in der Sidebar mit Expander für geladene Dateien.
    """
    with st.sidebar:
        st.sidebar.markdown("### 📁 Daten-Upload")
        
        inhaltsbericht_success = False
        seitenaufrufe_success = False
        
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
            st.sidebar.markdown("---")
    
    inhaltsbericht_df = st.session_state.get('inhaltsbericht_df', None)
    seitenaufrufe_df = st.session_state.get('seitenaufrufe_df', None)
    
    return inhaltsbericht_df, seitenaufrufe_df

def add_time_analysis(df):
    """
    Fügt zeitliche Analysen zum DataFrame hinzu.
    """
    df['Datum'] = pd.to_datetime(
        df['Erstellungs-/Aktualisierungsdatum'], 
        format='%d.%m.%Y, %H:%M:%S'
    )
    df['Wochentag'] = df['Datum'].dt.day_name()
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
    df['Engagement_Rate'] = (
        (df['Likes'] + df['Kommentare']) / 
        df['Seitenaufrufe'] * 100
    ).fillna(0)
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
    inhaltsbericht_df = inhaltsbericht_df[
        inhaltsbericht_df['Markenname'].isin(portale)
    ]
    inhaltsbericht_df['Dokument-ID'] = inhaltsbericht_df['Dokument-ID'].astype(str)
    seitenaufrufe_df['docID'] = seitenaufrufe_df['docID'].astype(str)
    seitenaufrufe_agg = seitenaufrufe_df.groupby('docID', observed=True).agg({
        'Titel': 'first',
        'Seitenaufrufe': 'sum',
        'Eindeutige Benutzer': 'sum',
        'Likes': 'sum',
        'Kommentare': 'sum'
    }).reset_index()
    merged_data = pd.merge(
        inhaltsbericht_df,
        seitenaufrufe_agg,
        left_on='Dokument-ID',
        right_on='docID',
        how='left'
    )
    result = merged_data[[ 
        'Markenname',
        'Dokument-ID',
        'Inhaltstitel',
        'Quell-ID',
        'Canonical URL',
        'Veröffentlichte URL',
        'Inhaltsstatus',
        'Datum der Bearbeitung',
        'Erstellungs-/Aktualisierungsdatum',
        'Seitenaufrufe',
        'Eindeutige Benutzer',
        'Likes',
        'Kommentare'
    ]].copy()
    numeric_columns = ['Seitenaufrufe', 'Eindeutige Benutzer', 'Likes', 'Kommentare']
    result[numeric_columns] = result[numeric_columns].fillna(0)
    result = add_time_analysis(result)
    result = calculate_extended_metrics(result)
    result = result.sort_values('Seitenaufrufe', ascending=False)
    
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
    # Hauptbereich - Metriken
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Wichtige Metriken")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        with metrics_col1:
            st.metric(
                "Gesamtaufrufe",
                GermanFormatter.format_number(result_df['Seitenaufrufe'].sum())
            )
        with metrics_col2:
            st.metric(
                "Durchschnitt/Artikel",
                GermanFormatter.format_number(result_df['Seitenaufrufe'].mean())
            )
        with metrics_col3:
            st.metric(
                "Engagement-Rate",
                GermanFormatter.format_number(
                    result_df['Engagement_Rate'].mean(), 
                    decimals=1,
                    as_percentage=True
                )
            )
    
    st.subheader("📑 Artikel-Übersicht")
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        selected_portal = st.selectbox(
            "Portal auswählen",
            ["Alle"] + list(portal_stats.keys())
        )
    
    if selected_portal != "Alle":
        filtered_df = result_df[result_df['Markenname'] == selected_portal].copy()
    else:
        filtered_df = result_df.copy()
        
    columns_order = [
        'Markenname',
        'Dokument-ID',
        'Seitenaufrufe',  # Seitenaufrufe an dritter Position
        'Inhaltstitel',
        'Quell-ID',
        'Canonical URL',
        'Veröffentlichte URL',
        'Inhaltsstatus',
        'Datum der Bearbeitung',
        'Erstellungs-/Aktualisierungsdatum',
        'Engagement_Rate'
    ]
    columns_to_use = [col for col in columns_order if col in filtered_df.columns]
    filtered_df = filtered_df[columns_to_use]

    # Konvertiere die Datumsspalten mittels GermanFormatter
    date_columns = ['Datum der Bearbeitung', 'Erstellungs-/Aktualisierungsdatum']
    for col in date_columns:
        if col in filtered_df.columns:
            filtered_df[col] = filtered_df[col].apply(lambda x: GermanFormatter.format_date(x, include_time=True))

    # Zahlenformatierung
    filtered_df['Seitenaufrufe'] = filtered_df['Seitenaufrufe'].apply(
        GermanFormatter.format_number
    )
    filtered_df['Engagement_Rate'] = filtered_df['Engagement_Rate'].apply(
        lambda x: GermanFormatter.format_number(x, decimals=1, as_percentage=True)
    )

    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=800,
        column_config={
            "Markenname": st.column_config.TextColumn("Portal", width=100),
            "Dokument-ID": st.column_config.TextColumn("ID", width=100),
            "Seitenaufrufe": st.column_config.TextColumn("Aufrufe", width=100),
            "Inhaltstitel": st.column_config.TextColumn("Titel", width=300),
            "Quell-ID": st.column_config.TextColumn("Quell-ID", width=100),
            "Canonical URL": st.column_config.TextColumn("URL", width=200),
            "Veröffentlichte URL": st.column_config.TextColumn("Veröff. URL", width=200),
            "Inhaltsstatus": st.column_config.TextColumn("Status", width=100),
            "Datum der Bearbeitung": st.column_config.TextColumn("Bearbeitung", width=150),
            "Erstellungs-/Aktualisierungsdatum": st.column_config.TextColumn("Datum", width=150),
            "Engagement_Rate": st.column_config.TextColumn("Engagement", width=100),
        },
        hide_index=True
    )
    
    st.subheader("💾 Download")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        german_number_format = workbook.add_format({'num_format': '#.##0'})
        german_percent_format = workbook.add_format({'num_format': '#.##0,0%'})
        filtered_df.to_excel(
            writer,
            sheet_name='Detailanalyse',
            index=False
        )
        worksheet = writer.sheets['Detailanalyse']
        for col_num, col_name in enumerate(filtered_df.columns):
            if col_name == 'Seitenaufrufe':
                worksheet.set_column(col_num, col_num, None, german_number_format)
            elif col_name == 'Engagement_Rate':
                worksheet.set_column(col_num, col_num, None, german_percent_format)
    output.seek(0)
    
    st.download_button(
        label="📥 Excel-Report herunterladen",
        data=output,
        file_name=f"MSN_Analyse_{selected_portal}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )
    
def main():
    """
    Hauptfunktion für die Analyse App
    """
    st.title("Artikel Analyse 📊")
    inhaltsbericht_df, seitenaufrufe_df = upload_files()
    
    if inhaltsbericht_df is not None and seitenaufrufe_df is not None:
        with st.spinner('Analyse wird durchgeführt...'):
            result, summary, portal_stats = analyze_msn_data(inhaltsbericht_df, seitenaufrufe_df)
            create_dashboard(result, summary, portal_stats)
    else:
        st.info('👈 Bitte laden Sie beide CSV-Dateien in der Seitenleiste hoch, um die Analyse zu starten.')

if __name__ == "__main__":
    main()
