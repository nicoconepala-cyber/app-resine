import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURATION (Toujours pareil) ---
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

st.set_page_config(page_title="Suivi Résine (Journée Production)", layout="wide")
st.title("🏭 Suivi Résine - Journée de Production")

# 1. Chargement
st.sidebar.header("1. Chargement")
uploaded_file = st.sidebar.file_uploader("Fichier CSV PowerShell", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Nettoyage et conversion
    if 'Date_Cible' not in df.columns:
        st.error("Colonne 'Date_Cible' manquante.")
        st.stop()
        
    df['Date_Cible'] = pd.to_datetime(df['Date_Cible'])
    
    # --- LA LOGIQUE MAGIQUE (Décalage de date) ---
    def calculer_jour_production(row):
        date_reelle = row['Date_Cible']
        # Si c'est le relevé de 05:30, cela appartient à la veille
        if date_reelle.hour == 5 and date_reelle.minute == 30:
            return (date_reelle - datetime.timedelta(days=1)).date()
        else:
            # Sinon (13:30 ou 21:30), c'est le jour même
            return date_reelle.date()

    # On crée une nouvelle colonne "Jour_Production"
    df['Jour_Production'] = df.apply(calculer_jour_production, axis=1)

    # Conversion valeurs
    if 'Valeur' in df.columns:
        df['Valeur'] = pd.to_numeric(df['Valeur'], errors='coerce').fillna(0)
        df['Valeur_kg'] = df['Valeur'] / 1000

    # 2. Sélecteur
    st.sidebar.header("2. Sélection")
    
    # On choisit parmi les Jours de Production calculés
    dates_dispo = sorted(df['Jour_Production'].unique(), reverse=True)
    if not dates_dispo:
        st.warning("Aucune date valide trouvée.")
        st.stop()

    selected_date = st.sidebar.selectbox(
        "Choisir la Journée de Production :",
        dates_dispo,
        index=0
    )

    st.markdown(f"### 📅 Journée de Production du : **{selected_date.strftime('%d/%m/%Y')}**")
    st.info("Inclut les relevés de 13h30, 21h30 et 05h30 (le lendemain matin).")

    # 3. Filtrage sur la colonne calculée
    df_jour = df[df['Jour_Production'] == selected_date]
    
    if df_jour.empty:
        st.warning("Pas de données.")
    else:
        # 4. Totaux
        summary_data = []
        ateliers_noms = {"CIn": "FX1", "FIn": "FX2", "JInj": "FX3", "LDIn": "FX4"}

        for atelier_code, display_name in ateliers_noms.items():
            tags_atelier = TAG_MAPPING.get(atelier_code, [])
            df_atelier = df_jour[df_jour['TagName'].isin(tags_atelier)]
            
            iso_tot = df_atelier[df_atelier['TagName'].str.contains("_ISO_")]['Valeur_kg'].sum()
            pol_tot = df_atelier[df_atelier['TagName'].str.contains("_PO_")]['Valeur_kg'].sum()
            
            summary_data.append({
                "Atelier": display_name,
                "Total ISO (kg)": round(iso_tot, 2),
                "Total POL (kg)": round(pol_tot, 2)
            })
        
        st.subheader("Σ Totaux (Pour SAP)")
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary.style.background_gradient(cmap="Blues"), use_container_width=False)

        # 5. Preuve du calcul (Détail)
        st.subheader("🧐 Détail des relevés pris en compte")
        # On affiche la Date Réelle pour bien vérifier que le 05:30 est celui du lendemain
        detail_view = df_jour[['Date_Cible', 'TagName', 'Valeur_kg']].copy()
        detail_view['Heure'] = detail_view['Date_Cible'].dt.strftime('%H:%M')
        
        pivot = detail_view.pivot_table(
            index="TagName", 
            columns="Heure", 
            values="Valeur_kg", 
            aggfunc='sum'
        ).fillna(0)
        
        # On réordonne les colonnes pour avoir l'ordre logique : 13:30 -> 21:30 -> 05:30
        cols_ordre = []
        for h in ["13:30", "21:30", "05:30"]:
            if h in pivot.columns: cols_ordre.append(h)
            
        if cols_ordre:
            pivot = pivot[cols_ordre]
            
        st.dataframe(pivot.style.format("{:.2f} kg"))

else:
    st.info("👋 Chargez le fichier CSV pour voir la magie.")
