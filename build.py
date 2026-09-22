"""Pipeline semanal: LEGO Obsoleto Semana N.xlsx (aba Base) -> data.json.

Uso:
    python build.py "Semana 11.xlsx"           # grava data.json
    python build.py "Semana 11.xlsx" --check   # so valida, nao grava
    python build.py "Semana 12.xlsx" --allow-new   # aceita SKU novo confirmado

Recalcula as 6 chaves DATA.LEGO_* a partir do historico acumulado do arquivo
(cada .xlsx ja vem com tudo desde 25/05, entao o recalculo e sempre integral,
nunca incremental). DATA.BAIXO_GIRO e preservado do data.json existente -- e um
snapshot fixo do fechamento de 04/05 e nao muda com as levas semanais.

Gate de nomes (spec secao 11): qualquer item que nao esteja no data.json atual
depois de aplicar merge_map.json interrompe a execucao. Variacao de nome do
mesmo SKU deve virar entrada no merge_map.json; SKU genuinamente novo exige
confirmacao humana e a flag --allow-new.

Depende de openpyxl. Os textos editoriais do index.html (periodo, contagem de
registros, rodape e os callouts) continuam manuais -- ver spec secao 10.3.
"""
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
flags = {a for a in sys.argv[1:] if a.startswith("--")}
if not args:
    sys.exit(__doc__)
xlsx = args[0]


def fix(n):
    """Corrige mojibake (UTF-8 lido como cp1252) nos nomes de item."""
    try:
        return n.encode("cp1252").decode("utf-8")
    except Exception:
        return n


merge_map = json.loads((ROOT / "merge_map.json").read_text(encoding="utf-8"))
old = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
known = {i["Nome do item"] for i in old["LEGO_ITEMS"]}

wb = openpyxl.load_workbook(ROOT / xlsx, read_only=True, data_only=True)
rows = [r for r in wb["Base"].iter_rows(values_only=True)][1:]
rows = [r for r in rows if r[0]]

# --- agrega item x dia -------------------------------------------------------
cell = defaultdict(lambda: [0, 0, 0, 0.0])  # (item, data) -> sessions, cart, purch, rev
src_tot = [0, 0, 0, 0.0]
for r in rows:
    name = merge_map.get(fix(r[0]), fix(r[0]))
    d = str(r[1])
    dt = date(int(d[:4]), int(d[4:6]), int(d[6:8]))
    vals = [int(r[2] or 0), int(r[3] or 0), int(r[4] or 0), float(r[5] or 0)]
    c = cell[(name, dt)]
    for i, v in enumerate(vals):
        c[i] += v
        src_tot[i] += v

items = sorted({k[0] for k in cell})
dates = sorted({k[1] for k in cell})
dmax = dates[-1]
ds = lambda dt: dt.strftime("%d/%m")
dl = lambda dt: dt.strftime("%d/%m/%Y")

# --- gate: nome nao reconhecido bloqueia a publicacao ------------------------
novos = [n for n in items if n not in known]
if novos and "--allow-new" not in flags:
    print("BLOQUEADO -- item(ns) nao reconhecido(s) pelo merge_map.json:")
    for n in novos:
        print("   ", n)
    print("\nSe for variacao de nome de um SKU existente, adicione ao merge_map.json.")
    print("Se for SKU genuinamente novo, confirme e rode de novo com --allow-new.")
    sys.exit(1)
if novos:
    print("AVISO: SKU(s) novo(s) aceito(s) via --allow-new:", novos)

# --- LEGO_ITEMS --------------------------------------------------------------
tot = defaultdict(lambda: [0, 0, 0, 0.0])
for (name, dt), v in cell.items():
    for i in range(4):
        tot[name][i] += v[i]
LEGO_ITEMS = sorted(
    [
        {"Nome do item": n, "sessions": v[0], "cart": v[1], "purchased": v[2],
         "revenue": round(v[3], 2)}
        for n, v in tot.items()
    ],
    key=lambda x: (-x["sessions"], x["Nome do item"]),
)

# --- LEGO_TREND --------------------------------------------------------------
per_day = defaultdict(int)
for (name, dt), v in cell.items():
    per_day[dt] += v[0]
LEGO_TREND = [{"DataStr": ds(dt), "sessions": per_day[dt]} for dt in dates]

# --- LEGO_PIVOT --------------------------------------------------------------
LEGO_PIVOT = {
    "dates": [ds(dt) for dt in dates],
    "series": [
        {"item": n, "data": [cell.get((n, dt), [0])[0] for dt in dates]}
        for n in sorted(items, key=lambda n: -tot[n][0])
    ],
}

# --- LEGO_RAW ----------------------------------------------------------------
LEGO_RAW = sorted(
    [
        {"Nome do item": n, "Data": dl(dt), "sessions": v[0], "cart": v[1],
         "purchased": v[2], "revenue": round(v[3], 2)}
        for (n, dt), v in cell.items()
    ],
    key=lambda x: (x["Data"].split("/")[::-1], x["Nome do item"]),
)

# --- LEGO_WEEK_CURRENT (ultimos 7 dias corridos ate a data maxima) -----------
wstart = dmax - timedelta(days=6)
wk = defaultdict(lambda: [0, 0, 0, 0.0])
for (n, dt), v in cell.items():
    if wstart <= dt <= dmax:
        for i in range(4):
            wk[n][i] += v[i]
LEGO_WEEK_CURRENT = {
    "label": f"{ds(wstart)} – {dl(dmax)}",
    "items": sorted(
        [
            {"Nome do item": n, "sessions": wk[n][0], "cart": wk[n][1],
             "purchased": wk[n][2], "revenue": round(wk[n][3], 2)}
            for n in items
        ],
        key=lambda x: (-x["sessions"], x["Nome do item"]),
    ),
}

# --- LEGO_WEEKLY_EVOLUTION (semanas ISO, seg-dom) ----------------------------
weeks = defaultdict(lambda: [0, 0, 0, 0.0])
wdates = defaultdict(list)
for (n, dt), v in cell.items():
    key = dt - timedelta(days=dt.weekday())
    wdates[key].append(dt)
    for i in range(4):
        weeks[key][i] += v[i]
LEGO_WEEKLY_EVOLUTION = [
    {
        "label": f"S{i}",
        "range": f"{ds(min(wdates[k]))}–{ds(max(wdates[k]))}",
        "sessions": weeks[k][0],
        "cart": weeks[k][1],
        "purchased": weeks[k][2],
        "revenue": round(weeks[k][3], 2),
    }
    for i, k in enumerate(sorted(weeks), start=1)
]

# --- validacao: toda chave deve somar o mesmo total de sessoes da fonte ------
agg = [
    sum(x["sessions"] for x in LEGO_ITEMS),
    sum(x["cart"] for x in LEGO_ITEMS),
    sum(x["purchased"] for x in LEGO_ITEMS),
    round(sum(x["revenue"] for x in LEGO_ITEMS), 2),
]
print("totais fonte :", [round(v, 2) if isinstance(v, float) else v for v in src_tot])
print("totais itens :", agg)
ok = True
for label, total in [
    ("TREND", sum(t["sessions"] for t in LEGO_TREND)),
    ("PIVOT", sum(sum(s["data"]) for s in LEGO_PIVOT["series"])),
    ("RAW", sum(r["sessions"] for r in LEGO_RAW)),
    ("WEEKLY", sum(w["sessions"] for w in LEGO_WEEKLY_EVOLUTION)),
]:
    good = total == agg[0]
    ok &= good
    print(f"  {label:7s} sessions = {total}  {'OK' if good else '*** DIVERGE ***'}")
print("registros:", len(LEGO_RAW), "| SKUs:", len(items), "| dias:", len(dates),
      "| periodo:", dl(dates[0]), "a", dl(dmax))
print("semana atual:", LEGO_WEEK_CURRENT["label"])
print("ultimas semanas:")
for w in LEGO_WEEKLY_EVOLUTION[-3:]:
    print("   ", w)
if not ok:
    sys.exit("Divergencia entre as chaves -- data.json NAO foi gravado.")

if "--check" in flags:
    print("\n--check: data.json nao foi alterado.")
    sys.exit(0)

out = {
    "BAIXO_GIRO": old["BAIXO_GIRO"],
    "LEGO_ITEMS": LEGO_ITEMS,
    "LEGO_TREND": LEGO_TREND,
    "LEGO_PIVOT": LEGO_PIVOT,
    "LEGO_RAW": LEGO_RAW,
    "LEGO_WEEK_CURRENT": LEGO_WEEK_CURRENT,
    "LEGO_WEEKLY_EVOLUTION": LEGO_WEEKLY_EVOLUTION,
}
(ROOT / "data.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("\ndata.json gravado.")
print("Proximos passos manuais: atualizar periodo, contagem de registros, rodape")
print("e callouts no index.html; arquivar o par em archive/SemanaN/.")
