# Regulation retrieval

The assistant answers "what does the rule say" from the acquired regulatory documents, with the document, page and
regulator beside every passage. This note records the design and how to run it. Provenance of each file is in
`EIOS/data/corpus/regulatory/manifest.yaml`.

## How it works

- **Capability** `knowledge.regulation`, tool `search_regulations`, offered to the AML investigator and the compliance
  auditor. Arguments: a query, an optional regulator (`MT`, `LB`, `US`, `INTL`) and a limit.
- **Result** is marked untrusted. Each passage carries `passage_id`, document, title, jurisdiction, kind, `pages` (a
  label, not a figure) and the text. No passage is an answer in itself: nothing found returns an empty list and a note,
  and an index that cannot be reached is a typed `DATA_UNAVAILABLE`, never "no hits".
- **The model never types what a rule says.** The draft shows a passage with `{{quote:<passage_id>}}`; the assembler
  prints the text from this turn's result as a quotation with its credit line (`— Title, p. 41-42 (MT)`) and returns the
  passage as a source for the chat. A number the model types beside it is still rejected, and a passage id that no
  tool returned this turn is rejected. Text from a document is shown, never executed: it cannot become a placeholder.
- **The faithfulness judge** exempts a quotation only when its text and credit line equal a passage in a tool result of
  the same turn (`agent_gates/core/quotes.py`). An altered or invented quotation is judged like any other text.

## Why Agent Search

Agent Search (formerly Vertex AI Search) parses with a layout parser, chunks along headings and returns each chunk with its
page span and document metadata, which is exactly a citation. RAG Engine and Vector Search would mean building the parser,
the chunker and the citation mapping ourselves; the corpus is six documents, so the managed path is the proportionate one.
`VertexAiSearchTool` (the model-side built-in) is not used: its passages reach the model outside the port, so they would
bypass fact ids, the untrusted mark and tool-result screening. Our tool calls the service through
`eios.knowledge.agent_search` behind the `RegulationIndex` seam, so the offline gates run on an in-memory index.

## Running it

- **Infra** (dev sandbox, own state): `EIOS/infra/sandboxes/knowledge`, module `EIOS/infra/modules/knowledge`.
  A private versioned bucket and one data store with layout parsing and layout-aware chunks. No engine is created.
- **Load the corpus**: `python -m tools.ingest_regulations --project <id> --data-store <id> --bucket <name>` verifies each
  file's sha256 and prints the plan; add `--execute` to upload and import. Importing is the step that costs, because the
  data store parses every page.
- **Configure the gateway**: set `EIOS_KNOWLEDGE_DATA_STORE` and `GOOGLE_CLOUD_PROJECT`. Without them the tool says the
  index is not configured.
- **Measure retrieval**: `python -m evals.knowledge.run --project <id> --data-store <id>` runs the cases in
  `evals/knowledge/cases.yaml` (page-level truth read from the files) and reports recall at 1, 3 and 5 and the share of
  unanswerable questions that returned nothing.

## Limits

- Page numbers are PDF page indexes, which can differ from the numbers printed on a page.
- The relevance threshold defaults to LOW `[ASSUMPTION]`; tune it with the retrieval cases, not by feel.
- The jurisdiction filter is exercised against the real index by the retrieval cases, not by unit tests.
- The offline agent baseline answers from labelled test passages (origin `fixture`); it shows routing and assembly, not
  retrieval quality.
- SAR drafts do not cite a rule yet; the dossier does not pick the rule for an entity's licensing jurisdiction yet.
