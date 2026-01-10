import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : 17m Réels", layout="wide")
st.title("🚚 Planificateur de Chargement - Mode Double Colonne")

# --- CONFIGURATION ---
L_UTILE = 13600  #
LARG_UTILE = 2460 #
H_UTILE = 2600   # Hauteur 2.6m
SEUIL_DOUBLE = 1230 #

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 LANCER LE CHARGEMENT CÔTE À CÔTE"):
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
                                    mat = 'fer' if 'fer' in desc else 'carton' if 'carton' in desc else 'bois' if 'bois' in desc else 'inconnu'

                                    # On garde les dimensions d'origine pour ne pas fausser le métrage
                                    long = float(row['Longueur (mm)'])
                                    larg = float(row['Largeur (mm)'])

                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": long, "l": larg, "H": float(row['Hauteur (mm)']),
                                            "Mat": mat, "Dim_Key": f"{long}x{larg}"
                                        })
                                    break

            # 1. CRÉATION DES PILES (Cartons mixables / Bois mêmes dimensions)
            piles = []
            # Cartons
            cartons = sorted([p for p in all_palettes if p['Mat'] == 'carton'], key=lambda x: x['l'], reverse=True)
            while cartons:
                base = cartons.pop(0)
                h_act, p_refs = base['H'], [base['Ref']]
                i = 0
                while i < len(cartons):
                    if h_act + cartons[i]['H'] <= H_UTILE and cartons[i]['l'] <= base['l']:
                        h_act += cartons[i]['H']
                        p_refs.append(cartons.pop(i)['Ref'])
                    else: i += 1
                piles.append({"Refs": p_refs, "L": base['L'], "l": base['l'], "Mat": "carton"})
            # Bois et Fer
            autres = [p for p in all_palettes if p['Mat'] != 'carton']
            for p in autres: # Simplification pour le test : bois/fer au sol
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": p['Mat']})

            # 2. ALGORITHME DE RÉPARTITION CÔTE À CÔTE
            piles_larges = [p for p in piles if p['l'] > SEUIL_DOUBLE]
            piles_etroites = [p for p in piles if p['l'] <= SEUIL_DOUBLE]
            
            # Calcul du métrage réel
            metrage_piles_larges = sum(p['L'] for p in piles_larges)
            
            # Pour les étroites, on remplit deux colonnes virtuellement
            col1, col2 = 0, 0
            for p in piles_etroites:
                if col1 <= col2: col1 += p['L']
                else: col2 += p['L']
            metrage_piles_etroites = max(col1, col2)
            
            total_mm = metrage_piles_larges + metrage_piles_etroites

            st.divider()
            st.metric("📏 MÉTRAGE LINÉAIRE FINAL", f"{total_mm / 1000:.2f} m")
            
            # 3. AFFICHAGE DES CAMIONS
            st.info(f"Piles larges (Pleine largeur) : {len(piles_larges)} | Piles étroites (Doublables) : {len(piles_etroites)}")
            
            # Répartition simplifiée pour l'affichage
            tout_le_chargement = piles_larges + piles_etroites
            camions, c_act = [], {"libre": L_UTILE, "piles": []}
            for p in tout_le_chargement:
                occ = p['L'] if p['l'] > SEUIL_DOUBLE else p['L']/2
                if occ <= c_act["libre"]:
                    c_act["piles"].append(p)
                    c_act["libre"] -= occ
                else:
                    camions.append(c_act)
                    c_act = {"libre": L_UTILE - occ, "piles": [p]}
            camions.append(c_act)

            for idx, c in enumerate(camions, 1):
                with st.expander(f"🚛 CAMION N°{idx}"):
                    st.table([{"Pile": " / ".join(p['Refs']), "Largeur": p['l']} for p in c['piles']])

    except Exception as e:
        st.error(f"Erreur : {e}")
