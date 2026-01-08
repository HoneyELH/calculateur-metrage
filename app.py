import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Expert Chargement", layout="wide")
st.title("🚚 Optimisation & Plan de Chargement")

# --- CONFIGURATION (Selon tes paramètres image) ---
L_SEMI = 13600  # Longueur utile 13.6m
l_UTILE = 2460  # Largeur utile
H_UTILE = 2700  # Hauteur utile (mise à jour à 2.70m selon ton tableau)

st.sidebar.header("1. Paramètres")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les Bons de Préparation (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 GÉNÉRER LE PLAN DE CHARGEMENT"):
            toutes_les_rangées = []

            # --- ANALYSE DES PDF ---
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # On sépare les refs Excel (ex: 74677 / 74679)
                            liste_refs = [r.strip() for r in str(row['Référence']).split('/')]
                            
                            for ref_solo in liste_refs:
                                if len(ref_solo) > 3 and ref_solo in ligne:
                                    # Extraction Quantité (dernier nombre de la ligne)
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if nombres:
                                        val = nombres[-1]
                                        qte = int(nombres[-2]) if val == ref_solo and len(nombres) > 1 else int(val)

                                    l_art = float(row['Longueur (mm)'])
                                    h_art = float(row.get('Hauteur (mm)', 0))
                                    empilable = str(row.get('Empilable', 'Non')).strip().lower()
                                    
                                    # Calcul des étages (ex: 2700 / 900 = 3 étages)
                                    nb_etages = 1
                                    if empilable == 'oui' and h_art > 0:
                                        nb_etages = max(1, math.floor(H_UTILE / h_art))
                                    
                                    # Calcul des rangées au sol (Capacité = 2 colonnes * nb_etages)
                                    capa_rangée = 2 * nb_etages
                                    nb_rangées = math.ceil(qte / capa_rangée)

                                    for _ in range(nb_rangées):
                                        toutes_les_rangées.append({
                                            "label": f"Réf {ref_solo} ({row['Libelle'] if 'Libelle' in row else ''})",
                                            "longueur": l_art,
                                            "qte_lot": min(qte, capa_rangée)
                                        })
                                    break

            # --- RÉPARTITION DANS LES CAMIONS (13.6m) ---
            if toutes_les_rangées:
                camions = []
                c_actuel = {"utilisé": 0, "articles": []}
                
                for rangée in toutes_les_rangées:
                    if c_actuel["utilisé"] + rangée["longueur"] <= L_SEMI:
                        c_actuel["articles"].append(rangée)
                        c_actuel["utilisé"] += rangée["longueur"]
                    else:
                        camions.append(c_actuel)
                        c_actuel = {"utilisé": rangée["longueur"], "articles": [rangée]}
                camions.append(c_actuel)

                # --- AFFICHAGE ---
                st.divider()
                metrage_total = sum(r["longueur"] for r in toutes_les_rangées) / 1000
                
                col1, col2 = st.columns(2)
                col1.metric("Métrage Linéaire Total", f"{metrage_total:.2f} m")
                col2.metric("Nombre de Semi (13.6m)", len(camions))

                for i, cam in enumerate(camions, 1):
                    with st.expander(f"🚛 CAMION N°{i} - Occupation : {cam['utilisé']/1000:.2f}m / 13.6m", expanded=True):
                        df_cam = pd.Series([a["label"] for a in cam["articles"]]).value_counts().reset_index()
                        df_cam.columns = ['Désignation Article', 'Nombre de rangées au sol']
                        st.table(df_cam)
            else:
                st.error("Aucune référence détectée. Vérifiez que les numéros du PDF correspondent à l'Excel.")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
