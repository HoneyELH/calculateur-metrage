import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : 17m Final", layout="wide")
st.title("🚚 Planification Optimisée 17m")

L_UTILE = 13600  
LARG_UTILE = 2460 
H_UTILE = 2600   

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
                                            "Ref": r, 
                                            "d1": float(row['Longueur (mm)']),
                                            "d2": float(row['Largeur (mm)']), 
                                            "H": float(row['Hauteur (mm)']), 
                                            "Mat": mat
                                        })
                                    break

            # 1. GERBAGE (Vertical)
            piles = []
            all_palettes = sorted(all_palettes, key=lambda x: (x['Mat'], x['Ref']))
            while all_palettes:
                base = all_palettes.pop(0)
                h_act = base['H']; p_refs = [base['Ref']]
                i = 0
                while i < len(all_palettes):
                    if all_palettes[i]['Ref'] == base['Ref'] and (h_act + all_palettes[i]['H'] <= H_UTILE):
                        h_act += all_palettes[i]['H']; p_refs.append(all_palettes.pop(i)['Ref'])
                    else: i += 1
                # On définit une orientation par défaut (petite largeur pour doubler)
                piles.append({"Refs": p_refs, "L": max(base['d1'], base['d2']), "l": min(base['d1'], base['d2']), "Mat": base['Mat']})

            # 2. JUMELAGE (Horizontal) - C'est ici qu'on gagne les 3 mètres manquants
            piles = sorted(piles, key=lambda x: x['L'], reverse=True)
            rangees, used = [], [False] * len(piles)
            
            for i in range(len(piles)):
                if used[i]: continue
                p1 = piles[i]
                used[i] = True
                p2 = None
                
                # On cherche une pile à mettre à côté
                for j in range(i + 1, len(piles)):
                    if not used[j] and (p1['l'] + piles[j]['l'] <= LARG_UTILE):
                        p2 = piles[j]; used[j] = True; break
                
                rangees.append({"G": p1, "D": p2, "L_sol": max(p1['L'], p2['L'] if p2 else 0)})

            # 3. AFFICHAGE
            total_m = sum(r['L_sol'] for r in rangees)
            st.header(f"📏 MÉTRAGE LINÉAIRE TOTAL : {total_m / 1000:.2f} m")

            curr_L, cam_num = 0, 1
            for r in rangees:
                if curr_L + r['L_sol'] > L_UTILE:
                    cam_num += 1; curr_L = r['L_sol']; st.divider()
                else: curr_L += r['L_sol']
                st.write(f"🚛 Camion {cam_num} | Section {r['L_sol']}mm | G: {' / '.join(r['G']['Refs'])} ({r['G']['l']}mm) | D: {(' / '.join(r['D']['Refs']) + ' (' + str(r['D']['l']) + 'mm)') if r['D'] else 'VIDE'}")

    except Exception as e:
        st.error(f"Erreur : {e}")
