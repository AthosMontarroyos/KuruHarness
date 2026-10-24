"""Checagens determinísticas das regras do SPEC.md (Fase 2).

Uso:
    python3 -m harness.check_rules            # varre os arquivos versionados do repo
    git diff | python3 -m harness.check_rules --diff   # varre só um diff unificado
Sai com 1 se achar violação. Regras: R1 segredos, R2 model no frontmatter,
R4 [x] sem evidência, R5 limite de 3 tentativas.
"""
import re
import subprocess
import sys
from pathlib import Path

MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
# fixtures de teste contêm segredos falsos de propósito
TREE_SKIP = ("harness/eval/",)

R1_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu)_[A-Za-z0-9_]{16,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bBearer\s+(?![$<{])[A-Za-z0-9_.\-]{16,}"),
    re.compile(r"(?i)(?:token|secret|api[_-]?key|password|senha)\w*[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_\-./+]{12,})[\"']"),
    re.compile(r"\b[A-Z][A-Z_]*(?:TOKEN|SECRET|KEY|PASSWORD)[A-Z_]*=(?![<$\"'{(])([^\s\"']{8,})"),
]
R1_OK_VALUE = re.compile(r"(?i)^(?:os\.environ|process\.env|env\.|\$|<|\{)")

R4_EVIDENCE = re.compile(r"`[^`]+`|\b[0-9a-f]{7,40}\b|(?<![\w.])\d+(?:[.,]\d+)?\s*(?:/\s*\d+|passed|tests?|ok|exit|casos|s\b)|exit\s*\d")
R4_BLOCKED = re.compile(r"(?i)\b(bloquead[oa]|pendente|adiad[oa])\b")


def _frontmatter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            return lines[1:i]
    return None


def check_r1_lines(path, lines):
    out = []
    for n, line in lines:
        for pat in R1_PATTERNS:
            m = pat.search(line)
            if not m:
                continue
            val = m.group(1) if pat.groups else m.group(0)
            if R1_OK_VALUE.match(val):
                continue
            out.append(("R1", path, n, "possível segredo literal"))
            break
    return out


def check_r2_text(path, text):
    fm = _frontmatter(text)
    if fm is None:
        return [("R2", path, 1, "subagent sem frontmatter")]
    for line in fm:
        m = re.match(r"model\s*:\s*(.*)$", line)
        if m:
            val = m.group(1).strip().strip("\"'")
            if val in MODELS or val.startswith("claude-"):
                return []
            return [("R2", path, 1, f"model inválido ou vazio: {val!r}")]
    return [("R2", path, 1, "frontmatter sem campo model")]


def check_r4_lines(path, lines):
    out = []
    for n, line in lines:
        m = re.match(r"\s*-\s*\[x\]\s*(.*)$", line)
        if not m:
            continue
        rest = re.sub(r"^[\w.]+\s*(?:—|-|:)?\s*", "", m.group(1), count=1)
        if R4_BLOCKED.search(rest):
            out.append(("R4", path, n, "marcada [x] mas a linha diz bloqueada/pendente"))
        elif not R4_EVIDENCE.search(rest):
            out.append(("R4", path, n, "[x] sem critério/resultado verificável na linha"))
    return out


def check_r5_lines(path, lines):
    out = []
    name = Path(path).name
    for n, line in lines:
        m = re.match(r"\s*(MAX\w*)\s*=\s*(\d+)\s*$", line)
        if m and name in ("end-of-task.sh", "tasklog.py") and int(m.group(2)) != 3:
            out.append(("R5", path, n, f"{m.group(1)} deve ser 3"))
        if name == "end-of-task.sh" and re.search(r"\bwhile\s+(true|:)\b", line):
            out.append(("R5", path, n, "loop sem limite no hook"))
        if name == "CLAUDE.md" or name.endswith(".md"):
            if re.search(r"(?i)tent", line) and "paralelo" not in line.lower():
                for k in re.finditer(r"(\d+)\s*(?:vezes|tentativas)", line):
                    if int(k.group(1)) != 3:
                        out.append(("R5", path, n, "limite de tentativas diferente de 3"))
                # por extenso: "quatro tentativas", "na quarta falha"
                if re.search(r"(?i)\b(dois|duas|quatro|cinco|seis|sete|oito|nove|dez)\s+(?:vezes|tentativas)\b|\b(?:quarta|quinta|sexta|s[eé]tima)\s+(?:falha|tentativa)\b", line):
                    out.append(("R5", path, n, "limite de tentativas por extenso diferente de 3"))
    return out


def check_tree(root="."):
    root = Path(root)
    files = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True).stdout.split()
    out = []
    for f in files:
        if f.startswith(TREE_SKIP) or f.endswith((".webp", ".png", ".jpg")):
            continue
        p = root / f
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        lines = list(enumerate(text.splitlines(), 1))
        out += check_r1_lines(f, lines)
        if re.fullmatch(r"\.claude/agents/[^/]+\.md", f):
            out += check_r2_text(f, text)
        if f == "TASKS.md":
            out += check_r4_lines(f, lines)
        out += check_r5_lines(f, lines)
        if f == "harness/tasklog.py" and not re.search(r"<=\s*(MAX_ATTEMPTS\w*|3)\b", text):
            out.append(("R5", f, 0, "validação do limite de tentativas ausente"))
        if f == "scripts/end-of-task.sh" and not re.search(r"^\s*MAX=3\s*$", text, re.M):
            out.append(("R5", f, 0, "MAX=3 ausente no hook"))
    return out


def parse_diff(text):
    """{arquivo: {'added': [(n, linha)], 'removed': [linha], 'after': [linha]}}"""
    files, cur, n = {}, None, 0
    for line in text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            path = path[2:] if path.startswith("b/") else path
            if path == "/dev/null":
                continue
            cur = files.setdefault(path, {"added": [], "removed": [], "after": []})
        elif line.startswith("--- ") or line.startswith("diff --git"):
            continue
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            n = int(m.group(1)) if m else 1
            if cur is not None:
                cur["after"].append("\x00")  # separa hunks
        elif cur is not None:
            if line.startswith("+"):
                cur["added"].append((n, line[1:]))
                cur["after"].append(line[1:])
                n += 1
            elif line.startswith("-"):
                cur["removed"].append(line[1:])
            elif line.startswith(" ") or line == "":
                cur["after"].append(line[1:])
                n += 1
    return files


def check_diff(text):
    out = []
    for path, d in parse_diff(text).items():
        out += check_r1_lines(path, d["added"])
        if re.fullmatch(r"\.claude/agents/[^/]+\.md", path):
            # hunks que começam no frontmatter (arquivo novo ou edição no topo)
            for chunk in "\n".join(d["after"]).split("\x00"):
                chunk = chunk.strip("\n")
                if chunk.startswith("---"):
                    out += check_r2_text(path, chunk)
        if path == "TASKS.md":
            out += check_r4_lines(path, d["added"])
        out += check_r5_lines(path, d["added"])
        bound = re.compile(r"attempts\s*<=\s*(?:3|MAX\w*)")
        if any(bound.search(r) for r in d["removed"]) and not any(bound.search(l) for _, l in d["added"]):
            out.append(("R5", path, 0, "validação do limite de tentativas removida"))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    found = check_diff(sys.stdin.read()) if "--diff" in argv else check_tree(".")
    for rule, path, n, msg in found:
        print(f"{rule} {path}:{n}: {msg}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
