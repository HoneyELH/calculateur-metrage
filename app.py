import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Plan de Chargement", layout="wide")
st.title("🚚 Planificateur de Chargement")

L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 GÉNÉRER LE PLAN DE CAMIONS"):
            toutes_les_tranches = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte_pdf = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte_pdf.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # --- LA CORRECTION EST ICI ---
                            # On sépare les références du Excel s'il y a des "/"
                            liste_refs_excel = [r.strip() for r in str(row['Référence']).split('/')]
                            
                            for ref_unique in liste_refs_excel:
                                # On cherche chaque numéro séparément dans la ligne du PDF
                                if len(ref_unique) > 3 and ref_unique in ligne:
                                    # Extraction Quantité
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if nombres:
                                        val = nombres[-1]
                                        qte = int(nombres[-2]) if val == ref_unique and len(nombres) > 1 else int(val)

                                    l_art = float(row['Longueur (mm)'])
                                    h_art = float(row.get('Hauteur (mm)', 0))
                                    empilable = str(row.get('Empilable', 'Non')).strip().lower()
                                    
                                    # Calcul des étages (ex: 2600 / 900 = 2 étages)
                                    etages = max(1, math.floor(H_CAMION / h_art)) if (empilable == 'oui' and h_art > 0) else 1
                                    
                                    # Calcul du nombre de rangées au sol (2 colonnes de large)
                                    nb_rangées = math.ceil(qte / (2 * etages))

                                    for _ in range(nb_rangées):
                                        toutes_les_tranches.append({
                                            "label": f"Réf {ref_unique} (Lot {min(qte, 2*etages)} pces)",
                                            "longueur": l_art
                                        })
                                    break # On a trouvé l'article, on passe à la ligne suivante

            # --- RÉPARTITION DANS LES CAMIONS ---
            if toutes_les_tranches:
                camions = []
                camion_actuel = {"libre": L_CAMION, "articles": [], "utilisé": 0}
                
                for item in toutes_les_tranches:
                    if item["longueur"] <= camion_actuel["libre"]:
                        camion_actuel["articles"].append(item)
                        camion_actuel["utilisé"] += item["longueur"]
                        camion_actuel["libre"] -= item["longueur"]
                    else:
                        camions.append(camion_actuel)
                        camion_actuel = {"libre": L_CAMION - item["longueur"], "articles": [item], "utilisé": item["longueur"]}
                camions.append(camion_actuel)

                # --- AFFICHAGE ---
                st.divider()
                metrage_total = sum(t["longueur"] for t in toutes_les_tranches) / 1000
                
                c1, c2 = st.columns(2)
                c1.metric("Métrage Linéaire Total", f"{metrage_total:.2f} m")
                c2.metric("Nombre de Camions (2.60m)", len(camions))

                st.subheader("📋 Répartition par véhicule")
                for i, cam in enumerate(camions, 1):
                    with st.expander(f"🚛 CAMION N°{i} (Occupé : {cam['utilisé']} / {L_CAMION} mm)", expanded=True):
                        labels = [a["label"] for a in cam["articles"]]
                        inventaire = pd.Series(labels).value_counts().reset_index()
                        inventaire.columns = ['Désignation', 'Nombre de rangées au sol']
                        st.table(inventaire)
            else:
                st.error("❌ Aucune référence trouvée. Le logiciel a lu les adresses mais n'a pas vu vos numéros d'articles.")

    except Exception as e:
        st.error(f"Erreur : {e}")
