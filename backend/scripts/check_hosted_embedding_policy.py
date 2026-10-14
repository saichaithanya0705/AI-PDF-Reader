"""Fail when deployable backend code reintroduces a local embedding runtime."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


FORBIDDEN_MODULES = {
    "huggingface_hub",
    "sentence_transformers",
    "torch",
    "transformers",
}
FORBIDDEN_DISTRIBUTIONS = {
    "huggingface-hub",
    "sentence-transformers",
    "torch",
    "transformers",
}
FORBIDDEN_RUNTIME_MARKERS = (
    "AutoModel",
    "AutoTokenizer",
    "CrossEncoder",
    "SentenceTransformer",
    "all-MiniLM",
)
REQUIREMENT_FILES = (
    "requirements.txt",
    "backend/requirements.txt",
    "backend/requirements-minimal.txt",
)
INSTALL_SURFACES = (
    ".github/workflows/deploy.yml",
    "deploy_backend.sh",
    "setup_env.bat",
)
RUNTIME_SOURCE_PATHS = (
    "backend/app",
    "verify_env.py",
)
FORBIDDEN_INSTALL_SOURCE = "download.pytorch.org"
_DISTRIBUTION_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)")
_FORBIDDEN_INSTALL_PACKAGE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"(?:huggingface[-_]hub|sentence[-_]transformers|torch|transformers)"
    r"(?![A-Za-z0-9_.-])",
    re.IGNORECASE,
)


def _normalized_distribution(line: str) -> str | None:
    stripped = line.split("#", 1)[0].strip()
    if not stripped or stripped.startswith(("-", "http://", "https://")):
        return None
    match = _DISTRIBUTION_PATTERN.match(stripped)
    if not match:
        return None
    return match.group(1).lower().replace("_", "-").replace(".", "-")


def _runtime_import_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    runtime_paths: list[Path] = []
    for relative in RUNTIME_SOURCE_PATHS:
        source_path = repo_root / relative
        if source_path.is_dir():
            runtime_paths.extend(source_path.rglob("*.py"))
        elif source_path.is_file():
            runtime_paths.append(source_path)

    for path in sorted(runtime_paths):
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError) as exc:
            violations.append(f"cannot inspect {path.relative_to(repo_root)}: {exc}")
            continue
        relative = path.relative_to(repo_root).as_posix()
        for marker in FORBIDDEN_RUNTIME_MARKERS:
            if marker in source:
                violations.append(f"{relative} contains local-model marker {marker}")
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                root_module = module.split(".", 1)[0]
                if root_module in FORBIDDEN_MODULES:
                    violations.append(f"{relative}:{node.lineno} imports {root_module}")
    return violations


def _requirement_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    for relative in REQUIREMENT_FILES:
        path = repo_root / relative
        if not path.exists():
            violations.append(f"missing dependency manifest: {relative}")
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            distribution = _normalized_distribution(line)
            if distribution in FORBIDDEN_DISTRIBUTIONS:
                violations.append(f"{relative}:{line_number} declares {distribution}")
    return violations


def _install_surface_violations(repo_root: Path) -> list[str]:
    violations: list[str] = []
    for relative in INSTALL_SURFACES:
        path = repo_root / relative
        if not path.exists():
            violations.append(f"missing deployment surface: {relative}")
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if FORBIDDEN_INSTALL_SOURCE in line.lower():
                violations.append(
                    f"{relative}:{line_number} uses the PyTorch package index"
                )
            if _FORBIDDEN_INSTALL_PACKAGE_PATTERN.search(line):
                violations.append(
                    f"{relative}:{line_number} installs a local-model package"
                )
    return violations


def check_policy(repo_root: Path) -> list[str]:
    """Return hosted-only policy violations for a repository root."""
    return [
        *_runtime_import_violations(repo_root),
        *_requirement_violations(repo_root),
        *_install_surface_violations(repo_root),
    ]


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    violations = check_policy(repo_root)
    if violations:
        print("Hosted embedding policy failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("Hosted embedding policy passed: no local embedding runtime is deployable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
