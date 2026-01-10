import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : 17m Fix", layout="wide")
st.title("🚚 Plan de Chargement (Optimisation Côte à Côte)")

# --- CONFIGURATION CAMION ---
L_UTILE = 13600  #
LARG_UTILE = 2460 #
H_UTILE = 2600   #

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 GÉNÉRER LE PLAN 17M"):
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
                                            "Mat": mat, "Dim": f"{row['Longueur (mm)']}x{row['Largeur (mm)']}"
                                        })
                                    break

            # 1. FORMATION DES PILES (Vertical)
            piles = []
            # Cartons
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
            # Bois (Même dimensions)
            bois = [p for p in all_palettes if p['Mat'] == 'bois']
            for dk in set(p['Dim'] for p in bois):
                grp = [p for p in bois if p['Dim'] == dk]
                while grp:
                    base = grp.pop(0)
                    h, refs = base['H'], [base['Ref']]
                    i = 0
                    while i < len(grp):
                        if h + grp[i]['H'] <= H_UTILE:
                            h += grp[i]['H']; refs.append(grp.pop(i)['Ref'])
                        else: i += 1
                    piles.append({"Refs": refs, "L": base['L'], "l": base['l'], "Mat": "bois"})
            # Fer
            for p in [p for p in all_palettes if p['Mat'] == 'fer']:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # 2. JUMELAGE RÉEL (Horizontal)
            piles = sorted(piles, key=lambda x: x['L'], reverse=True)
            rangées = []
            utilisés = [False] * len(piles)

            for i in range(len(piles)):
                if utilisés[i]: continue
                p1 = piles[i]
                utilisés[i] = True
                paire_trouvée = None
                
                # Chercher une pile pour mettre à côté
                for j in range(i + 1, len(piles)):
                    if not utilisés[j] and (p1['l'] + piles[j]['l']) <= LARG_UTILE:
                        paire_trouvée = piles[j]
                        utilisés[j] = True
                        break
                
                rangées.append({
                    "G": p1, 
                    "D": paire_trouvée, 
                    "L_sol": max(p1['L'], paire_trouvée['L']) if paire_trouvée else p1['L']
                })

            # 3. RÉPARTITION CAMIONS
            total_metrage = sum(r['L_sol'] for r in rangées)
            st.metric("📏 MÉTRAGE LINÉAIRE TOTAL", f"{total_metrage / 1000:.2f} m")

            current_L = 0
            cam_num = 1
            for r in rangées:
                if current_L + r['L_sol'] > L_UTILE:
                    cam_num += 1
                    current_L = r['L_sol']
                else:
                    current_L += r['L_sol']
                
                with st.expander(f"🚛 CAMION N°{cam_num} | Section de {r['L_sol']} mm"):
                    col_g, col_d = st.columns(2)
                    col_g.markdown(f"**GAUCHE** : {' / '.join(r['G']['Refs'])} ({r['G']['l']}mm)")
                    if r['D']:
                        col_d.markdown(f"**DROITE** : {' / '.join(r['D']['Refs'])} ({r['D']['l']}mm)")
                    else:
                        col_d.write("VIDE")

    except Exception as e:
        st.error(f"Erreur : {e}")
