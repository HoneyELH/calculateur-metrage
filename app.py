import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Plan de Chargement", layout="wide")
st.title("🚚 Organisateur de Chargement par Camion")

# --- CONFIGURATION FIXE ---
L_CAMION = 2600 
H_CAMION = 2600 

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Charger la base Excel (Palettes)", type=None)

st.subheader("2. Documents")
uploaded_pdfs = st.file_uploader("Glissez vos PDF ici", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success("✅ Base articles connectée")
        
        if st.button("🚀 GÉNÉRER LE PLAN DE CHARGEMENT"):
            liste_globale_tranches = []

            # 1. ANALYSE DES DOCUMENTS
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            ref_cible = str(row['Référence']).strip()
                            if ref_cible in ligne and len(ref_cible) > 3:
                                # Extraction Quantité
                                nombres = re.findall(r'\b\d+\b', ligne)
                                qte = 1
                                if nombres:
                                    val = nombres[-1]
                                    qte = int(nombres[-2]) if val == ref_cible and len(nombres) > 1 else int(val)

                                # Paramètres article
                                l_art = float(row['Longueur (mm)'])
                                h_art = float(row.get('Hauteur (mm)', 0))
                                autorise = str(row.get('Empilable', 'Non')).strip().lower()
                                
                                # Calcul capacité par tranche de longueur (Largeur + Hauteur)
                                etages = max(1, math.floor(H_CAMION / h_art)) if (autorise == 'oui' and h_art > 0) else 1
                                capacite_tranche = 2 * etages
                                nb_tranches_necessaires = math.ceil(qte / capacite_tranche)

                                # On ajoute chaque "tranche" de cet article à la liste d'attente
                                for _ in range(nb_tranches_necessaires):
                                    liste_globale_tranches.append({
                                        "Réf": ref_cible,
                                        "L": l_art,
                                        "Détail": f"{ref_cible} (Lot de {min(qte, capacite_tranche)})"
                                    })
                                break

            # 2. RÉPARTITION DANS LES CAMIONS (Algorithme de remplissage)
            camions = []
            camion_actuel = {"longueur_utilisee": 0, "articles": []}

            for tranche in liste_globale_tranches:
                # Si la tranche d'article rentre dans le camion actuel
                if camion_actuel["longueur_utilisee"] + tranche["L"] <= L_CAMION:
                    camion_actuel["longueur_utilisee"] += tranche["L"]
                    camion_actuel["articles"].append(tranche["Détail"])
                else:
                    # Sinon on ferme ce camion et on en ouvre un nouveau
                    camions.append(camion_actuel)
                    camion_actuel = {"longueur_utilisee": tranche["L"], "articles": [tranche["Détail"]]}
            
            if camion_actuel["articles"]:
                camions.append(camion_actuel)

            # 3. AFFICHAGE DU PLAN
            st.divider()
            st.header(f"📋 Répartition : {len(camions)} Camion(s) nécessaire(s)")

            for i, c in enumerate(camions, 1):
                with st.expander(f"🚛 CAMION N°{i} - Remplissage : {c['longueur_utilisee']} / {L_CAMION} mm", expanded=True):
                    # On regroupe les articles identiques pour la lisibilité
                    df_camion = pd.Series(c['articles']).value_counts().reset_index()
                    df_camion.columns = ['Article (et son lot)', 'Nombre de rangées']
                    st.table(df_camion)

    except Exception as e:
        st.error(f"Erreur technique : {e}")
