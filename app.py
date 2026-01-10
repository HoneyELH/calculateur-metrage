import streamlit as st
import pandas as pd
import pdfplumber
import re
import math

st.set_page_config(page_title="Hako-Toro : Correction 17m", layout="wide")
st.title("🚚 Planificateur de Chargement - Version Stable")

# --- CONFIGURATION STRICTE ---
L_UTILE = 13600  #
LARG_UTILE = 2460 #
H_UTILE = 2600   # Hauteur plafonnée à 2.6m
SEUIL_DOUBLE = 1230 # Largeur max pour mettre 2 palettes de front

uploaded_excel = st.sidebar.file_uploader("1. Base Excel", type=None)
uploaded_pdfs = st.file_uploader("2. Charger les PDF", type="pdf", accept_multiple_files=True)

if uploaded_excel and uploaded_pdfs:
    try:
        df_articles = pd.read_excel(uploaded_excel, sheet_name='Palettes')
        
        if st.button("🚀 RECALCULER LE MÉTRAGE"):
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

                                    # LOGIQUE DE POSITIONNEMENT RÉELLE
                                    long = float(row['Longueur (mm)'])
                                    larg = float(row['Largeur (mm)'])
                                    
                                    # On ne pivote que si la largeur bloque le passage ( > 1230) 
                                    # et que la longueur est plus petite que la largeur
                                    if larg > SEUIL_DOUBLE and long < larg:
                                        L_sol, l_sol = larg, long
                                    else:
                                        L_sol, l_sol = long, larg

                                    for _ in range(qte):
                                        all_palettes.append({
                                            "Ref": r, "L": L_sol, "l": l_sol, "H": float(row['Hauteur (mm)']),
                                            "Mat": mat, "Dim_Key": f"{L_sol}x{l_sol}"
                                        })
                                    break

            piles = []
            # 1. CARTONS (Mélangeable + Pyramide)
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

            # 2. BOIS (Mêmes dimensions seulement)
            bois_all = [p for p in all_palettes if p['Mat'] == 'bois']
            for d_key in set(p['Dim_Key'] for p in bois_all):
                grp = [p for p in bois_all if p['Dim_Key'] == d_key]
                while grp:
                    base = grp.pop(0)
                    h_act, p_refs = base['H'], [base['Ref']]
                    i = 0
                    while i < len(grp):
                        if h_act + grp[i]['H'] <= H_UTILE:
                            h_act += grp[i]['H']
                            p_refs.append(grp.pop(i)['Ref'])
                        else: i += 1
                    piles.append({"Refs": p_refs, "L": base['L'], "l": base['l'], "Mat": "bois"})

            # 3. FER
            for p in [p for p in all_palettes if p['Mat'] == 'fer']:
                piles.append({"Refs": [p['Ref']], "L": p['L'], "l": p['l'], "Mat": "fer"})

            # CALCUL FINAL DU MÉTRAGE
            total_mm = 0
            for p in piles:
                # Si la largeur au sol est > 1230, elle prend toute la rangée
                if p['l'] > SEUIL_DOUBLE: total_mm += p['L']
                # Sinon on divise par 2 car on en met deux côte à côte
                else: total_mm += (p['L'] / 2)

            st.divider()
            st.metric("📏 MÉTRAGE LINÉAIRE TOTAL", f"{total_mm / 1000:.2f} m")

            # REPARTITION CAMIONS
            camions, c_act = [], {"libre": L_UTILE, "piles": []}
            for p in piles:
                occ = p['L'] if p['l'] > SEUIL_DOUBLE else p['L']/2
                if occ <= c_act["libre"]:
                    c_act["piles"].append(p)
                    c_act["libre"] -= occ
                else:
                    camions.append(c_act)
                    c_act = {"libre": L_UTILE - occ, "piles": [p]}
            camions.append(c_act)

            for idx, c in enumerate(camions, 1):
                occ_m = (L_UTILE - c['libre']) / 1000
                with st.expander(f"🚛 CAMION N°{idx} - {occ_m:.2f} m", expanded=True):
                    st.table([{"Pile": " / ".join(p['Refs']), "L au sol": f"{p['L']} mm", "l au sol": f"{p['l']} mm"} for p in c['piles']])
    except Exception as e:
        st.error(f"Erreur : {e}")
