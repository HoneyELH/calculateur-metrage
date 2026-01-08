import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Correctif Quantité", layout="wide")
st.title("🚚 Calculateur de Chargement (Précision Quantités)")

# --- PARAMÈTRES FIXES ---
L_CAMION = 2600 
l_CAMION = 2460
H_CAMION = 2600 # Hauteur standard

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel", type=None)

st.subheader("2. Documents")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 RELANCER LE CALCUL PRÉCIS"):
            total_mm_lineaire = 0
            details = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        lignes = page.extract_text().split('\n')
                        for ligne in lignes:
                            for _, row in df_articles.iterrows():
                                ref_cible = str(row['Référence']).strip()
                                
                                # Sécurité : On vérifie si la référence est présente dans la ligne
                                if ref_cible in ligne and len(ref_cible) > 3:
                                    # --- EXTRACTION SÉCURISÉE DE LA QUANTITÉ ---
                                    # On enlève la référence de la ligne pour ne pas la compter comme quantité
                                    texte_sans_ref = ligne.replace(ref_cible, "")
                                    # On cherche les nombres restants
                                    nombres = re.findall(r'\b\d+\b', texte_sans_ref)
                                    
                                    # On prend généralement le dernier nombre de la ligne (souvent la quantité)
                                    # ou le premier nombre après la référence
                                    qte = 1
                                    if nombres:
                                        qte = int(nombres[-1]) # On prend le dernier chiffre (plus fiable sur vos bons)
                                    
                                    # --- LOGIQUE DE CALCUL ---
                                    l_art = float(row['Longueur (mm)'])
                                    h_art = float(row.get('Hauteur (mm)', 0))
                                    autorise = str(row.get('Empilable', 'Non')).strip().lower()
                                    
                                    # Hauteur
                                    nb_etages = 1
                                    if autorise == 'oui' and h_art > 0:
                                        nb_etages = max(1, math.floor(H_CAMION / h_art))
                                    
                                    # Capacité par tranche de 2.46m (Largeur)
                                    capacite_tranche = 2 * nb_etages
                                    
                                    # Sol occupé
                                    nb_tranches = math.ceil(qte / capacite_tranche)
                                    sol_occupé = nb_tranches * l_art
                                    total_mm_lineaire += sol_occupé
                                    
                                    details.append({
                                        "Document": pdf_file.name,
                                        "Référence": ref_cible,
                                        "Qté réelle": qte,
                                        "L (mm)": l_art,
                                        "Étages": nb_etages,
                                        "Sol (mm)": sol_occupé
                                    })
                                    break # On passe à la ligne suivante du PDF

            # --- AFFICHAGE ---
            st.divider()
            metrage_m = total_mm_lineaire / 1000
            nb_camions = math.ceil(total_mm_lineaire / L_CAMION)
            
            c1, c2 = st.columns(2)
            c1.metric("Métrage Linéaire Total", f"{metrage_m:.2f} m")
            c2.metric("NB CAMIONS (2.60m)", f"{nb_camions}")

            st.subheader("Vérification des données extraites")
            st.table(pd.DataFrame(details))

    except Exception as e:
        st.error(f"Erreur : {e}")
