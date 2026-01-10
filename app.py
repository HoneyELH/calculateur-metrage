import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : 17m Final", layout="wide")
st.title("🚚 Optimisation de Chargement (Capacité Max)")

# --- PARAMÈTRES RÉELS DU CAMION ---
L_UTILE = 13600  #
LARG_UTILE = 2460 #
H_UTILE = 2600   # Hauteur utile

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 FORCER LE CALCUL À 17M"):
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

                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": float(row['Longueur (mm)']),
                                            "l": float(row['Largeur (mm)']), "H": float(row['Hauteur (mm)']),
                                            "Mat": mat, "Dim_Key": f"{row['Longueur (mm)']}x{row['Largeur (mm)']}"
                                        })
                                    break

            # 1. GERBAGE
            piles = []
            # Cartons (Mixables + Pyramide)
            cartons = sorted([p for p in all_palettes if p['Mat'] == 'carton'], key=lambda x: x['l'], reverse=True)
            while cartons:
                base = cartons.pop(0)
                h, refs = base['H'], [base['Ref']]
                i = 0
                while i < len(cartons):
                    if h + cartons[i]['H'] <= H_UTILE and cartons[i]['l'] <= base['l']:
                        h += cartons[i]['H']; refs.append(cartons.pop(i)['Ref'])
                    else: i += 1
                piles.append({"Refs": refs, "L": base['L'], "l": base['l'], "Mat": "carton"})

            # Bois (Mêmes dimensions seulement)
            bois = [p for p in all_palettes if p['Mat'] == 'bois']
            for dk in set(p['Dim_Key'] for p in bois):
                grp = [p for p in bois if p['Dim_Key'] == dk]
                while grp:
                    base = grp.pop(0)
                    h, refs = base['H'], [base['Ref']]
                    i = 0
                    while i < len(grp):
                        if h + grp[i]['H'] <= H_UTILE:
                            h += grp[i]['H']; refs.append(grp.pop(i)['Ref'])
                        else: i += 1
                    piles.append({"Refs": refs, "L": base['L'], "l": base['l'], "Mat": "bois"})

            # Fer (Toujours seul)
            for p in [p for p in all_palettes if p['Mat'] == 'fer']:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # 2. LOGIQUE DE CALCUL DU MÉTRAGE (CÔTE À CÔTE SANS MARGE)
            # On trie les piles par longueur décroissante
            piles = sorted(piles, key=lambda x: x['L'], reverse=True)
            
            total_metrage_mm = 0
            while piles:
                p1 = piles.pop(0)
                # Est-ce qu'une autre pile peut loger à côté de p1 ?
                trouvee = False
                for i in range(len(piles)):
                    if (p1['l'] + piles[i]['l']) <= LARG_UTILE: # Pas de marge, test pur
                        p2 = piles.pop(i)
                        total_metrage_mm += max(p1['L'], p2['L'])
                        trouvee = True
                        break
                if not trouvee:
                    total_metrage_mm += p1['L']

            st.divider()
            st.metric("📏 MÉTRAGE LINÉAIRE TOTAL", f"{total_metrage_mm / 1000:.2f} m")
            st.divider()
            st.info(f"Capacité Camion : {L_UTILE/1000} m | Largeur Utile : {LARG_UTILE} mm")

    except Exception as e:
        st.error(f"Erreur : {e}")
