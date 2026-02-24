"""Git tool — shallow-clone repos and extract key files via GitPython."""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
from fnmatch import fnmatch
from pathlib import Path

from langchain_core.tools import tool

from app.graph.models import RepoInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

MAX_FILE_SIZE = 100_000  # 100 KB max per file
MAX_KEY_FILES = 15       # Don't extract more than 15 files
INTERESTING_PATTERNS = ["*.py", "*.md", "*.toml", "*.yaml", "*.yml", "*.json", "*.rs", "*.go"]


def _build_file_tree(root: Path, max_depth: int = 3) -> list[str]:
    """Walk the repo up to `max_depth` and return a list of relative paths."""
    tree: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        depth = len(rel.parts)
        if depth > max_depth:
            dirnames.clear()
            continue
        # Exclude hidden dirs and common noise
        dirnames[:] = [
            d for d in dirnames if not d.startswith(".") and d not in {"node_modules", "__pycache__", ".git", "venv", ".venv"}
        ]
        for f in filenames:
            if not f.startswith("."):
                tree.append(str(rel / f))
    return tree[:200]  # cap


def _extract_key_files(root: Path, patterns: list[str]) -> dict[str, str]:
    """Read files matching patterns (prioritise README, setup, config)."""
    key: dict[str, str] = {}
    priority_files = ["README.md", "readme.md", "README.rst", "setup.py", "pyproject.toml", "Cargo.toml", "go.mod"]

    # Priority files first
    for name in priority_files:
        p = root / name
        if p.exists() and p.stat().st_size <= MAX_FILE_SIZE:
            try:
                key[name] = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass

    # Then pattern-matched files
    for dirpath, _, filenames in os.walk(root):
        if len(key) >= MAX_KEY_FILES:
            break
        rel_dir = Path(dirpath).relative_to(root)
        if any(part.startswith(".") for part in rel_dir.parts):
            continue
        for f in filenames:
            if len(key) >= MAX_KEY_FILES:
                break
            fp = Path(dirpath) / f
            rel = str(rel_dir / f)
            if rel in key:
                continue
            if any(fnmatch(f, pat) for pat in patterns) and fp.stat().st_size <= MAX_FILE_SIZE:
                try:
                    key[rel] = fp.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
    return key


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def clone_and_parse_repo(
    repo_url: str,
    patterns: list[str] | None = None,
) -> RepoInfo:
    """
    Shallow-clone a GitHub repo into a temp directory, extract key files,
    then clean up.
    """
    import git

    patterns = patterns or INTERESTING_PATTERNS
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    tmp_dir = tempfile.mkdtemp(prefix=f"oracle_{repo_name}_")
    try:
        logger.info(f"Cloning {repo_url} (shallow) into {tmp_dir}")
        git.Repo.clone_from(
            repo_url,
            tmp_dir,
            depth=1,
            single_branch=True,
            no_checkout=False,
        )
        root = Path(tmp_dir)
        file_tree = _build_file_tree(root)
        key_files = _extract_key_files(root, patterns)

        readme = key_files.get("README.md", key_files.get("readme.md", ""))

        return RepoInfo(
            url=repo_url,
            name=repo_name,
            readme=readme,
            file_tree=file_tree,
            key_files=key_files,
        )
    except Exception as e:
        logger.error(f"Failed to clone {repo_url}: {e}")
        return RepoInfo(url=repo_url, name=repo_name)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@tool
def clone_repo_tool(repo_url: str) -> dict:
    """Clone a GitHub repo and extract its README, file tree, and key source files."""
    info = clone_and_parse_repo(repo_url)
    return info.model_dump()
