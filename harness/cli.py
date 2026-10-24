"""Ponto de entrada único do kit: `kuru <comando> ...` (veja bin/kuru).

Não depende de PYTHONPATH nem de `python3 -m`: insere a raiz do kit no sys.path sozinho, então
funciona igual no Linux, no macOS e no Windows (Git Bash), instalado como plugin ou clonado.
"""
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS = {
    "route": "harness.route",
    "check-rules": "harness.check_rules",
    "review-flow": "harness.review_flow",
    "tasklog": "harness.tasklog",
    "hooklog": "harness.hooklog",
    "brief": "harness.brief",
    "ask-deepseek": "harness.llm:deepseek_main",   # "módulo:função" quando não é `main`
    "ask-jev": "harness.llm:jev_main",
    "higgsfield": "harness.higgsfield",
}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print("uso: kuru <comando> [args]\ncomandos: " + ", ".join(sorted(COMMANDS)) + ", cursor-task, unittest")
        return 0 if argv else 2
    name, rest = argv[0].replace("_", "-"), argv[1:]
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    if name == "unittest":  # testes do projeto atual (cwd), com o Python que achamos
        import unittest
        return 0 if unittest.main(module=None, argv=["unittest", "discover", "-s", "tests", "-t", ".", "-q", *rest],
                                  exit=False).result.wasSuccessful() else 1
    if name not in COMMANDS:
        print(f"comando desconhecido: {name}", file=sys.stderr)
        return 2
    module, _, func = COMMANDS[name].partition(":")
    return getattr(importlib.import_module(module), func or "main")(rest) or 0


if __name__ == "__main__":
    sys.exit(main())
