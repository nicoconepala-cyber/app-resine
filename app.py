import streamlit as st
import pandas as pd
import datetime

# --- 1. CONFIGURATION DES TAGS ---
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

st.set_page_config(page_title="Suivi Résine (Auto)", layout="wide")
st.title("🏭 Suivi Consommation Résine")

# --- 2. CONFIGURATION GITHUB (A MODIFIER !) ---
# Remplace le lien ci-dessous par le lien "Raw" de ton fichier sur GitHub
# Exemple : https://raw.githubusercontent.com/TonPseudo/TonRepo/main/Export_Resine_Cible.csv
CSV_URL = "https://raw.githubusercontent.com/TonPseudo/TonRepo/main/Export_Resine_Cible.csv"

# --- 3. FONCTION DE CHARGEMENT ROBUSTE ---
@st.cache_data(ttl=3600) # Garde les données en mémoire 1h pour aller plus vite
def load_data(url):
    try:
        # Essai 1 : Séparateur virgule (Standard PowerShell)
        df = pd.read_csv(url, sep=",")
        if len(df.columns) < 2:
            # Essai 2 : Séparateur point-virgule (Si Excel français s'en mêle)
            df = pd.read_csv(url, sep=";")
        return df
    except Exception as e:
        return None

# --- 4. INTERFACE & LOGIQUE ---
st.sidebar.header("1. Connexion Données")

# Bouton pour forcer la mise à jour si besoin
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()

df = load_data(CSV_URL)

if df is not None:
    st.sidebar.success("✅ Données chargées depuis GitHub")

    # A. Nettoyage des noms de colonnes
    df.columns = [c.strip().replace('"', '') for c in df.columns]
    
    # Vérification de sécurité
    if 'Date_Cible' not in df.columns or 'Valeur' not in df.columns:
        st.error(f"Colonnes manquantes ! Colonnes trouvées : {list(df.columns)}")
        st.stop()

    # B. Conversion des Dates (Format Français géré)
    df['Date_Cible'] = pd.to_datetime(df['Date_Cible'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Date_Cible'])

    # C. Nettoyage des Nombres (Virgules, Espaces...)
    def clean_currency(x):
        if isinstance(x, str):
            x = x.replace(',', '.') # Remplace virgule par point
            x = x.replace(' ', '')  # Enlève les espaces
            x = ''.join(c for c in x if c.isdigit() or c == '.') # Garde que les chiffres
        return x

    df['Valeur_Clean'] = df['Valeur'].apply(clean_currency)
    # Conversion en Kg (Division par 1000)
    df['Valeur_Kg'] = pd.to_numeric(df['Valeur_Clean'], errors='coerce').fillna(0) / 1000

    # D. Logique "Journée de Production"
    def get_prod_date(row):
        dt = row['Date_Cible']
        # Si c'est le relevé de 05h, il appartient à la veille
        if dt.hour == 5: 
            return (dt - datetime.timedelta(days=1)).date()
        return dt.date()

    df['Jour_Production'] = df.apply(get_prod_date, axis=1)

    # --- 5. SÉLECTEUR DE DATE ---
    st.sidebar.header("2. Analyse")
    dates_dispo = sorted(df['Jour_Production'].unique(), reverse=True)
    
    if not dates_dispo:
        st.warning("Aucune date valide trouvée.")
        st.stop()
        
    selected_date = st.sidebar.selectbox("Choisir la Journée de Production :", dates_dispo)
    
    # Filtrage sur la date choisie
    df_jour = df[df['Jour_Production'] == selected_date]

    # --- 6. CALCULS ET TABLEAUX ---
    st.markdown(f"### 📅 Journée du **{selected_date.strftime('%d/%m/%Y')}**")
    st.caption("Données consolidées : 13h30 (J), 21h30 (J) et 05h30 (J+1)")

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

    # Tableau Résumé (SAP)
    st.subheader("Σ Totaux Consolidés (SAP)")
    df_summary = pd.DataFrame(summary_data)
    
    # Formatage ciblé (Uniquement sur les colonnes numériques pour éviter le crash)
    format_mapping = {"Total ISO (kg)": "{:.2f}", "Total POL (kg)": "{:.2f}"}
    
    st.dataframe(
        df_summary.style.format(format_mapping).background_gradient(cmap="Blues", subset=["Total ISO (kg)", "Total POL (kg)"]),
        use_container_width=False
    )

    # Tableau Détail (Preuve)
    st.divider()
    st.subheader("🔍 Détail des compteurs")
    
    pivot = df_jour.pivot_table(
        index="TagName", 
        columns="Heure", 
        values="Valeur_Kg", 
        aggfunc='sum'
    ).fillna(0)

    # Réordonner les colonnes pour la logique visuelle
    cols_ordre = [c for c in ["13:30:00", "21:30:00", "05:30:00"] if c in pivot.columns]
    if cols_ordre:
        pivot = pivot[cols_ordre]

    st.dataframe(pivot.style.format("{:.2f}"))

else:
    # Message si l'URL ne fonctionne pas encore
    st.info("👋 Bonjour !")
    st.warning(f"Impossible de lire le fichier à l'adresse : {CSV_URL}")
    st.markdown("""
    **Pour corriger cela :**
    1. Assurez-vous que le script PowerShell a bien tourné au moins une fois.
    2. Vérifiez que la variable `CSV_URL` dans le code `app.py` correspond bien à votre fichier sur GitHub (bouton 'Raw').
    """)
