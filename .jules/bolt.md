## 2024-10-14 - [Memoizing reduce in React renders]
**Learning:** React re-evaluates all variables not wrapped in a `useMemo` on every render. If an array reduction is expensive and done directly inside the component body or JSX (e.g., `partners.reduce`), memoizing it saves CPU cycles, especially with long arrays or frequent renders.
**Action:** Extract inline array processing (`filter`, `reduce`) to `useMemo` hooks when dealing with list components or scatter plots that re-render frequently.
