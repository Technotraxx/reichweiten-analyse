# Notwendige Bibliotheken importieren
import pandas as pd
import streamlit as st
import io
import numpy as np
from datetime import datetime
from pytz import timezone

# =============================================================================
# 1. Konsistentes Error-Handling
# =============================================================================

# 1.1 Custom Exception-Klassen
class DataProcessingError(Exception):
    """Basis-Exception für Datenverarbeitungsfehler"""
    pass

class FileLoadError(DataProcessingError):
    """Exception für Fehler beim Laden von Dateien"""
    pass

class DataValidationError(DataProcessingError):
    """Exception für Fehler bei der Datenvalidierung"""
    pass

# 1.2 Error-Handler-Funktion
def handle_error(error: Exception, error_type: str = "Allgemeiner") -> None:
    """Zentralisierte Fehlerbehandlung mit benutzerfreundlichen Meldungen"""
    error_messages = {
        "FileLoadError": "Fehler beim Laden der Datei",
        "DataValidationError": "Fehler bei der Datenvalidierung",
        "ValueError": "Ungültiger Wert",
        "KeyError": "Erforderliches Feld nicht gefunden",
        "Exception": "Ein unerwarteter Fehler ist aufgetreten"
    }
    
    error_type = error.__class__.__name__
    base_message = error_messages.get(error_type, error_messages["Exception"])
    
    st.error(f"{base_message}: {str(error)}")
    if not isinstance(error, (FileLoadError, DataValidationError)):
        st.exception(error)  # Zeigt den Stacktrace nur bei unerwarteten Fehlern

# =============================================================================
# 2. Session State Management
# =============================================================================

class SessionStateManager:
    """Zentralisierte Verwaltung des Session States"""
    
    @staticmethod
    def initialize_state():
        """Initialisiert alle benötigten Session State Variablen"""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.update({
                'inhaltsbericht_loaded': False,
                'seitenaufrufe_loaded': False,
                'inhaltsbericht_df': None,
                'seitenaufrufe_df': None,
                'last_analysis': None,
                'selected_portal': 'Alle'
            })
    
    @staticmethod
    def reset_data_state():
        """Setzt datenbezogene States zurück"""
        st.session_state.inhaltsbericht_loaded = False
        st.session_state.seitenaufrufe_loaded = False
        st.session_state.inhaltsbericht_df = None
        st.session_state.seitenaufrufe_df = None
        st.session_state.last_analysis = None
    
    @staticmethod
    def update_data_state(data_type: str, df: pd.DataFrame):
        """Aktualisiert den State nach erfolgreichem Datenladen"""
        if data_type == 'inhaltsbericht':
            st.session_state.inhaltsbericht_loaded = True
            st.session_state.inhaltsbericht_df = df
        elif data_type == 'seitenaufrufe':
            st.session_state.seitenaufrufe_loaded = True
            st.session_state.seitenaufrufe_df = df
    
    @staticmethod
    def are_files_loaded() -> bool:
        """Prüft ob alle benötigten Dateien geladen sind"""
        return (st.session_state.inhaltsbericht_loaded and 
                st.session_state.seitenaufrufe_loaded)

# =============================================================================
# 3. DataFrame-Optimierung
# =============================================================================

class DataFrameOptimizer:
    """Optimiert DataFrame Operationen für bessere Performance"""
    
    @staticmethod
    def optimize_memory_usage(df: pd.DataFrame) -> pd.DataFrame:
        """Optimiert den Speicherverbrauch eines DataFrames"""
        df_optimized = df.copy()
        
        for col in df_optimized.columns:
            col_type = df_optimized[col].dtype
            
            if col_type == 'object':
                # Strings zu Kategorie-Typ konvertieren, wenn sinnvoll
                if df_optimized[col].nunique() / len(df_optimized) < 0.5:
                    df_optimized[col] = df_optimized[col].astype('category')
            
            elif col_type.name.startswith('int'):
                # Integers zum kleinstmöglichen Typ konvertieren
                c_min, c_max = df_optimized[col].min(), df_optimized[col].max()
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df_optimized[col] = df_optimized[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df_optimized[col] = df_optimized[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df_optimized[col] = df_optimized[col].astype(np.int32)
            
            elif col_type.name.startswith('float'):
                # Floats zum kleinstmöglichen Typ konvertieren
                df_optimized[col] = df_optimized[col].astype(np.float32)
        
        return df_optimized
    
    @staticmethod
    def efficient_merge(df1: pd.DataFrame, df2: pd.DataFrame, 
                        left_on: str, right_on: str) -> pd.DataFrame:
        """Führt einen optimierten Merge durch"""
        # Nur benötigte Spalten vor dem Merge auswählen
        df1_slim = df1.copy()
        df2_slim = df2.copy()
        
        # Index optimieren
        if not df1_slim[left_on].is_unique:
            df1_slim = df1_slim.set_index(left_on, drop=False)
        if not df2_slim[right_on].is_unique:
            df2_slim = df2_slim.set_index(right_on, drop=False)
        
        # Merge durchführen
        merged_df = pd.merge(
            df1_slim, 
            df2_slim,
            left_on=left_on,
            right_on=right_on,
            how='left'
        )
        
        return DataFrameOptimizer.optimize_memory_usage(merged_df)

# =============================================================================
# 4. Formatierungsklasse
# =============================================================================

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

# =============================================================================
# 5. Seiten-Konfiguration und Styling
# =============================================================================

st.set_page_config(
    page_title="Artikel Analyse",
    page_icon="📊",
    layout="wide"
)

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

# =============================================================================
# 6. Daten laden und Upload-Funktionen
# =============================================================================

@st.cache_data
def load_data(uploaded_file):
    """Lädt und cached die Daten aus der hochgeladenen CSV-Datei."""
    try:
        if uploaded_file is None:
            raise FileLoadError("Keine Datei ausgewählt")
        
        df = pd.read_csv(uploaded_file, encoding='utf-8')
        
        # Grundlegende Validierung
        required_columns = {
            'inhaltsbericht': ['Markenname', 'Dokument-ID', 'Inhaltstitel'],
            'seitenaufrufe': ['docID', 'Seitenaufrufe']
        }
        
        file_type = 'inhaltsbericht' if 'Markenname' in df.columns else 'seitenaufrufe'
        missing_cols = [col for col in required_columns[file_type] if col not in df.columns]
        
        if missing_cols:
            raise DataValidationError(f"Fehlende Spalten: {', '.join(missing_cols)}")
        
        return df
        
    except pd.errors.EmptyDataError:
        raise DataValidationError("Die Datei enthält keine Daten")
    except pd.errors.ParserError as e:
        raise FileLoadError(f"Fehler beim Parsen der CSV-Datei: {str(e)}")
    except Exception as e:
        raise DataProcessingError(f"Unerwarteter Fehler: {str(e)}")

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
                try:
                    inhaltsbericht_df = load_data(inhaltsbericht_file)
                    SessionStateManager.update_data_state('inhaltsbericht', inhaltsbericht_df)
                    inhaltsbericht_success = True
                    st.success(f"✅ {len(inhaltsbericht_df)} Zeilen")
                except Exception as e:
                    handle_error(e)
        
        if not st.session_state.get('seitenaufrufe_loaded', False):
            st.markdown("#### 2️⃣ Seitenaufrufe")
            seitenaufrufe_file = st.file_uploader(
                "Seitenaufrufe-CSV",
                type=['csv'],
                key="seitenaufrufe",
                help="CSV-Datei mit den Seitenaufrufen"
            )
            if seitenaufrufe_file is not None:
                try:
                    seitenaufrufe_df = load_data(seitenaufrufe_file)
                    SessionStateManager.update_data_state('seitenaufrufe', seitenaufrufe_df)
                    seitenaufrufe_success = True
                    st.success(f"✅ {len(seitenaufrufe_df)} Zeilen")
                except Exception as e:
                    handle_error(e)
        
        if st.session_state.get('inhaltsbericht_loaded', False) and st.session_state.get('seitenaufrufe_loaded', False):
            with st.expander("📊 Geladene Dateien", expanded=True):
                st.markdown("**Inhaltsbericht**")
                st.markdown(f"✅ {len(st.session_state.inhaltsbericht_df)} Zeilen")
                if st.button("Inhaltsbericht neu laden", key="reload_inhalt"):
                    SessionStateManager.reset_data_state()
                    st.experimental_rerun()
                st.markdown("---")
                st.markdown("**Seitenaufrufe**")
                st.markdown(f"✅ {len(st.session_state.seitenaufrufe_df)} Zeilen")
                if st.button("Seitenaufrufe neu laden", key="reload_seiten"):
                    SessionStateManager.reset_data_state()
                    st.experimental_rerun()
            st.sidebar.markdown("---")
    
    inhaltsbericht_df = st.session_state.get('inhaltsbericht_df', None)
    seitenaufrufe_df = st.session_state.get('seitenaufrufe_df', None)
    
    return inhaltsbericht_df, seitenaufrufe_df

# =============================================================================
# 7. Weitere Datenaufbereitung und Analysefunktionen
# =============================================================================

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
    """Analysiert Daten und aggregiert Seitenaufrufe mit optimierter Performance"""
    try:
        # Speicheroptimierung für Input DataFrames
        inhaltsbericht_df = DataFrameOptimizer.optimize_memory_usage(inhaltsbericht_df)
        seitenaufrufe_df = DataFrameOptimizer.optimize_memory_usage(seitenaufrufe_df)
        
        # Filterung nach relevanten Portalen
        portal_mask = inhaltsbericht_df['Markenname'].isin(portale)
        inhaltsbericht_df = inhaltsbericht_df[portal_mask]
        
        # Spaltentypen für die Verknüpfung vorbereiten
        inhaltsbericht_df['Dokument-ID'] = inhaltsbericht_df['Dokument-ID'].astype(str)
        seitenaufrufe_df['docID'] = seitenaufrufe_df['docID'].astype(str)
        
        # Seitenaufrufe aggregieren mit optimierter Gruppierung
        agg_cols = ['Seitenaufrufe', 'Eindeutige Benutzer', 'Likes', 'Kommentare']
        seitenaufrufe_agg = seitenaufrufe_df.groupby(
            'docID', 
            observed=True
        )[agg_cols].sum().reset_index()
        
        # Optimierter Merge
        merged_data = DataFrameOptimizer.efficient_merge(
            inhaltsbericht_df,
            seitenaufrufe_agg,
            'Dokument-ID',
            'docID'
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
        
    except Exception as e:
        handle_error(e)
        raise

# =============================================================================
# 8. Dashboard-Erstellung
# =============================================================================

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
    
# =============================================================================
# 9. Hauptfunktion
# =============================================================================

def main():
    """Hauptfunktion für die Analyse App"""
    # Session State initialisieren
    SessionStateManager.initialize_state()
    
    # Haupttitel
    st.title("Artikel Analyse 📊")
    
    # Datei-Upload in Sidebar
    inhaltsbericht_df, seitenaufrufe_df = upload_files()
    
    if SessionStateManager.are_files_loaded():
        try:
            with st.spinner('Analyse wird durchgeführt...'):
                # Analyse nur durchführen, wenn sich die Daten geändert haben
                current_data_hash = hash(str(inhaltsbericht_df) + str(seitenaufrufe_df))
                if st.session_state.get('last_analysis') != current_data_hash:
                    result, summary, portal_stats = analyze_msn_data(
                        inhaltsbericht_df, 
                        seitenaufrufe_df
                    )
                    st.session_state.last_analysis = current_data_hash
                    st.session_state.result = result
                    st.session_state.summary = summary
                    st.session_state.portal_stats = portal_stats
                
                # Dashboard mit gecachten Daten erstellen
                create_dashboard(
                    st.session_state.result,
                    st.session_state.summary,
                    st.session_state.portal_stats
                )
        except Exception as e:
            handle_error(e)
    else:
        st.info('👈 Bitte laden Sie beide CSV-Dateien in der Seitenleiste hoch.')

if __name__ == "__main__":
    main()
