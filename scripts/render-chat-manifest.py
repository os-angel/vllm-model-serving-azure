"""Render app-only manifests; validate repository and digest syntax, never apply."""
import argparse
import re
from pathlib import Path

PREFIX = "us-central1-docker.pkg.dev/llmresearch-510422/nemotron-lab-apps/chat"


def render(image):
    if not re.fullmatch(re.escape(PREFIX) + r"@sha256:[0-9a-f]{64}", image):
        raise ValueError(f"Usa {PREFIX}@sha256:<digest publicado de 64 caracteres hexadecimales>.")
    if len(set(image.rsplit(":", 1)[1])) == 1:
        raise ValueError("El digest parece un placeholder; usa el digest real de Artifact Registry.")
    template = Path(__file__).resolve().parents[1] / "k8s/app/chat.yaml.template"
    return template.read_text().replace("${APP_IMAGE}", image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        document = render(args.image)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document)
    print(f"Manifiestos de aplicación preparados: {args.output}; no se aplicaron. Verifica que el digest exista en Artifact Registry antes del despliegue.")


if __name__ == "__main__":
    main()
