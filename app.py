import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Scanner Robuste", layout="wide")
st.title("🚚 Calculateur de Chargement")

# Paramètres
L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("Configuration")
uploaded_excel = st.sidebar.file_uploader("1. Charger l'Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 LANCER LE CALCUL"):
            total_mm = 0
            details = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        texte = page.extract_text()
                        if not texte: continue
                        
                        lignes = texte.split('\n')
                        for ligne in lignes:
                            # On nettoie la ligne pour faciliter la recherche
                            ligne_nettoyee = ligne.replace(" ", "") 
                            
                            for _, row in df_articles.iterrows():
                                ref_cible = str(row['Référence']).strip()
                                
                                # On cherche si la référence est dans la ligne nettoyée
                                if ref_cible in ligne_nettoyee and len(ref_cible) > 2:
                                    # Extraction de la quantité : on cherche le chiffre à la fin de la ligne d'origine
                                    nombres = re.findall(r'\d+', ligne)
                                    qte = 1
                                    if nombres:
                                        # On prend le dernier nombre de la ligne s'il est différent de la référence
                                        qte_trouvee = int(nombres[-1])
                                        if str(qte_trouvee) != ref_cible:
                                            qte = qte_trouvee
                                        elif len(nombres) > 1:
                                            # Si le dernier nombre était la ref, on prend celui d'avant
                                            qte = int(nombres[-2])

                                    l_art = float(row['Longueur (mm)'])
                                    h_art = float(row.get('Hauteur (mm)', 0))
                                    autorise = str(row.get('Empilable', 'Non')).strip().lower()
                                    
                                    # Calcul étages
                                    etages = 1
                                    if autorise == 'oui' and h_art > 0:
                                        etages = max(1, math.floor(H_CAMION / h_art))
                                    
                                    # Occupation
                                    tranches = math.ceil(qte / (2 * etages))
                                    sol = tranches * l_art
                                    total_mm += sol
                                    
                                    details.append({
                                        "Réf": ref_cible,
                                        "Qté": qte,
                                        "Empilable": autorise,
                                        "Étages": etages,
                                        "Sol (mm)": sol
                                    })
                                    break

            if details:
                st.divider()
                st.metric("NB CAMIONS (2.60m)", math.ceil(total_mm / L_CAMION))
                st.subheader("Détail des correspondances trouvées")
                st.table(pd.DataFrame(details))
            else:
                st.warning("⚠️ Aucune référence de l'Excel n'a été trouvée dans les PDF. Vérifiez que les références dans l'Excel correspondent exactement aux numéros dans le PDF.")

    except Exception as e:
        st.error(f"Erreur : {e}")
