import argparse
import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Sign a Joga Bonito release manifest")
    parser.add_argument("--package", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--type", choices=("installer", "portable"), required=True)
    parser.add_argument("--notes", default="")
    parser.add_argument("--private-key", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    package = Path(args.package)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    signed = {
        "format": "joga-bonito.update",
        "schema": 1,
        "appVersion": args.version,
        "notes": args.notes,
        "package": {"type": args.type, "url": args.url, "size": package.stat().st_size, "sha256": digest},
    }
    key = serialization.load_pem_private_key(Path(args.private_key).read_bytes(), password=None)
    envelope = {"signed": signed, "signature": base64.b64encode(key.sign(canonical(signed))).decode("ascii")}
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(envelope, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
