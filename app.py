import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Optimisation Cartons", layout="wide")
st.title("🚚 Plan de Chargement (Optimisation Cartons)")

# --- PARAMÈTRES RÉELS ---
L_UTILE = 13600 #
H_UTILE = 2600  #
SEUIL_LARGEUR_PLEINE = 1100 

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 CALCULER LE MÉTRAGE"):
            all_palettes = []
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf:
                    texte = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
                    for ligne in texte.split('\n'):
                        for idx, row in df_articles.iterrows():
                            refs = [r.strip() for r in str(row['Référence']).split('/')]
                            for r in refs:
                                if len(r) > 3 and r in ligne:
                                    n = re.findall(r'\b\d+\b', ligne)
                                    qte = int(n[-2]) if n and n[-1] == r and len(n)>1 else int(n[-1]) if n else 1
                                    
                                    desc = str(row.get('Description', '')).lower()
                                    matiere = 'fer' if 'fer' in desc else 'carton' if 'carton' in desc else 'bois' if 'bois' in desc else 'inconnu'

                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": float(row['Longueur (mm)']),
                                            "l": float(row['Largeur (mm)']), "H": float(row['Hauteur (mm)']),
                                            "Mat": matiere, "Ligne_Excel": idx
                                        })
                                    break

            piles = []
            
            # --- 1. GESTION DES CARTONS (Mélange autorisé + Pyramide) ---
            cartons = [p for p in all_palettes if p['Mat'] == 'carton']
            cartons = sorted(cartons, key=lambda x: x['l'], reverse=True) # Largeur max en bas
            while cartons:
                base = cartons.pop(0)
                h_actuelle, p_refs = base['H'], [base['Ref']]
                i = 0
                while i < len(cartons):
                    if h_actuelle + cartons[i]['H'] <= H_UTILE and cartons[i]['l'] <= base['l']:
                        h_actuelle += cartons[i]['H']
                        p_refs.append(cartons.pop(i)['Ref'])
                    else: i += 1
                piles.append({"Refs": p_refs, "L": base['L'], "l": base['l'], "Mat": "carton"})

            # --- 2. GESTION DU BOIS (Même ligne uniquement + Pyramide) ---
            bois = [p for p in all_palettes if p['Mat'] == 'bois']
            lignes_bois = set(p['Ligne_Excel'] for p in bois)
            for l_idx in lignes_bois:
                groupe = sorted([p for p in bois if p['Ligne_Excel'] == l_idx], key=lambda x: x['l'], reverse=True)
                while groupe:
                    base = groupe.pop(0)
                    h_actuelle, p_refs = base['H'], [base['Ref']]
                    i = 0
                    while i < len(groupe):
                        if h_actuelle + groupe[i]['H'] <= H_UTILE and groupe[i]['l'] <= base['l']:
                            h_actuelle += groupe[i]['H']
                            p_refs.append(groupe.pop(i)['Ref'])
                        else: i += 1
                    piles.append({"Refs": p_refs, "L": base['L'], "l": base['l'], "Mat": "bois"})

            # --- 3. GESTION DU FER (Jamais empilé) ---
            fer = [p for p in all_palettes if p['Mat'] == 'fer']
            for p in fer:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # --- AFFICHAGE ---
            total_mm = sum([p['L'] if p['l'] > SEUIL_LARGEUR_PLEINE else p['L']/2 for p in piles])
            st.divider()
            st.metric("📏 MÉTRAGE LINÉAIRE TOTAL", f"{total_mm / 1000:.2f} m")
            
            # Répartition Camions
            camions, c_actuel = [], {"libre": L_UTILE, "piles": []}
            for p in piles:
                lg_sol = p['L'] if p['l'] > SEUIL_LARGEUR_PLEINE else p['L']/2
                if lg_sol <= c_actuel["libre"]:
                    c_actuel["piles"].append(p)
                    c_actuel["libre"] -= lg_sol
                else:
                    camions.append(c_actuel)
                    c_actuel = {"libre": L_UTILE - lg_sol, "piles": [p]}
            camions.append(c_actuel)

            for idx, c in enumerate(camions, 1):
                with st.expander(f"🚛 CAMION N°{idx} - {(L_UTILE-c['libre'])/1000:.2f} m", expanded=True):
                    st.table([{"Pile (Bas ⬆️ Haut)": " / ".join(p['Refs']), "Matériau": p['Mat']} for p in c['piles']])
    except Exception as e:
        st.error(f"Erreur : {e}")
