import ast
from pathlib import Path

SRC = Path("src/lendup_reputation")


def imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_domain_has_no_framework_or_infrastructure_imports() -> None:
    forbidden = (
        "fastapi",
        "sqlalchemy",
        "pika",
        "firebase_admin",
        "lendup_reputation.infrastructure",
    )
    for path in (SRC / "domain").rglob("*.py"):
        offenders = {name for name in imports(path) if name.startswith(forbidden)}
        assert not offenders, f"{path}: {sorted(offenders)}"


def test_application_ports_do_not_import_implementations() -> None:
    offenders = {
        name
        for name in imports(SRC / "application" / "ports.py")
        if name.startswith(("lendup_reputation.infrastructure", "fastapi", "sqlalchemy", "pika"))
    }
    assert not offenders


def test_controller_contains_no_sqlalchemy_or_business_persistence() -> None:
    router_imports = imports(SRC / "interfaces" / "api" / "router.py")
    assert not any(name.startswith("sqlalchemy") for name in router_imports)
    source = (SRC / "interfaces" / "api" / "router.py").read_text(encoding="utf-8")
    assert ".registrar_evaluacion(" in source
