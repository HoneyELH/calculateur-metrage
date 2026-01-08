import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Optimisation Précise", layout="wide")
st.title("🚚 Optimisation de Chargement (Calcul par Surface)")

# --- CONFIGURATION OFFICIELLE ---
L_UTILE = 13600  # Longueur semi (mm)
l_UTILE = 2460   # Largeur utile (mm)
H_UTILE = 2700   # Hauteur utile (mm)

st.sidebar.header("1. Paramètres")
uploaded_excel = st.sidebar.file_uploader("Base Excel (Palettes)", type=None)
uploaded_pdfs = st.file_uploader("2. Bons de Préparation (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 CALCULER L'OPTIMISATION"):
            surface_totale_sol_requise = 0
            details_chargement = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # Gestion des références groupées (ex: 74677 / 74679)
                            liste_refs = [r.strip() for r in str(row['Référence']).split('/')]
                            
                            for ref_solo in liste_refs:
                                if len(ref_solo) > 3 and ref_solo in ligne:
                                    # Extraction Quantité
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = 1
                                    if nombres:
                                        val = nombres[-1]
                                        qte = int(nombres[-2]) if val == ref_solo and len(nombres) > 1 else int(val)

                                    # Dimensions
                                    long_p = float(row['Longueur (mm)'])
                                    larg_p = float(row['Largeur (mm)'])
                                    haut_p = float(row['Hauteur (mm)'])
                                    empilable = str(row.get('Empilable', 'Oui')).strip().lower() == 'oui'

                                    # 1. Calcul du gerbage (Combien l'un sur l'autre ?)
                                    nb_etages = max(1, math.floor(H_UTILE / haut_p)) if empilable else 1
                                    
                                    # 2. Nombre de "places au sol" nécessaires pour cet article
                                    # On divise la quantité par le nombre d'étages
                                    places_sol = math.ceil(qte / nb_etages)
                                    
                                    # 3. Calcul de la surface occupée (Long x Larg)
                                    # Comme on charge en 2 colonnes, on ramène tout à la largeur de 1.23m (2.46m/2)
                                    # pour obtenir un métrage linéaire précis.
                                    metrage_ligne = (places_sol * long_p) / 2 # Division par 2 car 2 colonnes de large
                                    
                                    surface_totale_sol_requise += metrage_ligne
                                    
                                    details_chargement.append({
                                        "Réf": ref_solo,
                                        "Qté": qte,
                                        "Étages": nb_etages,
                                        "Long (mm)": long_p,
                                        "Métrage (mm)": metrage_ligne
                                    })
                                    break

            if details_chargement:
                st.divider()
                metrage_final_m = surface_totale_sol_requise / 1000
                nb_semis = math.ceil(metrage_final_m / 13.6)

                c1, c2 = st.columns(2)
                c1.metric("Métrage Linéaire TOTAL", f"{metrage_final_m:.2f} m")
                c2.metric("Nombre de Semi (13.6m)", nb_semis)

                st.subheader("Détail du calcul d'occupation")
                st.dataframe(pd.DataFrame(details_chargement), use_container_width=True)
                
                # Répartition virtuelle simple
                st.info(f"💡 Ce métrage de {metrage_final_m:.2f}m correspond à l'occupation réelle dans un camion de 2.46m de large.")
            else:
                st.error("Aucune référence détectée.")

    except Exception as e:
        st.error(f"Erreur : {e}")
