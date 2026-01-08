import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Plan de Chargement", layout="wide")
st.title("🚚 Planificateur de Chargement")

# --- CONFIGURATION FIXE ---
L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)

st.subheader("2. Charger les Bons de Préparation (PDF)")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture de l'Excel - On s'assure que les références sont lues comme du texte
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 GÉNÉRER LE PLAN DE CAMIONS"):
            toutes_les_tranches = []

            # --- ÉTAPE 1 : EXTRACTION ---
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    # On extrait tout le texte du PDF d'un coup
                    texte_pdf = ""
                    for page in pdf.pages:
                        texte_pdf += page.extract_text() + "\n"
                    
                    lignes = texte_pdf.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # On cherche la référence brute dans la ligne
                            ref = str(row['Référence']).strip()
                            
                            if ref in ligne and len(ref) > 3:
                                # On cherche tous les nombres dans la ligne pour trouver la quantité
                                nombres = re.findall(r'\b\d+\b', ligne)
                                qte = 1
                                if nombres:
                                    # On prend le dernier nombre de la ligne (souvent la qté)
                                    val = nombres[-1]
                                    # Si le dernier nombre est la ref, on prend l'avant-dernier
                                    if val == ref and len(nombres) > 1:
                                        qte = int(nombres[-2])
                                    else:
                                        qte = int(val)

                                # Paramètres Logistiques
                                l_art = float(row['Longueur (mm)'])
                                h_art = float(row.get('Hauteur (mm)', 0))
                                empilable = str(row.get('Empilable', 'Non')).strip().lower()
                                
                                # Calcul des couches (Hauteur)
                                nb_etages = 1
                                if empilable == 'oui' and h_art > 0:
                                    nb_etages = max(1, math.floor(H_CAMION / h_art))
                                
                                # 2 colonnes en largeur * nb_etages en hauteur
                                capacite_par_rangée = 2 * nb_etages
                                nb_rangées = math.ceil(qte / capacite_par_rangée)

                                # Ajout à la liste de chargement
                                for _ in range(nb_rangées):
                                    toutes_les_tranches.append({
                                        "label": f"Réf {ref} (Lot de {min(qte, capacite_par_rangée)} pces)",
                                        "longueur": l_art,
                                        "ref": ref
                                    })
                                break # On passe à la ligne suivante du PDF

            # --- ÉTAPE 2 : RÉPARTITION DANS LES CAMIONS ---
            if toutes_les_tranches:
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

                # --- ÉTAPE 3 : AFFICHAGE ---
                st.divider()
                metrage_total = sum(t["longueur"] for t in toutes_les_tranches) / 1000
                
                c1, c2 = st.columns(2)
                c1.metric("Métrage Linéaire Total", f"{metrage_total:.2f} m")
                c2.metric("Nombre de Camions (2.60m)", len(camions))

                st.subheader("📋 Répartition par véhicule")
                for i, cam in enumerate(camions, 1):
                    with st.expander(f"🚛 CAMION N°{i} (Occupé : {L_CAMION - cam['libre']} / {L_CAMION} mm)", expanded=True):
                        labels = [a["label"] for a in cam["articles"]]
                        # On compte combien de fois chaque lot apparaît
                        inventaire = pd.Series(labels).value_counts().reset_index()
                        inventaire.columns = ['Désignation', 'Nombre de rangées au sol']
                        st.table(inventaire)
            else:
                st.error("❌ Aucune référence trouvée. Vérifiez que l'onglet Excel s'appelle 'Palettes' et que les références sont bien dans la colonne 'Référence'.")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
