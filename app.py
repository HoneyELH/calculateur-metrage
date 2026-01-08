import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

# Configuration de l'interface
st.set_page_config(page_title="Hako-Toro : Optimisation Stable", layout="wide")

st.title("🚚 Calculateur de Métrage (Version Stable & Empilage)")

# --- CONFIGURATION ---
st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)
h_camion = st.sidebar.number_input("Hauteur utile du camion (mm)", value=2600)

# --- ZONE DOCUMENTS ---
st.subheader("2. Chargement des documents")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture de l'Excel
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 LANCER LE CALCUL"):
            total_mm_brut = 0
            total_mm_optimise = 0
            details = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # Nettoyage des références
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            l_art = float(row['Longueur (mm)'])
                            h_art = float(row.get('Hauteur (mm)', 0))
                            # On vérifie si l'Excel autorise l'empilage
                            autorise_excel = str(row.get('Empilable', 'Non')).strip().lower()
                            
                            for ref in refs:
                                # Si la référence est trouvée dans la ligne du PDF
                                if ref in ligne and len(ref) > 3:
                                    # Recherche de la quantité (dernier chiffre de la ligne)
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if nombres:
                                        derniere_val = nombres[-1]
                                        # Si le dernier nombre est la ref, on prend l'avant-dernier
                                        if derniere_val == ref and len(nombres) > 1:
                                            qte = int(nombres[-2])
                                        else:
                                            qte = int(derniere_val)
                                    
                                    # 1. Calcul Brut (Tout au sol)
                                    brut_ligne = l_art * qte
                                    total_mm_brut += brut_ligne
                                    
                                    # 2. Calcul du nombre d'étages possibles (Hauteur)
                                    nb_etages = 1
                                    if autorise_excel == 'oui' and h_art > 0:
                                        # On calcule combien de fois la machine rentre dans le camion
                                        nb_etages = max(1, math.floor(h_camion / h_art))
                                    
                                    # 3. Calcul de l'occupation au sol
                                    # On considère 2 colonnes en largeur, donc capacité = 2 * nb_etages
                                    capacite_par_tranche = 2 * nb_etages
                                    nb_piles = math.ceil(qte / capacite_par_tranche)
                                    opti_ligne = nb_piles * l_art
                                    
                                    total_mm_optimise += opti_ligne
                                    
                                    details.append({
                                        "Réf": ref,
                                        "Qté": qte,
                                        "H (mm)": h_art,
                                        "Étages": nb_etages,
                                        "Sol (mm)": opti_ligne
                                    })
                                    break

            # --- AFFICHAGE DES RÉSULTATS ---
            if details:
                st.divider()
                c1, c2 = st.columns(2)
                
                with c1:
                    st.metric("Métrage Brut", f"{total_mm_brut / 1000:.2f} m")
                
                with c2:
                    gain = (total_mm_brut - total_mm_optimise) / 1000
                    st.metric("Métrage Optimisé (LDM)", f"{total_mm_optimise / 1000:.2f} m", delta=f"-{gain:.2f}m")

                st.subheader("Détail des articles détectés")
                st.table(pd.DataFrame(details))
                
                # Calcul du nombre de camions de 2.60m
                nb_camions = math.ceil(total_mm_optimise / 2600)
                st.info(f"🚚 Estimation : Il faut environ **{nb_camions}** camion(s) de 2.60m.")
            else:
                st.warning("⚠️ Aucune référence trouvée dans le PDF. Vérifiez l'onglet 'Palettes'.")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
