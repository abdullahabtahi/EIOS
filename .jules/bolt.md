## 2025-05-18 - [NetworkX Hub Suppression Clustering Optimization]
**Learning:** [The codebase's `detect_communities` function in `property_graph.py` was doing a deep copy of the entire graph and then a loop to remove edges from "hub" nodes just to exclude them from the resulting communities. This is extremely slow for large graphs ($O(V+E)$ copy, then expensive edge removal). Because the original code excluded size-1 components anyway (`len(c) > 1`), a simple `subgraph` excluding those hub nodes is functionally equivalent and vastly faster.]
**Action:** [When working with NetworkX graphs to find communities or components while excluding specific nodes, always use `subgraph` with a filtered list of valid nodes instead of copying the graph and modifying it.]

## 2025-05-18 - [Pandas DataFrame Iteration Performance]
**Learning:** [Pandas `.iterrows()` yields a `pd.Series` for each row, resulting in massive object creation overhead when iterating over large datasets like network edges. Benchmarks show `iterrows()` is >10x slower than `.itertuples()` which yields a lightweight `NamedTuple`.]
**Action:** [Whenever iterating over Pandas DataFrames row-by-row, preferentially use `.itertuples()`. Use `getattr(row, "column_name", default_value)` to safely retrieve optional columns in `itertuples()`, which mirrors the behavior of `row.get()` in `iterrows()`.]
