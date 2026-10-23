"""Compara Jev e Haiku com os rótulos. Uso: python3 harness/eval/score.py"""
import glob
import json
import os

D = os.path.dirname(os.path.abspath(__file__))
labels = {c["id"]: c["label"] for f in glob.glob(f"{D}/cases_*.json") for c in json.load(open(f))}

jev = {}
for l in open(f"{D}/jev_results.txt"):
    if l.startswith("#") or not l.strip():
        continue
    i, v, p, c = l.strip().split("|")
    jev[i] = (v == "reprovar", float(c))
hk = {}
for l in open(f"{D}/haiku_results.txt"):
    if l.strip():
        p = l.strip().split("|")
        hk[p[0]] = p[1] == "REPROVADO"


def report(name, pred, ids, conf=None, thr=0.8):
    ok = sum(pred[i] == (labels[i] == "violates") for i in ids)
    fn = sum(not pred[i] and labels[i] == "violates" for i in ids)
    fp = sum(pred[i] and labels[i] == "ok" for i in ids)
    print(f"{name}: {ok}/{len(ids)} certos | falsos negativos={fn} falsos positivos={fp}")
    if conf:
        hi = [i for i in ids if conf[i] >= thr]
        hok = sum(pred[i] == (labels[i] == "violates") for i in hi)
        print(f"   alta confiança (>={thr}): {hok}/{len(hi)} certos")


ids = sorted(jev)
report("Jev  ", {i: jev[i][0] for i in ids}, ids, {i: jev[i][1] for i in ids})
report("Haiku", hk, ids)
from harness.check_rules import check_diff  # noqa: E402
det = {c: bool(check_diff(d)) for f in glob.glob(f"{D}/blind/*.json") for c, d in ((x["id"], x["diff"]) for x in json.load(open(f)))}
report("Determinístico (regras escritas DEPOIS de ver os casos, resultado otimista)", det, ids)
for p in ("r1", "r2", "r4", "r5"):
    sub = [i for i in ids if i.startswith(p)]
    a = sum(jev[i][0] == (labels[i] == "violates") for i in sub)
    b = sum(hk[i] == (labels[i] == "violates") for i in sub)
    print(f"  {p}: Jev {a}/{len(sub)}  Haiku {b}/{len(sub)}")
print("erros do Jev:", [(i, jev[i]) for i in ids if jev[i][0] != (labels[i] == "violates")])
print("erros do Haiku:", [i for i in sorted(hk) if hk[i] != (labels[i] == "violates")])
