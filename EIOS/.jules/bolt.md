## 2025-01-30 - Pandas iterrows() bottleneck
**Learning:** `pandas.DataFrame.iterrows()` combined with row-by-row dictionary construction is extremely slow, specifically in `PartnerFeatureExtractor.build_person_period_df` which creates permutations of data.
**Action:** Replace `iterrows` loops that construct DataFrames with vectorized operations like `df.loc[df.index.repeat()]` and `numpy.tile()`. This provides a ~150x speedup for data expansion tasks.
