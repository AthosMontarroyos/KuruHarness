"""Worktree isolado para tarefa longa, para o Claude rodar enquanto o usuário edita na IDE (Cursor).

    bash bin/kuru worktree create <id> [--base REF]   # cria .kuru/worktrees/<id> na branch kuru/<id>
    bash bin/kuru worktree status                     # worktrees do kit: sujo? commits à frente? como mesclar
    bash bin/kuru worktree remove <id> [--force]      # apaga o worktree e a branch (recusa se houver trabalho não mesclado)

A árvore principal é do usuário: o Claude trabalha só no worktree (index e arquivos próprios, então
não há conflito de arquivo nem de index.lock com a IDE) e entrega uma branch para mesclar. O worktree
nasce do último COMMIT (`--base`, padrão HEAD): edições não commitadas do usuário não entram nele.
`.kuru/active-worktree` (caminho e commit-base, uma linha cada) diz ao hook de fim de tarefa onde
conferir. Só um worktree ativo por vez.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
ACTIVE = Path(".kuru/active-worktree")
DIR = Path(".kuru/worktrees")


class WorktreeError(Exception):
    pass


def git(*args, cwd=None, check=True):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode != 0:
        raise WorktreeError((r.stderr or r.stdout).strip() or f"git {' '.join(args)} falhou")
    return r


def repo_root():
    root = Path(git("rev-parse", "--show-toplevel").stdout.strip())
    if DIR.name in root.parts and ".kuru" in root.parts:
        raise WorktreeError("rode a partir da árvore principal do projeto, não de dentro de um worktree do kit")
    return root


def check_id(task_id):
    if not ID_RE.match(task_id or ""):
        raise WorktreeError("id inválido: use letras, números, ponto, hífen ou sublinhado (até 40, sem começar por símbolo)")
    return task_id


def active(root):
    """(caminho, base) do worktree ativo, ou None."""
    try:
        lines = (root / ACTIVE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    return (lines[0].strip(), lines[1].strip() if len(lines) > 1 else "") if lines and lines[0].strip() else None


def create(task_id, base="HEAD"):
    check_id(task_id)
    root = repo_root()
    if active(root):
        raise WorktreeError(f"já existe um worktree ativo ({active(root)[0]}); termine e rode `kuru worktree remove` antes")
    branch, path = f"kuru/{task_id}", root / DIR / task_id
    if path.exists():
        raise WorktreeError(f"{path} já existe")
    if git("rev-parse", "--verify", "-q", f"refs/heads/{branch}", cwd=root, check=False).returncode == 0:
        raise WorktreeError(f"a branch {branch} já existe")
    sha = git("rev-parse", "--verify", base, cwd=root).stdout.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    git("worktree", "add", "-b", branch, str(path), sha, cwd=root)
    (root / ACTIVE).write_text(f"{path.as_posix()}\n{sha}\n", encoding="utf-8", newline="\n")
    return {"path": path.as_posix(), "branch": branch, "base": sha,
            "aviso": "nasce do último commit: edições não commitadas do usuário não estão aqui"}


def entries(root):
    out = []
    for p in sorted((root / DIR).glob("*")) if (root / DIR).is_dir() else []:
        if not p.is_dir():
            continue
        branch = git("rev-parse", "--abbrev-ref", "HEAD", cwd=p, check=False).stdout.strip()
        act = active(root)
        base = act[1] if act and Path(act[0]) == p else ""
        dirty = bool(git("status", "--porcelain", cwd=p, check=False).stdout.strip())
        ahead = int(git("rev-list", "--count", f"{base}..HEAD", cwd=p, check=False).stdout.strip() or 0) if base else None
        out.append({"id": p.name, "path": p.as_posix(), "branch": branch, "sujo": dirty, "commits_a_frente": ahead,
                    "mesclar": f"git merge {branch}"})
    return out


def remove(task_id, force=False):
    check_id(task_id)
    root = repo_root()
    branch, path = f"kuru/{task_id}", root / DIR / task_id
    if not path.exists():
        raise WorktreeError(f"{path} não existe")
    if not force:
        if git("status", "--porcelain", cwd=path, check=False).stdout.strip():
            raise WorktreeError("o worktree tem mudanças não commitadas (commite ou use --force para descartá-las)")
        if git("merge-base", "--is-ancestor", branch, "HEAD", cwd=root, check=False).returncode != 0:
            raise WorktreeError(f"a branch {branch} tem commits que não estão no HEAD atual: mescle antes (git merge {branch}) ou use --force")
    git("worktree", "remove", "--force", str(path), cwd=root)
    git("branch", "-D", branch, cwd=root, check=False)
    act = active(root)
    if act and Path(act[0]) == path:
        (root / ACTIVE).unlink()
    return {"removido": path.as_posix(), "branch": branch}


def main(argv=None):
    p = argparse.ArgumentParser(prog="kuru worktree", description="Worktree isolado para tarefa longa.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("id"); c.add_argument("--base", default="HEAD")
    sub.add_parser("status")
    r = sub.add_parser("remove"); r.add_argument("id"); r.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    try:
        if a.cmd == "create":
            res = create(a.id, a.base)
        elif a.cmd == "status":
            res = entries(repo_root())
        else:
            res = remove(a.id, a.force)
    except WorktreeError as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
