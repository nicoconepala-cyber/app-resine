import streamlit as st
import pandas as pd

# --- CONFIGURATION DES TAGS ---
# (On garde le même mapping pour regrouper par atelier)
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

st.set_page_config(page_title="Suivi Consommation Résine (Cible)", layout="wide")
st.title("🏭 Suivi Consommation Résine (Données Ciblées)")

# 1. Chargement
st.sidebar.header("Données")
uploaded_file = st.sidebar.file_uploader("Fichier CSV PowerShell", type=["csv"])

if uploaded_file:
    # Lecture du CSV optimisé
    df = pd.read_csv(uploaded_file)
    
    # Petit nettoyage si besoin
    if 'Valeur' in df.columns:
        df['Valeur'] = pd.to_numeric(df['Valeur'], errors='coerce').fillna(0)
        # Division par 1000 pour avoir des kg si c'est comme dans la macro
        df['Valeur_kg'] = df['Valeur'] / 1000 
    
    st.write("Aperçu des données brutes :", df.head())

    # 2. Calcul des totaux par Atelier
    st.subheader("Σ Totaux par Atelier (Pour SAP)")
    
    summary_data = []
    ateliers_noms = {"CIn": "FX1", "FIn": "FX2", "JInj": "FX3", "LDIn": "FX4"}

    for atelier_code, display_name in ateliers_noms.items():
        tags_atelier = TAG_MAPPING.get(atelier_code, [])
        
        # Filtrer les lignes qui concernent cet atelier
        # On regarde si le TagName de la ligne est dans la liste de l'atelier
        df_atelier = df[df['TagName'].isin(tags_atelier)]
        
        iso_tot = df_atelier[df_atelier['TagName'].str.contains("_ISO_")]['Valeur_kg'].sum()
        pol_tot = df_atelier[df_atelier['TagName'].str.contains("_PO_")]['Valeur_kg'].sum()
        
        summary_data.append({
            "Atelier": display_name,
            "Total ISO (kg)": round(iso_tot, 2),
            "Total POL (kg)": round(pol_tot, 2)
        })
    
    df_summary = pd.DataFrame(summary_data)
    st.dataframe(df_summary.style.background_gradient(cmap="Blues"))
    
    # 3. Tableau croisé dynamique (Pivot) pour voir jour par jour
    st.subheader("📅 Détail par Jour et Heure")
    pivot = df.pivot_table(index=["Date_Cible", "Heure"], columns="TagName", values="Valeur_kg", aggfunc='sum')
    st.dataframe(pivot)

else:
    st.info("Chargez le fichier 'Export_Resine_Cible.csv' généré par PowerShell.")
