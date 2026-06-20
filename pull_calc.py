"""
pull_calc.py
HSR Eidolon Probability Calculator — Python port of the HTML/JS engine
Mirrors simulateOne() / runSimulations() / hardPityLossInfo() from the HTML.
"""

import random
import math
from dataclasses import dataclass, field
from typing import Optional

# ── HSR defaults ─────────────────────────────────────────────
HARD_PITY     = 90
SOFT_START    = 74     # soft pity kicks in on the 74th pull (pity counter = 74)
BASE_RATE_5   = 0.006
WIN_RATE      = 0.5
FOUR_HARD     = 10
FOUR_BASE     = 0.051
SIMULATIONS   = 8_000  # 8 k gives < 0.6 pp SE and runs < 0.5 s in CPython


@dataclass
class CalcInputs:
    pulls:       int   = 180
    current_e:   int   = -1      # -1 = not owned, 0-6 = E0-E6
    target_e:    int   = 0
    pity:        int   = 0       # current 5★ pity (pulls since last 5★)
    guarantee:   bool  = False   # 50/50 guaranteed next 5★?
    four_pity:   int   = 0       # current 4★ pity
    simulations: int   = SIMULATIONS
    # advanced (kept at HSR defaults, not exposed as command args)
    hard:        int   = HARD_PITY
    soft_start:  int   = SOFT_START
    base:        float = BASE_RATE_5
    win_rate:    float = WIN_RATE
    four_hard:   int   = FOUR_HARD
    four_base:   float = FOUR_BASE

    @property
    def need(self) -> int:
        cur = 0 if self.current_e < 0 else self.current_e + 1
        tgt = self.target_e + 1
        return max(0, tgt - cur)


# ── Rate functions (match JS rateAt / rate4At) ───────────────

def rate_at(pity: int, inp: CalcInputs) -> float:
    """5★ rate on the pity-th pull (1-indexed, i.e. pity counter AFTER increment)."""
    if pity >= inp.hard:
        return 1.0
    if pity < inp.soft_start:
        return inp.base
    steps = inp.hard - inp.soft_start + 1
    inc   = (1.0 - inp.base) / steps
    return min(1.0, inp.base + (pity - inp.soft_start + 1) * inc)


def rate4_at(four_pity: int, inp: CalcInputs) -> float:
    """4★ rate (simple: base or hard pity)."""
    if four_pity >= inp.four_hard:
        return 1.0
    return inp.four_base


# ── Single simulation run ─────────────────────────────────────

def simulate_one(inp: CalcInputs, rng=None) -> dict:
    """Mirrors simulateOne() in the HTML JS."""
    if rng is None:
        rng = random.random

    pity       = inp.pity
    guarantee  = inp.guarantee
    four_pity  = inp.four_pity

    copies              = 0
    total_losses        = 0
    losses_before_tgt   = 0
    five_stars          = 0
    four_stars          = 0
    starlight4          = 0.0

    success      = inp.need <= 0
    target_pull  = 0 if inp.need <= 0 else None
    target_losses = 0 if inp.need <= 0 else None

    for pull_num in range(1, inp.pulls + 1):
        pity += 1
        p5 = rate_at(pity, inp)

        if rng() < p5:
            five_stars += 1
            pity      = 0
            four_pity = 0   # 5★ resets 4★ pity (matches JS)

            if guarantee:
                copies   += 1
                guarantee = False
                if not success and copies >= inp.need:
                    success       = True
                    target_pull   = pull_num
                    target_losses = losses_before_tgt
            else:
                if rng() < inp.win_rate:
                    copies += 1
                    if not success and copies >= inp.need:
                        success       = True
                        target_pull   = pull_num
                        target_losses = losses_before_tgt
                else:
                    total_losses += 1
                    if not success:
                        losses_before_tgt += 1
                    guarantee = True
        else:
            four_pity += 1
            if rng() < rate4_at(four_pity, inp):
                four_pity   = 0
                four_stars += 1
                # Average ~5 starlight per 4★ pull (duplicate value)
                starlight4 += 5.0

    tl = target_losses if target_losses is not None else losses_before_tgt
    return {
        "copies":               copies,
        "total_losses":         total_losses,
        "losses_before_target": tl,
        "five_stars":           five_stars,
        "four_stars":           four_stars,
        "starlight4":           starlight4,
        "success":              success,
        "target_pull":          target_pull,
    }


# ── Monte Carlo driver ────────────────────────────────────────

def run_simulations(inp: CalcInputs) -> dict:
    """Mirrors runSimulations() in the HTML JS."""
    n = inp.simulations

    copy_dist        = {}
    success_by_loss  = {}
    target_pulls     = []
    successes        = 0

    sum_copies        = 0
    sum_total_losses  = 0
    sum_losses_before = 0
    sum_five_stars    = 0
    sum_four_stars    = 0
    sum_starlight4    = 0.0

    for _ in range(n):
        r = simulate_one(inp)
        c = r["copies"]
        copy_dist[c] = copy_dist.get(c, 0) + 1
        sum_copies        += c
        sum_total_losses  += r["total_losses"]
        sum_losses_before += r["losses_before_target"]
        sum_five_stars    += r["five_stars"]
        sum_four_stars    += r["four_stars"]
        sum_starlight4    += r["starlight4"]

        if r["success"]:
            successes += 1
            lb = r["losses_before_target"]
            success_by_loss[lb] = success_by_loss.get(lb, 0) + 1
            if r["target_pull"] is not None:
                target_pulls.append(r["target_pull"])

    target_pulls.sort()
    sr = successes / n
    se = math.sqrt(max(0.0, sr * (1 - sr) / n))

    def pctile(data: list, q: float) -> int:
        if not data:
            return 0
        idx = int(q * (len(data) - 1))
        return data[min(idx, len(data) - 1)]

    return {
        "success_rate":       sr,
        "se":                 se,
        "ci_low":             max(0.0, sr - 1.96 * se),
        "ci_high":            min(1.0, sr + 1.96 * se),
        "successes":          successes,
        "copy_dist":          {k: v / n for k, v in sorted(copy_dist.items())},
        "success_by_loss":    {k: v / n for k, v in sorted(success_by_loss.items())},
        "target_pulls":       target_pulls,
        "avg_copies":         sum_copies        / n,
        "avg_total_losses":   sum_total_losses  / n,
        "avg_losses_before":  sum_losses_before / n,
        "avg_five_stars":     sum_five_stars    / n,
        "avg_four_stars":     sum_four_stars    / n,
        "avg_starlight4":     sum_starlight4    / n,
        "p10":                pctile(target_pulls, 0.10),
        "median":             pctile(target_pulls, 0.50),
        "p90":                pctile(target_pulls, 0.90),
        "avg_target_pulls":   (sum(target_pulls) / len(target_pulls)) if target_pulls else 0,
    }


# ── Hard-pity worst-case analysis ────────────────────────────

def hard_pity_info(inp: CalcInputs) -> dict:
    """Mirrors hardPityLossInfo() in the HTML JS (exact, no RNG)."""
    if inp.need <= 0:
        return {
            "loss_affordable":      0,
            "max_possible_losses":  0,
            "pulls_worst_no_loss":  0,
            "pulls_worst_all_losses": 0,
            "hard_guaranteed":      True,
        }
    first_cost          = max(1, inp.hard - inp.pity)
    events_affordable   = (1 + (inp.pulls - first_cost) // inp.hard
                           if inp.pulls >= first_cost else 0)
    raw_loss_affordable = events_affordable - inp.need
    max_possible_losses = max(0, inp.need - (1 if inp.guarantee else 0))
    loss_affordable     = max(-1, min(max_possible_losses, raw_loss_affordable))
    pulls_worst_no_loss   = first_cost + inp.hard * (inp.need - 1)
    pulls_worst_all_losses = first_cost + inp.hard * (inp.need + max_possible_losses - 1)
    hard_guaranteed     = raw_loss_affordable >= max_possible_losses

    return {
        "loss_affordable":        loss_affordable,
        "max_possible_losses":    max_possible_losses,
        "pulls_worst_no_loss":    pulls_worst_no_loss,
        "pulls_worst_all_losses": pulls_worst_all_losses,
        "hard_guaranteed":        hard_guaranteed,
    }


# ── Public entry point ────────────────────────────────────────

def calc(pulls: int,
         current_e: int  = -1,
         target_e:  int  = 0,
         pity:      int  = 0,
         guarantee: bool = False,
         four_pity: int  = 0) -> tuple[dict, dict]:
    """
    Run the full calculation and return (sim_results, hard_pity_info).
    Suitable for calling from an async context via run_in_executor.
    """
    inp = CalcInputs(
        pulls=pulls,
        current_e=current_e,
        target_e=target_e,
        pity=pity,
        guarantee=guarantee,
        four_pity=four_pity,
    )
    sim = run_simulations(inp)
    hi  = hard_pity_info(inp)
    return inp, sim, hi
