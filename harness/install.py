"""Instala o kit na configuração GLOBAL do Claude Code (~/.claude), para valer em todos os projetos.

    bash bin/kuru install --global [--dest ~/.claude] [--dry-run] [--force]

Copia o kit para <dest>/kuru, os agents para <dest>/agents e as skills para <dest>/skills, reescreve
`bash bin/kuru` para o caminho global, junta a política de delegação no <dest>/CLAUDE.md (entre
marcadores) e o hook/permissões no <dest>/settings.json (com cópia de segurança). Idempotente.
Arquivo seu com o mesmo nome e conteúdo diferente NÃO é sobrescrito sem --force.
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEGIN, END = "<!-- kuru:begin -->", "<!-- kuru:end -->"
OLD_CMD = "bash bin/kuru"
SKIP_DIRS = {"__pycache__", "eval"}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def kit_cmd(dest):
    home = Path.home() / ".claude"
    base = "~/.claude/kuru" if dest.resolve() == home.resolve() else (dest / "kuru").resolve().as_posix()
    return f"bash {base}/bin/kuru", base


def rewrite(text, cmd):
    return text.replace(OLD_CMD, cmd)


def policy_block(claude_md, cmd):
    """Seções de política do CLAUDE.md do kit (sem as regras de quem codifica, que ficam na cópia do kit)."""
    m = re.search(r"(## Autonomia: quando delegar.*?)(?=\n## Regras para quem codifica)", claude_md, re.S)
    if not m:
        raise SystemExit('erro: seção "Autonomia" não encontrada no CLAUDE.md do kit')
    body = "## KuruHarness (subagents)\nMáximo de 3 tentativas por tarefa; na terceira falha, pare e reporte. Chaves só em variável de ambiente.\n\n" + m.group(1).strip()
    return f"{BEGIN}\n{rewrite(body, cmd)}\n{END}\n"


def merge_claude_md(existing, block):
    if BEGIN in existing and END in existing:
        return re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", lambda _: block, existing, flags=re.S)
    return (existing.rstrip() + "\n\n" if existing.strip() else "") + block


def merge_settings(settings, cmd, base):
    allow = settings.setdefault("permissions", {}).setdefault("allow", [])
    for rule in (f"Bash({cmd} *)", "Bash(git diff*)", "Bash(git status*)", "Bash(git apply*)", "Bash(git add -N*)"):
        if rule not in allow:
            allow.append(rule)
    stop = settings.setdefault("hooks", {}).setdefault("Stop", [])
    hook_cmd = f"bash {base}/scripts/end-of-task.sh --diff"
    mine = [h for e in stop for h in e.get("hooks", []) if "end-of-task.sh" in h.get("command", "")]
    for h in mine:  # reinstalar atualiza o comando em vez de duplicar
        h.update(command=hook_cmd, shell="bash")
    if not mine:
        stop.append({"hooks": [{"type": "command", "command": hook_cmd, "shell": "bash"}]})
    return settings


def plan_files(cmd):
    """[(origem relativa ao kit, destino relativo a <dest>, texto)]"""
    out = []

    def add(src, dst):
        text = rewrite(src.read_text(encoding="utf-8"), cmd) if src.suffix in (".md", ".sh", ".py", ".json", "") else None
        out.append((src, dst, text))

    for sub in ("bin", "harness", "scripts"):
        for f in sorted((ROOT / sub).rglob("*")):
            if f.is_file() and not (set(f.relative_to(ROOT).parts) & SKIP_DIRS) and f.suffix != ".pyc":
                add(f, Path("kuru") / f.relative_to(ROOT))
    add(ROOT / "CLAUDE.md", Path("kuru/CLAUDE.md"))
    for f in sorted((ROOT / ".claude/agents").glob("*.md")):
        add(f, Path("agents") / f.name)
    for f in sorted((ROOT / ".claude/skills").glob("*/SKILL.md")):
        add(f, Path("skills") / f.parent.name / "SKILL.md")
    return out


def install(dest, dry_run=False, force=False):
    dest = Path(dest).expanduser()
    cmd, base = kit_cmd(dest)
    manifest_path = dest / "kuru" / ".manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    report = {"copiados": 0, "iguais": 0, "conflitos": []}
    new_manifest = {}
    for src, rel, text in plan_files(cmd):
        target = dest / rel
        data = text if text is not None else None
        if target.exists():
            current = target.read_text(encoding="utf-8") if data is not None else None
            if data is not None and current == data:
                report["iguais"] += 1
                new_manifest[rel.as_posix()] = sha(data)
                continue
            ours = manifest.get(rel.as_posix()) == (sha(current) if current is not None else None)
            if not (ours or force):
                report["conflitos"].append(rel.as_posix())
                if rel.as_posix() in manifest:
                    new_manifest[rel.as_posix()] = manifest[rel.as_posix()]
                continue
        report["copiados"] += 1
        if data is not None:
            new_manifest[rel.as_posix()] = sha(data)
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            if data is not None:
                target.write_text(data, encoding="utf-8", newline="\n")
            else:
                shutil.copy2(src, target)
    # arquivos que o kit instalou antes e não existem mais nele (ex.: cursor-task.sh): apaga se você não mexeu
    report["removidos"] = []
    for rel, digest in manifest.items():
        if rel.startswith("_") or rel in new_manifest:
            continue
        old = dest / rel
        try:
            unchanged = old.exists() and sha(old.read_text(encoding="utf-8")) == digest
        except (OSError, UnicodeDecodeError):
            unchanged = False
        if unchanged:
            report["removidos"].append(rel)
            if not dry_run:
                old.unlink()
        elif old.exists():
            new_manifest[rel] = digest  # alterado por você: fica, e continua listado
    claude_md = dest / "CLAUDE.md"
    block = policy_block((ROOT / "CLAUDE.md").read_text(encoding="utf-8"), cmd)
    old_md = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
    settings_path = dest / "settings.json"
    try:
        old_settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    except ValueError:
        raise SystemExit(f"erro: {settings_path} não é JSON puro (comentários?). Junte à mão o bloco hooks/permissions de .claude/settings.json do kit.")
    new_settings = merge_settings(json.loads(json.dumps(old_settings)), cmd, base)
    report["claude_md_chars_por_turno"] = len(block)
    if not dry_run:
        for path, content in ((claude_md, merge_claude_md(old_md, block)),
                              (settings_path, json.dumps(new_settings, indent=2, ensure_ascii=False) + "\n")):
            if path.exists() and not Path(str(path) + ".kuru-bak").exists():
                shutil.copy2(path, str(path) + ".kuru-bak")
            path.write_text(content, encoding="utf-8", newline="\n")
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        new_manifest["_origem"] = ROOT.as_posix()  # onde atualizar: a skill atualizar-kuru lê daqui
        manifest_path.write_text(json.dumps(new_manifest, indent=2, sort_keys=True), encoding="utf-8")
    report["comando"] = cmd
    report["dry_run"] = dry_run
    return report


def main(argv=None):
    p = argparse.ArgumentParser(prog="kuru install", description="Instala o kit na configuração global do Claude Code.")
    p.add_argument("--global", dest="glob", action="store_true", required=True, help="instala em ~/.claude (ou --dest)")
    p.add_argument("--dest", default=str(Path.home() / ".claude"))
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="sobrescreve arquivos seus com o mesmo nome")
    a = p.parse_args(argv)
    rep = install(a.dest, a.dry_run, a.force)
    print(json.dumps(rep, ensure_ascii=False))
    if rep["conflitos"]:
        print("conflitos (arquivo seu com o mesmo nome; use --force para sobrescrever): " + ", ".join(rep["conflitos"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
