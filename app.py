# Notwendige Bibliotheken importieren
import pandas as pd
import numpy as np
import streamlit as st
from google.colab import files
import io
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Streamlit Seitenkonfiguration
st.set_page_config(
    page_title="MSN Republishing Analyse",
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

def upload_files():
    """
    Handhabt den sequentiellen Upload der CSV-Dateien.
    """
    st.title("MSN Republishing-Test Analyse 📊")
    
    # Container für Datei-Uploads
    upload_container = st.container()
    
    # Erste Datei: Inhaltsbericht
    with upload_container:
        st.subheader("1️⃣ Inhaltsbericht hochladen")
        inhaltsbericht_file = st.file_uploader(
            "Wählen Sie die Inhaltsbericht-CSV aus",
            type=['csv'],
            key="inhaltsbericht"
        )
        
        if inhaltsbericht_file is not None:
            try:
                inhaltsbericht_df = pd.read_csv(inhaltsbericht_file, encoding='utf-8')
                st.success(f"✅ Inhaltsbericht erfolgreich geladen: {len(inhaltsbericht_df)} Zeilen")
                
                # Zweite Datei nur anzeigen, wenn erste erfolgreich geladen
                st.subheader("2️⃣ Seitenaufrufe hochladen")
                seitenaufrufe_file = st.file_uploader(
                    "Wählen Sie die Seitenaufrufe-CSV aus",
                    type=['csv'],
                    key="seitenaufrufe"
                )
                
                if seitenaufrufe_file is not None:
                    try:
                        seitenaufrufe_df = pd.read_csv(seitenaufrufe_file, encoding='utf-8')
                        st.success(f"✅ Seitenaufrufe erfolgreich geladen: {len(seitenaufrufe_df)} Zeilen")
                        return inhaltsbericht_df, seitenaufrufe_df
                    except Exception as e:
                        st.error(f"❌ Fehler beim Laden der Seitenaufrufe: {str(e)}")
                        return None, None
            except Exception as e:
                st.error(f"❌ Fehler beim Laden des Inhaltsberichts: {str(e)}")
                return None, None
    
    return None, None

def create_dashboard(result_df, summary, portal_stats):
    """
    Erstellt ein interaktives Dashboard mit den Analyseergebnissen.
    """
    # Seitenleiste für Filter
    st.sidebar.title("Filter")
    
    # Portal Filter
    selected_portal = st.sidebar.selectbox(
        "Portal auswählen",
        ["Alle"] + list(portal_stats.keys())
    )
    
    # Anzahl der anzuzeigenden Artikel
    display_options = {
        "Top 5": 5,
        "Top 10": 10,
        "Alle": len(result_df)
    }
    selected_display = st.sidebar.selectbox(
        "Anzahl Artikel",
        list(display_options.keys())
    )
    
    # Daten filtern
    if selected_portal != "Alle":
        filtered_df = result_df[result_df['Markenname'] == selected_portal]
    else:
        filtered_df = result_df
    
    # Hauptbereich
    col1, col2 = st.columns(2)
    
    # Zusammenfassung Metriken
    with col1:
        st.subheader("📈 Wichtige Metriken")
        metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
        
        with metrics_col1:
            st.metric(
                "Gesamtaufrufe",
                f"{int(filtered_df['Seitenaufrufe'].sum()):,}"
            )
        with metrics_col2:
            st.metric(
                "Durchschnitt/Artikel",
                f"{filtered_df['Seitenaufrufe'].mean():,.0f}"
            )
        with metrics_col3:
            st.metric(
                "Engagement-Rate",
                f"{filtered_df['Engagement_Rate'].mean():.1f}%"
            )
    
    # Tageszeit-Analyse
    with col2:
        st.subheader("⏰ Performance nach Tageszeit")
        tageszeit_data = filtered_df.groupby('Tageszeit', observed=True)['Seitenaufrufe'].mean()
        fig_tageszeit = px.bar(
            tageszeit_data,
            title="Durchschnittliche Seitenaufrufe nach Tageszeit"
        )
        st.plotly_chart(fig_tageszeit, use_container_width=True)
    
    # Artikel-Tabelle
    st.subheader("📑 Artikel-Übersicht")
    
    displayed_df = filtered_df.head(display_options[selected_display])
    
    # Formatierte Tabelle mit Plotly
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=["Portal", "Titel", "Seitenaufrufe", "Engagement", "Tageszeit"],
            font=dict(size=12, color='white'),
            fill_color='rgb(75, 75, 75)',
            align=['left', 'left', 'right', 'right', 'center']
        ),
        cells=dict(
            values=[
                displayed_df['Markenname'],
                displayed_df['Inhaltstitel'],
                displayed_df['Seitenaufrufe'].apply(lambda x: f"{int(x):,}"),
                displayed_df['Engagement_Rate'].apply(lambda x: f"{x:.1f}%"),
                displayed_df['Tageszeit']
            ],
            font=dict(size=11),
            align=['left', 'left', 'right', 'right', 'center']
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
        filtered_df.to_excel(writer, sheet_name='Detailanalyse', index=False)
        
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
        file_name=f"MSN_Analyse_{selected_portal}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.ms-excel"
    )

def main():
    """
    Hauptfunktion für die MSN Analyse App
    """
    # Datei-Upload
    inhaltsbericht_df, seitenaufrufe_df = upload_files()
    
    if inhaltsbericht_df is not None and seitenaufrufe_df is not None:
        # Analyse durchführen
        result, summary, portal_stats = analyze_msn_data(inhaltsbericht_df, seitenaufrufe_df)
        
        # Dashboard erstellen
        create_dashboard(result, summary, portal_stats)

if __name__ == "__main__":
    main()
