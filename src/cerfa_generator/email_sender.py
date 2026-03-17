"""
Module d'envoi d'emails via l'API Brevo.

Envoie les PDF CERFA générés aux souscripteurs via l'API transactionnelle Brevo.
"""

import base64
import logging
from pathlib import Path
from typing import Optional

import requests

from .models import EmailResult, Souscripteur

logger = logging.getLogger("cerfa_generator")

# URL de l'API Brevo
BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailSenderError(Exception):
    """Erreur lors de l'envoi d'email."""

    pass


def encode_pdf_base64(pdf_path: Path) -> str:
    """
    Encode un fichier PDF en base64.

    Args:
        pdf_path: Chemin vers le fichier PDF

    Returns:
        Contenu du PDF encodé en base64
    """
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def send_email(
    souscripteur: Souscripteur,
    pdf_path: Path,
    api_key: str,
    sender_email: str,
    sender_name: str,
    dry_run: bool = False,
) -> EmailResult:
    """
    Envoie un email avec le PDF CERFA en pièce jointe via Brevo.

    Args:
        souscripteur: Données du souscripteur
        pdf_path: Chemin vers le fichier PDF à envoyer
        api_key: Clé API Brevo
        sender_email: Email de l'expéditeur
        sender_name: Nom de l'expéditeur
        dry_run: Si True, simule l'envoi sans réellement envoyer

    Returns:
        EmailResult avec le statut de l'envoi
    """
    logger.info(f"Préparation email pour {souscripteur.nom_complet} ({souscripteur.email})")

    if dry_run:
        logger.info(f"[DRY RUN] Email simulé pour {souscripteur.email}")
        return EmailResult(
            souscripteur=souscripteur,
            success=True,
            message="Email simulé (dry run)",
            message_id="dry-run-no-id",
        )

    if not pdf_path.exists():
        return EmailResult(
            souscripteur=souscripteur,
            success=False,
            message=f"Fichier PDF introuvable: {pdf_path}",
        )

    # Encoder le PDF en base64
    pdf_content = encode_pdf_base64(pdf_path)
    pdf_filename = pdf_path.name

    # Préparer la requête API Brevo
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }

    # Utiliser le template Brevo si spécifié
    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email,
        },
        "to": [
            {
                "email": souscripteur.email,
                "name": souscripteur.nom_complet,
            }
        ],
        "subject": f"Votre IFU CERFA 2561 - Année {souscripteur.annee}",
        "htmlContent": f"""
        <html>
        <body>
            <p>Bonjour {souscripteur.prenom} {souscripteur.nom},</p>
            
            <p>Veuillez trouver ci-joint votre Imprimé Fiscal Unique (IFU) CERFA 2561 
            pour l'année {souscripteur.annee}, relatif à vos titres participatifs 
            dans la {souscripteur.raison_sociale}.</p>
            
            <p>Ce document est à conserver pour votre déclaration de revenus.</p>
            
            <p><strong>Récapitulatif des montants :</strong></p>
            <ul>
                <li>Case 2TR (Revenus de capitaux mobiliers) : {souscripteur.montant_2tr:.2f} €</li>
                <li>Case 2BH (Revenus déjà soumis aux prélèvements sociaux) : {souscripteur.montant_2bh:.2f} €</li>
                <li>Case 2CK (Crédit d'impôt) : {souscripteur.montant_2ck:.2f} €</li>
            </ul>
            
            <p>Cordialement,<br>
            L'équipe {souscripteur.raison_sociale}</p>
        </body>
        </html>
        """,
        "attachment": [
            {
                "content": pdf_content,
                "name": pdf_filename,
            }
        ],
        "tags": ["cerfa-2561", f"annee-{souscripteur.annee}", souscripteur.id_template_brevo],
    }

    try:
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=30)

        if response.status_code == 201:
            message_id = response.json().get("messageId", "unknown")
            logger.info(f"Email envoyé avec succès à {souscripteur.email} (ID: {message_id})")
            return EmailResult(
                souscripteur=souscripteur,
                success=True,
                message="Email envoyé avec succès",
                message_id=message_id,
            )
        else:
            error_msg = f"Erreur API Brevo: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return EmailResult(
                souscripteur=souscripteur,
                success=False,
                message=error_msg,
            )

    except requests.exceptions.RequestException as e:
        error_msg = f"Erreur de connexion: {e}"
        logger.error(error_msg)
        return EmailResult(
            souscripteur=souscripteur,
            success=False,
            message=error_msg,
        )


def send_all_emails(
    souscripteurs_pdfs: list[tuple[Souscripteur, Path]],
    api_key: str,
    sender_email: str,
    sender_name: str,
    dry_run: bool = False,
) -> list[EmailResult]:
    """
    Envoie les emails à tous les souscripteurs.

    Args:
        souscripteurs_pdfs: Liste de tuples (souscripteur, chemin_pdf)
        api_key: Clé API Brevo
        sender_email: Email de l'expéditeur
        sender_name: Nom de l'expéditeur
        dry_run: Si True, simule l'envoi sans réellement envoyer

    Returns:
        Liste des résultats d'envoi
    """
    results = []
    total = len(souscripteurs_pdfs)

    if dry_run:
        logger.warning("MODE TEST ACTIVÉ - Les emails ne seront pas réellement envoyés")

    logger.info(f"Envoi de {total} emails...")

    for i, (souscripteur, pdf_path) in enumerate(souscripteurs_pdfs, start=1):
        logger.info(f"[{i}/{total}] Envoi à {souscripteur.email}")

        result = send_email(
            souscripteur=souscripteur,
            pdf_path=pdf_path,
            api_key=api_key,
            sender_email=sender_email,
            sender_name=sender_name,
            dry_run=dry_run,
        )
        results.append(result)

    # Résumé
    success_count = sum(1 for r in results if r.success)
    logger.info(f"Envoi terminé: {success_count}/{total} emails envoyés avec succès")

    return results


def validate_api_key(api_key: str) -> bool:
    """
    Valide la clé API Brevo en effectuant un appel test.

    Args:
        api_key: Clé API à valider

    Returns:
        True si la clé est valide, False sinon
    """
    headers = {
        "accept": "application/json",
        "api-key": api_key,
    }

    try:
        response = requests.get(
            "https://api.brevo.com/v3/account",
            headers=headers,
            timeout=10,
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False
