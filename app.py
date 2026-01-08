import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Diagnostic", layout="wide")
st.title("🚚 Planificateur de Chargement (Mode Diagnostic)")

L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture Excel forcée en texte
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes', dtype={'Référence': str})
        st.sidebar.success("✅ Excel chargé")
        
        if st.button("🚀 LANCER LE CALCUL ET LE DIAGNOSTIC"):
            toutes_les_tranches = []
            log_diag = [] # Pour comprendre pourquoi ça rate

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        texte = page.extract_text()
                        if not texte: continue
                        
                        lignes = texte.split('\n')
                        for ligne in lignes:
                            for _, row in df_articles.iterrows():
                                # On nettoie la ref (ex: " 74677 " -> "74677")
                                ref_brute = str(row['Référence']).strip()
                                
                                # TEST DE DÉTECTION
                                if ref_brute in ligne and len(ref_brute) > 2:
                                    # Extraction quantité
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if nombres:
                                        val = nombres[-1]
                                        qte = int(nombres[-2]) if val == ref_brute and len(nombres) > 1 else int(val)

                                    l_art = float(row['Longueur (mm)'])
                                    h_art = float(row.get('Hauteur (mm)', 0))
                                    empilable = str(row.get('Empilable', 'Non')).strip().lower()
                                    
                                    etages = max(1, math.floor(H_CAMION / h_art)) if (empilable == 'oui' and h_art > 0) else 1
                                    nb_rangées = math.ceil(qte / (2 * etages))

                                    for _ in range(nb_rangées):
                                        toutes_les_tranches.append({
                                            "label": f"Réf {ref_brute} (Lot {min(qte, 2*etages)})",
                                            "longueur": l_art
                                        })
                                    break
                                else:
                                    # On garde une trace des essais manqués si la ligne contient un nombre
                                    if len(re.findall(r'\d{4,}', ligne)) > 0:
                                        log_diag.append(f"Ligne PDF : '{ligne}' | Cherché : '{ref_brute}'")

            if toutes_les_tranches:
                # --- CALCUL DES CAMIONS ---
                camions = []
                camion_actuel = {"libre": L_CAMION, "articles": []}
                for item in toutes_les_tranches:
                    if item["longueur"] <= camion_actuel["libre"]:
                        camion_actuel["articles"].append(item)
                        camion_actuel["libre"] -= item["longueur"]
                    else:
                        camions.append(camion_actuel)
                        camion_actuel = {"libre": L_CAMION - item["longueur"], "articles": [item]}
                camions.append(camion_actuel)

                st.metric("Nombre de Camions", len(camions))
                for i, cam in enumerate(camions, 1):
                    with st.expander(f"🚛 CAMION N°{i}", expanded=True):
                        st.table(pd.Series([a["label"] for a in cam["articles"]]).value_counts())
            else:
                st.error("❌ Aucune correspondance trouvée.")
                with st.expander("🔍 Pourquoi ça ne marche pas ? (Analyse technique)"):
                    st.write("Le logiciel a essayé de comparer tes références Excel avec ces lignes du PDF :")
                    for log in log_diag[:20]: # Affiche les 20 premiers essais
                        st.code(log)

    except Exception as e:
        st.error(f"Erreur : {e}")
