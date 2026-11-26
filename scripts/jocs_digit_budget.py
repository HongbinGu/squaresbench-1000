"""jocs_digit_budget.py — 数字预算实验：坐标保留 k 位有效数字时，还能通过认证的题数。

这是论文第 4 节的核心实验：它不是"我们踩了个坑"，而是
「认证通过率对十进制有效位数的敏感度曲线」，用来定出 17 位这条硬线。

用法：python src/jocs_digit_budget.py --sample 150 --workers 6
输出：paper_jocs/figures/digit_budget.json
"""
import argparse
import csv
import importlib.util
import json
import os
import sys
from collections import defaultdict
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL = os.path.join(ROOT, 'verifier', 'metric.py')

_spec = importlib.util.spec_from_file_location('official_metric', OFFICIAL)
metric_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(metric_mod)

DIGITS = [12, 13, 14, 15, 16, 17]


def load_rows(path):
    per_n = defaultdict(list)
    with open(path, newline='', encoding='utf-8') as f:
        rd = csv.DictReader(f)
        cols = {c.lower(): c for c in rd.fieldnames}
        for r in rd:
            per_n[int(r[cols['n']])].append({
                'square_id': r[cols['square_id']].strip(),
                'x': r[cols['x']].strip(),
                'y': r[cols['y']].strip(),
                'angle': r[cols['angle']].strip(),
            })
    return per_n


def truncate(s, k):
    """把十进制串压到 k 位有效数字（模拟下游只保留 k 位）。"""
    v = float(s)
    if v == 0.0:
        return '0'
    return f'{v:.{k}g}'


def job(args):
    n, rows = args
    out = {}
    for k in DIGITS:
        rows_k = [{'square_id': r['square_id'],
                   'x': truncate(r['x'], k),
                   'y': truncate(r['y'], k),
                   'angle': truncate(r['angle'], k)} for r in rows]
        try:
            _, score, L_text, reason = metric_mod.evaluate_single_puzzle(n, rows_k)
        except Exception as e:  # noqa: BLE001
            out[k] = ('error', str(e))
            continue
        out[k] = ('ok', float(L_text)) if reason == 'ok' and L_text else (reason, None)
    return n, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=150)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--csv', default=os.path.join(ROOT, 'data', 'submission.csv'))
    args = ap.parse_args()

    per_n = load_rows(args.csv)
    keys = sorted(per_n)
    step = max(1, len(keys) // args.sample)
    sel = keys[::step][:args.sample]
    print(f'{len(sel)} 题 × {len(DIGITS)} 档位数，{args.workers} 进程 …', flush=True)

    with Pool(args.workers) as pool:
        res = pool.map(job, [(n, per_n[n]) for n in sel], chunksize=1)

    summary = {}
    for k in DIGITS:
        ok = sum(1 for _, o in res if o[k][0] == 'ok')
        summary[k] = {'ok': ok, 'total': len(res), 'rate': ok / len(res)}
        print(f'  {k} 位有效数字：通过 {ok}/{len(res)}  ({ok/len(res):.1%})')

    out = {
        'sample': len(sel),
        'digits': DIGITS,
        'summary': {str(k): v for k, v in summary.items()},
        'per_instance': {str(n): {str(k): v[0] for k, v in o.items()} for n, o in res},
        'n_list': sel,
    }
    path = os.path.join(ROOT, 'results', 'digit_budget.json')
    json.dump(out, open(path, 'w', encoding='utf-8'), indent=1)
    print('written', path)


if __name__ == '__main__':
    main()
