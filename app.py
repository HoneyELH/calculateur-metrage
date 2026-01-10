import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : 17m Final", layout="wide")
st.title("🚚 Optimisation Finale 17m (Jumelage Intelligent)")

L_UTILE = 13600  
LARG_UTILE = 2460 
H_UTILE = 2600   

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 CALCULER L'OPTIMISATION 17M"):
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
                                            "dim1": float(row['Longueur (mm)']),
                                            "dim2": float(row['Largeur (mm)']), 
                                            "H": float(row['Hauteur (mm)']), "Mat": mat
                                        })
                                    break

            # 1. PILES (Vertical) - On garde les deux dimensions possibles pour l'instant
            piles = []
            # Traitement simplifié pour trouver le meilleur compromis
            for p in all_palettes:
                # Pour les cartons, on privilégie souvent le 800mm en largeur pour doubler
                if p['Mat'] == 'carton' or p['Mat'] == 'bois':
                    # On crée une pile "flexible"
                    l_min = min(p['dim1'], p['dim2'])
                    L_max = max(p['dim1'], p['dim2'])
                    piles.append({"Refs": [p['Ref']], "L": L_max, "l": l_min, "H": p['H'], "Mat": p['Mat']})
                else:
                    # Pour le Fer, souvent trop large, on met le max en largeur
                    piles.append({"Refs": [p['Ref']], "L": min(p['dim1'], p['dim2']), "l": max(p['dim1'], p['dim2']), "H": p['H'], "Mat": p['Mat']})

            # 2. ALGORITHME DE JUMELAGE AVEC ROTATION
            piles = sorted(piles, key=lambda x: x['L'], reverse=True)
            rangees = []
            used = [False] * len(piles)

            for i in range(len(piles)):
                if used[i]: continue
                p1 = piles[i]
                used[i] = True
                p2 = None
                
                # On cherche un partenaire. Si p1 est très large, on essaie de le pivoter 
                # pour voir si ça libère de la place à droite
                for j in range(i + 1, len(piles)):
                    if not used[j]:
                        # Test 1 : p1 tel quel + p2
                        if (p1['l'] + piles[j]['l']) <= LARG_UTILE:
                            p2 = piles[j]; used[j] = True; break
                
                rangees.append({"G": p1, "D": p2, "L_sol": max(p1['L'], p2['L'] if p2 else 0)})

            total_m = sum(r['L_sol'] for r in rangees)
            st.header(f"📏 MÉTRAGE LINÉAIRE TOTAL : {total_m / 1000:.2f} m")

            # Affichage
            curr_L, cam_num = 0, 1
            for r in rangees:
                if curr_L + r['L_sol'] > L_UTILE:
                    cam_num += 1; curr_L = r['L_sol']; st.divider()
                else: curr_L += r['L_sol']
                st.write(f"🚛 Camion {cam_num} | Section {r['L_sol']}mm | G: {'/'.join(r['G']['Refs'])} | D: {('/'.join(r['D']['Refs']) if r['D'] else 'VIDE')}")

    except Exception as e:
        st.error(f"Erreur : {e}")
