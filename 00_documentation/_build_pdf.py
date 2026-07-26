"""
Genere les PDF de la documentation a partir des fichiers Markdown.

Chaque document .md du dossier produit un .pdf de meme nom. Le Markdown reste
la source unique : les PDF ne sont jamais edites a la main.

Rendu supporte : titres, paragraphes, gras, code inline, liens, citations,
listes a puces et numerotees, tableaux, blocs de code, filets horizontaux.

Usage :
    python 00_documentation/_build_pdf.py
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace

DOSSIER = Path(__file__).resolve().parent
DOCUMENTS = [
    "1_description_projet.md",
    "2_description_donnees.md",
    "3_timeline.md",
    "4_guide_technique.md",
]

# Les polices DejaVu sont livrees avec matplotlib : on les localise via son
# chemin de donnees plutot que par un chemin absolu, qui casserait sur une
# autre machine.
POLICES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"

MARINE = (11, 53, 148)
GRIS = (95, 99, 104)
GRIS_CLAIR = (208, 215, 222)
BLANC = (255, 255, 255)
FOND_CODE = (246, 248, 250)
FOND_CITATION = (242, 242, 242)
FOND_ENTETE = (11, 53, 148)
# Gris tres clair des lignes alternees : doit rester lisible avec du texte noir
FOND_LIGNE = (243, 245, 248)


def decouper_inline(texte: str):
    """Decoupe un texte en segments (contenu, style, lien).

    Styles : "" normal, "B" gras, "C" code monospace.
    """
    motif = re.compile(
        r"\*\*(?P<gras>[^*]+)\*\*"
        r"|`(?P<code>[^`]+)`"
        r"|\[(?P<libelle>[^\]]+)\]\((?P<url>[^)]+)\)"
    )
    segments = []
    position = 0
    for m in motif.finditer(texte):
        if m.start() > position:
            segments.append((texte[position:m.start()], "", None))
        if m.group("gras") is not None:
            segments.append((m.group("gras"), "B", None))
        elif m.group("code") is not None:
            segments.append((m.group("code"), "C", None))
        else:
            segments.append((m.group("libelle"), "L", m.group("url")))
        position = m.end()
    if position < len(texte):
        segments.append((texte[position:], "", None))
    return segments


def nettoyer(texte: str) -> str:
    """Retire le balisage pour les contextes sans rendu enrichi (tableaux)."""
    texte = re.sub(r"\*\*([^*]+)\*\*", r"\1", texte)
    texte = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", texte)
    texte = re.sub(r"`([^`]+)`", r"\1", texte)
    texte = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texte)
    return texte.strip()


class Document(FPDF):
    def __init__(self, titre: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.titre = titre
        self.marge_gauche = 20
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 18, 20)

        self.add_font("DJ", "", str(POLICES / "DejaVuSans.ttf"))
        self.add_font("DJ", "B", str(POLICES / "DejaVuSans-Bold.ttf"))
        self.add_font("DJ", "I", str(POLICES / "DejaVuSans-Oblique.ttf"))
        self.add_font("MONO", "", str(POLICES / "DejaVuSansMono.ttf"))
        self.set_font("DJ", "", 10)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("DJ", "", 7.5)
        self.set_text_color(*GRIS)
        self.cell(0, 6, self.titre, align="R",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*GRIS_CLAIR)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("DJ", "", 7.5)
        self.set_text_color(*GRIS)
        self.cell(0, 8, f"{self.page_no()}", align="C")

    # ------------------------------------------------------------------ #
    # Blocs
    # ------------------------------------------------------------------ #

    def titre_document(self, texte: str):
        self.set_fill_color(*FOND_ENTETE)
        self.rect(0, 0, self.w, 42, style="F")
        self.set_xy(self.l_margin, 14)
        self.set_font("DJ", "B", 19)
        self.set_text_color(255, 255, 255)
        self.multi_cell(self.w - self.l_margin - self.r_margin, 9, texte,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_y(52)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(*BLANC)

    def titre_section(self, texte: str, niveau: int):
        tailles = {2: 14, 3: 11.5, 4: 10.5}
        self.ln(4 if niveau == 2 else 2.5)
        if self.get_y() > self.h - 45:
            self.add_page()
        self.set_font("DJ", "B", tailles.get(niveau, 10.5))
        self.set_text_color(*MARINE)
        self.multi_cell(0, 6.5, nettoyer(texte), align="L",
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if niveau == 2:
            self.set_draw_color(*GRIS_CLAIR)
            self.line(self.l_margin, self.get_y() + 1,
                      self.w - self.r_margin, self.get_y() + 1)
            self.ln(3)
        else:
            self.ln(1.5)
        self.set_text_color(0, 0, 0)

    def paragraphe(self, texte: str, puce: str = ""):
        marge = self.marge_gauche
        if puce:
            self.set_font("DJ", "", 9.5)
            self.set_text_color(0, 0, 0)
            self.set_x(marge + 3)
            self.cell(5, 5.2, puce)
            gauche = marge + 8
        else:
            gauche = marge

        # Le retour a la ligne de write() se cale sur la marge gauche courante :
        # on la deplace le temps de l'item pour que les lignes suivantes
        # restent alignees sous le texte, pas sous la puce.
        self.set_left_margin(gauche)
        self.set_x(gauche)

        for contenu, style, lien in decouper_inline(texte):
            if style == "C":
                self.set_font("MONO", "", 8.6)
                self.set_text_color(180, 40, 60)
            elif style == "B":
                self.set_font("DJ", "B", 9.5)
                self.set_text_color(0, 0, 0)
            elif style == "L":
                self.set_font("DJ", "", 9.5)
                self.set_text_color(*MARINE)
            else:
                self.set_font("DJ", "", 9.5)
                self.set_text_color(0, 0, 0)
            self.write(5.2, contenu, link=lien)

        self.set_text_color(0, 0, 0)
        self.ln(5.2)
        self.set_left_margin(marge)
        self.set_x(marge)
        self.ln(1.6)

    def citation(self, lignes: list[str]):
        """Chaque ligne du bloc citation garde sa propre ligne a l'affichage."""
        contenu = [nettoyer(l) for l in lignes if l.strip()]
        if not contenu:
            return

        largeur = self.w - self.l_margin - self.r_margin
        # Estimation du nombre de lignes apres retour a la ligne automatique
        nb_lignes = sum(max(1, -(-len(l) // 95)) for l in contenu)
        hauteur = 5.0 * nb_lignes + 4

        y = self.get_y()
        self.set_fill_color(*FOND_CITATION)
        self.rect(self.l_margin, y, largeur, hauteur, style="F")
        self.set_fill_color(*MARINE)
        self.rect(self.l_margin, y, 1.2, hauteur, style="F")

        self.set_font("DJ", "I", 9)
        self.set_text_color(*GRIS)
        self.set_y(y + 2)
        for ligne in contenu:
            self.set_x(self.l_margin + 5)
            self.multi_cell(largeur - 8, 5, ligne,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_text_color(0, 0, 0)
        self.set_fill_color(*BLANC)
        self.set_y(y + hauteur)
        self.ln(3)

    def bloc_code(self, lignes: list[str], langage: str = ""):
        if not lignes:
            return
        self.ln(1)
        hauteur = 4.4 * len(lignes) + 5
        if self.get_y() + hauteur > self.h - 25:
            self.add_page()
        y = self.get_y()
        self.set_fill_color(*FOND_CODE)
        self.set_draw_color(*GRIS_CLAIR)
        self.rect(self.l_margin, y, self.w - self.l_margin - self.r_margin,
                  hauteur, style="DF")
        self.set_xy(self.l_margin + 3, y + 2.5)
        self.set_font("MONO", "", 8.2)
        self.set_text_color(40, 45, 55)
        for ligne in lignes:
            self.set_x(self.l_margin + 3)
            self.cell(0, 4.4, ligne[:110],
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(*BLANC)
        self.set_y(y + hauteur)
        self.ln(3)

    def tableau(self, lignes: list[list[str]]):
        if len(lignes) < 2:
            return
        entete, corps = lignes[0], lignes[1:]
        self.ln(1)
        self.set_font("DJ", "", 8.2)
        self.set_text_color(0, 0, 0)
        self.set_draw_color(*GRIS_CLAIR)
        # La couleur de remplissage courante sert de repli si le moteur ignore
        # cell_fill_color : sans cela, un fond fonce defini plus haut rendrait
        # le texte noir des lignes alternees illisible.
        self.set_fill_color(*FOND_LIGNE)

        style_entete = FontFace(
            emphasis="BOLD", color=BLANC, fill_color=MARINE
        )

        with self.table(
            borders_layout="HORIZONTAL_LINES",
            cell_fill_color=FOND_LIGNE,
            cell_fill_mode="ROWS",
            headings_style=style_entete,
            line_height=4.8,
            text_align="LEFT",
            width=self.w - self.l_margin - self.r_margin,
            markdown=True,
        ) as table:
            entete_pdf = table.row()
            for cellule in entete:
                entete_pdf.cell(nettoyer(cellule))
            for ligne in corps:
                r = table.row()
                for cellule in ligne:
                    r.cell(nettoyer(cellule))

        self.set_text_color(0, 0, 0)
        self.set_fill_color(*BLANC)
        self.ln(3)

    def filet(self):
        self.ln(2)
        self.set_draw_color(*GRIS_CLAIR)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)


def convertir(chemin_md: Path) -> Path:
    lignes = chemin_md.read_text(encoding="utf-8").splitlines()

    titre = chemin_md.stem
    for ligne in lignes:
        if ligne.startswith("# "):
            titre = ligne[2:].strip()
            break

    pdf = Document(titre)
    pdf.add_page()
    pdf.titre_document(titre)

    i = 0
    premier_titre_vu = False
    while i < len(lignes):
        ligne = lignes[i]
        depouillee = ligne.strip()

        # Titre principal : deja rendu en couverture
        if depouillee.startswith("# "):
            if not premier_titre_vu:
                premier_titre_vu = True
                i += 1
                continue
            pdf.titre_section(depouillee[2:], 2)
            i += 1
            continue

        if depouillee.startswith("#### "):
            pdf.titre_section(depouillee[5:], 4)
            i += 1
            continue
        if depouillee.startswith("### "):
            pdf.titre_section(depouillee[4:], 3)
            i += 1
            continue
        if depouillee.startswith("## "):
            pdf.titre_section(depouillee[3:], 2)
            i += 1
            continue

        # Bloc de code
        if depouillee.startswith("```"):
            langage = depouillee[3:].strip()
            bloc = []
            i += 1
            while i < len(lignes) and not lignes[i].strip().startswith("```"):
                bloc.append(lignes[i])
                i += 1
            i += 1
            if langage == "mermaid":
                pdf.paragraphe("Diagramme (rendu graphiquement dans la version "
                               "Markdown du document) :")
            pdf.bloc_code(bloc, langage)
            continue

        # Citation
        if depouillee.startswith(">"):
            bloc = []
            while i < len(lignes) and lignes[i].strip().startswith(">"):
                bloc.append(lignes[i].strip().lstrip(">").strip())
                i += 1
            pdf.citation([l for l in bloc if l])
            continue

        # Tableau
        if depouillee.startswith("|"):
            bloc = []
            while i < len(lignes) and lignes[i].strip().startswith("|"):
                cellules = [c.strip() for c in lignes[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") and c for c in cellules):
                    bloc.append(cellules)
                i += 1
            pdf.tableau(bloc)
            continue

        # Filet horizontal
        if depouillee in ("---", "***", "___"):
            pdf.filet()
            i += 1
            continue

        # Liste a puces et liste numerotee.
        # Un item peut s'etendre sur plusieurs lignes : les lignes suivantes
        # indentees en font partie et doivent etre agregees, sinon elles
        # seraient rendues comme des paragraphes revenus a la marge gauche.
        m_num = re.match(r"^(\d+)\.\s+(.*)", depouillee)
        if depouillee.startswith(("- ", "* ")) or m_num:
            if m_num:
                puce, contenu = f"{m_num.group(1)}.", m_num.group(2)
            else:
                puce, contenu = "•", depouillee[2:]
            i += 1
            while (i < len(lignes) and lignes[i].strip()
                   and lignes[i].startswith(("  ", "\t"))
                   and not lignes[i].strip().startswith(("- ", "* ", "|", "```"))
                   and not re.match(r"^\d+\.\s", lignes[i].strip())):
                contenu += " " + lignes[i].strip()
                i += 1
            pdf.paragraphe(contenu, puce=puce)
            continue

        # Ligne vide
        if not depouillee:
            i += 1
            continue

        # Paragraphe : on agrege les lignes consecutives
        bloc = []
        while i < len(lignes) and lignes[i].strip() and not lignes[i].strip().startswith(
            ("#", "|", ">", "```", "- ", "* ", "---")
        ) and not re.match(r"^\d+\.\s", lignes[i].strip()):
            bloc.append(lignes[i].strip())
            i += 1
        pdf.paragraphe(" ".join(bloc))

    sortie = chemin_md.with_suffix(".pdf")
    pdf.output(str(sortie))
    return sortie


def main():
    print(f"Polices : {POLICES}\n")
    for nom in DOCUMENTS:
        chemin = DOSSIER / nom
        if not chemin.exists():
            print(f"  ! introuvable : {nom}")
            continue
        sortie = convertir(chemin)
        ko = sortie.stat().st_size / 1024
        print(f"  {nom:32s} -> {sortie.name:32s} {ko:7.1f} Ko")
    print("\nTermine.")


if __name__ == "__main__":
    main()
