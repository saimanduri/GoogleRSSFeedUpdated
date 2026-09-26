# Requirements: RBI English ⇄ Hindi Translation Model (Data, Fine-tuning, Evaluation)

**Audience:** a Claude Code session running on the project owner's desktop. That machine has an RTX 5090 and internet access to RBI and Government of India websites.
**Owner:** a single developer (beginner level). No team. Automate as much as possible.
**Status of this document:** the build specification. The evidence behind every decision is in [`docs/hindi-translation-model-research.md`](docs/hindi-translation-model-research.md) (research v3). Read that file too, but this document is the one to build from.

---

## 0. Instructions to the Claude Code session reading this

1. **Read this whole file first**, including **§18 (research findings and the reasons for each decision)**. Do not repeat that research. Resolve only the gaps listed in §18.5, at the phase shown there.
2. **Before writing code, confirm the open questions in §3.2** with the owner (use the AskUserQuestion tool). Do not guess them.
3. **Work phase by phase (§14).** Do not start a phase until the previous phase's acceptance criteria are met and shown to the owner.
4. **Keep a progress log** in `translation_corpus/PROGRESS.md`. After each work session, record what was done, what is next, open problems and counts. A new session must be able to resume from it alone.
5. **Commit after every meaningful step**, with clear commit messages. Never commit scraped data to a public repository (§4.3).
6. **Accuracy beats speed.** When unsure whether a document pair or an extraction is correct, mark it `needs_human`. Never guess.
7. **Be honest in reports.** State exact counts (documents, paragraphs, sentences, rejected, flagged). If something failed or was skipped, say so.
8. **Verify what this document marks as unverified**, such as URL patterns, model sizes and licences, before relying on it. It was written in an environment without access to these websites.

---

## 1. Objective

Build a **bidirectional English ⇄ Hindi translation capability for RBI institutional text**: circulars, Master Directions, notifications, press releases, monetary policy documents, reports, FAQs and speeches. It must run fully **on-premise** on one RTX 5090.

Quality priorities, in order:

| # | Priority | What it means in practice |
|---|---|---|
| 1 | **Meaning and legal force preserved exactly** | "shall" stays mandatory; provisos, conditions and exceptions are never dropped |
| 2 | **Approved RBI and Government terminology** | Uses the official glossary term, consistently across a document |
| 3 | **Numbers, amounts, dates and references exact** | ₹5,000 crore never becomes ₹500 crore; circular numbers are unchanged |
| 4 | **Document-level coherence** | Pronouns, repeated terms and cross-references stay consistent across sentences |
| 5 | **Structure preserved** | Paragraph numbering, lists and tables |
| 6 | **Natural institutional Hindi / English** | Official register, not word-for-word |

**Directions:** English→Hindi **and** Hindi→English (both confirmed as required).

**The lasting asset** is the curated, reviewed bilingual corpus, the terminology store and the protected evaluation set. The model can be replaced later; the data is what keeps its value.

---

## 2. Scope

### 2.1 In scope (this build)
- Collect RBI bilingual content **from HTML pages**. Pair each English document with its Hindi counterpart using **published date, subject and reference number**.
- Build a terminology store from **official government glossaries**, including the RBI Banking Glossary and the Rajbhasha portal's Hindi vocabulary (§6.2).
- Ingest the owner's existing **~1 lakh (100,000) English–Hindi pairs** of words, phrases, sentences and paragraphs.
- Have Claude **review every extracted file and every document pair personally** before it enters the corpus (§8).
- Validators for numbers, dates, units and references.
- Deploy **IndicTrans3-beta locally** in the roles defined in §6.4.
- Benchmark the candidate models, fine-tune the best one or two with QLoRA on the RTX 5090 for both directions, and evaluate.
- A local translation service with glossary injection and validators.

### 2.2 Out of scope for now (deferred to later phases, §15)
- Full fine-tuning (needs 80 GB-class on-premise hardware).
- DPO/RL preference training (needs human correction data first).
- A reviewer web UI, dashboards, a lineage database, and a trained RBI-specific quality-estimation model.
- PDF extraction as a primary source (§6.1.3).
- Other Indian languages.

---

## 3. Decisions

### 3.1 Already decided (do not re-open)

| Decision | Choice | Reason (details in research v3) |
|---|---|---|
| Directions | Both EN→HI and HI→EN, **one model** with the direction given in the prompt | LLM-based models support this; each pair gives two training examples |
| Primary data source | **HTML pages** from RBI (English and Hindi), paired by date, subject and reference number | Hindi PDFs often have encoding problems (legacy fonts, broken Unicode) |
| Training data | **Human-translated official text only**; machine-generated text is tagged and capped | Training on another model's output teaches its mistakes |
| Model selection | **Benchmark first**, then fine-tune the top 1–2 | No independent Hindi human evaluation exists for any candidate on RBI text |
| Candidates | IndicTrans2-1B (en-indic and indic-en), IndicTrans3-beta, TranslateGemma-12B, TranslateGemma-27B, plus any translation system the owner uses today | See research v3 §5 |
| Training method | **QLoRA (4-bit)** on the RTX 5090 | Full fine-tuning of 12B+ does not fit in 32 GB |
| Terminology | **Separate, versioned terminology store** injected into the prompt, not left to fine-tuning alone | Fine-tuning cannot guarantee approved terms; terms change over time |
| Validators | Deterministic code checks on every output | Cheap and exact; catch number and reference errors |
| Train/test split | **By document**, never by sentence | Prevents leakage that inflates scores |
| Hosting | On-premise only; no cloud GPUs or hosted translation APIs for confidential data | RBI confidentiality |
| Review | Claude reviews every file and pair (§8); a human spot-checks a sample | The owner's explicit requirement |

### 3.2 Open questions to confirm with the owner before starting

1. **Where to keep the data.** The GitHub repository `saimanduri/GoogleRSSFeedUpdated` is **public**. Scraped documents and the curated corpus must not go into a public repository. Options:
   - (a) make this repository private;
   - (b) create a new **private** repository for data;
   - (c) keep data only on the local disk with backups, and commit only code, manifests and review records.

   **Recommend (b) or (c).**
2. **Existing 1 lakh pairs:** file format and location; origin (human-translated, machine-translated, or mixed); whether they are confidential. If confidential, Claude must not read their contents (§4.2).
3. **Operating system** of the desktop: Linux, or Windows with WSL2. It affects CUDA and bitsandbytes setup.
4. **Current translation system:** is anything in use today that new models must beat? If yes, how can it be run offline for benchmarking?
5. **Human reviewer availability:** can a Hindi/Rajbhasha reviewer give a few hours for blind rating (Phase 5) and for a 5% spot-check of Claude's reviews?
6. **Date range to collect:** for example, the last 10 years, or everything available.
7. **Permission:** confirm that using RBI website content for internal model training is acceptable under RBI's website terms and internal policy.

---

## 4. Constraints

### 4.1 Hardware
- One **RTX 5090, 32 GB VRAM**. Measured requirements (from research, to be confirmed with a test run):
  - 12B model in BF16 is about 24 GB for weights alone, so full fine-tuning is not feasible.
  - 12B QLoRA fits comfortably.
  - 27B QLoRA fits with gradient checkpointing and about 4K sequence length.
- **Run a test training job before planning experiments**, and record actual VRAM use, tokens per second and time per epoch in `PROGRESS.md`.

### 4.2 Confidentiality
- Code runs locally, but **file contents Claude reads are sent to Anthropic's API**.
- **Public RBI web content** (the §6.1 sources) can be read and reviewed by Claude.
- **Confidential material** (the owner's dataset if confidential, internal RBI documents): Claude writes and tests code only on public or sample data. The owner runs the finished scripts on the confidential files. Claude reviews only summary statistics and automated check output, not the text itself.

### 4.3 Repository and licensing
- **Never commit** raw HTML, extracted text, paired corpus or glossaries to a public repository. Add `translation_corpus/data/` to `.gitignore` unless §3.2 Q1 resolves to a private repository.
- Record source URL, retrieval date and publishing authority for every document and glossary entry.
- Check each model's licence before use:
  - IndicTrans2: MIT.
  - TranslateGemma: Gemma Terms of Use and its prohibited-use policy.
  - IndicTrans3-beta: check the model card.
  - NLLB-200: **CC-BY-NC**, so excluded.

### 4.4 Polite, resumable crawling
- Check `robots.txt` and the site's terms first.
- **At most one request every 2–3 seconds**, sequential, with a descriptive User-Agent.
- **Cache every raw response to disk** and never re-download a page already cached, unless a refresh is explicitly requested.
- Crawls must be **resumable**. Keep a crawl state file so an interrupted run continues where it stopped.
- Log every HTTP error; retry with backoff at most three times.

---

## 5. System overview

```
┌────────────────────────── DATA (Phases 1–3) ───────────────────────────┐
│ RBI HTML (EN) ─┐                                                       │
│                ├─► extract ─► encoding checks ─► document pairing       │
│ RBI HTML (HI) ─┘   (main text,   (legacy font,     (date + ref no.      │
│                    structure)     mojibake)         + subject)          │
│                                                        │                │
│                                                        ▼                │
│      paragraph alignment ─► sentence alignment ─► validators            │
│                                                        │                │
│                                                        ▼                │
│              CLAUDE REVIEWS EVERY PAIR (review packet ─► ledger)        │
│                                                        │                │
│                                                        ▼                │
│    dedup ─► quality tier ─► split by document (train / dev / TEST)      │
│                                                                         │
│ Official glossaries + owner's word/phrase pairs ─► terminology store    │
│ Owner's sentence/paragraph pairs ─► same checks ─► corpus               │
└─────────────────────────────────────────────────────────────────────────┘
┌──────────────────────── MODEL (Phases 4–6) ────────────────────────────┐
│ Zero-shot benchmark of all candidates (both directions) on TEST set     │
│   ─► pick top 1–2 ─► QLoRA fine-tune (bidirectional, with context)      │
│   ─► evaluate (automatic + validators + human blind test) ─► gates      │
└─────────────────────────────────────────────────────────────────────────┘
┌──────────────────────── SERVICE (Phase 7) ─────────────────────────────┐
│ document ─► segment + context ─► glossary lookup ─► model ─► validators │
│   ─► output (flags for human review) ─► human edits logged for later    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Data sources

### 6.1 RBI website (primary bilingual source)

#### 6.1.1 Document types, in order of priority

| Priority | Type | Why |
|---|---|---|
| 1 | Notifications / circulars | Core regulatory language; published bilingually |
| 2 | Master Directions / Master Circulars | Dense regulatory and legal language |
| 3 | Press releases | High volume; varied topics; numbers and dates |
| 4 | Monetary policy statements / resolutions | Monetary policy terminology |
| 5 | FAQs | Consumer-facing register |
| 6 | Speeches (where Hindi versions exist) | Discourse and long-form text |
| 7 | Reports (HTML versions only) | Long documents |

#### 6.1.2 URL structure (unverified; inspect the live site first)
- RBI runs a classic site (`www.rbi.org.in`, Hindi section under `/hindi/`) and a newer portal (`website.rbi.org.in`). Both may be live. **Find out which one lists bilingual documents most completely**, and whether English and Hindi pages share an ID.
- The classic site likely uses pages such as `Scripts/NotificationUser.aspx?Id=…` for notifications and `Scripts/BS_PressReleaseDisplay.aspx?prid=…` for press releases, with Hindi equivalents under `/hindi/`. **These are hints from memory, not facts. Verify them.**
- **Do not assume the English and Hindi IDs match.** Pairing must follow §7.3 even if they appear to.

#### 6.1.3 PDFs
- Not a primary source.
- A PDF may be used only when no HTML version exists **and** the extracted text passes all encoding checks (§7.2.3).
- Legacy-font PDFs (Kruti Dev and similar) are **excluded**. Optionally, in a later phase, convert them with a legacy-to-Unicode converter, with 100% Claude review of the converted text.

### 6.2 Official terminology sources
Only **official government or RBI publications**. For every entry, record `authority`, `source_url`, `retrieved_at` and `licence_note`.

| Source | URL | Notes |
|---|---|---|
| RBI Banking Glossary (Rajbhasha Department) | https://website.rbi.org.in/en/web/rbi/banking-glossary | Highest authority for banking terms. Also offered as a downloadable glossary application; inspect the format. |
| Department of Official Language, Hindi vocabulary | https://rajbhasha.gov.in/en/hindi-vocabulary | Official administrative vocabulary; named by the owner |
| Commission for Scientific and Technical Terminology (CSTT) | https://www.cstt.education.gov.in/en | Official technical glossaries (banking, finance, economics, law, administration); check the "Shabd" portal |
| e-Mahashabdkosh (Department of Official Language) | find via rajbhasha.gov.in | Bilingual administrative dictionary; verify availability |
| Legislative Department "Legal Glossary" (Ministry of Law) | find via legislative.gov.in | English–Hindi legal terms; verify availability and format |
| Other regulators and ministries (SEBI, IRDAI, NABARD, Department of Financial Services, Ministry of Finance) | search each site for a Hindi glossary or शब्दावली | Include only if officially published; mark the authority |

**Precedence when sources conflict**, for RBI use: RBI Banking Glossary > Department of Official Language > CSTT > Legislative Department (legal terms) > other regulators. Keep **all** variants with their authority; mark one as `preferred` per domain. Conflicts go to the owner (§13).

### 6.3 The owner's existing ~1 lakh pairs

| Content | Destination |
|---|---|
| Single words, short phrases | Terminology store (candidate status, authority "owner_dataset") |
| Sentences | Corpus, through the same validators and review as scraped data |
| Paragraphs | Corpus as paragraph pairs, then sentence-aligned; the paragraph is kept as context |
| Machine-translated items (if identifiable) | Tier Q2 at most, or terminology mining only |

- **Deduplicate against scraped data.** If an owner pair exists in scraped official data, keep the official version as primary.
- **Remove any pair whose text appears in the test set** (leakage check).

### 6.4 IndicTrans3-beta (deploy locally): allowed roles
1. **Candidate model** in the benchmark.
2. **Alignment helper.** Translate one side to help match sentences within an already-paired document. Its output is used only for matching, never stored as training text.
3. **Disagreement detector.** Segments where its output differs strongly from the official translation, or from other models, go to the top of Claude's review queue.
4. **Back-translation** of RBI documents that exist in only one language. Allowed only as tier Q2, tagged `synthetic: true` with generator and version, and **capped at ≤20% of training examples** (tune through experiments).

**Not allowed:** using IndicTrans3 output as the main training data for documents that already have an official translation.

Check the model card for size, licence and inference requirements before deploying.

---

## 7. Data pipeline: detailed requirements

### 7.1 Crawl
- Build **listing crawlers** per document type and language that collect, for each document:
  - `url`, `lang`, `doc_type`, `published_date` (ISO);
  - `subject` (title as shown);
  - `reference_numbers` (all found on the page, e.g. `RBI/2024-25/123`, `DOR.STR.REC.12/21.04.048/2024-25`, press release numbers);
  - `addressee` where present, and `retrieved_at`.
- Save raw HTML to `data/raw/{source}/{lang}/{doc_type}/{id}.html`, with a sidecar `.meta.json`.
- Keep crawl state for resuming (§4.4).

### 7.2 Extraction
1. **Main content only.** Remove navigation, menus, footers, "print / share" links, breadcrumbs and repeated site boilerplate. Build and test the selectors on at least 20 pages per document type and language before a full run.
2. **Preserve structure:**
   - paragraph boundaries and paragraph labels (1., 2.1, (a), (i));
   - headings and lists;
   - tables as structured rows and columns (not flattened text);
   - footnotes;
   - "Yours faithfully / भवदीय" closings and signatory blocks, tagged separately so they can be excluded from training.
3. **Encoding checks** on every extracted file, using `rbicorpus/normalize.py::encoding_issues`:
   - replacement characters and UTF-8 mojibake;
   - private-use characters;
   - legacy-font text (e.g. Kruti Dev read as Latin);
   - low Devanagari share in Hindi, and unexpected Devanagari in English.

   Any issue → the file is **quarantined** with a reason; it is not dropped silently.
4. Normalise text with `normalize_text`:
   - NFC form;
   - invisible characters removed, **but ZWJ and ZWNJ kept**;
   - whitespace cleaned.
5. Output per document: `data/extracted/{lang}/{doc_id}.json`, following the **Document** schema (§9.1).

### 7.3 Document pairing (EN ⇄ HI)
Pair using the three signals the owner specified. **A pair is `confirmed` only if all of these hold:**

| Signal | Rule |
|---|---|
| Published date | Identical. If the two versions were published on different days, allow ±N days only with the owner's approval, and mark it. |
| Reference number(s) | At least one identical reference number. Hindi pages normally keep these in Latin script; normalise Devanagari digits first. |
| Subject | Consistent: numbers, reference numbers and named schemes in the subject agree. Claude confirms the meaning matches during review (§8). |
| Uniqueness | Mutual best match: this English document's best Hindi candidate has this English document as its best candidate, and no other candidate ties. |

Pairing statuses:
- `confirmed`: all rules hold.
- `probable`: date and subject agree, but a reference number is missing on one side. Goes to review; not auto-accepted.
- `ambiguous`: more than one candidate. Goes to review.
- `unmatched`: no candidate. Recorded; no pair created.

Claude reviews every pair whatever its status. `probable` and `ambiguous` pairs need a specific justification in the review record to be accepted.

Also compute a **body agreement score**: the overlap of numbers, dates and reference identifiers across the full bodies (see `rbicorpus/validators.py`). A low score on a `confirmed` pair is a red flag for review.

### 7.4 Alignment
1. **Paragraph alignment** (`rbicorpus/segment.py::align_paragraphs`):
   - Pair by matching paragraph labels (1., 2.1, (a)) when both sides have unique labels.
   - Otherwise pair by position only if the paragraph counts are equal.
   - Otherwise do not align; send to review.
   - Run `check_pair` on every paragraph pair.
2. **Sentence alignment** within aligned paragraphs:
   - Use a proven aligner (e.g. **Bertalign** or **vecalign** with **LaBSE** embeddings), allowing 1:1, 1:N, N:1 and N:M matches.
   - Evaluate the aligner on 100 hand-checked paragraph pairs before choosing; record precision.
   - IndicTrans3 may assist (§6.4.2).
   - Every sentence pair gets an alignment confidence score.
3. Keep the paragraph as **context** for every sentence pair (§9.2).

### 7.5 Validators (`rbicorpus/validators.py`, extend as needed)

| Check | Status in draft code |
|---|---|
| Numbers: multiset equality after converting Devanagari digits and removing grouping commas | done |
| Dates: English and Hindi month names, numeric formats, compared as ISO dates | done |
| Units: counts of crore/करोड़, lakh/लाख, per cent/%/प्रतिशत | done |
| Reference identifiers: set equality | done |
| Currency symbols (₹, Rs., रु.) | **to add** |
| Basis points (bps / आधार अंक) | **to add** |
| Financial years (2024-25) | **to add** |
| Section, paragraph and annex references ("paragraph 3(b)") | **to add** |
| Table cell values: row/column counts and numbers per cell | **to add** |

- **A failed check means `flag`, never automatic rejection.** Official translations sometimes write a number in words.
- Claude resolves every flag during review, recording `false_positive` with a reason, or rejecting or excluding the segment.

### 7.6 Deduplication
1. Exact duplicate pairs (hash of normalised EN + HI).
2. Same source with different translations: keep all, mark them as a group, and prefer the official, most recent version for training.
3. Near-duplicates: e.g. boilerplate paragraphs repeated in hundreds of circulars. Keep **at most 3 copies** of boilerplate in training so it doesn't dominate.
4. Document-level: the same document reached through different URLs or pages counts as one document.

### 7.7 Quality tiers (every pair carries one)

| Tier | Meaning | Use |
|---|---|---|
| Q5 | Official RBI/Government bilingual publication, pair `confirmed` and approved by Claude, spot-checked by a human | Training + evaluation |
| Q4 | Official publication, `confirmed`, approved by Claude (no human spot-check yet) | Training |
| Q3 | Owner dataset, human-translated, passed validators and Claude review | Training |
| Q2 | Machine or synthetic (IndicTrans3 back-translation, etc.), filtered | Training, capped by quota |
| Q1 | Unreviewed or unverified | Not used for training |
| Q0 | Rejected | Never used; kept with the reason for audit |

### 7.8 Split by document (do this before any training export)
- Split **by document ID**:
  - **TEST (protected)** about 5% of documents, stratified by document type, year and topic;
  - **DEV** about 5%;
  - **TRAIN** the rest.
- All versions of a document (amended, re-issued, HTML/PDF copies) go into the **same** split.
- The TEST set is **frozen and versioned**; never train on it. Before every training export, check that no training text matches TEST text, both exactly and by near-duplicate matching.
- Build dedicated **evaluation subsets**, each ≥50 items where data allows:
  - general;
  - regulatory/legal (shall/may, provisos, "notwithstanding");
  - numbers/currency/dates;
  - references;
  - tables;
  - discourse (pronouns, repeated terms);
  - consumer FAQs;
  - Hindi-original text for HI→EN, if any can be identified.

### 7.9 Terminology store
- One record per (term, sense, authority), following the **GlossaryEntry** schema (§9.3).
- Lookup must handle:
  - Hindi inflection;
  - English plurals and case;
  - multi-word terms (longest match first);
  - document date (effective dates);
  - domain.
- Export: `data/glossary/terms.jsonl`, plus a CSV for the owner to review.

---

## 8. Claude's per-file review protocol (mandatory)

The owner requires Claude to **personally review every extracted file and every pair**. This is how that works in practice:

### 8.1 What Claude reviews
1. **Extraction review:** every extracted document, English and Hindi.
   - Is this the complete main text?
   - Is any boilerplate or menu text left in?
   - Is any paragraph missing or duplicated?
   - Is the Hindi real Unicode Devanagari (no mojibake or legacy font)?
   - Are tables intact?
2. **Pair review:** every document pair.
   - Same document? (date, reference number, and whether the subject meaning matches)
   - Is the paragraph alignment correct?
   - Does each paragraph pair say the same thing?
   - Are validator flags genuine errors or false positives?
3. **Sentence-alignment review:** every sentence pair in low-confidence alignments, plus a random ≥10% of high-confidence ones per document. If a sample shows errors, review 100% of that document.

### 8.2 How
- A script generates a **review packet** per document pair: `data/review_packets/{pair_id}.md`. It shows metadata, then English and Hindi paragraph by paragraph side by side, with validator flags and alignment scores beside each pair.
- Claude reads the packet **in full** and writes one **ReviewRecord** (§9.4) to the ledger `data/review/ledger.jsonl`:
  - verdict: `accept`, `accept_with_exclusions` (specific paragraphs or sentences excluded), `reject`, or `needs_human`;
  - issues found;
  - notes;
  - a SHA-256 hash of the reviewed content.
- **Only pairs whose latest verdict is `accept`, or `accept_with_exclusions`, and whose content hash still matches, may be exported for training.** If extraction is re-run and the text changes, the pair must be reviewed again.
- **Work in batches**, e.g. 20–50 pairs per batch depending on length. Record progress in `PROGRESS.md` so work can resume across sessions.

### 8.3 Honest limits (state these to the owner in progress reports)
- Claude verifies that extraction, pairing and alignment are correct, and flags suspected translation errors. **The official Hindi text is the reference.** Claude does not re-translate it or "improve" it.
- Claude cannot see visual layout. Tables and forms need extra care, and complex tables should be marked `needs_human`.
- A human spot-check of **≥5% of accepted pairs**, chosen at random, is required to promote Q4 to Q5 and to measure Claude's review accuracy. Report the agreement rate.
- Reviewing thousands of documents takes many sessions. Report throughput honestly, in pairs per session.

---

## 9. Data schemas (JSON / JSONL; Parquet for large exports)

### 9.1 Document
```json
{
  "doc_id": "rbi-notif-en-12345",
  "source": "rbi",
  "lang": "en",
  "doc_type": "notification",
  "url": "https://...",
  "published_date": "2026-09-26",
  "subject": "…",
  "reference_numbers": ["RBI/2026-27/45", "DOR.STR.REC.12/21.04.048/2026-27"],
  "retrieved_at": "2026-10-01T10:00:00Z",
  "raw_path": "data/raw/rbi/en/notification/12345.html",
  "blocks": [
    {"block_id": "b001", "type": "paragraph", "label": "1", "text": "…"},
    {"block_id": "b002", "type": "table", "rows": [["…", "…"]]},
    {"block_id": "b003", "type": "closing", "text": "Yours faithfully, …"}
  ],
  "encoding_issues": [],
  "extractor_version": "0.1.0"
}
```

### 9.2 Segment pair (the unit exported for training)
```json
{
  "pair_id": "rbi-notif-12345:p003:s002",
  "doc_pair_id": "rbi-notif-12345",
  "granularity": "sentence",
  "en": "…",
  "hi": "…",
  "context_en": ["previous sentence 1", "previous sentence 2"],
  "context_hi": ["…", "…"],
  "paragraph_label": "3",
  "alignment": {"method": "bertalign", "type": "1-1", "score": 0.93},
  "checks": {"status": "pass", "flags": []},
  "tier": "Q4",
  "split": "train",
  "provenance": {"source": "rbi", "translation": "official", "synthetic": false},
  "review": {"verdict": "accept", "reviewer": "claude", "ledger_ref": "…"}
}
```

### 9.3 GlossaryEntry
```json
{
  "term_id": "rbi-bg-000123",
  "en": "Monetary Policy Committee",
  "hi": "मौद्रिक नीति समिति",
  "hi_variants": [],
  "en_variants": ["MPC"],
  "domain": "monetary_policy",
  "authority": "RBI Banking Glossary",
  "status": "preferred",
  "source_url": "https://…",
  "retrieved_at": "2026-10-01",
  "effective_from": null,
  "effective_to": null,
  "notes": ""
}
```

### 9.4 ReviewRecord (append-only ledger)
```json
{
  "pair_id": "rbi-notif-12345",
  "stage": "document_pair",
  "verdict": "accept_with_exclusions",
  "excluded_blocks": ["p007"],
  "issues": ["p007 Hindi paragraph missing a proviso present in English"],
  "flags_resolved": {"p004:number_mismatch": "false_positive: number written in words in Hindi"},
  "reviewer": "claude",
  "reviewed_at": "2026-10-01T11:00:00Z",
  "content_sha256": "…",
  "pipeline_version": "0.1.0"
}
```

### 9.5 Dataset manifest (one YAML file per exported dataset version)
Records:
- dataset id and version;
- creation date;
- pipeline version;
- counts of documents, pairs, sentences and tokens by tier, split, doc_type and direction;
- excluded test document IDs;
- synthetic share;
- glossary version.

---

## 10. Model phase

### 10.1 Candidates (confirm licences and sizes first)

| Model | Notes |
|---|---|
| `ai4bharat/indictrans2-en-indic-1B` + `indictrans2-indic-en-1B` | Sentence-level; one model per direction; needs IndicTransToolkit preprocessing; cannot take a glossary in the prompt |
| `ai4bharat/IndicTrans3-beta` | Gemma-3-based, document-level; check size, licence and prompt format on the model card |
| TranslateGemma-12B, TranslateGemma-27B | Gemma-3-based; use the official prompt template; quality reportedly drops past ~2K tokens |
| The owner's current system | If one exists and can run offline |

### 10.2 Zero-shot benchmark (E0 and E0+)
- Run every candidate, **both directions**, on the DEV and TEST sets and on every evaluation subset (§7.8).
- **E0:** plain translation.
- **E0+:** the same, with glossary terms (and, for LLMs, the preceding context) injected into the prompt.
- Score with §12 metrics. **Choose the top 1–2 models to fine-tune.** Record the results table in `PROGRESS.md` and `translation_corpus/reports/benchmark.md`.

---

## 11. Fine-tuning phase

### 11.1 Setup
- Hugging Face `transformers` + `peft` + `bitsandbytes` + TRL `SFTTrainer`, **or** Unsloth. Choose whichever works reliably on the RTX 5090 (Blackwell) with the installed CUDA version, and record the versions.
- QLoRA with 4-bit NF4 quantisation.
- Adapters on all linear layers.
- Start with rank 32–64 (tune), gradient checkpointing, and bf16 compute.

### 11.2 Training examples
- **Bidirectional:** every accepted pair produces an EN→HI example and an HI→EN example.
- **Prompt:** use each model's documented template. Add optional blocks in a fixed order:
  1. `Glossary:` (terms found in the source, with preferred translations);
  2. `Context:` (preceding sentences, in the source language);
  3. `Text:` (the sentence or paragraph to translate).

  The target is the reference translation only.
- **Context views:** a mix of:
  - no context;
  - 1–3 preceding sentences;
  - a whole paragraph as the unit.

  Cap total input at about **1,500 tokens**.
- **Glossary injection during training:** include a glossary block in about 50% of examples, drawn from the terms actually present, so the model learns to use it when given.
- **Mix:**
  - Q5/Q4 official data forms the core;
  - Q3 owner data;
  - Q2 synthetic ≤20%;
  - boilerplate capped (§7.6).
- **Loss on target tokens only.**

### 11.3 Experiments (pilot set)

| Run | Data | Context | Glossary in prompt | Purpose |
|---|---|---|---|---|
| E0 / E0+ | none (zero-shot) | – / ✓ | – / ✓ | Choose base; measure retrieval-only gain |
| E1 | official gold, sentence-level | ✗ | ✗ | Domain-adaptation gain |
| E2 | E1 + context views | ✓ | ✗ | Context gain |
| E3 | E2 + owner data (+ Q2 if any) | ✓ | ✗ | Does extra data help? |
| E4 | best of E1–E3 | ✓ | ✓ | Full pilot system |

- **Learning curve:** repeat the best of E1/E2 at 10K, 50K, 200K examples and at the full set. Stop adding data when gains flatten.
- **Stability check:** evaluate on a general-domain set (e.g. FLORES-200 en–hi devtest, or IN22-Gen) to confirm general Hindi and English did not regress.
- **Decision rule:** if E0+ is within the noise of E4 on the human evaluation, report that fine-tuning may not be worth its upkeep. Let the owner decide.

---

## 12. Evaluation

### 12.1 Automatic (indicators only, never the only decision basis)
- chrF++ and BLEU (sacreBLEU, with signatures recorded).
- A COMET-family metric, if one can run offline and its licence permits.
- Validator pass rates:
  - number, date and reference exactness;
  - unit agreement.
- **Terminology accuracy:** % of glossary terms present in the source that are rendered with the preferred translation.
- Omission and addition checks (length ratio outliers, paragraph count).
- **Report every metric per direction and per evaluation subset.**

### 12.2 LLM-as-judge (optional, calibrated)
- Use an MQM-style rubric: error span, category, severity (minor/major/critical).
- **Calibrate against the human ratings first** (§12.3). Use it only if it agrees with humans reasonably well, and report the agreement.

### 12.3 Human evaluation
| Stage | Size | When |
|---|---|---|
| Smoke test | ~50 items | After E0, to sanity-check candidates |
| Selection test | **200–500 items**, stratified by subset, both directions | After fine-tuning, to choose the final model |
| Release gate | Protected TEST subset | Before any real use |

- **Blind and randomised:** the rater never sees which system produced an output.
- Rate adequacy (1–5), fluency (1–5), terminology correct (y/n) and critical error (y/n, with type).
- Legal and regulatory items get two reviewers where possible.
- Claude generates the rating sheets (CSV or Excel) and computes the results. It **does not** rate its own pipeline's outputs as the deciding vote.

### 12.4 Release gates (hard; thresholds to be set with the owner)
- No critical legal-meaning errors above the agreed threshold.
- Number, date and reference exactness ≥ the agreed threshold. The target is 100% on the numbers subset once validators flag failures.
- No regression versus the best zero-shot model on any high-risk subset.
- No regression on the general-domain stability set.

---

## 13. Translation service (Phase 7)
- A local HTTP API (FastAPI or similar) and a CLI:
  - input: a document (text or HTML) plus the direction;
  - output: the translation, plus a JSON report of flags.
- Steps:
  1. Segment into paragraphs and sentences, keeping context.
  2. Glossary lookup, date- and domain-aware.
  3. Build the prompt.
  4. Model inference (vLLM, or HF with batching).
  5. Validators.
  6. Output each segment with `status: ok | flagged` and reasons.
- **Log** every human correction the owner makes, as source, output, corrected text and error type, for a future training round. These are **never used automatically** for training (§15).
- Record latency and throughput on the RTX 5090.

---

## 14. Phases, deliverables and acceptance criteria

| Phase | Deliverables | Acceptance criteria (show the owner before moving on) |
|---|---|---|
| **0. Setup** | Python env (3.11), CUDA check, `requirements.txt`, repo layout, `.gitignore` for data, `PROGRESS.md`; answers to §3.2 recorded | `pytest` passes; GPU visible to PyTorch; data directory not tracked in a public repo |
| **1. Crawl + extract (pilot)** | Crawlers and extractors for notifications and press releases (EN + HI); encoding quarantine | On a 200-document pilot: 100% of files pass or are quarantined with reasons; Claude has reviewed every extracted file; selector accuracy reported |
| **2. Pairing + alignment (pilot)** | Document pairing, paragraph and sentence alignment, validators, review packets, ledger | On the pilot: every pair reviewed with a verdict; pairing precision reported (errors found by review / pairs); aligner precision on 100 hand-checked paragraphs reported |
| **3. Full data build** | All §6.1 document types for the agreed date range; glossary store from §6.2 sources; owner's 1 lakh pairs ingested; dedup; tiers; document-level split; frozen TEST set; manifest | Counts reported by tier, type, year and direction; leakage check passes; human 5% spot-check done with agreement rate reported |
| **4. Benchmark** | E0/E0+ for all candidates, both directions; smoke human evaluation | `reports/benchmark.md` with a full results table; top 1–2 chosen with reasons |
| **5. Fine-tuning** | Test training run stats; E1–E4; learning curve | `reports/experiments.md`; each run's config, data manifest version and metrics recorded; reproducible from committed config |
| **6. Evaluation + gates** | Selection human evaluation (200–500 items); release-gate results | Gates met or clearly reported as not met; final model chosen by the owner |
| **7. Service** | Local API + CLI with glossary injection and validators; correction logging | End-to-end: translate 10 unseen RBI documents in each direction; flags shown; latency reported |

**End-to-end definition of done:** Phases 0–7 accepted by the owner, with:
- a reproducible data build (manifests);
- a versioned glossary;
- a frozen TEST set;
- a documented chosen model (adapter plus base, with licence recorded);
- a working local service;
- `PROGRESS.md` and the `reports/` folder complete enough that another engineer could rebuild everything.

---

## 15. Deferred to later phases (agreed; do not build now)
- Translation-memory service (semantic retrieval of past approved translations).
- Reviewer web UI; model-disagreement routing as a service.
- Preference data and DPO; RL with quality rewards.
- Trained RBI quality-estimation model; dashboards; lineage database.
- Automatic retraining from production corrections. **Corrections must always pass review first.**
- Full fine-tuning on larger on-premise hardware.
- Other Indian languages.
- Legacy-font PDF conversion.

---

## 16. Repository layout (target)

```
translation_corpus/
  requirements.txt
  PROGRESS.md                 # session log (mandatory)
  config/                     # YAML configs: crawl, pipeline, training, eval
  rbicorpus/
    normalize.py              # EXISTS (draft): normalisation + encoding checks
    validators.py             # EXISTS (draft): numbers, dates, units, references
    segment.py                # EXISTS (draft): paragraph/sentence split, paragraph alignment
    crawl/                    # per-source listing and page crawlers
    extract/                  # per-source HTML → Document extractors
    pairing.py                # document pairing (§7.3)
    align.py                  # sentence alignment (§7.4)
    review.py                 # review packets + ledger (§8)
    glossary/                 # glossary ingestion per source + lookup
    dataset.py                # dedup, tiers, split, export, manifest
  training/                   # QLoRA scripts, prompt builders, configs
  evaluation/                 # benchmark runner, metrics, human-eval sheets
  service/                    # local API + CLI
  reports/                    # benchmark.md, experiments.md, data_report.md
  tests/                      # pytest; every module has tests with EN+HI fixtures
  data/                       # NOT in a public repo (§4.3)
    raw/ extracted/ pairs/ glossary/ review/ review_packets/ exports/
```

**Draft code already in the repository** (`translation_corpus/rbicorpus/`) was written in an environment without website access and has **only been smoke-tested**:
- `normalize.py`: NFC normalisation that keeps ZWJ/ZWNJ; detection of mojibake, replacement characters, private-use characters and Kruti Dev legacy fonts.
- `validators.py`: number, date (English and Hindi months), unit (crore/lakh/percent) and reference-identifier checks.
- `segment.py`: paragraph split, sentence split (English and Hindi, with an abbreviation list), and conservative paragraph alignment.

**First task in Phase 0:** write proper pytest tests for these modules, fix what fails, and extend them per §7.5.

### 16.1 Engineering standards
- Python 3.11, type hints, small modules, a pytest test for every function that touches text.
- Tests include real Hindi examples, including nukta forms (क़/ज़/ड़), ZWJ/ZWNJ, Devanagari digits, and the danda ।.
- All scripts are **idempotent and resumable**; configuration lives in YAML, not hard-coded.
- Every output file carries a pipeline or extractor version.
- Logging goes to files under `logs/`; never print secrets.
- No data in a public repository.

---

## 17. Known risks and mitigations

| Risk | Mitigation |
|---|---|
| English and Hindi pages paired wrongly | Three-signal rule (§7.3), mutual best match, Claude review of every pair, human 5% spot-check |
| Hindi encoding corruption | HTML-first; encoding checks with quarantine; no legacy-font PDFs |
| Boilerplate dominates the corpus | Boilerplate cap (§7.6) |
| Test leakage | Split by document; version grouping; exact and near-duplicate leakage check before every export |
| Glossary conflicts across authorities | Keep all variants with authority; precedence rule (§6.2); owner decides disputes |
| Hindi→English test set is "translationese" | Add Hindi-original texts where identifiable; report HI→EN results with this caveat |
| RTX 5090 software stack issues (new GPU architecture) | Test run in Phase 0/5; pin working library versions |
| Model licence or terms unsuitable | Check before Phase 4; exclude if unclear |
| Claude review throughput limits the timeline | Batches plus `PROGRESS.md`; report throughput; prioritise document types by §6.1.1 |
| Scraping blocked or rate-limited | Polite crawling, caching, resume; if blocked, stop and inform the owner |

---

## 18. Research findings and reasons for decisions (do not repeat this research)

This section summarises the research done in Sept 2026, so the building session does not redo it. Full detail and sources are in `docs/hindi-translation-model-research.md`.

**How reliable this research is:**
- Direct page fetching was **blocked** in the research environment. Every finding comes from **search-engine excerpts** of the linked sources, not full reads.
- Each finding is tagged:
  - **[Independent]**: academic study, government or Wikimedia record, or practitioner report;
  - **[Vendor]**: the model maker's own claim;
  - **[Anecdotal]**: individual user reports.

### 18.1 Model findings

| Model | Key findings | Tag | What it means here |
|---|---|---|---|
| **IndicTrans2** (AI4Bharat; MIT licence; 200M/1B) | Used in production by Bhashini: live-translated the PM's Independence Day speech (Aug 2026) into 22 languages ([TechTimes](https://www.techtimes.com/articles/324582/20260815/india-deploys-homegrown-ai-red-fort-pledges-ai-training-ten-million-youth.htm)) | Independent | Strongest real-world track record of any open Indic MT model |
| | Serves Wikipedia editors via Wikimedia MinT on CPU (CTranslate2) ([MediaWiki](https://www.mediawiki.org/wiki/MinT)) | Independent | Cheap to run; proven |
| | Human 11-factor study: better than NLLB for English–Hindi ([Springer](https://link.springer.com/chapter/10.1007/978-3-031-91331-0_7)) | Independent | |
| | English–Hindi comparison: Google Translate first, IndicTrans2 a close second, NLLB and OPUS-MT behind ([arXiv 2505.19604](https://arxiv.org/abs/2505.19604)) | Independent | |
| | ACL 2026 ITEM study: **GPT-4o-mini beat IndicTrans2 on Hindi**; IndicTrans2 won in the other 5 languages ([ACL](https://aclanthology.org/2026.acl-long.1171/)) | Independent | For Hindi, which has lots of training data, LLMs are catching up, so LLM candidates are worth testing |
| | Stiff on conversational text; +6.2 chrF after conversational fine-tuning ([arXiv 2606.29024](https://arxiv.org/abs/2606.29024)) | Independent | Stiffness matters less for formal RBI text |
| | Sentence-level; base models truncate at ~200–256 tokens; RoPE long-context variant (2048) since Jan 2025 ([GitHub](https://github.com/AI4Bharat/IndicTrans2)) | Independent | Cannot use document context; separate models per direction |
| | Official LoRA fine-tuning scripts plus IndicTransToolkit; a legal-domain fine-tune exists (InLegalTrans-En2Indic-1B) ([HF](https://huggingface.co/law-ai/InLegalTrans-En2Indic-1B)) | Independent | Fine-tuning is proven if chosen |
| **Discourse limits of sentence-level MT** | IndicDISCO-MT (EAMT 2026) was built because sentence-level Indic MT fails on pronouns and lexical cohesion ([ACL](https://aclanthology.org/2026.eamt-1.15/)) | Independent | Why document context and LLM candidates are needed |
| **TranslateGemma** (Google, Jan 2026; 4B/12B/27B; Gemma-3) | Two-stage training (SFT on human + synthetic data, then RL with MetricX-QE and AutoMQM rewards); 12B beats the Gemma 3 27B baseline on MetricX ([report](https://arxiv.org/abs/2601.09012), [blog](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/)) | Vendor | Good automatic scores |
| | Its professional MQM human evaluation covered 10 language pairs, including Marathi but **not Hindi** | Vendor | No human-verified Hindi quality, so benchmark it |
| | Users: "outstanding vs other offline models"; **4B noticeably weaker**; quality drops past ~2K tokens ([AiCybr](https://aicybr.com/blog/translategemma-guide)) | Anecdotal | Use 12B/27B; cap context at ~1.5K tokens |
| **IndicTrans3-beta** (AI4Bharat) | Gemma-3-based; document- and sentence-level; 15 languages plus 7 in preview; vLLM inference script ([HF](https://huggingface.co/ai4bharat/IndicTrans3-beta)) | Vendor | Architecturally the best fit, but unproven |
| | No published benchmark table, no independent evaluation, no fine-tuning recipe, no production deployment found | — | Benchmark it; don't assume it's best |
| **Sarvam-Translate** (Gemma-3-4B) | Vendor expert evaluation: better than Gemma3-27B, Llama-4 Scout and Llama-3.1-405B ([Sarvam](https://www.sarvam.ai/blogs/sarvam-translate)) | Vendor | |
| | Users report repetition and gibberish loops ([HF #7](https://huggingface.co/sarvamai/sarvam-translate/discussions/7), [#13](https://huggingface.co/sarvamai/sarvam-translate/discussions/13)); literal idioms (Kannada) | Independent/anecdotal | Optional reference only |
| **Bodhan AI Indic-Translate** (Sept 2026) | In-house test: 58.97 dBLEU vs Sarvam 47.44 vs IndicTrans2 31.93; human evaluation "in progress" ([HF](https://huggingface.co/bodhan-ai/indic-translate)) | Vendor | Too new; re-check later |
| **NLLB-200** (Meta) | Hallucination, repetition and omissions ([arXiv 2511.00486](https://arxiv.org/pdf/2511.00486)); loses to IndicTrans2; **CC-BY-NC licence** | Independent | Excluded |
| **General chat LLMs** (Gemma 4, Sarvam-30B/105B, Qwen3, Llama) | Mixed Indic results; Gemma 4 31B beat Sarvam-30B in every language in one test; Gemma 4 code-switches into English on specialised topics | Anecdotal | Not used as translators; dedicated translation models are more predictable |
| **Process9 Mox** (MoxVeda/MoxNMT) | Closed SaaS; "95%+ accuracy" with the method undisclosed; customers include Axis Bank, Tata 1mg and Startup India (all vendor-published); **no independent benchmark or review found** | Vendor | Excluded (closed, hosted, cannot be fine-tuned) |

### 18.2 Method findings

| Topic | Finding | Tag | Decision it supports |
|---|---|---|---|
| Data quality over quantity | Filtering noisy translations is essential; ~10K parallel sentences can match much larger sets; the MT objective alone works best ([NAACL 2025](https://aclanthology.org/2025.findings-naacl.225/)) | Independent (verified to exist) | Quality tiers; learning curves instead of size targets; no mixed objectives |
| Automatic metrics | Metrics are insensitive to differences among high-quality translations ([EMNLP 2024](https://aclanthology.org/2024.emnlp-main.802/)) | Independent (verified) | Human evaluation decides; metrics are indicators |
| LLM-as-judge | Rubric-MQM improves reliability; judges still struggle with near-perfect output ([ACL 2025](https://aclanthology.org/2025.acl-industry.12/)) | Independent (verified) | Calibrate the judge against humans before using it |
| Synthetic data | LLM-generated data helps **low-resource** MT even when noisy ([EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1408/)) | Independent (verified) | Hindi is not low-resource, and legal-text errors are costly, so synthetic data is capped at ≤20% and tagged |
| Corpus filtering with QE | Six-model QE ensemble explained ~60% of variance in human ratings (English–Ukrainian, 55M pairs) ([UNLP 2025](https://aclanthology.org/2025.unlp-1.9/)) | Independent (verified) | QE is for **prioritising** review, not auto-rejecting |
| LLM-labelled filters | Synthetic labels from LLMs can train effective small data filters ([EMNLP 2025 Findings](https://aclanthology.org/2025.findings-emnlp.495/)) | Independent (verified) | Possible later-phase filter |
| Document-level MT | Concatenating preceding sentences is a strong, simple baseline, especially with lots of data ([survey](https://arxiv.org/pdf/1912.08494)) | Independent | Context views in training (§11.2) |
| Domain adaptation | Fine-tuning on thousands of in-domain pairs gives large gains at a small fraction of retraining cost ([survey](https://arxiv.org/pdf/2104.06951)) | Independent | Fine-tuning is worth testing |
| Full fine-tuning vs LoRA | Full fine-tuning outperforms low-rank LoRA on translation ([arXiv 2504.01919](https://arxiv.org/pdf/2504.01919)) | Independent | Higher-rank QLoRA on all linear layers narrows the gap; full fine-tuning deferred (hardware) |
| RTX 5090 | 32 GB GDDR7, 1.79 TB/s ([Runpod](https://www.runpod.io/articles/guides/nvidia-rtx-5090)); 12B in BF16 is ~24 GB of weights, and QLoRA needs under 16 GB ([Spheron](https://www.spheron.network/blog/gpu-vram-requirements-fine-tune-llm-2026/)); 27B QLoRA works on 32 GB with gradient checkpointing and ~4K sequence length ([ai.rs](https://ai.rs/ai-developer/gemma-4-lora-fine-tuning-rtx-5090)) | Independent (general guides) | QLoRA only; test run required |

### 18.3 Terminology and data-source findings

| Finding | Source | Decision |
|---|---|---|
| RBI's Rajbhasha Department maintains a bilingual **Banking Glossary** (web plus a downloadable glossary app) | [RBI](https://website.rbi.org.in/en/web/rbi/banking-glossary) | Top-precedence terminology source |
| The Rajbhasha Department translates annual and statutory reports, bulletins, manuals and forms | [RBI Rajbhasha norms](https://www.rbi.org.in/commonman/upload/english/content/pdfs/89132.pdf) | Official Hindi versions are human gold (Q4/Q5) |
| CSTT publishes official English–Hindi technical glossaries | [CSTT](https://www.cstt.education.gov.in/en) | Terminology source |
| The Department of Official Language publishes a Hindi vocabulary | https://rajbhasha.gov.in/en/hindi-vocabulary (from the owner) | Terminology source |
| The Constitution (Art. 343(1)) specifies the international form of Indian numerals for official Union purposes | General knowledge; not re-verified in this research | Digits should match exactly between versions; validators still normalise Devanagari digits |

### 18.4 How the external (ChatGPT) review was handled
- **Adopted:**
  - benchmark before choosing a model;
  - quality tiers with provenance;
  - split by document;
  - learning curves;
  - a terminology store;
  - deterministic validators;
  - a hard-case evaluation set;
  - tiered human evaluation;
  - release gates;
  - Parquet or JSON as the master copy, with JSONL as an export.
- **Adopted with changes:**
  - synthetic data capped (its supporting study is on low-resource languages);
  - context views capped at ~1.5K tokens;
  - the experiment grid reduced to E0–E4 plus a four-point learning curve (one GPU);
  - QE used for prioritising, not rejecting;
  - canonical storage kept simple.
- **Deferred:**
  - correction and preference datasets and DPO;
  - active-learning service;
  - reviewer UI and dashboards;
  - 10-role team;
  - lineage database.
- **Rejected:** one wrong link. Its IndicTrans fine-tuning link pointed to the v1 repository; the correct one is `AI4Bharat/IndicTrans2`.
- **Citations:** all 7 research papers it cited were verified to exist, at the stated venues and with matching findings.
- **One error in the earlier plan was fixed** that the critique had not raised: "rent cloud A100/H100 for full fine-tuning" was removed because it conflicts with RBI confidentiality.

### 18.5 Not thoroughly researched: verify during the build

| # | Gap | Why it matters | When to resolve |
|---|---|---|---|
| 1 | All findings came from search excerpts, not full papers or pages | Numbers may be misquoted | Before citing any number in a decision |
| 2 | **RBI site structure:** classic site vs `website.rbi.org.in`; whether English and Hindi pages share IDs; which document types have Hindi HTML versions, and over which years | Determines the crawler design and the corpus size | Phase 1, first task |
| 3 | **RBI website terms of use and `robots.txt`** | Legal permission to crawl | Phase 0 |
| 4 | **Glossary formats and availability**: RBI glossary app format; rajbhasha.gov.in vocabulary structure; CSTT/Shabd download options; e-Mahashabdkosh; Legislative Department legal glossary; SEBI/IRDAI/NABARD/Department of Financial Services glossaries | Terminology store coverage | Phase 3 |
| 5 | **IndicTrans3-beta**: size, licence, prompt format, VRAM needs, whether fine-tuning is feasible | Candidate eligibility | Phase 4 |
| 6 | **TranslateGemma**: exact prompt template; Gemma Terms of Use suitability for RBI | Candidate eligibility | Phase 4 |
| 7 | **Sarvam-Translate licence**; Bodhan Indic-Translate base model and licence | Optional candidates | Phase 4 (optional) |
| 8 | Unconfirmed claim of a newer AI4Bharat model beating Sarvam on a 500-document LLM-judged test ([HF Space](https://huggingface.co/spaces/nithinshesh/indic-sarvam-translation-compare)); which model it tested is unclear | Could indicate IndicTrans3 strength | Optional check |
| 9 | **RTX 5090 (Blackwell) software support** for bitsandbytes, Unsloth, vLLM and the CUDA versions needed | Training may fail on a new architecture | Phase 0 test run |
| 10 | **Sentence aligners** (Bertalign, vecalign, LaBSE) not tested on RBI Hindi | Alignment precision | Phase 2 (evaluate on 100 hand-checked paragraphs) |
| 11 | **COMET-family metric licences** and offline availability | Evaluation tooling | Phase 4 |
| 12 | **IndicDISCO-MT** data availability and licence (usable as a discourse test?) | Discourse evaluation | Phase 3/4 |
| 13 | **Not reviewed at all:** MADLAD-400 (Google), Krutrim Translate, Aya (Cohere), BharatGen Param, Microsoft/Azure open models, Airavata. They appeared in searches or are known to exist but were not assessed | May be missed candidates | Optional quick check before Phase 4; include only if licence and offline use fit |
| 14 | No substantial independent community discussion (e.g. Reddit) found on Hindi MT quality | Real-world signal is thinner than ideal | Accept; our own benchmark fills the gap |
| 15 | Hardware numbers come from general sizing guides, not measured on this machine | Planning accuracy | Phase 0/5 test run |
| 16 | Constitution Art. 343(1) numeral rule stated from general knowledge | Validator assumption | Low risk; validators normalise digits anyway |

---

## 19. References
All evidence, sources and the independent-versus-vendor classification are in [`docs/hindi-translation-model-research.md`](docs/hindi-translation-model-research.md) (research v3). It covers:
- model comparisons;
- the review of the external (ChatGPT) critique, showing which suggestions were adopted and why;
- hardware sizing;
- verified citations for data filtering, synthetic data, metric limitations and LLM-as-judge.
