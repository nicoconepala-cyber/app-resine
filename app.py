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
    try:
        # 1. Lecture Robuste (Gère séparateur ; ou , automatiquement)
        # On essaie d'abord avec virgule (format standard PowerShell)
        df = pd.read_csv(uploaded_file, sep=",")
        
        # Si ça a échoué et qu'on a qu'une seule colonne, on tente le point-virgule (Excel FR)
        if len(df.columns) < 2:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=";")

        # Nettoyage des noms de colonnes
        df.columns = [c.strip().replace('"', '') for c in df.columns]
        
        # Vérification des colonnes
        if 'Date_Cible' not in df.columns or 'Valeur' not in df.columns:
            st.error(f"Colonnes manquantes ! Colonnes trouvées : {list(df.columns)}")
            st.stop()

        # 2. Conversion des Dates (FORCE LE FORMAT FRANÇAIS)
        # dayfirst=True est crucial pour dire que 10/01 est le 10 janvier, pas le 1er octobre
        df['Date_Cible'] = pd.to_datetime(df['Date_Cible'], dayfirst=True, errors='coerce')
        
        # Suppression des lignes où la date n'a pas pu être lue
        df = df.dropna(subset=['Date_Cible'])

        # 3. Nettoyage des Valeurs (Gère virgules et espaces)
        def clean_currency(x):
            if isinstance(x, str):
                # Remplace virgule par point (12,5 -> 12.5)
                x = x.replace(',', '.')
                # Enlève les espaces (1 000 -> 1000)
                x = x.replace(' ', '')
                # Enlève tout ce qui n'est pas chiffre ou point
                x = ''.join(c for c in x if c.isdigit() or c == '.')
            return x

        df['Valeur_Clean'] = df['Valeur'].apply(clean_currency)
        df['Valeur_Kg'] = pd.to_numeric(df['Valeur_Clean'], errors='coerce').fillna(0) / 1000

        # --- LOGIQUE JOURNÉE DE PRODUCTION ---
        def get_prod_date(row):
            dt = row['Date_Cible']
            # Si c'est 05h, c'est la veille
            if dt.hour == 5: 
                return (dt - datetime.timedelta(days=1)).date()
            return dt.date()

        df['Jour_Production'] = df.apply(get_prod_date, axis=1)

        # --- SÉLECTEUR DE DATE ---
        st.sidebar.header("2. Sélection")
        dates_dispo = sorted(df['Jour_Production'].unique(), reverse=True)
        
        if not dates_dispo:
            st.warning("Aucune date valide trouvée après analyse.")
            st.stop()
            
        selected_date = st.sidebar.selectbox("Choisir la Journée de Production :", dates_dispo)

        # Filtrage sur la date choisie
        df_jour = df[df['Jour_Production'] == selected_date]

        # --- TABLEAU DE CONTRÔLE (POUR COMPRENDRE LE CALCUL) ---
        st.markdown(f"### 📅 Journée du **{selected_date.strftime('%d/%m/%Y')}**")
        
        # On affiche d'abord le détail pour vérification
        pivot = df_jour.pivot_table(
            index="TagName", 
            columns="Heure", 
            values="Valeur_Kg", 
            aggfunc='sum'
        ).fillna(0)

        # Réordonner les colonnes (Matin -> Soir -> Lendemain Matin)
        cols_ordre = [c for c in ["13:30:00", "21:30:00", "05:30:00"] if c in pivot.columns]
        if cols_ordre:
            pivot = pivot[cols_ordre]

        # --- CALCUL DES TOTAUX ---
        summary_data = []
        ateliers_noms = {"CIn": "FX1", "FIn": "FX2", "JInj": "FX3", "LDIn": "FX4"}

        for atelier_code, display_name in ateliers_noms.items():
            tags_atelier = TAG_MAPPING.get(atelier_code, [])
            df_atelier = df_jour[df_jour['TagName'].isin(tags_atelier)]
            
            iso_tot = df
