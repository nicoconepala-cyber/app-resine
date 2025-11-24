import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURATION ---
TAG_MAPPING = {
    "CIn": ["CIn1P_T1_ConsoMasse_ISO_Tot", "CIn1P_T1_ConsoMasse_PO_Tot", 
            "CIn1P_T2_ConsoMasse_ISO_Tot", "CIn1P_T2_ConsoMasse_PO_Tot"],
    "FIn": ["FIn1P_T1_ConsoMasse_ISO_Tot", "FIn2P_T1_ConsoMasse_ISO_Tot",
            "FIn1P_T1_ConsoMasse_PO_Tot", "FIn2P_T1_ConsoMasse_PO_Tot",
            "FIn1P_T2_ConsoMasse_ISO_Tot", "FIn2P_T2_ConsoMasse_ISO_Tot",
            "FIn1P_T2_ConsoMasse_PO_Tot", "FIn2P_T2_ConsoMasse_PO_Tot"],
    "JInj": ["JInjP_T1_ConsoMasse_ISO_Tot", "JInjP_T1_ConsoMasse_PO_Tot",
             "JInjP_T2_ConsoMasse_ISO_Tot", "JInjP_T2_ConsoMasse_PO_Tot"],
    "LDIn": ["LDIn1P_T1_ConsoMasse_ISO_Tot", "LDIn2P_T1_ConsoMasse_ISO_Tot",
             "LDIn1P_T1_ConsoMasse_PO_Tot", "LDIn2P_T1_ConsoMasse_PO_Tot",
             "LDIn1P_T2_ConsoMasse_ISO_Tot", "LDIn2P_T2_ConsoMasse_ISO_Tot",
             "LDIn1P_T2_ConsoMasse_PO_Tot", "LDIn2P_T2_ConsoMasse_PO_Tot"]
}

st.set_page_config(page_title="Suivi Résine (Prod)", layout="wide")
st.title("🏭 Suivi Consommation Résine")

st.sidebar.header("1. Données")
uploaded_file = st.sidebar.file_uploader("Glisser le fichier Export_Resine_Cible.csv", type=["csv"])

if uploaded_file:
    # 1. Lecture Robuste
    # On tente de lire avec virgule (standard)
    try:
        df = pd.read_csv(uploaded_file, sep=",")
        if len(df.columns) < 2: # Si ça rate, on tente le point-virgule
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=";")
    except:
        st.error("Impossible de lire le fichier CSV. Vérifiez le format.")
        st.stop()

    # Nettoyage des noms de colonnes
    df.columns = [c.strip().replace('"', '') for c in df.columns]
    
    if 'Date_Cible' not in df.columns or 'Valeur' not in df.columns:
        st.error(f"Colonnes manquantes ! Colonnes trouvées : {list(df.columns)}")
        st.stop()

    # 2. Conversion des Dates
    df['Date_Cible'] = pd.to_datetime(df['Date_Cible'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date_Cible'])

    # 3. Nettoyage des Valeurs
    def clean_currency(x):
        if isinstance(x, str):
            x = x.replace(',', '.')
            x = x.replace(' ', '')
            x = ''.join(c for c in x if c.isdigit() or c == '.')
        return x

    df['Valeur_Clean'] = df['Valeur'].apply(clean_currency)
    df['Valeur_Kg'] = pd.to_numeric(df['Valeur_Clean'], errors='coerce').fillna(0) / 1000

    # --- LOGIQUE JOURNÉE DE PRODUCTION ---
    def get_prod_date(row):
        dt = row['Date_Cible']
        if dt.hour == 5: 
            return (dt - datetime.timedelta(days=1)).date()
        return dt.date()

    df['Jour_Production'] = df.apply(get_prod_date, axis=1)

    # --- SÉLECTEUR DE DATE ---
    st.sidebar.header("2. Sélection")
    dates_dispo = sorted(df['Jour_Production'].unique(), reverse=True)
    
    if not dates_dispo:
        st.warning("Aucune date valide trouvée.")
        st.stop()
        
    selected_date = st.sidebar.selectbox("Choisir la Journée de Production :", dates_dispo)

    # Filtrage
    df_jour = df[df['Jour_Production'] == selected_date]

    # --- AFFICHAGE ---
    st.markdown(f"### 📅 Journée du **{selected_date.strftime('%d/%m/%Y')}**")

    summary_data = []
    ateliers_noms = {"CIn": "FX1", "FIn": "FX2", "JInj": "FX3", "LDIn": "FX4"}

    for atelier_code, display_name in ateliers_noms.items():
        tags_atelier = TAG_MAPPING.get(atelier_code, [])
        df_atelier = df_jour[df_jour['TagName'].isin(tags_atelier)]
        
        iso_tot = df_atelier[df_atelier['TagName'].str.contains("_ISO_")]['Valeur_Kg'].sum()
        pol_tot = df_atelier[df_atelier['TagName'].str.contains("_PO_")]['Valeur_Kg'].sum()
        
        summary_data.append({
            "Atelier": display_name,
            "Total ISO (kg)": iso_tot,
            "Total POL (kg)": pol_tot
        })

    st.subheader("Σ Totaux Consolidés (SAP)")
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary.style.format("{:.2f}").background_gradient(cmap="Blues"), use_container_width=False)

    st.divider()
    st.subheader("🔍 Détail des compteurs")
    
    pivot = df_jour.pivot_table(
        index="TagName", 
        columns="Heure", 
        values="Valeur_Kg", 
        aggfunc='sum'
    ).fillna(0)

    cols_ordre = [c for c in ["13:30:00", "21:30:00", "05:30:00"] if c in pivot.columns]
    if cols_ordre:
        pivot = pivot[cols_ordre]

    st.dataframe(pivot.style.format("{:.2f}"))

else:
    st.info("Chargez votre fichier Export_Resine_Cible.csv")
