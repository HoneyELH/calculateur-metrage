import streamlit as st
import pandas as pd
import pdfplumber
import re

# =========================
# CONFIG CAMION
# =========================
L_UTILE = 13600   # mm
LARG_UTILE = 2460 # mm
H_UTILE = 2700    # mm

# =========================
# INTERFACE PREMIUM
# =========================
st.set_page_config(page_title="Chargement Premium", layout="wide")

st.markdown("""
<style>
    .title {
        font-size: 40px;
        font-weight: 900;
        text-align: center;
        color: #222;
        margin-bottom: 30px;
    }
    .card {
        padding: 20px;
        border-radius: 12px;
        background: white;
        border: 1px solid #ddd;
        margin-bottom: 20px;
    }
    .metric {
        font-size: 28px;
        font-weight: 700;
    }
    .sub {
        font-size: 16px;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>🚚 Chargement Camion — Interface Premium</div>", unsafe_allow_html=True)

# =========================
# SIDEBAR
# =========================
st.sidebar.header("📥 Import des fichiers")
uploaded_excel = st.sidebar.file_uploader("Base articles (Excel)", type=["xlsx"])
uploaded_pdfs = st.sidebar.file_uploader("Bons PDF", type=["pdf"], accept_multiple_files=True)

# =========================
# FONCTIONS MÉTIER
# =========================

def detect_matiere(desc: str) -> str:
    d = desc.lower()
    if "fer" in d:
        return "fer"
    if "carton" in d:
        return "carton"
    if "bois" in d:
        return "bois"
    return "inconnu"

def construire_base_articles(df_articles: pd.DataFrame) -> pd.DataFrame:
    lignes = []
    for _, row in df_articles.iterrows():
        refs = [r.strip() for r in str(row["Référence"]).split("/")]
        for r in refs:
            lignes.append({
                "Ref": r,
                "Description": row["Description"],
                "Largeur_mm": float(row["Largeur (mm)"]),
                "Longueur_mm": float(row["Longueur (mm)"]),
                "Hauteur_mm": float(row["Hauteur (mm)"]),
                "Poids_kg": float(row["Poids unitaire (kg)"]),
                "Empilable": str(row["Empilable (Oui/Non)"]).strip().lower().startswith("o"),
                "Matiere": detect_matiere(str(row["Description"]))
            })
    return pd.DataFrame(lignes)

def extraire_commandes(df_refs: pd.DataFrame, uploaded_pdfs) -> pd.DataFrame:
    lignes_cmd = []
    for pdf_file in uploaded_pdfs:
        with pdfplumber.open(pdf_file) as pdf:
            texte = "\n".join(p.extract_text() for p in pdf.pages if p.extract_text())

        for ligne in texte.split("\n"):
            for _, art in df_refs.iterrows():
                r = art["Ref"]
                if len(r) > 3 and r in ligne:
                    nums = re.findall(r"\b\d+\b", ligne)
                    qte = int(nums[-1]) if nums else 1
                    lignes_cmd.append({
                        "Ref": r,
                        "Quantite": qte,
                        "Ligne_PDF": ligne
                    })
                    break
    return pd.DataFrame(lignes_cmd)

def construire_piles(df_full: pd.DataFrame):
    piles = []
    pile_id = 0

    for _, art in df_full.iterrows():
        ref = art["Ref"]
        qte = int(art["Quantite"])
        L = float(art["Longueur_mm"])
        l = float(art["Largeur_mm"])
        h = float(art["Hauteur_mm"])
        empilable = bool(art["Empilable"])
        mat = art["Matiere"]

        if (not empilable) or mat == "fer":
            for _ in range(qte):
                pile_id += 1
                piles.append({
                    "PileID": pile_id,
                    "Refs": [ref],
                    "Mat": mat,
                    "L": L,
                    "l": l,
                    "H": h
                })
        else:
            reste = qte
            while reste > 0:
                h_courant = 0
                refs_pile = []
                while reste > 0 and h_courant + h <= H_UTILE:
                    h_courant += h
                    refs_pile.append(ref)
                    reste -= 1
                pile_id += 1
                piles.append({
                    "PileID": pile_id,
                    "Refs": refs_pile,
                    "Mat": mat,
                    "L": L,
                    "l": l,
                    "H": h_courant
                })

    return piles

def calcul_metrage_par_surface(piles, largeur_camion=LARG_UTILE) -> float:
    surface_totale_mm2 = 0
    for p in piles:
        orientations = [(p["L"], p["l"]), (p["l"], p["L"])]
        Lp, lp = min(orientations, key=lambda x: x[1])
        surface_totale_mm2 += Lp * lp

    longueur_equiv_mm = surface_totale_mm2 / largeur_camion
    return longueur_equiv_mm / 1000.0

def construire_rangees(piles):
    rangees = []
    restantes = piles.copy()
    restantes.sort(key=lambda p: max(p["L"], p["l"]), reverse=True)

    while restantes:
        p1 = restantes.pop(0)
        orientations_p1 = [(p1["L"], p1["l"]), (p1["l"], p1["L"])]
        L1, l1 = min(orientations_p1, key=lambda x: x[1])

        if p1["Mat"] == "fer":
            rangees.append({"G": (p1, L1, l1), "D": None, "L_sol": L1})
            continue

        best_idx = None
        best_L_sol = None
        best_conf = None

        for idx, p2 in enumerate(restantes):
            if p2["Mat"] == "fer":
                continue
            for (L2, l2) in [(p2["L"], p2["l"]), (p2["l"], p2["L"])]:
                if l1 + l2 <= LARG_UTILE:
                    L_sol = max(L1, L2)
                    if (best_L_sol is None) or (L_sol < best_L_sol):
                        best_L_sol = L_sol
                        best_idx = idx
                        best_conf = (L2, l2)

        if best_idx is not None:
            p2 = restantes.pop(best_idx)
            L2, l2 = best_conf
            rangees.append({"G": (p1, L1, l1), "D": (p2, L2, l2), "L_sol": best_L_sol})
        else:
            rangees.append({"G": (p1, L1, l1), "D": None, "L_sol": L1})

    return rangees

def detail_palettes(rangees):
    lignes = []
    curr_L = 0
    cam_num = 1
    rangee_num = 0

    for r in rangees:
        if curr_L + r["L_sol"] > L_UTILE:
            cam_num += 1
            curr_L = 0
            rangee_num = 0
        curr_L += r["L_sol"]
        rangee_num += 1

        for cote, label in [("G", "Gauche"), ("D", "Droite")]:
            bloc = r[cote]
            if bloc is None:
                continue
            pile, Lp, lp = bloc
            refs = pile["Refs"]
            for niveau, ref in enumerate(refs, start=1):
                lignes.append({
                    "Camion": cam_num,
                    "Rangee": rangee_num,
                    "Cote": label,
                    "PileID": pile["PileID"],
                    "Niveau": niveau,
                    "Ref": ref
                })
    return pd.DataFrame(lignes)

# =========================
# MAIN LOGIC
# =========================

if uploaded_excel and uploaded_pdfs and st.button("Analyser"):

    df_articles = pd.read_excel(uploaded_excel, sheet_name="Palettes")
    df_refs = construire_base_articles(df_articles)
    df_cmd = extraire_commandes(df_refs, uploaded_pdfs)

    if df_cmd.empty:
        st.error("Aucune référence trouvée dans les PDF.")
    else:
        df_full = df_cmd.merge(df_refs, on="Ref", how="left")

        piles = construire_piles(df_full)
        metrage = calcul_metrage_par_surface(piles)
        rangees = construire_rangees(piles)

        # =========================
        # DASHBOARD
        # =========================
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='card'><div class='metric'>{metrage:.2f} m</div><div class='sub'>Métrage réel</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='card'><div class='metric'>{len(piles)}</div><div class='sub'>Piles créées</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='card'><div class='metric'>{len(rangees)}</div><div class='sub'>Rangées</div></div>", unsafe_allow_html=True)

        # =========================
        # PLAN DE CHARGEMENT
        # =========================
        st.markdown("<div class='card'><h3>🧱 Plan de chargement</h3></div>", unsafe_allow_html=True)

        curr_L = 0
        cam_num = 1
        for r in rangees:
            if curr_L + r["L_sol"] > L_UTILE:
                st.markdown(f"<div class='card'><h4>🚛 Camion {cam_num+1}</h4></div>", unsafe_allow_html=True)
                cam_num += 1
                curr_L = 0
            curr_L += r["L_sol"]

            g = " / ".join(r["G"][0]["Refs"])
            d = " / ".join(r["D"][0]["Refs"]) if r["D"] else "VIDE"

            st.write(f"Camion {cam_num} | Profondeur : {r['L_sol']} mm | Gauche : {g} | Droite : {d}")

        # =========================
        # TABLEAU DÉTAILLÉ
        # =========================
        st.markdown("<div class='card'><h3>📋 Détail palette par palette</h3></div>", unsafe_allow_html=True)
        df_detail = detail_palettes(rangees)
        st.dataframe(df_detail.sort_values(["Camion", "Rangee", "Cote", "PileID", "Niveau"]))
