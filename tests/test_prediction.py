from dataclasses import FrozenInstanceError
import json

import numpy as np
import pytest

from arucomarket.config import Config
from arucomarket.state import Engine
from arucomarket.recording import Recorder, replay
from arucomarket.capture import Frame
from test_core import obs


def feed(engine, t, height=None, ambiguous=False):
    frame = 0 if engine.frame_id is None else engine.frame_id + 1
    raw = [] if height is None else [obs(t=t, frame=frame, y=1-height)]
    if ambiguous:
        raw.append(obs(t=t, frame=frame, x=.9, y=1-height))
    engine.process(t, frame, 'test', raw)
    return raw


def opened(direction='UP'):
    engine = Engine(Config())
    sign = 1 if direction == 'UP' else -1
    for t in [0, .1, .2, .31, .41]:
        feed(engine, t, .5 + sign * .1 * t)
    assert engine.market.rounds[0]['status'] == 'OPEN'
    assert engine.market.rounds[0]['terms'].direction == direction
    return engine


@pytest.mark.parametrize('direction,height,result', [
    ('UP', .8, 'WIN'), ('UP', .2, 'LOSS'), ('DOWN', .2, 'WIN'), ('DOWN', .8, 'LOSS'),
])
def test_frozen_bet_and_fixed_stake_payout(direction, height, result):
    engine = opened(direction)
    round_ = engine.market.rounds[0]
    terms = round_['terms']
    with pytest.raises(FrozenInstanceError):
        terms.direction = 'DOWN'
    assert engine.market.balances[0] == 990
    for t in [.5, .6, .7, .8]:
        feed(engine, t, .5 - .1 * t)
    assert round_['terms'] is terms  # Reversing motion cannot rewrite the wager.
    feed(engine, terms.expiry, height)
    assert round_['status'] == result
    assert round_['settlement_height'] == pytest.approx(height)
    expected = 990 + (10 * 100 / terms.entry_quote if result == 'WIN' else 0)
    assert engine.market.balances[0] == pytest.approx(expected)
    assert engine.market.errors[0]['count'] == 1
    feed(engine, terms.expiry + .1, height)
    assert engine.market.balances[0] == pytest.approx(expected)
    assert engine.market.counts[0][result] == 1
    assert engine.market.rounds[0] is round_


def test_neutral_refund_and_error_baseline():
    engine = opened()
    terms = engine.market.rounds[0]['terms']
    feed(engine, terms.expiry, terms.opening_height)
    ball = engine.snapshot()['market']['balls'][0]
    assert ball['round']['status'] == 'NEUTRAL'
    assert ball['balance'] == 1000
    assert ball['hold_mae'] == 0
    assert ball['forecast_mae'] > 0
    assert ball['round']['quotes'][-1][1] == terms.entry_quote


@pytest.mark.parametrize('ambiguous', [False, True])
def test_missing_or_ambiguous_expiry_is_void_not_guessed(ambiguous):
    engine = opened()
    terms = engine.market.rounds[0]['terms']
    feed(engine, terms.expiry, .8 if ambiguous else None, ambiguous)
    assert engine.market.rounds[0]['status'] == 'OPEN'
    feed(engine, terms.expiry + .36, .8, ambiguous)
    assert engine.market.rounds[0]['status'] == 'VOID'
    assert engine.market.balances[0] == 1000
    assert engine.market.errors[0]['count'] == 0


def test_first_fresh_sighting_inside_grace_and_no_preexpiry_settlement():
    engine = opened()
    terms = engine.market.rounds[0]['terms']
    feed(engine, terms.expiry - .01, .8)
    feed(engine, terms.expiry + .1)
    assert engine.market.rounds[0]['status'] == 'OPEN'
    feed(engine, terms.expiry + .2, .2)
    assert engine.market.rounds[0]['status'] == 'LOSS'
    assert engine.market.rounds[0]['settled_at'] == terms.expiry + .2


def test_freshness_gaps_quotes_and_no_invented_samples():
    engine = opened()
    observations = len(engine.histories[0])
    model = engine.market.forecasts[0]
    feed(engine, .5)
    assert engine.market.rounds[0]['quotes'][-1][2] == 'estimated'
    assert engine.market.forecasts[0] is model
    assert len(engine.histories[0]) == observations
    # A long-gap sighting corrects position while velocity is still estimated.
    feed(engine, 3.5, .9)
    assert engine.market.forecasts[0].height == pytest.approx(.9)
    assert engine.market.forecasts[0].sightings == 1
    assert engine.market.rounds[0]['quotes'][-1][2] == 'estimated'
    json.dumps(engine.snapshot(), allow_nan=False)


def test_missing_marker_keeps_pricing_without_becoming_more_certain():
    engine = opened()
    round_ = engine.market.rounds[0]
    terms = round_['terms']
    anchor = engine.market.forecasts[0]
    observed_count = len(engine.histories[0])
    previous_spread = anchor.projected_spread(terms.expiry, engine.timestamp)
    old_quotes = [list(q) for q in round_['quotes']]
    for t in [.6, 1., 2., 3.6, terms.expiry - .01]:
        feed(engine, t)
        quote = round_['quotes'][-1]
        assert quote[0] == t and quote[2] == 'estimated'
        assert 0 < quote[1] < 100
        spread = engine.market.forecasts[0].projected_spread(terms.expiry, t)
        assert spread > previous_spread
        previous_spread = spread
        assert len(engine.histories[0]) == observed_count
        assert engine.market.forecasts[0] is anchor
        assert round_['terms'] is terms
    assert engine.states[0] == 'lost'
    assert list(round_['quotes'])[:len(old_quotes)] == old_quotes
    assert round_['quotes'][-1][1] != round_['quotes'][-2][1]
    feed(engine, terms.expiry + .1)
    assert round_['quotes'][-1][0] == terms.expiry
    assert round_['status'] == 'OPEN'  # A projected quote is not settlement evidence.
    feed(engine, terms.expiry + .36)
    assert round_['status'] == 'VOID'
    assert round_['quotes'][-1][2] == 'settlement'
    assert engine.market.balances[0] == 1000


def test_reacquisition_replaces_projection_without_rewriting_history():
    engine = opened()
    round_ = engine.market.rounds[0]
    terms = round_['terms']
    feed(engine, 1.)
    before = [list(q) for q in round_['quotes']]
    feed(engine, 1.2, .3)
    assert round_['quotes'][-1][2] == 'sighting'
    assert list(round_['quotes'])[:-1] == before
    assert round_['terms'] is terms
    assert engine.market.forecasts[0].issued == 1.2
    assert engine.market.forecasts[0].height == pytest.approx(.3)
    assert engine.market.forecasts[0].velocity < 0
    assert engine.snapshot()['market']['balls'][0]['evidence_age'] == 0


def test_expiry_projection_cannot_see_a_later_sighting():
    a, b = opened(), opened()
    expiry = a.market.rounds[0]['terms'].expiry
    feed(a, expiry + .2, .9)
    feed(b, expiry + .2, .1)
    quotes_a = a.market.rounds[0]['quotes']
    quotes_b = b.market.rounds[0]['quotes']
    assert quotes_a[-2] == quotes_b[-2]
    assert quotes_a[-2][0] == expiry
    assert quotes_a[-1][1] == 100 and quotes_b[-1][1] == 0


def test_stationary_and_sparse_history_do_not_open_bets():
    engine = Engine(Config())
    for t in [0, .1, .2, .3, .4, .5]:
        feed(engine, t, .5)
    assert engine.market.rounds[0] is None
    for t, height in [(4., .2), (7.5, .3), (11., .4), (14.5, .5)]:
        feed(engine, t, height)
    assert engine.market.rounds[0] is None


def test_interpolation_uses_two_real_sightings_without_inventing_observations():
    engine = Engine(Config())
    feed(engine, 0., .4)
    feed(engine, 1.)
    assert engine.market.forecasts[0] is None
    assert engine.market.rounds[0] is None  # The second endpoint is not known yet.
    feed(engine, 2., .6)
    forecast = engine.market.forecasts[0]
    assert forecast.velocity == pytest.approx(.1)
    assert forecast.height == pytest.approx(.6)
    assert forecast.sightings == 2
    assert forecast.interpolation_steps == 13
    assert forecast.largest_gap == 2
    assert len(engine.histories[0]) == 2
    assert [c.start for c in engine.candles[0]] == [0, 2]
    assert engine.market.rounds[0]['terms'].direction == 'UP'
    assert forecast.noise > .025  # Sparse interpolation widens the estimate.


def test_resampling_weights_time_instead_of_dense_detection_bursts():
    from arucomarket.prediction import estimate
    def forecast_for(times):
        engine = Engine(Config())
        for t in times:
            feed(engine, t, .4 + .1 * t)
        return estimate(engine.histories[0], 1.2, 3.)
    sparse = forecast_for([0., 1.2])
    burst = forecast_for([0., .01, .02, .03, .04, 1.2])
    assert sparse.velocity == pytest.approx(burst.velocity)
    assert sparse.at(4.) == pytest.approx(burst.at(4.))
    assert sparse.interpolation_steps == burst.interpolation_steps == 13


def test_duplicate_frame_reset_and_snapshot_are_stable():
    engine = opened()
    before = engine.snapshot()
    engine.process(engine.timestamp, engine.frame_id, 'test', [])
    assert before == engine.snapshot()
    feed(engine, .51, .8)
    assert before['market']['balls'][0]['round']['quotes'] != engine.snapshot()['market']['balls'][0]['round']['quotes']
    engine.reset()
    assert engine.market.balances[0] == 1000
    assert engine.market.rounds[0] is None
    assert not engine.market.results[0]


def test_replay_reproduces_forecasts_quotes_and_payouts(tmp_path):
    path = tmp_path / 'market.jsonl'
    engine = Engine(Config())
    recorder = Recorder(path, engine.config)
    for i in range(121):
        t = i / 10
        raw = feed(engine, t, None if i % 10 in (5, 6, 7) else .5 + .2 * np.sin(t))
        recorder.frame(Frame(np.zeros((2, 2, 3), np.uint8), t, engine.frame_id, 'test'), raw)
    recorder.close()
    assert sum(engine.market.counts[0].values()) >= 2
    assert replay(path).snapshot() == engine.snapshot()
