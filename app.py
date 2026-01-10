import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : 17m Opti", layout="wide")
st.title("🚚 Planification Haute Densité (17m)")

# --- CONFIGURATION CAMION ---
L_UTILE = 13600  #
LARG_UTILE = 2460 #
H_UTILE = 2600   #

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 CALCULER L'OPTIMISATION"):
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

            # 1. GERBAGE (Règles Bois/Carton)
            piles = []
            # Cartons : Mélangeable + Pyramide
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

            # Bois (Même dimensions uniquement)
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

            # Fer (Seul)
            for p in [p for p in all_palettes if p['Mat'] == 'fer']:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # 2. ALGORITHME DE JUMELAGE (KEY TO 17M)
            # On trie par Longueur pour traiter les plus encombrants d'abord
            piles = sorted(piles, key=lambda x: x['L'], reverse=True)
            plan_final = []
            
            while piles:
                p1 = piles.pop(0)
                pair_found = False
                # On cherche une autre pile p2 qui peut tenir à côté de p1 en largeur
                for i in range(len(piles)):
                    if (p1['l'] + piles[i]['l']) <= LARG_UTILE: # Test pur sur 2460mm
                        p2 = piles.pop(i)
                        plan_final.append({"p1": p1, "p2": p2, "long_sol": max(p1['L'], p2['L'])})
                        pair_found = True
                        break
                if not pair_found:
                    plan_final.append({"p1": p1, "p2": None, "long_sol": p1['L']})

            # 3. AFFICHAGE
            total_metrage_mm = sum(item['long_sol'] for item in plan_final)
            st.divider()
            st.metric("📏 MÉTRAGE LINÉAIRE TOTAL", f"{total_metrage_mm / 1000:.2f} m")
            
            # Répartition camions
            current_camion_m = 0
            camion_num = 1
            st.subheader(f"🚛 CAMION N°{camion_num}")
            
            for item in plan_final:
                if (current_camion_m + item['long_sol']) > L_UTILE:
                    camion_num += 1
                    current_camion_m = item['long_sol']
                    st.divider()
                    st.subheader(f"🚛 CAMION N°{camion_num}")
                else:
                    current_camion_m += item['long_sol']
                
                txt = f"L: {item['long_sol']}mm | Gauche: {' / '.join(item['p1']['Refs'])}"
                if item['p2']:
                    txt += f" | Droite: {' / '.join(item['p2']['Refs'])}"
                st.write(txt)

    except Exception as e:
        st.error(f"Erreur : {e}")
