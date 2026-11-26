"""jocs_paper_assets.py — 生成 JoCS 投稿所需的图与实测数据。

产出（paper_jocs/figures/）：
  fig1_pipeline.png / .pdf   认证流水线示意
  fig2_precision_cost.png    精度陷阱的代价（1000 题中 10 题被拒，分数虚高 0.0717）
  fig3_gap_by_K.png          与公开最优的差距按 K 带分布
  graphical_abstract.png     图文摘要（>=1328 px 宽）

并实测官方度量的单题认证耗时，写入 paper_jocs/figures/timing.json。
"""
import csv
import importlib.util
import json
import math
import os
import sys
import time
from collections import defaultdict

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'results')
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    'font.size': 9,
    'axes.linewidth': 0.8,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'savefig.dpi': 300,
    'figure.dpi': 120,
})

C_DARK = '#1f2d3d'
C_BLUE = '#2a6fa8'
C_TEAL = '#2f8f83'
C_RED = '#b3352f'
C_GREY = '#8a9199'
C_LIGHT = '#eef2f6'


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


# ---------------------------------------------------------------- fig 1
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(7.2, 2.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3.4)
    ax.axis('off')

    boxes = [
        (0.15, 1.55, 'Candidate\npacking', C_LIGHT, C_DARK),
        (2.05, 1.55, 'Decimal\nround-trip\n(float64)', C_LIGHT, C_DARK),
        (4.05, 1.55, '60-dps\nmeasurement\n(measure_side_mp)', C_BLUE, 'white'),
        (6.35, 1.55, 'Interval SAT\nverification\n(escalating dps)', C_BLUE, 'white'),
        (8.55, 1.05, 'certified L\n+ score', C_TEAL, 'white'),
    ]
    w, h = 1.65, 1.15
    for x, y, txt, fc, tc in boxes:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.06,rounding_size=0.12',
                                    linewidth=0.9, edgecolor=fc if fc != C_LIGHT else C_GREY,
                                    facecolor=fc))
        ax.text(x + w / 2, y + h / 2, txt, ha='center', va='center', color=tc, fontsize=7.6,
                linespacing=1.35)

    arrows = [(1.80, 2.12, 2.05, 2.12), (3.70, 2.12, 4.05, 2.12),
              (5.70, 2.12, 6.35, 2.12), (8.00, 1.95, 8.55, 1.70)]
    for x0, y0, x1, y1 in arrows:
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-|>', mutation_scale=9,
                                     linewidth=0.9, color=C_DARK, shrinkA=0, shrinkB=0))

    # trap annotation
    ax.annotate('values re-serialised and re-parsed\nwith 17 significant digits or fewer',
                xy=(2.87, 1.50), xytext=(1.55, 0.45), fontsize=7, color=C_RED,
                ha='center', linespacing=1.3,
                arrowprops=dict(arrowstyle='-|>', color=C_RED, linewidth=0.8,
                                connectionstyle='arc3,rad=0.25'))
    ax.text(8.55 + w / 2, 0.55, 'rejected if\noverlap certified', fontsize=7, color=C_TEAL,
            ha='center', va='center', linespacing=1.3)
    fig.tight_layout(pad=0.15)
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(OUT, f'fig1_pipeline.{ext}'), bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- fig 2
def fig_precision_cost():
    """(a) 认证通过率 vs 坐标有效数字；(b) 一次 float64 往返造成的分数虚高。"""
    d = json.load(open(os.path.join(OUT, 'digit_budget.json'), encoding='utf-8'))
    ks = [int(k) for k in d['summary']]
    rates = [100 * d['summary'][str(k)]['rate'] for k in ks]
    oks = [d['summary'][str(k)]['ok'] for k in ks]
    tot = d['summary'][str(ks[0])]['total']

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6),
                             gridspec_kw={'width_ratios': [1.35, 1.0]})

    ax = axes[0]
    ax.plot(ks, rates, color=C_BLUE, marker='o', markersize=4.2, linewidth=1.4)
    ax.set_xlabel('significant decimal digits retained in coordinates')
    ax.set_ylabel('instances certified (%)')
    ax.set_ylim(40, 104)
    ax.set_xticks(ks)
    ax.axhline(100, color=C_GREY, linewidth=0.7, linestyle=':')
    for k, r, o in zip(ks, rates, oks):
        ax.annotate(f'{o}', xy=(k, r), xytext=(0, 7), textcoords='offset points',
                    ha='center', fontsize=7, color=C_DARK)
    ax.axvline(17, color=C_RED, linewidth=0.8, linestyle='--')
    ax.text(16.90, 44, '17 digits: float64\nround-trip is lossless', fontsize=7,
            color=C_RED, ha='right', va='bottom', linespacing=1.35)
    ax.set_title(f'(a) digit budget, {tot} sampled instances', fontsize=8.5, color=C_DARK,
                 loc='left', pad=4)

    ax = axes[1]
    vals = [22.250911, 22.322617]
    bars = ax.bar([0, 1], vals, width=0.5, color=[C_TEAL, C_RED])
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['round-trip\nlossless', 'float64\nround-trip'], fontsize=7.6)
    ax.set_ylim(22.20, 22.365)
    ax.set_ylabel('aggregate score')
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.0035, f'{v:.6f}',
                ha='center', fontsize=7.4, color=C_DARK)
    ax.annotate('', xy=(1.32, 22.313), xytext=(1.32, 22.258),
                arrowprops=dict(arrowstyle='<->', color=C_DARK, linewidth=0.9))
    ax.text(1.39, 22.292, '+0.0717', fontsize=9, color=C_DARK, weight='bold', va='center')
    ax.text(1.39, 22.278, '(+0.32%)', fontsize=7, color=C_GREY, va='top')
    ax.set_xlim(-0.65, 1.95)
    ax.set_title('(b) effect of 10 rejections', fontsize=8.5, color=C_DARK, loc='left', pad=4)

    fig.tight_layout(pad=0.35)
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(OUT, f'fig2_digit_budget.{ext}'), bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- fig 3
def fig_gap_by_K():
    d = json.load(open(os.path.join(ROOT, 'results', 'gap_structure.json'), encoding='utf-8'))
    rows = d['by_kband']
    K = [int(r['kband'].split('=')[1]) for r in rows]
    cnt = [r['n'] for r in rows]
    gap = [r['gap'] for r in rows]

    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.bar(K, gap, color=C_BLUE, width=0.72, label='excess score in band')
    ax.set_xlabel('K = floor(sqrt(n))  (instance band)')
    ax.set_ylabel('excess score')
    ax.set_xticks(K[::2])
    ax.set_xticklabels([str(k) for k in K[::2]], fontsize=7.5)

    ax2 = ax.twinx()
    ax2.plot(K, cnt, color=C_RED, marker='o', markersize=3.2, linewidth=1.1,
             label='instances behind')
    ax2.set_ylabel('instances behind', color=C_RED)
    ax2.tick_params(axis='y', colors=C_RED, labelsize=7.5)
    ax2.spines['right'].set_visible(True)
    ax2.spines['top'].set_visible(False)

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=7, loc='upper left')
    ax.set_ylim(0, max(gap) * 1.35)
    fig.tight_layout(pad=0.3)
    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(OUT, f'fig3_gap_by_K.{ext}'), bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- graphical abstract
def graphic_abstract():
    """图文摘要：左栏流水线，右栏分数虚高。用 gridspec 分栏，避免手工坐标相互压字。"""
    fig = plt.figure(figsize=(8.0, 4.2))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.5, 1.0],
                          left=0.035, right=0.975, top=0.70, bottom=0.14, wspace=0.12)

    fig.text(0.035, 0.915, 'Certified benchmark of 1,000 square-packing instances',
             fontsize=11.5, color=C_DARK, weight='bold', va='center')
    fig.text(0.035, 0.835, '60-digit measurement  \u00b7  exact geometric verification  '
             '\u00b7  1000/1000 certified', fontsize=8.2, color=C_GREY, va='center')

    # ---- left: pipeline
    ax = fig.add_subplot(gs[0, 0])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.4)
    ax.axis('off')
    steps = [('candidate\npacking', C_LIGHT), ('decimal\nround-trip', C_LIGHT),
             ('60-dps\nmeasure', C_BLUE), ('exact\nverify', C_BLUE)]
    bw, bh = 2.05, 1.45
    for i, (t, fc) in enumerate(steps):
        x = 0.15 + i * 2.45
        ax.add_patch(FancyBboxPatch((x, 4.25), bw, bh,
                                    boxstyle='round,pad=0.04,rounding_size=0.12',
                                    linewidth=0.8, edgecolor=fc if fc != C_LIGHT else C_GREY,
                                    facecolor=fc))
        ax.text(x + bw / 2, 4.25 + bh / 2, t, ha='center', va='center', fontsize=7.2,
                color='white' if fc == C_BLUE else C_DARK, linespacing=1.3)
        if i < 3:
            ax.add_patch(FancyArrowPatch((x + bw + 0.03, 4.25 + bh / 2),
                                         (x + 2.45 - 0.03, 4.25 + bh / 2),
                                         arrowstyle='-|>', mutation_scale=8,
                                         linewidth=0.8, color=C_DARK))
    ax.text(0.15, 3.55, 'certified L  \u2192  score', fontsize=8.2, color=C_TEAL, weight='bold')
    ax.text(0.15, 2.95, '990 instances reproduce the\npublished value exactly',
            fontsize=7.3, color=C_DARK, linespacing=1.4, va='top')
    ax.text(0.15, 1.55, '10 instances (n = 333 \u2026 857) are\nsilently rejected after a 17-digit round-trip',
            fontsize=7.3, color=C_RED, linespacing=1.4, va='top')

    # ---- right: score inflation
    bx = fig.add_subplot(gs[0, 1])
    vals = [22.250911, 22.322617]
    bars = bx.bar([0, 1], vals, width=0.55, color=[C_TEAL, C_RED])
    bx.set_ylim(22.20, 22.365)
    bx.set_xlim(-0.65, 1.85)
    bx.set_xticks([0, 1])
    bx.set_xticklabels(['exact\nround-trip', 'float64\nround-trip'], fontsize=7.6)
    bx.set_ylabel('aggregate score', fontsize=8)
    bx.tick_params(axis='y', labelsize=7.2)
    bx.spines['top'].set_visible(False)
    bx.spines['right'].set_visible(False)
    for b, v in zip(bars, vals):
        bx.text(b.get_x() + b.get_width() / 2, v + 0.0035, f'{v:.6f}',
                ha='center', fontsize=7.4, color=C_DARK)
    bx.annotate('', xy=(1.33, 22.313), xytext=(1.33, 22.258),
                arrowprops=dict(arrowstyle='<->', color=C_DARK, linewidth=0.9))
    bx.text(1.40, 22.288, '+0.0717', fontsize=9.2, color=C_DARK, weight='bold', va='center')
    bx.text(1.40, 22.276, 'pure\nartefact', fontsize=7.0, color=C_GREY, va='top', linespacing=1.35)
    fig.text(0.035, 0.015,
             'Fix: float64-normalised coordinates and bit-exact round-trip assertions',
             fontsize=7.2, color=C_DARK, va='bottom')

    for ext in ('png', 'pdf'):
        fig.savefig(os.path.join(OUT, f'graphical_abstract.{ext}'), dpi=300
                    if ext == 'png' else None, facecolor='white', bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------- timing
def time_certification(sample=40):
    spec = importlib.util.spec_from_file_location(
        'official_metric', os.path.join(ROOT, 'verifier', 'metric.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    per_n = load_rows(os.path.join(ROOT, 'data', 'submission.csv'))
    keys = sorted(per_n)
    idx = np.linspace(0, len(keys) - 1, sample).astype(int)
    times = []
    ok = 0
    for i in idx:
        n = keys[i]
        t0 = time.perf_counter()
        _, score, L_text, reason = mod.evaluate_single_puzzle(n, per_n[n])
        times.append(time.perf_counter() - t0)
        if reason == 'ok':
            ok += 1
    res = {
        'sample': int(sample),
        'ok': ok,
        'mean_s': float(np.mean(times)),
        'median_s': float(np.median(times)),
        'max_s': float(np.max(times)),
        'est_full_pass_s': float(np.sum(times) / sample * len(keys)),
        'sample_n': [keys[i] for i in idx],
    }
    json.dump(res, open(os.path.join(OUT, 'timing.json'), 'w', encoding='utf-8'), indent=2)
    print('timing:', json.dumps({k: v for k, v in res.items() if k != 'sample_n'}, ensure_ascii=False))


if __name__ == '__main__':
    fig_pipeline()
    fig_precision_cost()
    fig_gap_by_K()
    graphic_abstract()
    print('figures written to', OUT)
    time_certification()
