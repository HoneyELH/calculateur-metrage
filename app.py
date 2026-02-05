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

st.set_page_config(page_title="Chargement camion optimisé", layout="wide")
st.title("🚚 Optimisation de chargement (Hako / Toro)")

uploaded_excel = st.sidebar.file_uploader("1️⃣ Base articles (Excel)", type=["xlsx"])
uploaded_pdfs = st.sidebar.file_uploader("2️⃣ Bons de préparation (PDF)", type="pdf", accept_multiple_files=True)

# ---------- FONCTIONS MÉTIER ----------

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
    """
    Transforme les quantités en piles verticales en respectant :
    - empilable ou non
    - hauteur max camion
    - matière (fer = jamais empilé)
    """
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

        # Cas non empilable ou fer : 1 palette = 1 pile
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
            # Empilable : on empile jusqu'à H_UTILE
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
    """
    Calcule le métrage linéaire équivalent comme le ferait un humain :
    - on prend la surface au sol totale des piles
    - on divise par la largeur utile du camion
    """
    surface_totale_mm2 = 0
    for p in piles:
        # On autorise la meilleure orientation : on choisit la plus petite dimension en largeur
        orientations = [(p["L"], p["l"]), (p["l"], p["L"])]
        Lp, lp = min(orientations, key=lambda x: x[1])  # lp = largeur, Lp = longueur
        surface_totale_mm2 += Lp * lp

    longueur_equiv_mm = surface_totale_mm2 / largeur_camion
    return longueur_equiv_mm / 1000.0  # en mètres

def construire_rangees(piles):
    """
    Heuristique pour proposer un plan de chargement lisible :
    rangées gauche/droite, sans chercher l’optimal mathématique.
    """
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
    """
    Donne pour chaque palette :
    - Camion
    - Rangée
    - Côté
    - Niveau dans la pile
    - Référence
    """
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

# ---------- LOGIQUE STREAMLIT ----------

if uploaded_excel and uploaded_pdfs and st.button("🚀 LANCER L’OPTIMISATION"):

    try:
        # 1) Base articles
        df_articles = pd.read_excel(uploaded_excel, sheet_name="Palettes")
        df_refs = construire_base_articles(df_articles)

        # 2) Commandes depuis les PDF
        df_cmd = extraire_commandes(df_refs, uploaded_pdfs)

        if df_cmd.empty:
            st.warning("Aucune référence trouvée dans les PDF avec la base Excel fournie.")
        else:
            df_full = df_cmd.merge(df_refs, on="Ref", how="left")

            # 3) Piles verticales
            piles = construire_piles(df_full)

            # 4) Métrage linéaire équivalent (surface / largeur camion)
            metrage_m = calcul_metrage_par_surface(piles)
            st.subheader(f"📏 Métrage linéaire équivalent : **{metrage_m:.2f} m**")

            # 5) Plan de chargement (rangées) pour donner une idée visuelle
            rangees = construire_rangees(piles)
            total_mm_rangees = sum(r["L_sol"] for r in rangees)

            st.write(f"(Info) Métrage par somme des rangées : {total_mm_rangees/1000:.2f} m")

            st.subheader("🧱 Plan de chargement (rangées / camions)")
            curr_L = 0
            cam_num = 1
            for r in rangees:
                if curr_L + r["L_sol"] > L_UTILE:
                    st.markdown(f"---\n**🚛 Camion {cam_num+1}**")
                    cam_num += 1
                    curr_L = 0
                curr_L += r["L_sol"]
                g = " / ".join(r["G"][0]["Refs"])
                d = " / ".join(r["D"][0]["Refs"]) if r["D"] else "VIDE"
                st.write(
                    f"Camion {cam_num} | Profondeur rangée : {r['L_sol']} mm | "
                    f"Gauche : {g} | Droite : {d}"
                )

            # 6) Détail palette par palette (niveau, côté, camion)
            st.subheader("📋 Détail par palette (camion / rangée / côté / niveau)")
            df_detail = detail_palettes(rangees)
            st.dataframe(df_detail.sort_values(["Camion", "Rangee", "Cote", "PileID", "Niveau"]))

    except Exception as e:
        st.error(f"❌ Erreur : {e}")
