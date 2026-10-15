# Executive workstation on engines (Phase 2b)

The executive screen and the assistant's executive tools no longer read hand-written numbers. They read
`EngineExecutiveService` (`src/eios/dataplane/executive_service.py`), built once with the other planes by
`dataplane.plane`. `EIOS_DATA_PLANE=fixture` keeps the old service for unit tests. Origin on the wire is `engine`.

## What is computed

| Surface | Source |
|---|---|
| Competitive horizon, forecast | A seeded two-year daily firm series (`foundry/scenarios/executive_world.py`) |
| Partner horizon, top risks, opportunities | The partner engine's scored radar, hazard model and playbook counterfactuals |
| Client horizon, ring risk | The AML engine's top cases and deposit facts |
| Causal graph | `synthesis/scm_fit.py`: each edge fitted from the series and gated by the refuter battery |
| 28-day projection and interval | `synthesis/backtest.py`: rolling-origin backtest of the ridge forecaster, empirical interval |
| What-if | `ScenarioSimulator` over the fitted graph; regional allocation by exposure; playbooks ranked by margin kept |

Headlines are formatted from computed values. Nothing in a figure is typed.

## How it is checked

The world plants the coefficients (`ExecutiveTruth`) and one control: a spread series that rides on the competitor and
causes nothing. Only the evaluation reads the truth.

- The fit recovers the planted chain to a 1.5% largest coefficient error on the default world `[MEASURED]`, and within
  4% on forty other seeds `[MEASURED]`.
- The control, once adjusted for the competitor it rides on, is rejected by the gate. Without the adjustment the
  refuters accept it on every seed tried `[MEASURED]`: they cannot see confounding, so the adjustment set is a domain
  input, not something the gate finds. One seed in forty accepted the adjusted control as well `[MEASURED]`, which is
  the gate's false-accept rate on a null at this sample size.
- The projection beats carrying today's value forward (error 0.74 times that of persistence) and its 90% interval held
  87% out of sample over 75 past origins `[MEASURED]`.
- The what-if answers in under a millisecond on the default world `[MEASURED]` against the 200 ms budget `[TARGET]`,
  and its regional attribution closes to exactly 100.00% by the largest-remainder rule.

## Decisions worth knowing

- Slope fits standardise first. The existing ridge penalty is in raw units and shrank a rate-sized variable to a tenth
  of its true effect; the placebo p-value is now the median of five runs, because one run fails a true edge one time
  in twenty.
- Trend and the quarterly cycle are controls on the revenue edge. Without them slow drift reads as an effect.
- A shock whose resulting level lies outside the history is labelled correlation only and says why.
- The spread shock has no tested path to revenue, so the what-if refuses it (HTTP 422, tool error `DATA_UNAVAILABLE`).
  The shock on offer is `competitor_payout_increase`.
- Mitigation economics are the partner engine's own playbook prices and hazard counterfactuals, capped at the loss. They
  are model projections, not causal estimates, and say so.
- The old wire fields `projected_ebitda_impact_usd` and `client_turnover_delta_pct` were revenue and first-time deposits,
  not EBITDA and turnover; they are renamed `projected_revenue_impact_usd` and `first_deposit_delta_pct`.

## Not done here

Operations is still fixtures (next). The firm series is synthetic like every other world. Executive actions stage
through the intent hub exactly like the partner plays; the what-if's regional defences are advice, not stageable.
