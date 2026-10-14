from pathlib import Path

from backend.scripts.check_hosted_embedding_policy import check_policy


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_repository_obeys_hosted_embedding_policy():
    assert check_policy(REPO_ROOT) == []


def test_policy_rejects_local_runtime_import(tmp_path):
    _create_policy_fixture(tmp_path)
    runtime_file = tmp_path / "backend" / "app" / "embedding_service.py"
    runtime_file.write_text("from sentence_transformers import SentenceTransformer\n", encoding="utf-8")
    (tmp_path / "verify_env.py").write_text("import transformers\n", encoding="utf-8")

    violations = check_policy(tmp_path)
    assert any("imports sentence_transformers" in item for item in violations)
    assert any("imports transformers" in item for item in violations)


def test_policy_rejects_local_dependency_and_pytorch_index(tmp_path):
    _create_policy_fixture(tmp_path)
    (tmp_path / "backend" / "requirements.txt").write_text("torch==2.9.0\n", encoding="utf-8")
    (tmp_path / "deploy_backend.sh").write_text(
        "pip install --extra-index-url https://download.pytorch.org/whl/cpu\n",
        encoding="utf-8",
    )
    (tmp_path / "setup_env.bat").write_text(
        "python -m pip install transformers\n",
        encoding="utf-8",
    )

    violations = check_policy(tmp_path)
    assert any("declares torch" in item for item in violations)
    assert any("uses the PyTorch package index" in item for item in violations)
    assert any("installs a local-model package" in item for item in violations)


def _create_policy_fixture(repo_root: Path) -> None:
    (repo_root / "backend" / "app").mkdir(parents=True)
    (repo_root / ".github" / "workflows").mkdir(parents=True)
    for relative in (
        "requirements.txt",
        "backend/requirements.txt",
        "backend/requirements-minimal.txt",
        ".github/workflows/deploy.yml",
        "deploy_backend.sh",
        "setup_env.bat",
    ):
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# hosted-only fixture\n", encoding="utf-8")
