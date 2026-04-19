# |gatecrash⟩

QAOA-powered vehicle routing with a live benchmark UI. Built solo at Carolina Quantum Hacks 2026 in 24 hours.

---

## what is this

gatecrash takes the Travelling Salesman Problem, encodes it as a QUBO (Quadratic Unconstrained Binary Optimization), runs it through a QAOA circuit on Qiskit's Aer simulator, and benchmarks it against a classical greedy solver in real time — same stops, same distance matrix, side by side in a browser.

the frontend lets you drop pins on a Chapel Hill map, hit run, and watch COBYLA iterate live while both solvers race to find the shortest route.

---

## why does this matter

past n=20 stops, the number of possible routes hits 10^16. classical solvers can't brute-force that, so they fall back to heuristics like greedy nearest-neighbor or 2-opt local search. those run fast but there's zero guarantee the result is anywhere near optimal. could be off by a lot.

for a food delivery app that's fine. for an ambulance dispatcher or a food bank running on 4-hour perishable windows, "good enough" isn't really good enough. gatecrash is asking what a quantum solver does with those same inputs.

quantum saving lives isn't only a drug discovery story.

---

## how the encoding works

uses a time-indexed QUBO formulation from Lucas (2014). instead of edge variables, each binary variable `x_i,t` means "stop i is the t-th visit." depot is fixed at slot 0. this gives `(n-1)^2` variables, so 16 qubits at n=5.

two constraints get baked into the Q matrix as penalty terms:

- each stop visited exactly once: `Σ_t x_i,t = 1` for all i
- each time slot holds one stop: `Σ_i x_i,t = 1` for all t

these two together force a permutation matrix, which means subtours are structurally impossible. no subtour-elimination constraints needed (those blow up qubit count fast).

objective minimizes total distance:

```
minimize  Σᵢ d₀,ᵢ · xᵢ,₁                     (depot to first stop)
        + Σₜ Σᵢⱼ dᵢ,ⱼ · xᵢ,ₜ · xⱼ,ₜ₊₁       (consecutive stops)
        + Σᵢ dᵢ,₀ · xᵢ,ₙ₋₁                   (last stop back to depot)
```

---

## the QAOA circuit

```
|ψ(γ,β)⟩ = [ e^(-iβH_M) · e^(-iγH_C) ]^p · H^(⊗n) |0⟩
```

- Hadamard gates put every qubit in superposition — all possible routes at once
- the cost unitary `e^(-iγH_C)` imprints a phase on each state proportional to its route cost
- the mixer `e^(-iβH_M)` spreads amplitude across neighboring bitstrings so the optimizer doesn't get stuck
- after p=2 layers, measuring collapses everything to a single bitstring. low-cost routes show up more often

4 variational parameters (γ₁, β₁, γ₂, β₂) tuned by COBYLA minimizing expected energy across 1024 shots per eval.

---

## output pipeline

1. take the most probable bitstring from 1024 shots
2. decode to a permutation matrix, then to an ordered route
3. check every city got assigned and every slot got filled
4. if something's missing, append it and flag the repair in the UI

---

## resource scaling

| n stops | qubits (n-1)^2 | possible routes (n-1)!/2 | classical solver     |
|---------|----------------|--------------------------|----------------------|
| 5       | 16             | 12                       | exact, trivial       |
| 10      | 81             | 181,440                  | exact, still ok      |
| 20      | 361            | 6.1 x 10^16              | heuristics only      |
| 50      | 2,401          | 1.5 x 10^62              | heuristics only      |
| 100     | 9,801          | 4.7 x 10^157             | heuristics only      |

qubits grow as n^2. routes grow factorially. that gap is the whole argument.

---

## stack

- **quantum:** Qiskit 1.4.2, Aer 0.15.1
- **optimizer:** COBYLA via scipy
- **backend:** FastAPI
- **frontend:** vanilla JS, Leaflet, no build step

---

## structure

```
gatecrash/
├── backend/
│   ├── vrp.py        -- time-indexed TSP QUBO
│   ├── qaoa.py       -- QAOA pipeline: sampler, optimizer, decoder, repair
│   ├── api.py        -- FastAPI + benchmark endpoint
│   ├── classical.py  -- greedy nearest-neighbor baseline
│   ├── distance.py   -- distance matrix
│   └── metrics.py    -- CO2, distance, compute time
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
└── data/
    └── chapel_hill_stops.json
```

---

## running it

```bash
pip install -r requirements.txt
uvicorn backend.api:app --reload
# then open frontend/index.html
```

---

*Carolina Quantum Hacks 2026 · UNC Chapel Hill*
