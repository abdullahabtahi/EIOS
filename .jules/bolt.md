## 2025-05-18 - [NetworkX Hub Suppression Clustering Optimization]
**Learning:** [The codebase's `detect_communities` function in `property_graph.py` was doing a deep copy of the entire graph and then a loop to remove edges from "hub" nodes just to exclude them from the resulting communities. This is extremely slow for large graphs ($O(V+E)$ copy, then expensive edge removal). Because the original code excluded size-1 components anyway (`len(c) > 1`), a simple `subgraph` excluding those hub nodes is functionally equivalent and vastly faster.]
**Action:** [When working with NetworkX graphs to find communities or components while excluding specific nodes, always use `subgraph` with a filtered list of valid nodes instead of copying the graph and modifying it.]

## 2025-05-18 - [Pandas Graph Construction Optimization]
**Learning:** [Using pandas `.iterrows()` inside hot loops to construct large NetworkX graphs incurs severe performance penalties due to per-row Series object instantiation overhead. Iterating over 100k rows can take over 6 seconds.]
**Action:** [Always prefer `.itertuples(index=False)` for read-only iterations over large pandas DataFrames. When accessing optional columns, use `getattr(row, 'column_name', default)` instead of `row.get('column_name', default)`.]
