"""Writes public-schema.yml: only the endpoints an API key can call, for the SDK generators."""

from pathlib import Path

import yaml

ROOT = Path(__file__).parent
PUBLIC = ("/api/v1/countries/", "/api/v1/holidays/", "/api/v1/business-days/")

schema = yaml.safe_load((ROOT.parent / "backend" / "schema.yml").read_text(encoding="utf-8"))
schema["paths"] = {p: v for p, v in schema["paths"].items() if p.startswith(PUBLIC)}
schema["info"]["title"] = "HolidayOps public API"

# Keep only the component schemas the public paths reach, directly or through other schemas.
components = schema["components"]["schemas"]
keep: set[str] = set()
pending = [schema["paths"]]
while pending:
    node = pending.pop()
    if isinstance(node, dict):
        ref = node.get("$ref", "")
        if ref.startswith("#/components/schemas/") and ref.rsplit("/", 1)[1] not in keep:
            keep.add(ref.rsplit("/", 1)[1])
            pending.append(components[ref.rsplit("/", 1)[1]])
        pending.extend(node.values())
    elif isinstance(node, list):
        pending.extend(node)
schema["components"]["schemas"] = {k: v for k, v in components.items() if k in keep}
schemes = schema["components"]["securitySchemes"]
schema["components"]["securitySchemes"] = {"apiKey": schemes["apiKey"]}
(ROOT / "public-schema.yml").write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")
