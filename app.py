import streamlit as st
import pandas as pd
import datetime

# --- CONFIGURATION (Tes tags) ---
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

st.set_page_config(page_title="Suivi Résine (Production)", layout="wide")
st.title("🏭 Suivi Consommation Résine")

st.sidebar.header("1. Données")
uploaded_file = st.sidebar.file_uploader("Glisser le fichier Export_Resine_Cible.csv", type=["csv"])

if uploaded_file:
    # Lecture et nettoyage
    try:
        df = pd.read_csv(uploaded_file)
        
        # Nettoyage des noms de colonnes (au cas où il y a des espaces)
        df.columns = [c.strip() for c in df.columns]
        
        if 'Date_Cible' not in df.columns:
            st.error("Le fichier CSV doit contenir une colonne 'Date_Cible'.")
            st.stop()

        # Conversion des dates
        df['Date_Cible'] = pd.to_datetime(df['Date_Cible'], dayfirst=True)
        
        # Conversion des valeurs en numérique (force les erreurs en NaN puis remplace par 0)
        df['Valeur'] = pd.to_numeric(df['Valeur'], errors='coerce').fillna(0)
        df['Valeur_kg'] = df['Valeur'] / 1000 # On divise par 1000 comme dans ton Excel

        # --- LOGIQUE JOURNÉE DE PRODUCTION ---
        # Si heure = 05:30 -> Appartient au jour d'avant (J-1)
        # Sinon (13:30, 21:30) -> Appartient au jour même (J)
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
            st.warning("Le fichier ne contient aucune date valide.")
            st.stop()
            
        selected_date = st.sidebar.selectbox("Choisir la Journée de Production :", dates_dispo)

        st.markdown(f"### 📅 Journée du **{selected_date.strftime('%d/%m/%Y')}**")
        st.caption("Le calcul inclut : 13h30 (J), 21h30 (J) et 05h30 (J+1)")

        # Filtrage sur la date choisie
        df_jour = df[df['Jour_Production'] == selected_date]

        # --- CALCUL DES TOTAUX ---
        summary_data = []
        ateliers_noms = {"CIn": "FX1", "FIn": "FX2", "JInj": "FX3", "LDIn": "FX4"}

        for atelier_code, display_name in ateliers_noms.items():
            tags_atelier = TAG_MAPPING.get(atelier_code, [])
            
            # On filtre uniquement les lignes de cet atelier pour la journée sélectionnée
            df_atelier = df_jour[df_jour['TagName'].isin(tags_atelier)]
            
            # On somme toutes les valeurs trouvées (Matin + Aprem + Nuit)
            iso_tot = df_atelier[df_atelier['TagName'].str.contains("_ISO_")]['Valeur_kg'].sum()
            pol_tot = df_atelier[df_atelier['TagName'].str.contains("_PO_")]['Valeur_kg'].sum()
            
            summary_data.append({
                "Atelier": display_name,
                "Total ISO (kg)": iso_tot,
                "Total POL (kg)": pol_tot
            })

        # Affichage du tableau final
        st.subheader("Σ Totaux Consolidés")
        df_summary = pd.DataFrame(summary_data)
        # Mise en forme nombres
        st.dataframe(df_summary.style.format({"Total ISO (kg)": "{:.2f}", "Total POL (kg)": "{:.2f}"}).background_gradient(cmap="Blues"), use_container_width=False)

        # --- PREUVE DU CALCUL (Détail) ---
        st.divider()
        st.subheader("🧐 Détail des relevés utilisés pour ce calcul")
        
        # Tableau croisé : Lignes = Machines, Colonnes = Heures
        pivot = df_jour.pivot_table(
            index="TagName", 
            columns="Heure", 
            values="Valeur_kg", 
            aggfunc='sum'
        ).fillna(0)
        
        # Réordonner les colonnes pour la logique visuelle
        cols_ordre = [c for c in ["13:30:00", "21:30:00", "05:30:00"] if c in pivot.columns]
        if cols_ordre:
            pivot = pivot[cols_ordre]

        st.dataframe(pivot.style.format("{:.2f}"))
        
    except Exception as e:
        st.error(f"Erreur de lecture du fichier : {e}")

else:
    st.info("👋 Bonjour ! Veuillez lancer le script PowerShell et charger le fichier CSV généré.")
