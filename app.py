import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIGURATION ATELIERS (V4) ---
# Attention aux majuscules : CIk, FIk, JIk, LDIk
CONFIG_ATELIERS = {
    "FX1 (CIn)": {
        "Lot_Tag": "CIk3M_Palett_NumLot",
        "Resin_Tags": ["CIn1P_T1_ConsoMasse_ISO_Tot", "CIn1P_T1_ConsoMasse_PO_Tot", 
                       "CIn1P_T2_ConsoMasse_ISO_Tot", "CIn1P_T2_ConsoMasse_PO_Tot"]
    },
    "FX2 (FIn)": {
        "Lot_Tag": "FIk3M_Palett_NumLot",
        "Resin_Tags": ["FIn1P_T1_ConsoMasse_ISO_Tot", "FIn2P_T1_ConsoMasse_ISO_Tot",
                       "FIn1P_T1_ConsoMasse_PO_Tot", "FIn2P_T1_ConsoMasse_PO_Tot",
                       "FIn1P_T2_ConsoMasse_ISO_Tot", "FIn2P_T2_ConsoMasse_ISO_Tot",
                       "FIn1P_T2_ConsoMasse_PO_Tot", "FIn2P_T2_ConsoMasse_PO_Tot"]
    },
    "FX3 (JInj)": {
        "Lot_Tag": "JIk3M_Palett_NumLot",
        "Resin_Tags": ["JInjP_T1_ConsoMasse_ISO_Tot", "JInjP_T1_ConsoMasse_PO_Tot",
                       "JInjP_T2_ConsoMasse_ISO_Tot", "JInjP_T2_ConsoMasse_PO_Tot"]
    },
    "FX4 (LDIn)": {
        "Lot_Tag": "LDIk3M_Palett_NumLot",
        "Resin_Tags": ["LDIn1P_T1_ConsoMasse_ISO_Tot", "LDIn2P_T1_ConsoMasse_ISO_Tot",
                       "LDIn1P_T1_ConsoMasse_PO_Tot", "LDIn2P_T1_ConsoMasse_PO_Tot",
                       "LDIn1P_T2_ConsoMasse_ISO_Tot", "LDIn2P_T2_ConsoMasse_ISO_Tot",
                       "LDIn1P_T2_ConsoMasse_PO_Tot", "LDIn2P_T2_ConsoMasse_PO_Tot"]
    }
}

st.set_page_config(page_title="Suivi Lots & Résine", layout="wide", page_icon="📦")
st.title("📦 Suivi Résine par Ordre de Fabrication")

# --- CHARGEMENT DONNEES ---
# ⚠️ Vérifie que c'est bien le bon lien vers "Export_Resine_Smart.csv"
CSV_URL = "https://raw.githubusercontent.com/nicoconepala-cyber/app-resine/refs/heads/main/Export_Resine_Cible.csv"

@st.cache_data(ttl=900)
def load_data(url):
    try:
        # Lecture flexible (virgule ou point-virgule)
        df = pd.read_csv(url, sep=",")
        if len(df.columns) < 2: 
            df = pd.read_csv(url, sep=";")
        
        # Nettoyage des noms de colonnes
        df.columns = [c.strip().replace('"', '') for c in df.columns]
        
        # Conversion DateTime
        df['DateTime'] = pd.to_datetime(df['DateTime'])
        
        # Nettoyage des valeurs numériques
        def clean_val(x):
            try:
                if isinstance(x, str):
                    return float(x.replace(',', '.').replace(' ', ''))
                return float(x)
            except:
                return 0.0
        
        df['Value'] = df['Value'].apply(clean_val)
        return df.sort_values('DateTime')
    except Exception as e:
        return None

# --- ALGORITHME DE CALCUL INTELLIGENT ---
def calculate_smart_consumption(df_all, lot_tag, resin_tags):
    results = []
    
    # 1. Identifier les Changements de Lot (Trigger)
    # On ne regarde QUE le tag de lot de l'atelier sélectionné
    df_lots = df_all[(df_all['TagName'] == lot_tag) & (df_all['Type'] == 'LOT_CHANGE')].copy()
    
    # Nettoyage : On s'assure que le numéro de lot a vraiment changé
    df_lots['Prev_Val'] = df_lots['Value'].shift(1)
    df_lots = df_lots[df_lots['Value'] != df_lots['Prev_Val']]
    
    if df_lots.empty:
        return []

    # 2. Filtrer les données Résine (Optimisation)
    # On ne garde que les lignes concernant les tags résine de cet atelier
    df_resin = df_all[df_all['TagName'].isin(resin_tags)].copy()

    # 3. Boucle sur chaque Lot
    for i in range(len(df_lots) - 1):
        # Bornes temporelles du lot
        t_start = df_lots.iloc[i]['DateTime']
        lot_id = df_lots.iloc[i]['Value']
        t_end = df_lots.iloc[i+1]['DateTime']
        
        # On récupère tous les points de mesure pour cet intervalle
        # (Start Lot + Max Shifts + End Lot)
        mask = (df_resin['DateTime'] >= t_start) & (df_resin['DateTime'] <= t_end)
        points_in_lot = df_resin[mask]
        
        total_kg_lot = 0
        
        # Calcul pour chaque compteur (ISO/POL T1/T2...)
        for tag in resin_tags:
            # On isole les points de ce compteur spécifique, triés par temps
            data_tag = points_in_lot[points_in_lot['TagName'] == tag].sort_values('DateTime')
            vals = data_tag['Value'].values
            
            if len(vals) > 1:
                conso_tag = 0
                # On parcourt les points point par point
                for k in range(len(vals) - 1):
                    v_curr = vals[k]
                    v_next = vals[k+1]
                    
                    diff = v_next - v_curr
                    
                    if diff >= 0:
                        # Cas Normal : Le compteur monte (ex: 100 -> 150)
                        conso_tag += diff
                    else:
                        # Cas Reset : Le compteur a chuté (ex: 500 -> 20)
                        # v_curr (500) est le MAX atteint avant reset (grâce au script PowerShell)
                        # v_next (20) est la valeur après reset
                        # On considère qu'on a consommé les 20kg après le reset
                        conso_tag += v_next
                
                total_kg_lot += conso_tag

        # Ajout du résultat
        results.append({
            "Numéro OF": str(int(lot_id)) if lot_id > 0 else "Inconnu",
            "Début": t_start,
            "Fin": t_end,
            "Durée": str(t_end - t_start).split('.')[0], # Format HH:MM:SS
            "Conso (kg)": total_kg_lot / 1000 # Conversion grammes -> kg
        })
        
    return results

# --- INTERFACE UTILISATEUR ---
st.sidebar.header("Paramètres")

if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()

df = load_data(CSV_URL)

if df is not None:
    st.sidebar.success("✅ Données chargées avec succès.")
    
    # Sélecteur d'atelier
    atelier_choix = st.selectbox("Choisir l'Atelier :", list(CONFIG_ATELIERS.keys()))
    config = CONFIG_ATELIERS[atelier_choix]
    
    st.divider()
    st.subheader(f"📊 Analyse des Ordres de Fabrication - {atelier_choix}")
    
    # Lancement du calcul
    with st.spinner("Calcul des consommations en cours..."):
        batch_data = calculate_smart_consumption(df, config['Lot_Tag'], config['Resin_Tags'])
    
    if batch_data:
        # Création du tableau de résultats
        df_res = pd.DataFrame(batch_data)
        
        # On met le lot le plus récent en haut
        df_res = df_res.sort_values('Début', ascending=False)
        
        # Affichage du tableau avec mise en forme
        st.dataframe(
            df_res.style.format({
                "Conso (kg)": "{:.2f}", 
                "Début": "{:%d/%m/%Y %H:%M}", 
                "Fin": "{:%d/%m/%Y %H:%M}"
            })
            .background_gradient(cmap="Blues", subset=["Conso (kg)"]),
            use_container_width=True
        )
        
        # Section Indicateurs (KPIs) pour le dernier lot terminé
        st.divider()
        st.markdown("### 🔎 Détails du dernier lot terminé")
        
        last_lot = df_res.iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Numéro OF", last_lot['Numéro OF'])
        col2.metric("Durée", last_lot['Durée'])
        col3.metric("Consommation Totale", f"{last_lot['Conso (kg)']:.2f} kg")
        
        # Bouton Export
        csv = df_res.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Télécharger cet historique en CSV",
            data=csv,
            file_name=f"Export_OF_{atelier_choix}.csv",
            mime="text/csv"
        )
        
    else:
        st.warning(f"Aucun changement de lot détecté pour {atelier_choix} sur la période.")
        st.info("Cela peut arriver si la production est à l'arrêt ou si le même OF tourne depuis plus de 10 jours.")

else:
    st.error("Impossible de lire le fichier de données.")
    st.markdown(f"Vérifiez l'URL GitHub : `{CSV_URL}`")
    st.info("Assurez-vous que le script `SMART_EXTRACT.bat` a bien tourné sur le PC usine.")
