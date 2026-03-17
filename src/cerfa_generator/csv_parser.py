"""
Parseur CSV pour les données des souscripteurs.

Lit et valide les fichiers CSV contenant les informations des souscripteurs.
"""

import csv
import logging
from pathlib import Path
from typing import Generator

from .models import Souscripteur

logger = logging.getLogger("cerfa_generator")


class CSVParserError(Exception):
    """Erreur lors du parsing du fichier CSV."""

    pass


def parse_csv(csv_path: Path) -> Generator[Souscripteur, None, None]:
    """
    Parse un fichier CSV et génère des objets Souscripteur.

    Args:
        csv_path: Chemin vers le fichier CSV

    Yields:
        Objets Souscripteur pour chaque ligne valide

    Raises:
        CSVParserError: Si le fichier est invalide ou ne peut être lu
    """
    if not csv_path.exists():
        raise CSVParserError(f"Le fichier CSV n'existe pas: {csv_path}")

    logger.info(f"Lecture du fichier CSV: {csv_path}")

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # Utiliser le point-virgule comme délimiteur
            reader = csv.DictReader(f, delimiter=";")

            # Vérifier les colonnes requises
            required_columns = {
                "annee",
                "raison_sociale",
                "siret",
                "nom",
                "prenom",
                "date_naissance",
                "ville_naissance",
                "code_postal",
                "ville",
                "email",
                "id_template_brevo",
                "2TR",
                "2BH",
                "2CK",
            }

            if reader.fieldnames is None:
                raise CSVParserError("Le fichier CSV est vide ou mal formaté")

            missing_columns = required_columns - set(reader.fieldnames)
            if missing_columns:
                raise CSVParserError(f"Colonnes manquantes dans le CSV: {missing_columns}")

            # Parser chaque ligne
            for line_num, row in enumerate(reader, start=2):  # start=2 car ligne 1 = en-tête
                try:
                    souscripteur = Souscripteur(
                        annee=int(row["annee"]),
                        raison_sociale=row["raison_sociale"],
                        siret=row["siret"],
                        nom=row["nom"],
                        prenom=row["prenom"],
                        date_naissance=row["date_naissance"],
                        ville_naissance=row["ville_naissance"],
                        code_postal=row["code_postal"],
                        ville=row["ville"],
                        email=row["email"],
                        id_template_brevo=row["id_template_brevo"],
                        **{
                            "2TR": float(row["2TR"]),
                            "2BH": float(row["2BH"]),
                            "2CK": float(row["2CK"]),
                        },
                    )
                    logger.debug(f"Ligne {line_num}: {souscripteur.nom_complet}")
                    yield souscripteur

                except Exception as e:
                    logger.error(f"Erreur ligne {line_num}: {e}")
                    raise CSVParserError(f"Erreur de validation ligne {line_num}: {e}")

    except UnicodeDecodeError:
        raise CSVParserError(
            "Erreur d'encodage du fichier CSV. Assurez-vous qu'il est encodé en UTF-8."
        )
    except csv.Error as e:
        raise CSVParserError(f"Erreur de parsing CSV: {e}")


def count_rows(csv_path: Path) -> int:
    """
    Compte le nombre de lignes de données dans le fichier CSV.

    Args:
        csv_path: Chemin vers le fichier CSV

    Returns:
        Nombre de lignes de données (sans l'en-tête)
    """
    with open(csv_path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # -1 pour l'en-tête
