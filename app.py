import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Optimisation Finale", layout="wide")
st.title("🚚 Calculateur de Chargement Intelligent")

# --- CONFIGURATION ---
st.sidebar.header("1. Paramètres Camion")
# Valeurs transmises : Longueur 2.60m, Largeur 2.46m
L_CAMION = 2600 
l_CAMION = 2460
H_CAMION = st.sidebar.number_input("Hauteur utile du camion (mm)", value=2600)

uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)

st.subheader("2. Documents à analyser")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 LANCER LE CALCUL"):
            total_mm_lineaire = 0
            details = []

            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            l_art = float(row['Longueur (mm)'])
                            h_art = float(row.get('Hauteur (mm)', 0))
                            # On vérifie l'autorisation d'empilage
                            autorise = str(row.get('Empilable', 'Non')).strip().lower()
                            
                            for ref in refs:
                                if ref in ligne and len(ref) > 3:
                                    nombres = re.findall(r'\b\d+\b', ligne)
                                    qte = int(nombres[0]) if nombres else 1
                                    
                                    # --- CALCUL DE LA CAPACITÉ PAR PILE (HAUTEUR) ---
                                    if autorise == 'oui' and h_art > 0:
                                        nb_etages = math.floor(H_CAMION / h_art)
                                        # Sécurité : au moins 1 étage, même si erreur hauteur
                                        nb_etages = max(1, nb_etages)
                                    else:
                                        nb_etages = 1
                                    
                                    # --- CALCUL DE LA CAPACITÉ TOTALE PAR TRANCHE (LARGEUR + HAUTEUR) ---
                                    # On considère 2 palettes côte à côte dans la largeur (2.46m)
                                    capacite_par_tranche = 2 * nb_etages
                                    
                                    # Nombre de tranches de longueur occupées
                                    nb_tranches = math.ceil(qte / capacite_par_tranche)
                                    occupation_sol = nb_tranches * l_art
                                    total_mm_lineaire += occupation_sol
                                    
                                    details.append({
                                        "Réf": ref,
                                        "Qté": qte,
                                        "H (mm)": h_art,
                                        "Étages possibles": nb_etages,
                                        "Capacité/Tranche": capacite_par_tranche,
                                        "Sol occupé (mm)": occupation_sol
                                    })
                                    break

            # --- AFFICHAGE ---
            st.divider()
            metrage_m = total_mm_lineaire / 1000
            nb_camions = math.ceil(total_mm_lineaire / L_CAMION)
            
            c1, c2 = st.columns(2)
            c1.metric("Métrage Linéaire Total", f"{metrage_m:.2f} m")
            c2.metric("NB CAMIONS (2.60m)", nb_camions)

            st.subheader("Détail technique du chargement")
            st.dataframe(pd.DataFrame(details), use_container_width=True)
            
            st.info(f"Note : Le calcul prévoit 2 colonnes de palettes sur la largeur de {l_CAMION/1000}m.")

    except Exception as e:
        st.error(f"Erreur : Vérifiez les colonnes 'Référence', 'Longueur (mm)', 'Hauteur (mm)' et 'Empilable'.\nDétail : {e}")
