#!/usr/bin/env python3
"""
Script de calibration interactive pour le CERFA 2561.

Crée une série de PDFs avec des marqueurs à différentes positions
pour permettre de trouver les coordonnées exactes.

Usage:
    python scripts/find_positions.py
    
Ouvrir les PDFs générés et noter les bonnes coordonnées.
"""

import io
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, black


def create_horizontal_ruler(template_path: Path, output_path: Path, y_mm: float):
    """Crée un PDF avec une règle horizontale à la hauteur Y spécifiée."""
    reader = PdfReader(template_path)
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    
    y = y_mm * mm
    
    # Ligne horizontale rouge
    can.setStrokeColor(red)
    can.setLineWidth(0.5)
    can.line(0, y, width, y)
    
    # Graduations tous les 10mm
    can.setFont("Helvetica", 6)
    can.setFillColor(red)
    for x in range(0, 210, 10):
        x_pts = x * mm
        can.line(x_pts, y - 2*mm, x_pts, y + 2*mm)
        can.drawString(x_pts + 0.5*mm, y + 3*mm, f"{x}")
    
    # Indication Y
    can.setFont("Helvetica-Bold", 8)
    can.drawString(5*mm, y - 5*mm, f"Y = {y_mm} mm")
    
    can.save()
    packet.seek(0)
    
    overlay = PdfReader(packet)
    writer = PdfWriter()
    template_page = PdfReader(template_path).pages[0]
    template_page.merge_page(overlay.pages[0])
    writer.add_page(template_page)
    
    with open(output_path, "wb") as f:
        writer.write(f)


def create_full_grid_pdf(template_path: Path, output_path: Path):
    """
    Crée un PDF avec une grille complète et des marqueurs pour chaque zone.
    """
    reader = PdfReader(template_path)
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    
    # Grille fine tous les 5mm en gris clair
    from reportlab.lib.colors import Color
    can.setStrokeColor(Color(0.85, 0.85, 0.85))
    can.setLineWidth(0.1)
    
    for x in range(0, 220, 5):
        can.line(x*mm, 0, x*mm, height)
    for y in range(0, 300, 5):
        can.line(0, y*mm, width, y*mm)
    
    # Graduations tous les 10mm plus visibles
    can.setStrokeColor(Color(0.7, 0.7, 0.7))
    can.setLineWidth(0.2)
    
    for x in range(0, 220, 10):
        can.line(x*mm, 0, x*mm, height)
    for y in range(0, 300, 10):
        can.line(0, y*mm, width, y*mm)
    
    # Annotations des coordonnées tous les 20mm
    can.setFont("Helvetica", 5)
    can.setFillColor(Color(0.4, 0.4, 0.4))
    
    for x in range(0, 220, 20):
        can.drawString(x*mm + 0.5*mm, 3*mm, f"{x}")
        can.drawString(x*mm + 0.5*mm, 290*mm, f"{x}")
    
    for y in range(0, 300, 20):
        can.drawString(2*mm, y*mm + 0.5*mm, f"{y}")
        can.drawString(200*mm, y*mm + 0.5*mm, f"{y}")
    
    can.save()
    packet.seek(0)
    
    overlay = PdfReader(packet)
    writer = PdfWriter()
    template_page = PdfReader(template_path).pages[0]
    template_page.merge_page(overlay.pages[0])
    writer.add_page(template_page)
    
    with open(output_path, "wb") as f:
        writer.write(f)
    
    print(f"✅ Grille complète: {output_path}")


def create_zone_identifiers(template_path: Path, output_path: Path):
    """
    Crée un PDF avec des identifiants de zone basés sur l'analyse du texte.
    """
    reader = PdfReader(template_path)
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    
    from reportlab.lib.colors import Color
    
    # Zones identifiées d'après l'extraction de texte
    # Structure CERFA 2561:
    # - Haut: En-tête avec année (ligne 0-2)
    # - Section PAYEUR: lignes 5-16
    # - Section BÉNÉFICIAIRE: lignes 17-23
    # - Section MONTANTS: lignes 24-80
    
    zones = [
        # (y_min_mm, y_max_mm, label, color)
        (275, 290, "EN-TÊTE / ANNÉE", Color(0.9, 0.9, 0.5, alpha=0.3)),
        (235, 275, "PAYEUR (ZM, ZS...)", Color(0.5, 0.9, 0.5, alpha=0.3)),
        (190, 235, "BÉNÉFICIAIRE (ZC, ZD...)", Color(0.5, 0.5, 0.9, alpha=0.3)),
        (20, 190, "MONTANTS (2TR, 2BH, 2CK...)", Color(0.9, 0.5, 0.5, alpha=0.3)),
    ]
    
    for y_min, y_max, label, color in zones:
        can.setFillColor(color)
        can.rect(5*mm, y_min*mm, 200*mm, (y_max-y_min)*mm, fill=1, stroke=0)
        
        can.setFillColor(black)
        can.setFont("Helvetica-Bold", 8)
        can.drawString(10*mm, (y_min + 2)*mm, f"{label} (Y: {y_min}-{y_max}mm)")
    
    # Points de repère clés pour les cases 2XX
    key_positions = [
        # (x_mm, y_mm, label)
        (180, 185, "2TR?"),
        (180, 157, "2BH?"),
        (180, 123, "2CK?"),
    ]
    
    for x, y, label in key_positions:
        can.setStrokeColor(red)
        can.setFillColor(red)
        can.circle(x*mm, y*mm, 3, fill=1)
        can.setFont("Helvetica", 6)
        can.drawString(x*mm + 4, y*mm, f"{label} ({x},{y})")
    
    can.save()
    packet.seek(0)
    
    overlay = PdfReader(packet)
    writer = PdfWriter()
    template_page = PdfReader(template_path).pages[0]
    template_page.merge_page(overlay.pages[0])
    writer.add_page(template_page)
    
    with open(output_path, "wb") as f:
        writer.write(f)
    
    print(f"✅ Zones identifiées: {output_path}")


if __name__ == "__main__":
    template = Path("templates/2561_5243.pdf")
    
    if not template.exists():
        print(f"❌ Template non trouvé: {template}")
        exit(1)
    
    output_dir = Path("output/calibration")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Grille complète
    create_full_grid_pdf(template, output_dir / "grille_complete.pdf")
    
    # 2. Zones identifiées
    create_zone_identifiers(template, output_dir / "zones.pdf")
    
    # 3. Règles horizontales à différentes hauteurs pour les montants
    heights = [185, 170, 157, 145, 130, 123, 110, 95, 80, 65, 50]
    for h in heights:
        create_horizontal_ruler(template, output_dir / f"ruler_y{h}.pdf", h)
        print(f"✅ Règle Y={h}mm: {output_dir / f'ruler_y{h}.pdf'}")
    
    print(f"\n📂 Fichiers de calibration dans: {output_dir}")
    print("\n📋 Instructions:")
    print("1. Ouvrir grille_complete.pdf pour voir les coordonnées")
    print("2. Ouvrir zones.pdf pour voir les sections du formulaire")
    print("3. Utiliser les rulers pour trouver les Y exacts des cases 2TR, 2BH, 2CK")
    print("4. Mettre à jour les positions dans pdf_generator.py")
