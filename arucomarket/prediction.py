"""Source-time paper market. Forecasts never become observations.

Quotes and bands are experimental model estimates, not calibrated probabilities.
"""
from collections import deque
from dataclasses import dataclass, asdict, replace
from math import ceil, erf, exp, sqrt

import numpy as np


@dataclass(frozen=True)
class Forecast:
    issued: float
    height: float
    velocity: float
    noise: float
    x: float
    sightings: int = 0
    interpolation_steps: int = 0
    largest_gap: float = 0.

    def at(self, seconds):
        # Damping prevents short bursts from extrapolating indefinitely.
        return self.height + self.velocity * 1.5 * (1 - exp(-seconds / 1.5))

    def spread(self, seconds):
        return self.noise + .045 * sqrt(seconds) + .03 * seconds

    def projected_spread(self, target, now):
        # An unseen marker cannot become more certain just because expiry nears.
        # Keep the original target-time spread and add a missing-evidence penalty.
        return self.spread(max(0., target - self.issued)) + .06 * max(0., now - self.issued)

    def reanchor(self, sample):
        """Correct position after reacquisition even before velocity can be refit."""
        age = max(0., sample.timestamp - self.issued)
        return replace(self, issued=sample.timestamp, height=1 - sample.normalised[1],
                       velocity=self.velocity * exp(-age / 1.5), noise=self.spread(age),
                       x=sample.normalised[0], sightings=1, interpolation_steps=0, largest_gap=age)


@dataclass(frozen=True)
class Terms:
    number: int
    opened: float
    expiry: float
    opening_height: float
    direction: str
    entry_quote: float
    stake: float
    neutral: float
    forecast: Forecast


def estimate(history, now, max_gap):
    """Fit an evenly spaced, past-only trace between actual sightings.

    Include one anchor before the 1.2s fit window when needed. No interpolation
    exists beyond the last real sighting, and stale intervals cannot be bridged.
    The extra fitting points are never counted as independent observations.
    """
    if not history or history[-1].timestamp != now:
        return None
    recent = []
    for sample in reversed(history):
        if recent and recent[-1].timestamp - sample.timestamp > max_gap:
            break
        recent.append(sample)
        if sample.timestamp <= now - 1.2:
            break
    recent.reverse()
    if len(recent) < 2 or recent[-1].timestamp - recent[0].timestamp < .3:
        return None
    observed_ts = np.array([s.timestamp - now for s in recent])
    observed_heights = np.array([1 - s.normalised[1] for s in recent])
    start = max(-1.2, float(observed_ts[0]))
    ts = np.linspace(start, 0., max(4, ceil(-start * 10) + 1))
    heights = np.interp(ts, observed_ts, observed_heights)
    centered = ts - ts.mean()
    velocity = float(np.dot(centered, heights - heights.mean()) / np.dot(centered, centered))
    residual = observed_heights - (heights.mean() + velocity * (observed_ts - ts.mean()))
    largest_gap = float(np.max(np.diff(observed_ts)))
    # Use real residuals and widen for sparse evidence, never divide by grid size.
    noise = max(.025, float(np.std(residual)) * 2) + .025 * largest_gap
    return Forecast(now, float(observed_heights[-1]), velocity, noise, recent[-1].normalised[0],
                    len(recent), len(ts), largest_gap)


def outcomes(forecast, expiry, opening, neutral, direction, now=None):
    seconds = max(0., expiry - forecast.issued)
    mean = forecast.at(seconds)
    sigma = forecast.projected_spread(expiry, forecast.issued if now is None else now)
    cdf = lambda value: .5 * (1 + erf((value - mean) / (sigma * sqrt(2))))
    down = cdf(opening - neutral)
    up = 1 - cdf(opening + neutral)
    return (up if direction == "UP" else down), max(0., 1 - down - up)


class PaperMarket:
    horizon = 4.
    neutral = .015  # 1.5 percentage points of ROI height
    stake = 10.
    settlement_window = .35
    result_hold = 1.5

    def __init__(self, config):
        self.config = config
        self.rounds = {mid: None for mid in config.active_ids}
        self.forecasts = {mid: None for mid in config.active_ids}
        self.models = {mid: None for mid in config.active_ids}
        self.now = None
        self.messages = {mid: "Waiting for fresh sightings" for mid in config.active_ids}
        self.results = {mid: deque(maxlen=30) for mid in config.active_ids}
        self.balances = {mid: 1000. for mid in config.active_ids}
        self.counts = {mid: dict(WIN=0, LOSS=0, NEUTRAL=0, VOID=0) for mid in config.active_ids}
        self.errors = {mid: dict(count=0, forecast=0., hold=0.) for mid in config.active_ids}
        self.sequence = 0

    def process(self, now, histories, states):
        self.now = now
        for mid, history in histories.items():
            fresh = states[mid] == "observed"
            forecast = estimate(history, now, self.config.lost_after) if fresh else None
            self.forecasts[mid] = forecast
            round_ = self.rounds[mid]
            if round_ and round_["status"] == "OPEN":
                terms = round_["terms"]
                if now >= terms.expiry:
                    # Complete the estimate to expiry using only the model known
                    # before expiry, even when the source jumps over that instant.
                    if round_["quotes"][-1][0] < terms.expiry:
                        self.append_quote(mid, terms.expiry, self.models[mid], "estimated")
                    if fresh and now <= terms.expiry + self.settlement_window:
                        height = 1 - history[-1].normalised[1]
                        delta = height - terms.opening_height
                        result = ("NEUTRAL" if abs(delta) <= terms.neutral + 1e-12 else
                                  "WIN" if (delta > 0) == (terms.direction == "UP") else "LOSS")
                        self.settle(mid, now, result, height)
                    elif now >= terms.expiry + self.settlement_window:
                        self.settle(mid, now, "VOID", None)
                    self.messages[mid] = ("Awaiting expiry sighting" if round_["status"] == "OPEN"
                                          else round_["status"])
                    continue
                if forecast:
                    self.models[mid] = forecast
                elif fresh:
                    self.models[mid] = self.models[mid].reanchor(history[-1])
                model = self.models[mid]
                self.forecasts[mid] = model
                self.append_quote(mid, now, model, "sighting" if forecast else "estimated")
                if forecast:
                    self.messages[mid] = "Quote updated from fresh sightings"
                elif fresh:
                    self.messages[mid] = "Estimated motion · position corrected by fresh sighting"
                else:
                    self.messages[mid] = f"Estimated quote · no clear sighting for {now - model.issued:.1f}s"
                continue
            if round_ and now < round_["settled_at"] + self.result_hold:
                self.messages[mid] = round_["status"]
                continue
            if not forecast:
                self.messages[mid] = "Waiting for fresh motion history"
                continue
            delta = forecast.at(self.horizon) - forecast.height
            if abs(delta) <= self.neutral:
                self.messages[mid] = "No bet · forecast inside neutral zone"
                continue
            if self.balances[mid] < self.stake:
                self.messages[mid] = "No bet · insufficient virtual credits"
                continue
            direction = "UP" if delta > 0 else "DOWN"
            win, neutral = outcomes(forecast, now + self.horizon, forecast.height, self.neutral, direction)
            entry = min(99., max(1., 100 * win / max(1e-9, 1 - neutral)))
            self.sequence += 1
            terms = Terms(self.sequence, now, now + self.horizon, forecast.height,
                          direction, entry, self.stake, self.neutral, forecast)
            self.balances[mid] -= self.stake
            self.models[mid] = forecast
            self.rounds[mid] = dict(terms=terms, status="OPEN", quotes=deque([[now, entry, "sighting"]], maxlen=600),
                                    settled_at=None, settlement_height=None, profit=None)
            self.messages[mid] = "Live model quote"

    def append_quote(self, mid, now, model, kind):
        round_ = self.rounds[mid]
        terms = round_["terms"]
        win, neutral = outcomes(model, terms.expiry, terms.opening_height,
                                terms.neutral, terms.direction, now=now)
        quote = min(100., max(0., 100 * win + terms.entry_quote * neutral))
        round_["quotes"].append([now, quote, kind])

    def settle(self, mid, now, result, height):
        round_ = self.rounds[mid]
        terms = round_["terms"]
        payout = (terms.stake * 100 / terms.entry_quote if result == "WIN" else
                  0. if result == "LOSS" else terms.stake)
        self.balances[mid] += payout
        round_.update(status=result, settled_at=now, settlement_height=height, profit=payout - terms.stake)
        round_["quotes"].append([now, 100. if result == "WIN" else
                                 0. if result == "LOSS" else terms.entry_quote, "settlement"])
        self.counts[mid][result] += 1
        if height is not None:
            errors = self.errors[mid]
            errors["count"] += 1
            errors["forecast"] += abs(terms.forecast.at(self.horizon) - height)
            errors["hold"] += abs(terms.opening_height - height)
        self.results[mid].append(dict(number=terms.number, direction=terms.direction,
                                      expiry=terms.expiry, settled_at=now, status=result,
                                      profit=payout - terms.stake, terms=asdict(terms),
                                      settlement_height=height))

    def snapshot(self):
        balls = {}
        for mid, round_ in self.rounds.items():
            frozen = None
            if round_:
                frozen = {**round_, "terms": asdict(round_["terms"]),
                          "quotes": [list(q) for q in round_["quotes"]]}
            errors = self.errors[mid]
            balls[mid] = dict(round=frozen, forecast=asdict(self.forecasts[mid]) if self.forecasts[mid] else None,
                              quote_mode=round_["quotes"][-1][2] if round_ else None,
                              evidence_age=max(0., self.now - self.forecasts[mid].issued) if self.forecasts[mid] else None,
                              message=self.messages[mid], balance=self.balances[mid],
                              counts=dict(self.counts[mid]), results=list(self.results[mid]),
                              scored=errors["count"],
                              forecast_mae=errors["forecast"] / errors["count"] if errors["count"] else None,
                              hold_mae=errors["hold"] / errors["count"] if errors["count"] else None)
        return dict(horizon=self.horizon, neutral=self.neutral, stake=self.stake,
                    settlement_window=self.settlement_window, balls=balls)
