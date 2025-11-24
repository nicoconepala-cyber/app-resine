import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURATION (Même mapping que toujours) ---
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

st.set_page_config(page_title="Suivi Résine par Date", layout="wide")
st.title("📅 Suivi Journalier Consommation Résine")

# 1. Chargement du fichier
st.sidebar.header("1. Chargement")
uploaded_file = st.sidebar.file_uploader("Fichier CSV PowerShell", type=["csv"])

if uploaded_file:
    # Lecture et nettoyage
    df = pd.read_csv(uploaded_file)
    
    # Conversion de la colonne Date en format "Date compréhensible"
    # Le PowerShell sort un format 'Date_Cible' (ex: 2023-11-24 05:30:00)
    if 'Date_Cible' in df.columns:
        df['Date_Cible'] = pd.to_datetime(df['Date_Cible'])
        df['Jour'] = df['Date_Cible'].dt.date # On crée une colonne juste avec le JOUR (sans l'heure)
    else:
        st.error("Erreur : Le fichier CSV ne contient pas la colonne 'Date_Cible'. Vérifiez votre export PowerShell.")
        st.stop()

    if 'Valeur' in df.columns:
        df['Valeur'] = pd.to_numeric(df['Valeur'], errors='coerce').fillna(0)
        df['Valeur_kg'] = df['Valeur'] / 1000 # Conversion en kg
    
    # 2. Sélecteur de Date
    st.sidebar.header("2. Sélection")
    
    # On cherche les dates disponibles dans le fichier pour limiter le calendrier
    min_date = df['Jour'].min()
    max_date = df['Jour'].max()
    
    selected_date = st.sidebar.date_input(
        "Choisir la date à analyser :",
        value=max_date, # Par défaut : la date la plus récente
        min_value=min_date,
        max_value=max_date
    )

    st.markdown(f"### Analyse du : **{selected_date.strftime('%d/%m/%Y')}**")

    # 3. Filtrage des données pour ce jour précis
    df_jour = df[df['Jour'] == selected_date]
    
    if df_jour.empty:
        st.warning(f"Aucune donnée trouvée pour le {selected_date}.")
    else:
        # 4. Calcul des Totaux (Uniquement pour ce jour)
        summary_data = []
        ateliers_noms = {"CIn": "FX1", "FIn": "FX2", "JInj": "FX3", "LDIn": "FX4"}

        for atelier_code, display_name in ateliers_noms.items():
            tags_atelier = TAG_MAPPING.get(atelier_code, [])
            
            # On prend les lignes de l'atelier, MAIS uniquement sur le jour filtré
            df_atelier = df_jour[df_jour['TagName'].isin(tags_atelier)]
            
            iso_tot = df_atelier[df_atelier['TagName'].str.contains("_ISO_")]['Valeur_kg'].sum()
            pol_tot = df_atelier[df_atelier['TagName'].str.contains("_PO_")]['Valeur_kg'].sum()
            
            summary_data.append({
                "Atelier": display_name,
                "Total ISO (kg)": round(iso_tot, 2),
                "Total POL (kg)": round(pol_tot, 2)
            })
        
        # Affichage du tableau de synthèse
        st.subheader("Σ Totaux Journaliers (Pour SAP)")
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary.style.background_gradient(cmap="Blues"), use_container_width=False)

        # 5. Détail par Poste (05:30 / 13:30 / 21:30)
        st.subheader("🕒 Détail par Poste")
        st.info("Voici les relevés exacts utilisés pour le calcul ci-dessus :")
        
        # Pivot pour afficher : Lignes = Tags, Colonnes = Heures (05:30, 13:30, 21:30)
        pivot = df_jour.pivot_table(
            index="TagName", 
            columns="Heure", 
            values="Valeur_kg", 
            aggfunc='sum'
        ).fillna(0)
        
        st.dataframe(pivot.style.format("{:.2f} kg"))

else:
    st.info("👋 Bonjour ! Chargez le fichier 'Export_Resine_Cible.csv' pour commencer.")
