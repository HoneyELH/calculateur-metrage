import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Récupération", layout="wide")
st.title("🚚 Calculateur de Métrage Camion")

# Paramètres camions
L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel", type=None)
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # On lit l'Excel et on nettoie les références tout de suite
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        df_articles['Ref_Clean'] = df_articles['Référence'].astype(str).str.strip().str.upper()
        
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
                            ligne_u = ligne.upper() # On passe la ligne du PDF en majuscules
                            
                            for _, row in df_articles.iterrows():
                                ref_cible = row['Ref_Clean']
                                
                                # RECHERCHE SIMPLE : si le code est dans la ligne
                                if ref_cible in ligne_u and len(ref_cible) > 2:
                                    # Extraction quantité (on prend le dernier nombre de la ligne)
                                    nombres = re.findall(r'\d+', ligne)
                                    qte = 1
                                    if nombres:
                                        val = nombres[-1]
                                        # Si le dernier nombre est la ref, on prend l'avant-dernier
                                        if val == ref_cible and len(nombres) > 1:
                                            qte = int(nombres[-2])
                                        else:
                                            qte = int(val)

                                    l_art = float(row['Longueur (mm)'])
                                    h_art = float(row.get('Hauteur (mm)', 0))
                                    autorise = str(row.get('Empilable', 'Non')).strip().lower()
                                    
                                    # Calcul des étages (ex: 2600 / 800 = 3 étages)
                                    etages = 1
                                    if autorise == 'oui' and h_art > 0:
                                        etages = max(1, math.floor(H_CAMION / h_art))
                                    
                                    # Calcul sol (2 colonnes de large)
                                    tranches = math.ceil(qte / (2 * etages))
                                    sol = tranches * l_art
                                    total_mm += sol
                                    
                                    details.append({
                                        "Réf": ref_cible,
                                        "Qté": qte,
                                        "Étages": etages,
                                        "Sol (mm)": sol
                                    })
                                    break

            if details:
                st.divider()
                st.metric("NB CAMIONS (2.60m)", math.ceil(total_mm / L_CAMION))
                st.table(pd.DataFrame(details))
            else:
                st.error("❌ Aucune référence trouvée. Vérifiez que l'onglet s'appelle bien 'Palettes' et que les références sont identiques.")
    except Exception as e:
        st.error(f"Erreur : {e}")
