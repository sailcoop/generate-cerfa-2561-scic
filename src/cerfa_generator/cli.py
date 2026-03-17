"""
Interface en ligne de commande (CLI) pour le générateur CERFA 2561.

Fournit les commandes pour générer les PDFs et envoyer les emails.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .config import Config, setup_logging
from .csv_parser import CSVParserError, count_rows, parse_csv
from .email_sender import send_all_emails, validate_api_key
from .pdf_generator import PDFGeneratorError, generate_all_pdfs


# Groupe de commandes principal
@click.group()
@click.version_option(version=__version__, prog_name="cerfa-generator")
@click.option("--debug", is_flag=True, help="Active le mode debug")
@click.pass_context
def main(ctx: click.Context, debug: bool):
    """
    Générateur de CERFA 2561 pour les souscripteurs SCIC.

    Ce script permet de générer les formulaires CERFA 2561 pré-remplis
    et de les envoyer par email aux souscripteurs via l'API Brevo.
    """
    # Initialiser la configuration
    config = Config.from_env()
    config.debug = debug or config.debug

    # Configurer le logging
    logger = setup_logging(config.log_dir, config.debug)

    # Stocker la config dans le contexte Click
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["logger"] = logger


@main.command()
@click.argument("csv_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--template",
    "-t",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Chemin vers le template PDF (défaut: templates/2561_5243.pdf)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Répertoire de sortie (défaut: output/)",
)
@click.pass_context
def generate(
    ctx: click.Context,
    csv_file: Path,
    template: Optional[Path],
    output: Optional[Path],
):
    """
    Génère les PDF CERFA 2561 à partir d'un fichier CSV.

    CSV_FILE: Chemin vers le fichier CSV contenant les données des souscripteurs.

    Le fichier CSV doit contenir les colonnes suivantes:
    annee, raison_sociale, siret, nom, prenom, date_naissance,
    ville_naissance, code_postal, ville, email, id_template_brevo,
    2TR, 2BH, 2CK
    """
    config: Config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    # Chemins par défaut
    template_path = template or config.template_path
    output_dir = output or config.output_dir

    # Vérifications
    if not template_path.exists():
        click.echo(
            click.style(f"Erreur: Template PDF introuvable: {template_path}", fg="red"),
            err=True,
        )
        click.echo("Placez le fichier template dans templates/2561_5243.pdf", err=True)
        sys.exit(1)

    # Créer le répertoire de sortie
    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"📄 Fichier CSV: {csv_file}")
    click.echo(f"📋 Template PDF: {template_path}")
    click.echo(f"📁 Répertoire de sortie: {output_dir}")

    try:
        # Compter les lignes
        row_count = count_rows(csv_file)
        click.echo(f"📊 Nombre de souscripteurs: {row_count}")

        # Parser le CSV
        souscripteurs = list(parse_csv(csv_file))
        click.echo(f"✅ CSV validé: {len(souscripteurs)} souscripteurs")

        # Générer les PDFs
        with click.progressbar(
            length=len(souscripteurs),
            label="Génération des PDF",
            show_eta=True,
        ) as bar:
            results = []
            for souscripteur in souscripteurs:
                output_path = output_dir / souscripteur.get_pdf_filename()
                try:
                    from .pdf_generator import generate_pdf

                    pdf_path = generate_pdf(souscripteur, template_path, output_path)
                    results.append((souscripteur, pdf_path))
                except PDFGeneratorError as e:
                    logger.error(f"Échec: {souscripteur.nom_complet} - {e}")
                bar.update(1)

        # Résumé
        click.echo()
        click.echo(click.style(f"✅ {len(results)}/{len(souscripteurs)} PDF générés", fg="green"))
        click.echo(f"📁 Les fichiers sont dans: {output_dir.absolute()}")

    except CSVParserError as e:
        click.echo(click.style(f"Erreur CSV: {e}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Erreur inattendue")
        click.echo(click.style(f"Erreur: {e}", fg="red"), err=True)
        sys.exit(1)


@main.command()
@click.argument("csv_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--api-key",
    "-k",
    envvar="BREVO_API_KEY",
    required=True,
    help="Clé API Brevo (ou variable BREVO_API_KEY)",
)
@click.option(
    "--sender-email",
    envvar="SENDER_EMAIL",
    default="contact@windcoop.fr",
    help="Email de l'expéditeur",
)
@click.option(
    "--sender-name",
    envvar="SENDER_NAME",
    default="SCIC WindCoop",
    help="Nom de l'expéditeur",
)
@click.option(
    "--pdf-dir",
    "-p",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Répertoire contenant les PDF (défaut: output/)",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Mode test: simule l'envoi sans envoyer réellement",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Confirme automatiquement l'envoi",
)
@click.pass_context
def send(
    ctx: click.Context,
    csv_file: Path,
    api_key: str,
    sender_email: str,
    sender_name: str,
    pdf_dir: Optional[Path],
    dry_run: bool,
    yes: bool,
):
    """
    Envoie les PDF CERFA par email via l'API Brevo.

    CSV_FILE: Fichier CSV contenant les données des souscripteurs.
    Les PDF correspondants doivent exister dans le répertoire PDF.
    """
    config: Config = ctx.obj["config"]
    logger = ctx.obj["logger"]

    pdf_directory = pdf_dir or config.output_dir

    if dry_run:
        click.echo(click.style("🧪 MODE TEST - Les emails ne seront pas envoyés", fg="yellow"))
    else:
        # Valider la clé API
        click.echo("🔑 Validation de la clé API Brevo...")
        if not validate_api_key(api_key):
            click.echo(click.style("Erreur: Clé API Brevo invalide", fg="red"), err=True)
            sys.exit(1)
        click.echo(click.style("✅ Clé API valide", fg="green"))

    try:
        # Parser le CSV
        souscripteurs = list(parse_csv(csv_file))
        click.echo(f"📊 {len(souscripteurs)} souscripteurs trouvés")

        # Vérifier les PDF
        souscripteurs_pdfs = []
        missing_pdfs = []

        for s in souscripteurs:
            pdf_path = pdf_directory / s.get_pdf_filename()
            if pdf_path.exists():
                souscripteurs_pdfs.append((s, pdf_path))
            else:
                missing_pdfs.append(s)

        if missing_pdfs:
            click.echo(
                click.style(f"⚠️  {len(missing_pdfs)} PDF manquants:", fg="yellow")
            )
            for s in missing_pdfs[:5]:
                click.echo(f"   - {s.get_pdf_filename()}")
            if len(missing_pdfs) > 5:
                click.echo(f"   ... et {len(missing_pdfs) - 5} autres")

        if not souscripteurs_pdfs:
            click.echo(
                click.style("Erreur: Aucun PDF à envoyer", fg="red"),
                err=True,
            )
            click.echo("Générez d'abord les PDF avec la commande 'generate'")
            sys.exit(1)

        click.echo(f"📧 {len(souscripteurs_pdfs)} emails à envoyer")
        click.echo(f"📤 Expéditeur: {sender_name} <{sender_email}>")

        # Confirmation
        if not dry_run and not yes:
            if not click.confirm("Confirmer l'envoi des emails?"):
                click.echo("Annulé.")
                sys.exit(0)

        # Envoi
        with click.progressbar(
            length=len(souscripteurs_pdfs),
            label="Envoi des emails",
            show_eta=True,
        ) as bar:
            results = []
            for souscripteur, pdf_path in souscripteurs_pdfs:
                from .email_sender import send_email

                result = send_email(
                    souscripteur=souscripteur,
                    pdf_path=pdf_path,
                    api_key=api_key,
                    sender_email=sender_email,
                    sender_name=sender_name,
                    dry_run=dry_run,
                )
                results.append(result)
                bar.update(1)

        # Résumé
        click.echo()
        success = sum(1 for r in results if r.success)
        failed = len(results) - success

        if failed == 0:
            click.echo(click.style(f"✅ {success} emails envoyés avec succès", fg="green"))
        else:
            click.echo(click.style(f"⚠️  {success} réussis, {failed} échecs", fg="yellow"))
            for r in results:
                if not r.success:
                    click.echo(f"   ❌ {r.souscripteur.email}: {r.message}")

    except CSVParserError as e:
        click.echo(click.style(f"Erreur CSV: {e}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        logger.exception("Erreur inattendue")
        click.echo(click.style(f"Erreur: {e}", fg="red"), err=True)
        sys.exit(1)


@main.command()
@click.argument("csv_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--template",
    "-t",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Chemin vers le template PDF",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Répertoire de sortie",
)
@click.option(
    "--api-key",
    "-k",
    envvar="BREVO_API_KEY",
    required=True,
    help="Clé API Brevo",
)
@click.option(
    "--sender-email",
    envvar="SENDER_EMAIL",
    default="contact@windcoop.fr",
    help="Email de l'expéditeur",
)
@click.option(
    "--sender-name",
    envvar="SENDER_NAME",
    default="SCIC WindCoop",
    help="Nom de l'expéditeur",
)
@click.option(
    "--dry-run",
    "-n",
    is_flag=True,
    help="Mode test: génère les PDF mais ne les envoie pas",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Confirme automatiquement l'envoi",
)
@click.pass_context
def all(
    ctx: click.Context,
    csv_file: Path,
    template: Optional[Path],
    output: Optional[Path],
    api_key: str,
    sender_email: str,
    sender_name: str,
    dry_run: bool,
    yes: bool,
):
    """
    Génère ET envoie les PDF CERFA en une seule commande.

    Cette commande combine 'generate' et 'send'.
    """
    # Appeler generate
    ctx.invoke(generate, csv_file=csv_file, template=template, output=output)

    # Appeler send
    ctx.invoke(
        send,
        csv_file=csv_file,
        api_key=api_key,
        sender_email=sender_email,
        sender_name=sender_name,
        pdf_dir=output,
        dry_run=dry_run,
        yes=yes,
    )


if __name__ == "__main__":
    main()
