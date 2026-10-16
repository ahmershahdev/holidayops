import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "apps" / "core"


def test_core_never_imports_django_or_other_apps() -> None:
    offenders = []
    for path in CORE.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if top in {"django", "rest_framework"} or (
                    name.startswith("apps.") and not name.startswith("apps.core")
                ):
                    offenders.append(f"{path.name}: {name}")
    assert offenders == []
