import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Version Stable", layout="wide")
st.title("🚚 Calculateur de Métrage Camion")

# --- PARAMÈTRES FIXES ---
L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)

st.subheader("2. Documents")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture de l'Excel
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 LANCER LE CALCUL"):
            total_mm_lineaire = 0
            details = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte_complet = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte_complet.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            ref_cible = str(row['Référence']).strip()
                            
                            # Si la référence est trouvée dans la ligne
                            if ref_cible in ligne and len(ref_cible) > 3:
                                # Extraction de la quantité (on cherche les chiffres qui ne sont pas la réf)
                                nombres = re.findall(r'\b\d+\b', ligne)
                                qte = 1
                                if nombres:
                                    # On prend le dernier chiffre de la ligne (souvent la qté sur vos bons)
                                    derniere_valeur = nombres[-1]
                                    if derniere_valeur != ref_cible:
                                        qte = int(derniere_valeur)
                                    elif len(nombres) > 1:
                                        qte = int(nombres[-2])

                                # Données Excel
                                l_art = float(row['Longueur (mm)'])
                                h_art = float(row.get('Hauteur (mm)', 0))
                                autorise = str(row.get('Empilable', 'Non')).strip().lower()
                                
                                # Calcul du gerbage
                                etages = 1
                                if autorise == 'oui' and h_art > 0:
                                    etages = max(1, math.floor(H_CAMION / h_art))
                                
                                # Calcul occupation au sol (2 colonnes de large)
                                tranches = math.ceil(qte / (2 * etages))
                                sol_mm = tranches * l_art
                                total_mm_lineaire += sol_mm
                                
                                details.append({
                                    "Référence": ref_cible,
                                    "Qté": qte,
                                    "L (mm)": l_art,
                                    "H (mm)": h_art,
                                    "Étages": etages,
                                    "Sol (mm)": sol_mm
                                })
                                break

            # --- AFFICHAGE DES RÉSULTATS ---
            if details:
                st.divider()
                metrage_m = total_mm_lineaire / 1000
                nb_camions = math.ceil(total_mm_lineaire / L_CAMION)
                
                c1, c2 = st.columns(2)
                c1.metric("Métrage Linéaire Total", f"{metrage_m:.2f} m")
                c2.metric("NB CAMIONS (2.60m)", nb_camions)

                st.subheader("Détail du chargement")
                st.dataframe(pd.DataFrame(details), use_container_width=True)
            else:
                st.warning("Aucune référence trouvée. Vérifiez que l'onglet Excel s'appelle 'Palettes'.")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
