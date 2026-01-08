import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Organisateur Universel", layout="wide")
st.title("🚚 Planificateur de Chargement Multi-Bons")

# --- CONFIGURATION FIXE ---
L_UTILE = 13600  # Longueur semi (mm)
H_UTILE = 2700   # Hauteur utile (mm)
SEUIL_LARGEUR_PLEINE = 1100 # Seuil pour bloquer une rangée complète (mm)

st.sidebar.header("1. Configuration")
uploaded_excel = st.sidebar.file_uploader("Base Excel (Palettes)", type=None)
uploaded_pdfs = st.file_uploader("2. Charger TOUS les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        # Lecture de la base
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        st.sidebar.success(f"✅ {len(df_articles)} références chargées")
        
        if st.button("🚀 GÉNÉRER LE PLAN DE CHARGEMENT"):
            toutes_les_tranches = []

            # --- ANALYSE DE CHAQUE BON ---
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    lignes = texte.split('\n')

                    for ligne in lignes:
                        for _, row in df_articles.iterrows():
                            # Gestion des références multiples (74677 / 74679...)
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

                                    # 1. Calcul du gerbage (Hauteur)
                                    nb_etages = max(1, math.floor(H_UTILE / haut_p)) if empilable else 1
                                    nb_places_sol = math.ceil(qte / nb_etages)

                                    # 2. Calcul du métrage (Largeur)
                                    # Règle : Si > 1100mm, prend toute la largeur du camion
                                    if larg_p > SEUIL_LARGEUR_PLEINE:
                                        metrage_item = nb_places_sol * long_p
                                        note = "Pleine Largeur"
                                    else:
                                        metrage_item = (nb_places_sol * long_p) / 2
                                        note = "Demi-Largeur"

                                    # On ajoute chaque lot à la liste globale
                                    toutes_les_tranches.append({
                                        "Ref": ref_solo,
                                        "Libellé": f"{ref_solo} ({note})",
                                        "Longueur": metrage_item,
                                        "Détail": f"Lot de {qte} (sur {nb_places_sol} place(s) au sol)"
                                    })
                                    break

            # --- RÉPARTITION DANS LES CAMIONS ---
            if toutes_les_tranches:
                camions = []
                camion_actuel = {"libre": L_UTILE, "articles": [], "occupé": 0}

                for item in toutes_les_tranches:
                    if item["Longueur"] <= camion_actuel["libre"]:
                        camion_actuel["articles"].append(item)
                        camion_actuel["occupé"] += item["Longueur"]
                        camion_actuel["libre"] -= item["Longueur"]
                    else:
                        camions.append(camion_actuel)
                        camion_actuel = {"libre": L_UTILE - item["Longueur"], "articles": [item], "occupé": item["Longueur"]}
                camions.append(camion_actuel)

                # --- AFFICHAGE FINAL ---
                st.divider()
                m_total = sum(i["Longueur"] for i in toutes_les_tranches) / 1000
                
                col1, col2 = st.columns(2)
                col1.metric("Métrage Linéaire TOTAL", f"{m_total:.2f} m")
                col2.metric("Camions nécessaires (13.6m)", len(camions))

                st.subheader("📋 Quel article mettre dans quel camion ?")
                for i, cam in enumerate(camions, 1):
                    with st.expander(f"🚛 CAMION N°{i} - Occupation : {cam['occupé']/1000:.2f} m / 13.6 m", expanded=True):
                        # Regrouper pour la lisibilité
                        df_cam = pd.DataFrame(cam["articles"])
                        inventaire = df_cam.groupby(['Libellé', 'Détail']).size().reset_index(name='Nombre de rangées')
                        st.table(inventaire)
            else:
                st.error("Aucune correspondance trouvée entre vos PDF et votre Excel.")

    except Exception as e:
        st.error(f"Erreur technique : {e}")
