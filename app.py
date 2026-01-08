import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Plan de Chargement", layout="wide")
st.title("🚚 Planificateur de Chargement (Porteurs 2.60m)")

# --- CONFIGURATION FIXE ---
L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)

st.subheader("2. Charger les Bons de Préparation (PDF)")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture de l'Excel
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        df_articles['Ref_Str'] = df_articles['Référence'].astype(str).str.strip()
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 GÉNÉRER LE PLAN DE CAMIONS"):
            toutes_les_tranches = []

            # --- ÉTAPE 1 : EXTRACTION DES DONNÉES ---
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            ref = row['Ref_Str']
                            if ref in ligne and len(ref) > 3:
                                # Extraction Quantité
                                nombres = re.findall(r'\b\d+\b', ligne)
                                qte = 1
                                if nombres:
                                    val = nombres[-1]
                                    qte = int(nombres[-2]) if val == ref and len(nombres) > 1 else int(val)

                                # Paramètres Logistiques
                                l_art = float(row['Longueur (mm)'])
                                h_art = float(row.get('Hauteur (mm)', 0))
                                empilable = str(row.get('Empilable', 'Non')).strip().lower()
                                
                                # Calcul des couches (Hauteur)
                                nb_etages = 1
                                if empilable == 'oui' and h_art > 0:
                                    nb_etages = max(1, math.floor(H_CAMION / h_art))
                                
                                # On divise la quantité par (2 colonnes * nb_etages)
                                capacite_par_rangée = 2 * nb_etages
                                nb_rangées = math.ceil(qte / capacite_par_rangée)

                                # On crée des blocs de chargement
                                for _ in range(nb_rangées):
                                    toutes_les_tranches.append({
                                        "label": f"{ref} (Lot de {min(qte, capacite_par_rangée)} pces)",
                                        "longueur": l_art
                                    })
                                break

            # --- ÉTAPE 2 : RÉPARTITION DANS LES CAMIONS ---
            camions = []
            if toutes_les_tranches:
                camion_actuel = {"longueur_libre": L_CAMION, "articles": []}
                
                for item in toutes_les_tranches:
                    if item["longueur"] <= camion_actuel["longueur_libre"]:
                        camion_actuel["articles"].append(item)
                        camion_actuel["longueur_libre"] -= item["longueur"]
                    else:
                        camions.append(camion_actuel)
                        camion_actuel = {"longueur_libre": L_CAMION - item["longueur"], "articles": [item]}
                
                camions.append(camion_actuel)

                # --- ÉTAPE 3 : AFFICHAGE ---
                st.divider()
                metrage_total = sum(t["longueur"] for t in toutes_les_tranches) / 1000
                
                col1, col2 = st.columns(2)
                col1.metric("Métrage Linéaire Total", f"{metrage_total:.2f} m")
                col2.metric("Nombre de Camions", len(camions))

                st.subheader("📋 Liste de chargement par véhicule")
                for i, cam in enumerate(camions, 1):
                    with st.expander(f"🚛 CAMION N°{i} (Utilisé : {L_CAMION - cam['longueur_libre']} / {L_CAMION} mm)", expanded=True):
                        # Regrouper les mêmes articles pour que ce soit lisible
                        liste_brute = [a["label"] for a in cam["articles"]]
                        inventaire = pd.Series(liste_brute).value_counts().reset_index()
                        inventaire.columns = ['Désignation Article', 'Nombre de rangées au sol']
                        st.table(inventaire)
            else:
                st.error("Aucun article correspondant n'a été trouvé dans le PDF.")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
