"""
Modèles de données pour le générateur CERFA.

Définit les structures de données pour les souscripteurs et les formulaires CERFA.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class Souscripteur(BaseModel):
    """Modèle représentant un souscripteur de titres participatifs."""

    # Informations sur l'année et la société
    annee: int = Field(..., description="Année fiscale")
    raison_sociale: str = Field(..., description="Raison sociale de la SCIC")
    siret: str = Field(..., description="Numéro SIRET de la SCIC")

    # Informations personnelles du souscripteur
    nom: str = Field(..., description="Nom du souscripteur")
    prenom: str = Field(..., description="Prénom du souscripteur")
    date_naissance: str = Field(..., description="Date de naissance (format YYYYMMDD)")
    ville_naissance: str = Field(..., description="Ville de naissance")

    # Adresse
    code_postal: str = Field(..., description="Code postal")
    ville: str = Field(..., description="Ville de résidence")

    # Contact et template Brevo
    email: EmailStr = Field(..., description="Adresse email")
    id_template_brevo: str = Field(..., description="ID du template Brevo")

    # Montants fiscaux (cases du CERFA)
    montant_2tr: float = Field(..., alias="2TR", description="Montant case 2TR - Revenus")
    montant_2bh: float = Field(..., alias="2BH", description="Montant case 2BH - Revenus déjà soumis")
    montant_2ck: float = Field(..., alias="2CK", description="Montant case 2CK - Crédit d'impôt")

    class Config:
        """Configuration du modèle."""

        populate_by_name = True

    @field_validator("date_naissance")
    @classmethod
    def validate_date_naissance(cls, v: str) -> str:
        """Valide le format de la date de naissance."""
        if len(v) != 8:
            raise ValueError("La date de naissance doit être au format YYYYMMDD")
        try:
            int(v)
        except ValueError:
            raise ValueError("La date de naissance doit contenir uniquement des chiffres")
        return v

    @property
    def date_naissance_formatted(self) -> str:
        """Retourne la date de naissance au format DD/MM/YYYY."""
        return f"{self.date_naissance[6:8]}/{self.date_naissance[4:6]}/{self.date_naissance[:4]}"

    @property
    def nom_complet(self) -> str:
        """Retourne le nom complet du souscripteur."""
        return f"{self.prenom} {self.nom}"

    @property
    def adresse_complete(self) -> str:
        """Retourne l'adresse complète."""
        return f"{self.code_postal} {self.ville}"

    def get_pdf_filename(self) -> str:
        """Génère le nom de fichier PDF pour ce souscripteur."""
        nom_clean = self.nom.replace(" ", "_").upper()
        prenom_clean = self.prenom.replace(" ", "_").upper()
        return f"CERFA_2561_{self.annee}_{nom_clean}_{prenom_clean}.pdf"


class EmailResult(BaseModel):
    """Résultat de l'envoi d'un email."""

    souscripteur: Souscripteur
    success: bool
    message: str
    message_id: Optional[str] = None
