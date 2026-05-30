import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

LIVE_SMOKE_PROBES = sorted(path.name for path in (ROOT / "backend").glob("test_*.py"))
EXACT_NPM_VERSION = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")


def _read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def _is_main_guard(node):
    if not isinstance(node, ast.If):
        return False

    test = node.test
    if not isinstance(test, ast.Compare):
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
        return False
    if len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
        return False
    if len(test.comparators) != 1:
        return False
    comparator = test.comparators[0]
    return isinstance(comparator, ast.Constant) and comparator.value == "__main__"


def _is_exit_call(node):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in {"exit", "quit"}:
            return True
        if isinstance(node.func, ast.Attribute):
            return (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "sys"
                and node.func.attr == "exit"
            )
    return False


def _is_system_exit_raise(node):
    if not isinstance(node, ast.Raise) or node.exc is None:
        return False
    target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
    return isinstance(target, ast.Name) and target.id == "SystemExit"


def _npx_package_arg(args):
    for arg in args:
        if arg in {"-y", "--yes"}:
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def _package_spec_has_exact_version(spec):
    if not spec:
        return False

    if spec.startswith("@"):
        slash = spec.find("/")
        version_separator = spec.find("@", slash)
    else:
        version_separator = spec.rfind("@")

    if version_separator <= 0:
        return False

    package_name = spec[:version_separator]
    version = spec[version_separator + 1 :]
    if not package_name or version == "latest":
        return False
    return bool(EXACT_NPM_VERSION.fullmatch(version))


def test_mcp_npx_server_packages_are_explicitly_pinned():
    settings = json.loads(_read("mcp.json"))

    unpinned = []
    for name, server in settings["mcpServers"].items():
        if server.get("command") != "npx":
            continue
        package_arg = _npx_package_arg(server.get("args", []))
        if not _package_spec_has_exact_version(package_arg):
            unpinned.append((name, package_arg))

    assert not unpinned, f"npx MCP packages must use exact versions: {unpinned}"


def test_local_agent_permissions_do_not_allow_broad_shell_access():
    settings_path = ROOT / ".claude" / "settings.local.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    allowed = settings["permissions"]["allow"]

    forbidden_prefixes = (
        "Bash(ssh:",
        "Bash(scp:",
        "Bash(mcp-cli call:",
        "Bash(timeout:",
    )

    assert not [entry for entry in allowed if entry.startswith(forbidden_prefixes)]


def test_ci_runs_backend_and_frontend_verification_with_locked_installs():
    workflow = _read(".github/workflows/deploy.yml")

    assert "working-directory: frontend" in workflow
    assert "cache-dependency-path: frontend/package-lock.json" in workflow
    assert (ROOT / "frontend" / "package-lock.json").is_file()
    assert "run: npm ci" in workflow
    assert "run: npm test" in workflow
    assert "run: npm run lint" in workflow
    assert "npm exec tsc -- -b --noEmit" in workflow
    assert "run: npm run build" in workflow
    assert "python -m pytest backend/tests -q" in workflow
    assert "backend/requirements.txt" in workflow
    assert "backend/requirements-minimal.txt" not in workflow
    assert "npm install" not in workflow


def test_deploy_paths_use_lockfile_and_backend_requirements():
    workflow = _read(".github/workflows/deploy.yml")
    backend_deploy = _read("deploy_backend.sh")
    frontend_deploy = _read("deploy_frontend.sh")

    assert "npm ci" in workflow
    assert "npm install" not in workflow
    assert "npm ci" in frontend_deploy
    assert "npm install" not in frontend_deploy
    assert "python -m pip install --requirement backend/requirements.txt" in workflow
    assert "python -m pip install --no-cache-dir --requirement backend/requirements.txt" in backend_deploy
    assert "-r requirements.txt" not in backend_deploy


def test_obsolete_azure_workflow_is_manual_only_and_non_deploying():
    workflow = _read(".github/workflows/main_ai-pdf-reader.yml")

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "branches:" not in workflow
    assert "azure/webapps-deploy" not in workflow
    assert "publish-profile" not in workflow
    assert "AZUREAPPSERVICE_PUBLISHPROFILE" not in workflow
    assert "Deployment disabled" in workflow
    assert ".github/workflows/deploy.yml" in workflow


def test_backend_deploy_does_not_download_spacy_models_at_runtime():
    backend_deploy = _read("deploy_backend.sh")

    assert "spacy download" not in backend_deploy
    assert "python -m spacy download" not in backend_deploy
    assert "spacy.load(\"en_core_web_sm\")" in backend_deploy
    assert "must not download NLP models at runtime" in backend_deploy


def test_upload_script_requires_secure_env_source_and_does_not_package_repo_envs():
    upload_script = _read("upload_to_droplet.bat")
    exclude_patterns = {
        line.strip()
        for line in _read("exclude.txt").splitlines()
        if line.strip()
    }

    assert "SECURE_ENV_FILE" in upload_script
    assert "%REMOTE_PATH%/.env" in upload_script
    assert 'set "REPO_ROOT=%SCRIPT_DIR%"' in upload_script
    assert 'findstr /L /I /B /C:"%REPO_ROOT%\\\\"' in upload_script
    assert "/EXCLUDE:exclude.txt" in upload_script
    assert ".env" in exclude_patterns
    assert "copy .env " not in upload_script
    assert "copy .env\\" not in upload_script
    assert "copy .env.production" not in upload_script


def test_deploy_scripts_do_not_pipe_remote_installers_to_shell_or_disable_host_key_checks():
    setup_script = _read("setup_droplet.sh")
    upload_script = _read("upload_to_droplet.bat")

    assert "| bash" not in setup_script
    assert "StrictHostKeyChecking=no" not in upload_script


def test_root_requirements_delegates_to_backend_lockfile():
    root_requirements = [
        line.strip()
        for line in _read("requirements.txt").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert root_requirements == ["-r backend/requirements.txt"]


def test_pytest_default_collection_is_scoped_to_backend_unit_tests():
    pytest_ini = _read("pytest.ini")

    assert "testpaths = backend/tests" in pytest_ini
    assert "pythonpath = ." in pytest_ini


def test_top_level_live_smoke_probes_are_guarded_from_pytest_collection():
    assert LIVE_SMOKE_PROBES, "Expected top-level backend smoke probes to be discoverable"

    for file_name in LIVE_SMOKE_PROBES:
        path = ROOT / "backend" / file_name
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        docstring = ast.get_docstring(module) or ""

        assert "Manual" in docstring
        assert "Run with:" in docstring

        test_like_functions = [
            node.name
            for node in module.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test")
        ]
        assert not test_like_functions, f"{file_name} exposes pytest tests: {test_like_functions}"

        test_like_classes = [
            node.name
            for node in module.body
            if isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        ]
        assert not test_like_classes, f"{file_name} exposes pytest classes: {test_like_classes}"

        test_like_methods = [
            f"{class_node.name}.{method.name}"
            for class_node in module.body
            if isinstance(class_node, ast.ClassDef)
            for method in class_node.body
            if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
            and method.name.startswith("test")
        ]
        assert not test_like_methods, f"{file_name} exposes pytest methods: {test_like_methods}"

        for node in module.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if _is_main_guard(node):
                continue

            for child in ast.walk(node):
                assert not _is_exit_call(child), f"{file_name} exits at import time"
                assert not _is_system_exit_raise(child), f"{file_name} raises SystemExit at import time"
