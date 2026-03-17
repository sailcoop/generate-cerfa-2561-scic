#!/usr/bin/env python3
"""
Script d'analyse du template PDF CERFA 2561.

Ce script permet d'identifier les champs de formulaire et leurs positions
dans le template PDF.
"""

from pathlib import Path
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, ArrayObject, NameObject

def analyze_pdf(pdf_path: Path):
    """Analyse un PDF et affiche ses champs de formulaire."""
    reader = PdfReader(pdf_path)
    
    print(f"Nombre de pages: {len(reader.pages)}")
    
    # Dimensions de la page
    page = reader.pages[0]
    mediabox = page.mediabox
    print(f"\nDimensions de la page:")
    print(f"  Largeur: {float(mediabox.width):.2f} points ({float(mediabox.width)/72*25.4:.2f} mm)")
    print(f"  Hauteur: {float(mediabox.height):.2f} points ({float(mediabox.height)/72*25.4:.2f} mm)")
    
    # Chercher les champs de formulaire (AcroForm)
    if "/AcroForm" in reader.trailer["/Root"]:
        acroform = reader.trailer["/Root"]["/AcroForm"]
        print("\n=== Champs de formulaire AcroForm ===")
        if "/Fields" in acroform:
            fields = acroform["/Fields"]
            for field in fields:
                field_obj = field.get_object()
                print_field(field_obj)
    else:
        print("\nPas de champs AcroForm détectés")
    
    # Chercher les annotations sur chaque page
    print("\n=== Annotations par page ===")
    for i, page in enumerate(reader.pages):
        print(f"\nPage {i+1}:")
        if "/Annots" in page:
            annots = page["/Annots"]
            for annot in annots:
                annot_obj = annot.get_object()
                annot_type = annot_obj.get("/Subtype", "Unknown")
                rect = annot_obj.get("/Rect", [])
                if rect:
                    rect_vals = [float(r) for r in rect]
                    print(f"  Type: {annot_type}, Rect: {rect_vals}")
                    if "/T" in annot_obj:
                        print(f"    Nom: {annot_obj['/T']}")
        else:
            print("  Pas d'annotations")


def print_field(field_obj, indent=0):
    """Affiche les informations d'un champ de formulaire."""
    prefix = "  " * indent
    field_name = field_obj.get("/T", "Sans nom")
    field_type = field_obj.get("/FT", "Unknown")
    rect = field_obj.get("/Rect", [])
    
    if rect:
        rect_vals = [float(r) for r in rect]
        # Convertir en mm depuis le bas-gauche
        x_mm = rect_vals[0] / 72 * 25.4
        y_mm = rect_vals[1] / 72 * 25.4
        print(f"{prefix}Champ: {field_name}, Type: {field_type}")
        print(f"{prefix}  Position: x={x_mm:.1f}mm, y={y_mm:.1f}mm")
        print(f"{prefix}  Rect (points): {rect_vals}")
    
    # Sous-champs
    if "/Kids" in field_obj:
        for kid in field_obj["/Kids"]:
            print_field(kid.get_object(), indent + 1)


def create_test_grid(template_path: Path, output_path: Path):
    """
    Crée un PDF avec une grille de test superposée sur le template.
    Permet de repérer visuellement les positions.
    """
    import io
    from pypdf import PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import red, blue, gray
    
    reader = PdfReader(template_path)
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    
    # Créer une couche avec grille
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    
    # Grille tous les 10mm
    can.setStrokeColor(gray)
    can.setLineWidth(0.2)
    
    for x in range(0, int(width/mm*10), 10):
        x_pts = x * mm / 10
        can.line(x_pts, 0, x_pts, height)
        if x % 50 == 0:
            can.setFont("Helvetica", 6)
            can.setFillColor(gray)
            can.drawString(x_pts + 1, 5, f"{x}")
    
    for y in range(0, int(height/mm*10), 10):
        y_pts = y * mm / 10
        can.line(0, y_pts, width, y_pts)
        if y % 50 == 0:
            can.setFont("Helvetica", 6)
            can.setFillColor(gray)
            can.drawString(2, y_pts + 1, f"{y}")
    
    # Marquer les zones connues du CERFA 2561
    can.setStrokeColor(red)
    can.setLineWidth(1)
    can.setFont("Helvetica-Bold", 8)
    can.setFillColor(red)
    
    # Zones approximatives basées sur un CERFA standard
    # Ces valeurs devront être ajustées
    zones = [
        # (x_mm, y_mm, label)
        (15, 265, "EN-TETE"),
        (15, 240, "DECLARANT"),
        (15, 200, "BENEFICIAIRE"),
        (15, 150, "REVENUS"),
        (120, 100, "2TR"),
        (120, 80, "2BH"),
        (120, 60, "2CK"),
    ]
    
    for x_mm, y_mm, label in zones:
        x_pts = x_mm * mm
        y_pts = y_mm * mm
        can.circle(x_pts, y_pts, 3, fill=1)
        can.drawString(x_pts + 5, y_pts, label)
    
    can.save()
    packet.seek(0)
    
    # Superposer sur le template
    overlay_reader = PdfReader(packet)
    writer = PdfWriter()
    
    page.merge_page(overlay_reader.pages[0])
    writer.add_page(page)
    
    with open(output_path, "wb") as f:
        writer.write(f)
    
    print(f"Grille de test créée: {output_path}")


if __name__ == "__main__":
    template = Path("templates/2561_5243.pdf")
    
    if template.exists():
        print("=== Analyse du template CERFA 2561 ===\n")
        analyze_pdf(template)
        
        # Créer une grille de test
        output = Path("output/test_grid.pdf")
        create_test_grid(template, output)
    else:
        print(f"Template non trouvé: {template}")
