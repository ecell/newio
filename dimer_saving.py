#!/usr/bin/env python
# coding: utf-8

from egfrd import *
from bd import *
from gfrdbase import *
from logger import *
import _gfrd
import model
import sys


N = 300

L = 5e-6   # World size (meters)
#L = 2e-6
#L = 5e-8
#L = 3e-7

# サイズ 5um の粒子シミュレーションモデル
m = model.ParticleModel(L)

# 分子種の定義 （名前、拡散係数、半径）
S = model.Species('S', 1.5e-12, 5e-9)
P = model.Species('P', 1e-12, 7e-9)

# モデルに分子種を登録
m.add_species_type(S)
m.add_species_type(P)

# 結合反応規則の定義
# S と S が結合して P ができる。反応係数は 1e7/N_A
r1 = model.create_binding_reaction_rule(S, S, P, 1e7 / N_A)
# 分離反応規則の定義
# P が分離して S と S ができる。反応係数は 1e3
r2 = model.create_unbinding_reaction_rule(P, S, S, 1e3)
# 代謝ネットワークを登録。
m.network_rules.add_reaction_rule(r1)
m.network_rules.add_reaction_rule(r2)
# その他の分子の組み合わせは総て離反（反応係数0）にセットする。
m.set_all_repulsive()

# 6N^(1/3) セル立方のワールドモデルを生成する
world = create_world(m, int((N * 6) ** (1. / 3.)))
# 代謝ネットワークのネイティブラッパーを生成
nrw = _gfrd.NetworkRulesWrapper(m.network_rules)
# シミュレータの生成
s = EGFRDSimulator(world, myrandom.rng, nrw)
#s = BDSimulator(world. myrandom.rng, nrw)

# 分子を配置
throw_in_particles(s.world, S, N / 2)
throw_in_particles(s.world, P, N / 2)


#l = Logger('dimer')
l = None
interrupter = None

# ロガーフックインタラプタを登録
#if l is not None:
#    interrupter = FixedIntervalInterrupter(s, 1e-7, l.log)
interrupter = FixedIntervalInterrupter(s, 1e-7, lambda sim, time: s.save_space('saved.hdf5', str(time)))

# ランダムシード。
import myrandom
myrandom.seed(0)


# 15000 ステップ実行。
def profrun():
    if l is not None:
        l.start(s)
    for _ in xrange(15000):
        if interrupter is not None:
            interrupter.step()
        else:
            s.step()

PROFMODE = True

if PROFMODE:
    try:
        import cProfile as profile
    except:
        import profile
    profile.run('profrun()', 'fooprof')
    s.print_report()

    import pstats
    pstats.Stats('fooprof').sort_stats('time').print_stats(40)

else:
    profrun()
    s.print_report()
