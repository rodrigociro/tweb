#!/usr/bin/env python3
"""Valida data/entornos.yaml y genera el sitio estático en _site/.

Uso:
    python scripts/build.py [--data data/entornos.yaml] [--out _site]

Sale con código 1 (sin generar nada) si hay errores de validación.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: falta PyYAML. Instálalo con: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent

REQUIRED = ("nombre", "entorno", "tipo")
ENTORNOS = ("dev", "pre", "pro")
TIPOS = ("aws", "openshift")
STRING_FIELDS = ("nombre", "aplicacion", "cuenta_aws", "region", "cluster",
                 "api", "consola", "argocd", "confluence", "notas")
LIST_FIELDS = ("namespaces", "tags")
URL_FIELDS = ("api", "consola", "argocd", "confluence")

# Palabras que delatan un posible secreto.
SECRET_WORDS = r"pass(?:word|wd)|contrase[ñn]a|pwd|secret|token|api[_-]?key|private[_-]?key|credential"
# Nombre de campo sospechoso (p. ej. "password", "db_secret", "apiKey").
SECRET_KEY_RE = re.compile(rf"(?:{SECRET_WORDS})", re.IGNORECASE)
# Valor del tipo "password: xxx", "token=xxx", "apikey -> xxx".
SECRET_ASSIGN_RE = re.compile(rf"(?:{SECRET_WORDS})\s*(?:[:=]|->)\s*\S", re.IGNORECASE)
# Claves de acceso AWS (AKIA = permanentes, ASIA = temporales).
AWS_KEY_RE = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")
# Clave privada PEM.
PEM_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")


def iter_values(value, path):
    """Recorre recursivamente un valor devolviendo (ruta, clave, valor_hoja)."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield f"{path}.{k}", str(k), None
            yield from iter_values(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from iter_values(v, f"{path}[{i}]")
    else:
        yield path, None, value


def check_secrets(entry: dict, where: str) -> list[str]:
    errors = []
    for path, key, value in iter_values(entry, where):
        if key is not None:
            if SECRET_KEY_RE.search(key):
                errors.append(f"{path}: el nombre del campo parece un secreto ('{key}')")
            continue
        if not isinstance(value, str):
            continue
        if AWS_KEY_RE.search(value):
            errors.append(f"{path}: contiene una posible clave de acceso AWS (AKIA/ASIA...)")
        if PEM_RE.search(value):
            errors.append(f"{path}: contiene una clave privada")
        if SECRET_ASSIGN_RE.search(value):
            errors.append(f"{path}: parece contener un secreto (password/secret/token/apikey...)")
    return errors


def validate(data) -> list[str]:
    if data is None:
        return ["el fichero está vacío"]
    if not isinstance(data, list):
        return ["la raíz del YAML debe ser una lista de entornos"]

    errors: list[str] = []
    seen: dict[str, int] = {}
    for i, entry in enumerate(data, start=1):
        label = f"entrada #{i}"
        if not isinstance(entry, dict):
            errors.append(f"{label}: debe ser un objeto clave/valor")
            continue
        if isinstance(entry.get("nombre"), str) and entry["nombre"].strip():
            label = f"entrada #{i} ('{entry['nombre']}')"

        for field in REQUIRED:
            v = entry.get(field)
            if v is None or (isinstance(v, str) and not v.strip()):
                errors.append(f"{label}: falta el campo obligatorio '{field}'")

        if entry.get("entorno") is not None and entry["entorno"] not in ENTORNOS:
            errors.append(f"{label}: 'entorno' debe ser uno de {'|'.join(ENTORNOS)} "
                          f"(es '{entry['entorno']}')")
        if entry.get("tipo") is not None and entry["tipo"] not in TIPOS:
            errors.append(f"{label}: 'tipo' debe ser uno de {'|'.join(TIPOS)} "
                          f"(es '{entry['tipo']}')")

        for field in STRING_FIELDS:
            if field in entry and entry[field] is not None and not isinstance(entry[field], str):
                hint = ' (ponlo entre comillas, p. ej. "012345678901")' if field == "cuenta_aws" else ""
                errors.append(f"{label}: '{field}' debe ser un texto{hint}")
        if isinstance(entry.get("cuenta_aws"), str) and not re.fullmatch(r"\d{12}", entry["cuenta_aws"]):
            errors.append(f"{label}: 'cuenta_aws' debe tener 12 dígitos")

        for field in LIST_FIELDS:
            if field in entry and entry[field] is not None:
                v = entry[field]
                if not isinstance(v, list) or not all(isinstance(x, (str, int, float)) for x in v):
                    errors.append(f"{label}: '{field}' debe ser una lista de textos")

        for field in URL_FIELDS:
            v = entry.get(field)
            if isinstance(v, str) and not re.match(r"https?://", v):
                errors.append(f"{label}: '{field}' debe ser una URL http(s)://")

        name = entry.get("nombre")
        if isinstance(name, str) and name.strip():
            key = name.strip().lower()
            if key in seen:
                errors.append(f"{label}: nombre duplicado (igual que la entrada #{seen[key]})")
            else:
                seen[key] = i

        errors.extend(check_secrets(entry, label))
    return errors


def to_jsonable(value):
    """Convierte fechas u otros tipos que YAML pueda generar a texto."""
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", default=str(ROOT / "data" / "entornos.yaml"))
    ap.add_argument("--out", default=str(ROOT / "_site"))
    args = ap.parse_args()

    data_path, out = Path(args.data), Path(args.out)
    try:
        data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: no existe {data_path}", file=sys.stderr)
        return 1
    except yaml.YAMLError as e:
        print(f"ERROR: YAML inválido en {data_path}:\n{e}", file=sys.stderr)
        return 1

    errors = validate(data)
    if errors:
        print(f"ERROR: {len(errors)} problema(s) en {data_path}:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copyfile(ROOT / "index.html", out / "index.html")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    (out / "data.json").write_text(
        json.dumps(to_jsonable(data), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {len(data)} entorno(s) validados. Sitio generado en {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
