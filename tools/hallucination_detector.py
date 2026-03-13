"""tools/hallucination_detector.py — Detector de alucinaciones en código generado por LLMs."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python < 3.11
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

if hasattr(sys, "stdlib_module_names"):
    _STDLIB_NAMES: frozenset[str] = frozenset(sys.stdlib_module_names)
else:
    _STDLIB_NAMES = frozenset({
        *sys.builtin_module_names,
        "abc", "ast", "asyncio", "base64", "collections", "concurrent", "contextlib",
        "copy", "csv", "dataclasses", "datetime", "decimal", "difflib", "email",
        "enum", "functools", "gc", "getopt", "getpass", "glob", "hashlib", "heapq",
        "hmac", "html", "http", "importlib", "inspect", "io", "ipaddress", "itertools",
        "json", "linecache", "logging", "math", "mimetypes", "multiprocessing",
        "numbers", "operator", "os", "pathlib", "pickle", "platform", "pprint",
        "queue", "random", "re", "shutil", "signal", "socket", "sqlite3", "ssl",
        "statistics", "string", "struct", "subprocess", "sys", "tempfile", "textwrap",
        "threading", "time", "timeit", "tomllib", "traceback", "typing", "unicodedata",
        "unittest", "urllib", "uuid", "venv", "warnings", "weakref", "xml",
        "zipfile", "zlib", "__future__",
    })

from agents.hulk import GuardrailViolation, ViolationType
from core.blueprint_schema import BlueprintV1
from tools.file_tools import PROJECT_ROOT, read_file

_ENDPOINT_RE = re.compile(r'["\'](/\w[/\w{}]*)["\']')
_ENV_PATTERNS = [
    re.compile(r'\bos\.environ\b'),
    re.compile(r'\bos\.getenv\s*\('),
    re.compile(r'\bdotenv\.load_dotenv\s*\('),
]
_EXEMPT_ENV_SUFFIXES = ("core/settings.py",)
_KNOWN_BASE_CLASSES = frozenset({
    "BaseModel", "Exception", "Protocol", "Enum", "IntEnum", "StrEnum",
    "BaseException", "ABC", "TypedDict", "NamedTuple", "ValueError",
    "RuntimeError", "HTTPException",
})


def parse_allowed_packages(pyproject_path: Path | None = None) -> set[str]:
    """Extrae nombres de paquetes permitidos desde pyproject.toml."""
    path = pyproject_path or (PROJECT_ROOT / "pyproject.toml")
    if tomllib is None:
        text = path.read_text(encoding="utf-8")
        names = re.findall(r'"([A-Za-z0-9_-]+)(?:[>=<!;\[\s,])', text)
        return {n.replace("-", "_").lower() for n in names} | {n.lower() for n in names}
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    raw: list[str] = data.get("project", {}).get("dependencies", [])
    raw += data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    packages: set[str] = set()
    for dep in raw:
        name = re.split(r"[>=<!;\[,\s]", dep)[0].strip()
        packages.add(name.replace("-", "_").lower())
        packages.add(name.lower())
    return packages


class HallucinationDetector:
    """Detecta alucinaciones comunes en código generado por LLMs."""

    def __init__(self, blueprint: BlueprintV1, allowed_packages: set[str]) -> None:
        self._blueprint = blueprint
        self._allowed_packages = {p.lower() for p in allowed_packages}

    def check_imports(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """Detecta imports de librerías no en pyproject.toml ni stdlib."""
        violations: list[GuardrailViolation] = []
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return violations
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0].lower()
                    if pkg not in _STDLIB_NAMES and pkg not in self._allowed_packages:
                        violations.append(GuardrailViolation(
                            file_path=file_path, violation_type=ViolationType.FORBIDDEN_PATTERN,
                            line_number=node.lineno, severity="error",
                            detail=f"Import alucinado: '{pkg}' no está en pyproject.toml",
                        ))
            elif isinstance(node, ast.ImportFrom):
                pkg = (node.module or "").split(".")[0].lower()
                if pkg and pkg not in _STDLIB_NAMES and pkg not in self._allowed_packages:
                    violations.append(GuardrailViolation(
                        file_path=file_path, violation_type=ViolationType.FORBIDDEN_PATTERN,
                        line_number=node.lineno, severity="error",
                        detail=f"Import alucinado: '{pkg}' no está en pyproject.toml",
                    ))
        return violations

    def check_endpoints(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """Detecta paths de API hardcodeados no declarados en el Blueprint."""
        declared = {ep.path for ep in self._blueprint.api_endpoints}
        violations: list[GuardrailViolation] = []
        for line_no, line in enumerate(source_code.splitlines(), start=1):
            for match in _ENDPOINT_RE.finditer(line):
                path = match.group(1)
                if path not in declared:
                    violations.append(GuardrailViolation(
                        file_path=file_path, violation_type=ViolationType.FORBIDDEN_PATTERN,
                        line_number=line_no, severity="warning",
                        detail=f"Endpoint '{path}' no declarado en Blueprint",
                    ))
        return violations

    def check_env_access(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """Detecta acceso directo a vars de entorno fuera de settings y tests."""
        if any(file_path.endswith(s) for s in _EXEMPT_ENV_SUFFIXES):
            return []
        if file_path.startswith("tests/") or "/tests/" in file_path:
            return []
        violations: list[GuardrailViolation] = []
        for line_no, line in enumerate(source_code.splitlines(), start=1):
            for pattern in _ENV_PATTERNS:
                if pattern.search(line):
                    violations.append(GuardrailViolation(
                        file_path=file_path, violation_type=ViolationType.FORBIDDEN_PATTERN,
                        line_number=line_no, severity="error",
                        detail="Acceso directo a entorno — usa pydantic-settings (Settings)",
                    ))
                    break
        return violations

    def check_data_models(self, source_code: str, file_path: str) -> list[GuardrailViolation]:
        """Detecta clases no declaradas en Blueprint ni en interfaces estándar."""
        declared = {dm.name for dm in self._blueprint.data_models}
        violations: list[GuardrailViolation] = []
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return violations
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name not in declared and node.name not in _KNOWN_BASE_CLASSES:
                violations.append(GuardrailViolation(
                    file_path=file_path, violation_type=ViolationType.FORBIDDEN_PATTERN,
                    line_number=node.lineno, severity="warning",
                    detail=f"Clase '{node.name}' no declarada en Blueprint data_models",
                ))
        return violations

    async def scan_all(self, file_paths: list[str]) -> list[GuardrailViolation]:
        """Ejecuta todos los checks. [ROOT JAIL: usa read_file()]"""
        violations: list[GuardrailViolation] = []
        for fp in file_paths:
            try:
                source = read_file(fp)
            except FileNotFoundError:
                continue
            violations.extend(self.check_imports(source, fp))
            violations.extend(self.check_endpoints(source, fp))
            violations.extend(self.check_env_access(source, fp))
            violations.extend(self.check_data_models(source, fp))
        return violations

