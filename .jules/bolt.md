## 2025-05-18 - [NetworkX Hub Suppression Clustering Optimization]
**Learning:** [The codebase's `detect_communities` function in `property_graph.py` was doing a deep copy of the entire graph and then a loop to remove edges from "hub" nodes just to exclude them from the resulting communities. This is extremely slow for large graphs ($O(V+E)$ copy, then expensive edge removal). Because the original code excluded size-1 components anyway (`len(c) > 1`), a simple `subgraph` excluding those hub nodes is functionally equivalent and vastly faster.]
**Action:** [When working with NetworkX graphs to find communities or components while excluding specific nodes, always use `subgraph` with a filtered list of valid nodes instead of copying the graph and modifying it.]
## 2026-11-03 - Replaced iterrows with itertuples
**Learning:** Pandas .iterrows() is extremely slow due to creating a Series object for each row. Using .itertuples() creates namedtuples instead, resulting in significant performance improvements.
**Action:** Use .itertuples() instead of .iterrows() for iterating over DataFrame rows, and safely access optional columns using getattr(row, 'column_name', default_value).
