"""jocs_undecided_rate.py — 统计 binary64 预筛无法判定的接触对比例。

论文用途：解释为什么验证器必须做「浮点预筛 + 区间算术升级」两级设计，
而不是单用浮点 SAT。单点：在最优（塞满）构型里，大量方块精确相切，
浮点无法区分「相切」与「微重叠」。

用法：python src/jocs_undecided_rate.py --sample 120 --workers 6
输出：paper_jocs/figures/undecided.json
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

_orig_sat_float = metric_mod.sat_check_float
_orig_verify = metric_mod.verify_puzzle


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


def job(args):
    n, rows = args
    stats = {'pairs': 0, 'undecided': 0, 'overlap': 0, 'sep': 0}

    def patched(sq1, sq2, undecided_tol=1e-8):
        r = _orig_sat_float(sq1, sq2, undecided_tol)
        stats['pairs'] += 1
        if r == 'undecided':
            stats['undecided'] += 1
        elif r == 'overlap':
            stats['overlap'] += 1
        else:
            stats['sep'] += 1
        return r

    metric_mod.sat_check_float = patched
    try:
        _, score, L_text, reason = metric_mod.evaluate_single_puzzle(n, rows)
    finally:
        metric_mod.sat_check_float = _orig_sat_float
    stats['n'] = n
    stats['reason'] = reason
    stats['ok'] = reason == 'ok'
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=120)
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()

    per_n = load_rows(os.path.join(ROOT, 'data', 'submission.csv'))
    keys = sorted(per_n)
    step = max(1, len(keys) // args.sample)
    sel = keys[::step][:args.sample]
    print(f'{len(sel)} 题，统计浮点预筛的判定分布 …', flush=True)

    with Pool(args.workers) as pool:
        res = pool.map(job, [(n, per_n[n]) for n in sel], chunksize=1)

    pairs = sum(r['pairs'] for r in res)
    und = sum(r['undecided'] for r in res)
    draww = sum(1 for r in res if r['undecided'] > 0)
    out = {
        'instances': len(res),
        'pairs_total': pairs,
        'pairs_undecided': und,
        'pairs_undecided_ratio': und / pairs if pairs else 0,
        'instances_with_undecided': draww,
        'instances_with_undecided_ratio': draww / len(res),
        'median_undecided_per_instance': sorted(r['undecided'] for r in res)[len(res) // 2],
        'max_undecided_per_instance': max(r['undecided'] for r in res),
        'all_certified': all(r['ok'] for r in res),
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    json.dump(out, open(os.path.join(ROOT, 'results', 'undecided.json'),
                        'w', encoding='utf-8'), indent=1)


if __name__ == '__main__':
    main()
