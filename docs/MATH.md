# Swarm Desk — The Maths

Every formula below is the formula the code actually runs
(`swarm_desk/engine.py`). Nothing here is aspirational: if the code and
this document ever disagree, the code is the truth and this document is
a bug.

## Inputs and features

Raw signals per asset (all optional, defaults in parentheses):

| Signal | Range | Default |
|---|---|---|
| `momentum` | $[-1, 1]$ | 0 |
| `volatility` | $[0, 1]$ | 0.5 |
| `value` | $[-1, 1]$ | 0 |
| `sentiment` | $[-1, 1]$ | 0 |

The engine converts them into five features $x_k \in [-1, 1]$:

$$x_{\text{momentum}} = \text{clip}(\text{momentum}), \quad
  x_{\text{value}} = \text{clip}(\text{value}), \quad
  x_{\text{sentiment}} = \text{clip}(\text{sentiment})$$

Volatility enters inverted, as a **calm** feature — calm markets score
positive:

$$x_{\text{calm}} = 1 - 2 \cdot \text{volatility}$$

## Headline keyword scoring

For one headline $t$, let $P(t)$ be the number of tokens in the positive
keyword set and $N(t)$ the number in the negative set:

$$h(t) = \begin{cases} \dfrac{P(t) - N(t)}{P(t) + N(t)} & P(t) + N(t) > 0 \\ 0 & \text{otherwise} \end{cases}$$

The headline feature is the mean over all headlines ($\bar{h} = 0$ when
there are none):

$$x_{\text{headlines}} = \frac{1}{H}\sum_{t} h(t)$$

**Optional LLM mode** (`use_llm=True` with `SWARM_LLM_*` configured):
the keyword score is blended 50/50 with the model's read $L$:

$$x_{\text{headlines}} \leftarrow 0.5 \cdot x_{\text{headlines}} + 0.5 \cdot L$$

Offline or unconfigured, $L$ does not exist and the pure keyword score
is used. The default path never touches the network.

## Round 1 — stances

Persona $i$ has weights $w_{ik}$ over the five features, a bias $b_i$,
and a noise scale $\sigma_i$. Its Round-1 stance is

$$s_i^{(1)} = \text{clip}\!\left( \sum_{k} w_{ik}\, x_k \;+\; b_i \;+\; \varepsilon_i, \; -1, \; 1 \right),
\qquad \varepsilon_i \sim \mathcal{N}(0, \sigma_i)$$

The noise is drawn from a `random.Random` seeded with the string
`swarm-desk:{seed}:{ASSET}`, so a run is fully reproducible: same
inputs, same seed, same verdict, byte for byte.

A persona's confidence in its own stance is

$$c_i = \text{clip}\left( 0.30 + 0.70 \cdot |s_i|,\; 0,\; 1 \right)$$

## Round 2 — the debate

Personas see the Round-1 swarm mean $\mu^{(1)} = \frac{1}{N}\sum_j s_j^{(1)}$
and shift by their herd coefficient $h_i$:

$$s_i^{(r)} = \text{clip}\!\left( s_i^{(r-1)} + h_i \left( \mu^{(r-1)} - s_i^{(r-1)} \right) + \varepsilon_i', \; -1, \; 1 \right),
\qquad \varepsilon_i' \sim \mathcal{N}\!\left(0, \tfrac{\sigma_i}{2}\right)$$

- $h_i > 0$: herder — moves toward consensus (retail watcher $+0.50$).
- $h_i < 0$: contrarian — moves away from it (contrarian $-0.60$).
- $h_i = 0$: ignores the crowd (quant statistician).

Debate rounds repeat for $r = 2 \dots R$ (`rounds` parameter, default 2).

## Aggregation

From the final stances $s_i$ ($N = 9$ personas):

$$\mu = \frac{1}{N}\sum_i s_i, \qquad
  B^{+} = \frac{\#\{s_i > 0\}}{N}, \qquad
  B^{-} = \frac{\#\{s_i < 0\}}{N}$$

**Majority conviction** $M$ — the average strength of the winning side,
signed toward it (and $0$ when $\mu = 0$ exactly):

$$M = \begin{cases} \text{mean of } \{s_i : s_i > 0\} & \mu > 0 \\ -\,\text{mean of } \{|s_i| : s_i < 0\} & \mu < 0 \\ 0 & \mu = 0 \end{cases}$$

**Consensus** $A$ — how one-sided the split is:

$$A = \left| B^{+} - B^{-} \right|$$

**Confidence** — conviction does most of the work, consensus confirms:

$$\boxed{\;C = \text{clip}\left( 0.65 \cdot M + 0.35 \cdot A, \; 0, \; 1 \right)\;}$$

The population standard deviation of the final stances is also computed
and reported as *dispersion* for transparency; it is not an input to $C$.

Worked checks (also unit tests):

| Stances | $M$ | $A$ | $C$ |
|---|---|---|---|
| $[1, 1, 1, 1]$ | 1.0 | 1.0 | **1.000** |
| $[1, -1, 1, -1]$ | 0 | 0 | **0.000** |
| $[0.5, 0.5]$ | 0.5 | 1.0 | **0.675** |

## Labels and the gate

Verdict label from the mean stance $\mu$:

| $\mu$ | Label |
|---|---|
| $\ge 0.35$ | BULLISH |
| $0.10$ to $0.35$ | LEAN BULLISH |
| $-0.10$ to $0.10$ | NEUTRAL |
| $-0.35$ to $-0.10$ | LEAN BEARISH |
| $\le -0.35$ | BEARISH |

The H-QRD Agent 02 gate mapping:

$$\text{gate}(C) = \begin{cases} \texttt{KEEP} & C \ge 0.70 \\ \texttt{PRUNE-CANDIDATE} & C < 0.70 \end{cases}$$

That is the entire contract: Swarm Desk emits $C$; Agent 02 keeps the
asset only when the swarm's conviction clears 0.70.
