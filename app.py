import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Hako-Toro : 17m Réels", layout="wide")
st.title("🚚 Optimisation de Longueur (Cible 17m)")

# --- CONFIGURATION CAMION ---
L_UTILE = 13600  
LARG_UTILE = 2460 
H_UTILE = 2600   

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
                                    mat = 'fer' if 'fer' in desc else 'carton' if 'carton' in desc else 'bois' if 'bois' in desc else 'inconnu'

                                    # --- LOGIQUE TERRAIN ---
                                    # Pour gagner de la place, on met la dimension la plus LONGUE dans la LARGEUR du camion.
                                    # Exemple : Un carton de 2250x800 sera posé pour occuper 0.80m de long et 2.25m de large.
                                    d1 = float(row['Longueur (mm)'])
                                    d2 = float(row['Largeur (mm)'])
                                    
                                    largeur_camion = max(d1, d2) # On tente de mettre le plus grand dans la largeur (2.46m)
                                    longueur_camion = min(d1, d2) # Le plus petit occupe le plancher
                                    
                                    # Sécurité : Si même le petit côté ne rentre pas dans les 2.46m (cas rare)
                                    if largeur_camion > LARG_UTILE:
                                        largeur_camion, longueur_camion = longueur_camion, largeur_camion

                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": longueur_camion, "l": largeur_camion, 
                                            "H": float(row['Hauteur (mm)']), "Mat": mat, "Dim": f"{longueur_camion}x{largeur_camion}"
                                        })
                                    break

            # 1. PILES (Vertical)
            piles = []
            # Cartons
            cartons = sorted([p for p in all_palettes if p['Mat'] == 'carton'], key=lambda x: x['l'], reverse=True)
            while cartons:
                base = cartons.pop(0); h, refs = base['H'], [base['Ref']]; i = 0
                while i < len(cartons):
                    if h + cartons[i]['H'] <= H_UTILE and cartons[i]['l'] <= base['l']:
                        h += cartons[i]['H']; refs.append(cartons.pop(i)['Ref'])
                    else: i += 1
                piles.append({"Refs": refs, "L": base['L'], "l": base['l'], "Mat": "carton"})
            # Bois
            bois = [p for p in all_palettes if p['Mat'] == 'bois']
            for dk in set(p['Dim'] for p in bois):
                grp = [p for p in bois if p['Dim'] == dk]
                while grp:
                    base = grp.pop(0); h, refs = base['H'], [base['Ref']]; i = 0
                    while i < len(grp):
                        if h + grp[i]['H'] <= H_UTILE:
                            h += grp[i]['H']; refs.append(grp.pop(i)['Ref'])
                        else: i += 1
                    piles.append({"Refs": refs, "L": base['L'], "l": base['l'], "Mat": "bois"})
            # Fer
            for p in [p for p in all_palettes if p['Mat'] == 'fer']:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # 2. JUMELAGE (Horizontal)
            piles = sorted(piles, key=lambda x: x['L'], reverse=True)
            rangees, uses = [], [False] * len(piles)
            for i in range(len(piles)):
                if uses[i]: continue
                p1 = piles[i]; uses[i] = True; p2 = None
                for j in range(i + 1, len(piles)):
                    if not uses[j] and (p1['l'] + piles[j]['l']) <= LARG_UTILE:
                        p2 = piles[j]; uses[j] = True; break
                rangees.append({"G": p1, "D": p2, "L_sol": max(p1['L'], p2['L']) if p2 else p1['L']})

            # 3. RÉSULTAT
            total_m = sum(r['L_sol'] for r in rangees)
            st.header(f"📏 MÉTRAGE LINÉAIRE TOTAL : {total_m / 1000:.2f} m")

            curr_L, cam_num = 0, 1
            for r in rangees:
                if curr_L + r['L_sol'] > L_UTILE:
                    cam_num += 1; curr_L = r['L_sol']; st.divider()
                else: curr_L += r['L_sol']
                st.write(f"🚛 Camion {cam_num} | Section {r['L_sol']}mm | G: {'/'.join(r['G']['Refs'])} ({r['G']['l']}mm) | D: {('/'.join(r['D']['Refs']) if r['D'] else 'VIDE')}")

    except Exception as e:
        st.error(f"Erreur : {e}")
