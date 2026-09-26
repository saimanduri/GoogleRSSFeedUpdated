# RBI English–Hindi Translation: Research, Critique Review and Revised Plan (v3)

*Updated 26 Sep 2026. Replaces v2 (the consolidated model research). v3 folds in an external review of v2 (produced with ChatGPT: "RBI Translation Research Improvement and Dataset Strategy v2"). Each suggestion in that review was checked against our evidence. It was adopted, adopted with changes, deferred, or rejected, and §3 gives the reason for each.*

---

## 1. Objective (corrected)

**What v2 assumed.** v2 inferred the use case from this repository, a Google News RSS pipeline. So it optimised for short English news headlines and summaries translated into Hindi.

**The actual use case is RBI institutional translation:** circulars, Master Directions, notifications, monetary policy documents, annual reports, press releases, FAQs and forms. That changes the priority order:

| Priority | v2 (news assumption) | v3 (RBI) |
|---|---|---|
| 1 | Contextual coherence | **Meaning and legal force preserved exactly** ("shall" must not become "may") |
| 2 | Fluency | **Approved RBI terminology used consistently** |
| 3 | Named entities | **Numbers, amounts, dates and references exact** |
| 4 | — | Document-level coherence (pronouns, repeated terms) |
| 5 | — | Structure preserved (tables, lists, section numbering) |
| 6 | — | Natural, institutional-register Hindi |
| Constraint | Offline | **On-premise only.** Confidential data must not go to cloud GPUs or hosted APIs |

**Direction.** **Both directions are in scope (confirmed): English→Hindi and Hindi→English.** One LLM-based model can serve both, with the direction stated in the prompt (see §12).

**Hardware.** One RTX 5090 (32 GB) on-premise.

---

## 2. Revised recommendation (summary)

| Decision | v2 said | v3 says | Why it changed |
|---|---|---|---|
| **Base model** | Fine-tune TranslateGemma-12B first | **Benchmark first, then fine-tune the top 1–2.** Zero-shot test IndicTrans2-1B, IndicTrans3-beta, TranslateGemma-12B/27B and the current production baseline on a protected RBI evaluation set. | v2 chose a model with no Hindi human evaluation behind it. Zero-shot benchmarking is cheap on a 5090 (inference only) and removes the guess. *(Critique was right.)* |
| **IndicTrans2's role** | Reference baseline only | **Full candidate** | RBI text is formal and legal. That is IndicTrans2's strongest register, and its "stiffness" weakness matters less here. It may win on the legal, number and sentence-precision subsets even though it can't handle discourse. |
| **Terminology** | Left to fine-tuning | **A separate, versioned terminology store plus translation-memory retrieval, fed into the model's prompt** | Fine-tuning can't guarantee approved terms, and terms change over time. RBI already publishes a bilingual Banking Glossary. *(Critique was right.)* |
| **Post-generation checks** | None | **Deterministic validators for numbers, currency (₹, lakh, crore), percentages, dates, circular and section references, and table cells** | These checks are cheap and exact, and catch errors like ₹5,000 crore becoming ₹500 crore. *(Critique was right.)* |
| **Dataset** | Six bullets on context windows | **Quality tiers with provenance, document-level canonical storage, train/test split by document, deduplication, alignment confidence, and a protected evaluation set** | v2's weakest section. *(Critique was right.)* |
| **Training method** | QLoRA on a 5090 | **Unchanged: QLoRA.** Run ablations to show *which data* helps, not just which model. | The hardware limit still applies. The ablation idea was adopted in a reduced form (§8). |
| **Full fine-tune path** | "Rent an A100/H100" | **Only on-premise hardware** | Renting cloud GPUs likely conflicts with RBI data-confidentiality rules. This was an error in v2 that I've corrected, not a point the critique raised. |
| **Evaluation** | 50-item blind test | **Tiered: a 50-item smoke test, a 200–500 item selection test, then a protected release-gate set.** Uses MQM-style error labels, with hard gates for legal, number and entity regressions. | 50 items can't separate models statistically. *(Critique was right.)* |
| **Scope** | Model plus fine-tune | **Pilot first (§9, Phase A).** The full "data factory" platform is built only after the pilot proves value. | The critique's 60-section platform is a sensible long-term target but the wrong first step (§4). |

---

## 3. Point-by-point review of the external critique

**Verdicts:** ✅ adopt · 🟡 adopt with changes · ⏸ defer to later phase · ❌ reject.

| # | Critique's suggestion | Verdict | Reasoning |
|---|---|---|---|
| 1 | v2 was strong on models and weak on data | ✅ | True. The model research was about 80% of v2, and dataset construction was one short section. |
| 2 | Don't pick the base model first; benchmark all candidates on the same RBI data | ✅ | True. v2's TranslateGemma pick rests on Google's own MetricX scores plus anecdotes. Its human evaluation (MQM) did not include Hindi. |
| 3 | Quality tiers Q0–Q5 with provenance on every example | ✅ | Needed so that a model can later be traced back to the data it trained on. It also makes it possible to exclude machine-translated or synthetic data. |
| 4 | Split train and test **by document**, never by sentence | ✅ | A critical gap in v2. Splitting sentences of the same circular across train and test inflates every score. Also deduplicate PDF, HTML, DOCX and scanned copies of the same document. |
| 5 | Dataset size is not the KPI; measure learning curves | ✅ | Supported by verified evidence. The NAACL 2025 paper by Lin, Martins and Schütze found that *filtering noisy translations is essential*, and that *~10K parallel sentences can match much larger sets*, when adapting LLMs ([ACL](https://aclanthology.org/2025.findings-naacl.225/)). |
| 6 | Terminology store with effective dates, domains and deprecated terms | ✅ | RBI already has a source for this: the **RBI Banking Glossary** maintained by the Rajbhasha Department ([RBI](https://website.rbi.org.in/en/web/rbi/banking-glossary)). A second source is the Government of India's **CSTT** glossaries ([CSTT](https://www.cstt.education.gov.in/en)). |
| 7 | Translation-memory retrieval at inference time | ✅ | This point also favours an LLM base model. TranslateGemma and IndicTrans3 accept retrieved examples and glossary entries in their prompt. IndicTrans2 is a plain sequence-to-sequence model and can't use them, so for it terminology would have to be enforced by post-editing or constrained decoding. |
| 8 | Deterministic number, date, reference and table validators | ✅ | This is the highest-value, lowest-cost item in the critique. Note the Official Languages rule: Union official documents use the *international form of Indian numerals* (Constitution Art. 343(1)), so digits should match exactly between source and target. The validator should still normalise any Devanagari digits it finds. |
| 9 | Human-correction dataset and preference dataset | ⏸ | Correct in principle, but these datasets only exist once a model is in reviewers' hands. Start logging corrections from the first pilot, and train on them in a later phase. |
| 10 | Active learning (reviewers see low-confidence and model-disagreement cases first) | 🟡 | Adopt the cheap version in the pilot: run 2–3 candidate models and send the segments where they disagree to reviewers. A trained, scored active-learning loop comes later. |
| 11 | Synthetic data with provenance and quotas | 🟡 | The critique's source is real ([EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1408/)) but studies **low-resource** languages. Hindi isn't low-resource, and RBI likely has a large human-translated corpus, so synthetic data adds less here. In legal text, synthetic errors are also costly. Use it only to cover rare terms and hard cases, always tagged, never as the bulk of training data. |
| 12 | Hard-case and adversarial corpus (legal modals, numbers, cross-references, pronoun traps) | ✅ | Essential for RBI. Build it for **evaluation first**; that is cheap. Use it for training later. |
| 13 | Multiple context "views" (sentence, ±1 sentence, paragraph, section) | 🟡 | Adopt sentence, ±1–3 sentences and paragraph views. Section-level views often exceed TranslateGemma's ~2K-token comfort zone ([user reports](https://aicybr.com/blog/translategemma-guide)), so cap windows at about 1.5K tokens until testing shows longer ones help. |
| 14 | Automatic metrics are unreliable for high-quality translations | ✅ | Verified ([EMNLP 2024, Agrawal et al.](https://aclanthology.org/2024.emnlp-main.802/)): metrics are least reliable at the high end, exactly where fine-tuned candidates will land. Human evaluation stays the deciding test. |
| 15 | An LLM-as-judge must be calibrated against humans (Rubric-MQM) | ✅ | Verified ([ACL 2025](https://aclanthology.org/2025.acl-industry.12/)). The paper itself notes LLM judges struggle with near-perfect translations, so calibrate on RBI human labels before trusting the judge. |
| 16 | Ensemble quality-estimation filtering | 🟡 | Verified ([UNLP 2025](https://aclanthology.org/2025.unlp-1.9/)): the best ensemble explained about 60% of variance in human ratings on English–Ukrainian. That is useful for **ranking** which data to review, not for automatically rejecting data. Use it to prioritise human review. |
| 17 | Canonical Parquet store, a metadata database, then JSONL export | 🟡 | The principle is right: JSONL should be an export, not the master copy. For the pilot, Parquet plus a YAML manifest per dataset version is enough. Build a lineage database only if the platform phase goes ahead. |
| 18 | Nine-experiment matrix (E0–E8) and a seven-point learning curve (10K to 1M) | 🟡 | On one 5090, running that full grid with a 12B model is weeks of GPU time. Pilot a subset instead: E0 (base), E1 (RBI gold), E2 (gold plus context), then E7 (plus terminology and translation memory). Use four learning-curve points: 10K, 50K, 200K, full. |
| 19 | Stage 4–5 training (preference optimisation, quality-aware reinforcement learning) | ⏸ | Premature without correction and preference data. DPO with QLoRA is feasible on a 5090 later. |
| 20 | Release gates (no regression on legal, numbers, entities or hallucination) | ✅ | Adopt. Thresholds need to be agreed with the Rajbhasha and legal reviewers. |
| 21 | 10-role team and reviewer UI | ⏸ | Right for a production platform, not a pilot. The pilot minimum is one ML engineer, one Hindi or Rajbhasha reviewer, and one legal or regulatory reviewer for high-risk sets. |
| 22 | Build the data factory first; treat the model as replaceable | 🟡 | The strategic point is sound: data, terminology and evaluation outlast any model checkpoint. Building the whole factory before any model result, though, risks months of infrastructure with no evidence fine-tuning is needed. Build the **minimum** version first (inventory, gold set, protected evaluation set, terminology v1), then benchmark. |
| 23 | Rules for handling evidence (label vendor claims, verify snippets) | ✅ | Already practised in v2. Kept and made explicit (§11). |
| 24 | Link for "IndicTrans fine-tuning" | ❌ (minor) | It points to `AI4Bharat/indicTrans`, the **v1** repository. IndicTrans2's fine-tuning scripts are in [AI4Bharat/IndicTrans2](https://github.com/AI4Bharat/IndicTrans2). |

**Citation check.** All seven research papers the critique cites were confirmed to exist, with the claimed venues and matching findings (§10, rows 30–35). No fabricated references were found. The only issue was the wrong repository link in row 24.

---

## 4. Where the critique overreaches

Being objective runs both ways:

1. **Scope versus resources.** The critique describes a full enterprise platform: ten roles, a reviewer UI, dashboards, a quality-estimation service, lineage database and RL stages. Against one GPU and an unproven hypothesis, building all of that first is the most likely way the project stalls. The pilot has to answer one question quickly: *does a fine-tuned model, with terminology and validators, beat the current baseline on RBI text by enough to justify the platform?*
2. **It adds no new model evidence.** Its model section restates v2. It doesn't challenge the candidate list or the evidence behind it, so v2's model research (§5) stands.
3. **Its synthetic-data argument cites low-resource research.** Hindi isn't low-resource, and the risk of synthetic errors is higher in legal text (row 11).
4. **Its pilot dataset sizes** (100K–500K gold segments, 2K–10K terms, and so on) are guesses. The critique says so itself. Only the data inventory (Phase A1) can set real targets.

---

## 5. Model landscape (evidence carried over from v2, re-weighted for RBI)

| | IndicTrans2-1B | TranslateGemma 12B/27B | IndicTrans3-beta | Sarvam-Translate | NLLB-200 | Process9 Mox |
|---|---|---|---|---|---|---|
| Architecture | Sentence-level encoder-decoder | Gemma-3, document-aware | Gemma-3, document-level | Gemma-3-4B fine-tune | Sentence-level | Closed |
| Licence | MIT | Gemma Terms of Use (check the prohibited-use policy against RBI's intended use) | Check the model card (beta) | Check the model card | **CC-BY-NC**, which rules out production use | Closed SaaS |
| Accepts glossary or TM in the prompt | ❌ | ✅ | ✅ | ✅ | ❌ | N/A |
| Independent human evaluation for Hindi | ✅ Beat NLLB ([Springer](https://link.springer.com/chapter/10.1007/978-3-031-91331-0_7)); close second to Google ([arXiv](https://arxiv.org/abs/2505.19604)) | ❌ Its MQM evaluation covered Marathi, not Hindi | ❌ | ❌ Vendor-run only | ✅ Loses to IndicTrans2 | ❌ |
| Production track record | ✅ Bhashini at national scale; Wikipedia MinT | Developer and hobbyist use | None yet | Sarvam API | Wikipedia (other languages) | Vendor case studies |
| Known risks | No discourse handling; 200–256 token base limit | Quality drops past ~2K tokens; no Hindi human evaluation | Beta; no published fine-tuning recipe | Repetition loops ([HF](https://huggingface.co/sarvamai/sarvam-translate/discussions/7)) | Hallucination and omission | Unverifiable; hosted |
| **v3 role** | **Candidate**, likely strong on legal and number subsets | **Candidate**, likely strong on discourse | **Candidate** | Optional reference | Excluded (licence) | Excluded (hosted, closed) |

Supporting detail for every row is in the findings table (§10).

---

## 6. Dataset strategy

### 6.1 Sources to inventory first (Phase A1)
- **Officially bilingual RBI publications.** Circulars, notifications, Master Directions, press releases, annual and statutory reports, and FAQs are typically published in both English and Hindi under the Official Languages policy. The Rajbhasha Department translates annual and statutory reports, bulletins, manuals and forms ([RBI Rajbhasha norms](https://www.rbi.org.in/commonman/upload/english/content/pdfs/89132.pdf)). This is the likely **Q4–Q5 gold core**.
- **RBI Banking Glossary** as terminology v1 ([RBI](https://website.rbi.org.in/en/web/rbi/banking-glossary)), plus **CSTT** banking and finance glossaries ([CSTT](https://www.cstt.education.gov.in/en)).
- **The large EN–Hindi corpus you already hold.** Its provenance must be classified before use (human versus machine translation, and source system).
- **Any existing translation memories** held by the Rajbhasha Department or its vendors.
- **English-only and Hindi-only RBI documents**, kept for terminology mining and possible back-translation later.

### 6.2 Quality tiers (adopted from the critique)

| Tier | Meaning | Use |
|---|---|---|
| Q5 | Officially published or two-stage reviewed human translation | Gold training data; eligible for evaluation (never both for the same document) |
| Q4 | Human translation, single review | Training |
| Q3 | Machine-assisted, human-validated | Training |
| Q2 | Synthetic or machine output, automatically filtered | Coverage only, capped by quota; tagged `synthetic: true` |
| Q1 | Unverified | Mining only, never training |
| Q0 | Rejected | Never used |

### 6.3 Pipeline, pilot version (the full data factory is deferred)
1. **Ingest and keep the raw file unchanged.** Parse the PDF, DOCX or HTML, preserving section, paragraph and table structure. Flag OCR'd documents and do not treat them as Q5 without review.
2. **Align at the document level first** (match each English document to its Hindi version), then at paragraph and sentence level. Allow 1→N and N→1 matches, and give every alignment a confidence score.
3. **Check each pair** for:
   - length ratio;
   - language ID;
   - **matching numbers, dates and references** (the same code as the §7 validators);
   - QE ensemble score, used for prioritising review rather than automatic rejection.
4. **Deduplicate** at three levels:
   - exact pair;
   - near-duplicate;
   - **document level** (the PDF, HTML and scanned copy of the same circular count as one document).
5. **Split by document.** Hold out the protected evaluation set by document identity *before* building any training data. Also exclude every other version of those documents (amended circulars, HTML copies).
6. **Build context views:** a single sentence, ±1–3 sentences, and a paragraph, capped at about 1.5K tokens. Vary window sizes within the training mix.
7. **Export:** Parquet as the master copy, JSONL generated from it for training, and a YAML manifest per dataset version recording counts, tiers, date range, excluded document IDs and pipeline version.

### 6.4 Protected evaluation set (build before any fine-tuning)

Stratify it into these subsets:
- general RBI;
- regulation and legal (modals, provisos, "notwithstanding");
- monetary policy;
- consumer-facing;
- numbers, currency and dates;
- entities and references;
- tables;
- discourse (pronouns, repeated terms);
- OCR or noisy source text.

Store it with access control, version it, and never train on it.

---

## 7. Inference-time layers (new in v3)

```
source document ─► segment + context window
                    │
                    ├─► terminology lookup (versioned, date- and domain-aware)
                    ├─► translation-memory lookup (exact, then semantic)
                    ▼
               translation model (prompt includes retrieved terms and TM matches)
                    ▼
               deterministic validators ── fail ─► flag for human review
                    │ pass
                    ▼
               output (+ log any human edits as correction data)
```

**Deterministic validators to build first:**
- digits and numeric values;
- ₹, INR, lakh and crore forms;
- percentages and basis points;
- dates and financial years;
- circular, notification, section and paragraph identifiers;
- table row and column counts, with cell values.

These are pure code. They don't depend on which model is chosen.

---

## 8. Training and experiments (single RTX 5090)

**Method.** QLoRA (4-bit). The v2 hardware analysis stands:
- a 12B model in BF16 needs about 24 GB for weights alone, so full fine-tuning is tight to infeasible on 32 GB;
- 12B QLoRA fits comfortably;
- 27B QLoRA is feasible with gradient checkpointing at about 4K sequence length ([Spheron](https://www.spheron.network/blog/gpu-vram-requirements-fine-tune-llm-2026/), [ai.rs](https://ai.rs/ai-developer/gemma-4-lora-fine-tuning-rtx-5090)).

Confirm these figures with a short test run before planning experiments.

**Pilot experiment set (reduced from the critique's E0–E8):**

| Run | Data | Context | Terms/TM in prompt | Purpose |
|---|---|---|---|---|
| E0 | None (zero-shot), all candidates | — | — | Choose the 1–2 base models to fine-tune |
| E0+ | None (zero-shot), best candidate | — | ✅ | Measure how much retrieval gains **without** any training |
| E1 | RBI gold (Q4–Q5), sentence-level | ❌ | ❌ | Measure the pure domain-adaptation gain |
| E2 | RBI gold plus context views | ✅ | ❌ | Measure the context gain |
| E3 | E2 plus hard cases | ✅ | ❌ | Check whether targeted data fixes weak subsets |
| E4 | Best of E1–E3 | ✅ | ✅ | The full pilot system |

**Learning curve.** Run E1 or E2 at 10K, 50K and 200K examples and at the full dataset. Stop expanding the corpus once gains flatten.

**E0+ matters.** If retrieval plus validators on a base model gets close to the fine-tuned result, fine-tuning may not justify its maintenance cost.

**Stays out of the pilot:** full fine-tuning, which needs on-premise 80 GB-class hardware; DPO and RL; and training on synthetic data beyond hard-case coverage.

---

## 9. Evaluation and release gates

**Tiered human evaluation:**
- a 50-item smoke test;
- a **200–500 item** model-selection test, stratified by the §6.4 subsets, blind and randomised;
- a protected release-gate set.

For legal and regulatory subsets, use two qualified reviewers.

**Scorecard:**
- MQM-style error spans and severity (minor, major, critical);
- adequacy and fluency;
- terminology match against the glossary;
- number, date and entity exactness (from the validators);
- discourse consistency;
- omission and addition rates;
- latency and throughput on the 5090.

**Automatic metrics** (chrF, COMET-style, quality estimation) are indicators only. Any LLM judge must be calibrated against the human labels first.

**Hard release gates:**
- no critical legal-meaning regressions;
- no increase in number, entity or reference errors;
- no rise in hallucinated additions;
- no regression on the general-domain sanity set.

### Phased roadmap

**Phase A — Pilot** (about 6–10 weeks, estimated; one GPU, 2–3 people):
- A1: data inventory and provenance classification;
- A2: RBI gold v1, protected evaluation set v1, terminology v1 from the Banking Glossary, hard-case evaluation set v1;
- A3: validators;
- A4: zero-shot benchmark (E0 and E0+);
- A5: QLoRA runs E1–E4 plus the learning curve;
- A6: human evaluation and a go/no-go decision.

**Phase B — Production hardening**, if the pilot succeeds:
- translation-memory service;
- reviewer workflow that logs corrections and preferences;
- routing of model disagreements to reviewers;
- canonical store with lineage.

**Phase C — Continuous learning:**
- preference optimisation (DPO) on the collected corrections;
- an RBI-specific quality estimator;
- governed periodic retraining;
- extension to other Indian languages.

---

## 10. All findings, with sources and independence

| # | Finding | Subject | Source | Independent? |
|---|---|---|---|---|
| 1 | Live-translated the Prime Minister's Hindi speech into 22 languages in production (Aug 2026) | IndicTrans2 | [TechTimes](https://www.techtimes.com/articles/324582/20260815/india-deploys-homegrown-ai-red-fort-pledges-ai-training-ten-million-youth.htm) | ✅ |
| 2 | Serves Wikipedia editors via MinT, on CPU | IndicTrans2 | [MediaWiki](https://www.mediawiki.org/wiki/MinT) | ✅ |
| 3 | Human 11-factor evaluation: better than NLLB for English–Hindi | IndicTrans2 | [Springer](https://link.springer.com/chapter/10.1007/978-3-031-91331-0_7) | ✅ |
| 4 | Close second to Google Translate on English–Hindi | IndicTrans2 | [arXiv 2505.19604](https://arxiv.org/abs/2505.19604) | ✅ |
| 5 | GPT-4o-mini beats IndicTrans2 on Hindi; IndicTrans2 wins in other languages | IndicTrans2 vs LLM | [ACL 2026 ITEM](https://aclanthology.org/2026.acl-long.1171/) | ✅ |
| 6 | Stiff on conversational text; +6.2 chrF after adaptation | IndicTrans2 | [arXiv 2606.29024](https://arxiv.org/abs/2606.29024) | ✅ |
| 7 | 200–256 token limit; RoPE long-context variant | IndicTrans2 | [GitHub](https://github.com/AI4Bharat/IndicTrans2) | ✅ |
| 8 | Sentence-level Indic MT fails on discourse phenomena | Discourse | [IndicDISCO-MT](https://aclanthology.org/2026.eamt-1.15/) | ✅ |
| 9 | Two-stage SFT plus RL; 12B beats Gemma 3 27B on MetricX | TranslateGemma | [Google](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/), [report](https://arxiv.org/abs/2601.09012) | ❌ vendor |
| 10 | MQM human evaluation covered Marathi, not Hindi | TranslateGemma | [Review](https://www.themoonlight.io/en/review/translategemma-technical-report) | ❌ vendor |
| 11 | 4B is weak; quality degrades past ~2K tokens | TranslateGemma | [AiCybr](https://aicybr.com/blog/translategemma-guide) | ✅ anecdotal |
| 12 | Gemma-3-based, document-level, beta, 15+7 languages | IndicTrans3 | [HF](https://huggingface.co/ai4bharat/IndicTrans3-beta) | ❌ vendor |
| 13 | Unconfirmed claim that a newer AI4Bharat model beats Sarvam on a large LLM-judged test | IndicTrans3? | [HF Space](https://huggingface.co/spaces/nithinshesh/indic-sarvam-translation-compare) | ⚠️ unverified |
| 14 | Vendor-run expert evaluation: beats larger models | Sarvam-Translate | [Sarvam](https://www.sarvam.ai/blogs/sarvam-translate) | ❌ vendor |
| 15 | Users report repetition and gibberish loops | Sarvam-Translate | [HF #7](https://huggingface.co/sarvamai/sarvam-translate/discussions/7), [#13](https://huggingface.co/sarvamai/sarvam-translate/discussions/13) | ✅ |
| 16 | In-house test: 58.97 dBLEU vs 47.44 (Sarvam) vs 31.93 (IndicTrans2) | Bodhan | [HF](https://huggingface.co/bodhan-ai/indic-translate) | ❌ vendor |
| 17 | Hallucination and omission; non-commercial licence | NLLB-200 | [arXiv 2511.00486](https://arxiv.org/pdf/2511.00486) | ✅ |
| 18 | "95%+ accuracy" claimed with no disclosed method; no independent evidence found | Process9 | [Process9](https://process9.com/faq-translation-tools-indian-languages/) | ❌ vendor |
| 19 | Customers include Axis Bank, Tata 1mg and Startup India (vendor-published) | Process9 | [Axis case study](https://process9.com/case-study/axis-bank-case-study/) | ❌ vendor |
| 20 | RTX 5090: 32 GB GDDR7, 1.79 TB/s | Hardware | [Runpod](https://www.runpod.io/articles/guides/nvidia-rtx-5090) | ✅ |
| 21 | 12B: ~24 GB in BF16; QLoRA under 16 GB | Hardware | [Spheron](https://www.spheron.network/blog/gpu-vram-requirements-fine-tune-llm-2026/) | ✅ |
| 22 | 27B QLoRA feasible on 32 GB with gradient checkpointing | Hardware | [ai.rs](https://ai.rs/ai-developer/gemma-4-lora-fine-tuning-rtx-5090) | ✅ practitioner |
| 23 | Full fine-tuning outperforms low-rank LoRA on translation | Method | [arXiv 2504.01919](https://arxiv.org/pdf/2504.01919) | ✅ |
| 24 | Sentence concatenation is a strong baseline for document-level MT | Method | [Survey](https://arxiv.org/pdf/1912.08494) | ✅ |
| 25 | LoRA scripts and IndicTransToolkit exist; a legal-domain fine-tune exists (InLegalTrans) | IndicTrans2 fine-tuning | [GitHub](https://github.com/AI4Bharat/IndicTrans2), [InLegalTrans](https://huggingface.co/law-ai/InLegalTrans-En2Indic-1B) | ✅ |
| 26 | RBI publishes a bilingual Banking Glossary (Rajbhasha Dept.) | Terminology source | [RBI](https://website.rbi.org.in/en/web/rbi/banking-glossary) | ✅ primary |
| 27 | Rajbhasha Dept. translates annual and statutory reports, bulletins, manuals and forms | Gold data source | [RBI norms](https://www.rbi.org.in/commonman/upload/english/content/pdfs/89132.pdf) | ✅ primary |
| 28 | CSTT publishes official English–Hindi technical glossaries | Terminology source | [CSTT](https://www.cstt.education.gov.in/en) | ✅ primary |
| 29 | No independent benchmark, academic evaluation or public user review found | Process9 | Academic, G2/Capterra and community searches | — (absence of evidence) |
| 30 | Filtering noisy translations is essential; ~10K pairs can match larger sets; the MT objective alone works best | Data strategy | [NAACL 2025](https://aclanthology.org/2025.findings-naacl.225/) | ✅ verified |
| 31 | Metrics are insensitive to differences between high-quality translations | Evaluation | [EMNLP 2024](https://aclanthology.org/2024.emnlp-main.802/) | ✅ verified |
| 32 | Rubric-MQM improves LLM-as-judge; judges still struggle with near-perfect output | Evaluation | [ACL 2025](https://aclanthology.org/2025.acl-industry.12/) | ✅ verified |
| 33 | LLM synthetic data helps **low-resource** MT, even when noisy | Synthetic data | [EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1408/) | ✅ verified (low-resource setting) |
| 34 | QE ensemble explains ~60% of human-rating variance (English–Ukrainian, 55M pairs) | Data filtering | [UNLP 2025](https://aclanthology.org/2025.unlp-1.9/) | ✅ verified |
| 35 | LLM-labelled synthetic data can train small, effective data filters | Data filtering | [EMNLP 2025 Findings](https://aclanthology.org/2025.findings-emnlp.495/) | ✅ verified |
| 36 | The critique's IndicTrans fine-tuning link points to the v1 repository | Correction | [IndicTrans2 repo](https://github.com/AI4Bharat/IndicTrans2) | — |

---

## 11. Caveats and evidence rules

- **How the research was done.** Direct page fetching was blocked in this research environment. Every finding comes from search-result excerpts. Rows 30–35 were checked for existence, venue and headline finding, not read in full. Verify any number before it becomes a decision input.
- **No independent human evaluation compares these candidates on Hindi, and none uses RBI-domain text.** The zero-shot benchmark (E0) is therefore the most important step in the plan.
- **Hardware figures** come from general sizing guides. Validate them with a test run on the actual 5090.
- **Licences and model cards** (Gemma Terms of Use, IndicTrans3-beta, Sarvam) must be rechecked immediately before selection.
- **Dataset counts** should always distinguish documents, segments, tokens and unique content.
- **Timeline estimates** (Phase A: 6–10 weeks) are planning assumptions, not measurements.

---

## 12. Implementation plan for a one-person team using Claude Code

### 12.1 Both directions with one model
- TranslateGemma and IndicTrans3 are prompt-based, so **one fine-tuned model can translate both ways**. The prompt says which direction to translate.
- **Each parallel pair gives two training examples** (EN→HI and HI→EN), which doubles the training data for free.
- IndicTrans2 has separate models per direction (`en-indic`, `indic-en`). It stays in the benchmark, but would mean maintaining two models.
- **Build evaluation sets for each direction separately.** Most official RBI Hindi text is translated *from* English, which gives it a translated style. So the Hindi→English test set should also include some Hindi-original text, such as Hindi press releases or speeches, where available.

### 12.2 How to use the existing ~1 lakh pairs

| Part of the dataset | Where it goes |
|---|---|
| Single words and short phrases | **Terminology store**, merged with the RBI Banking Glossary. Word lists alone teach a model little context; as looked-up terms they are very effective. |
| Sentences | Training data, tiered by provenance (§6.2) |
| Paragraphs | Training data **and** context examples, split into sentences with the paragraph kept as context |
| Anything machine-translated | Tier Q2 at most; or used only for terminology mining |

### 12.3 Role of a locally hosted IndicTrans3 (revised)
- **Do not use it as the main source of training data.** Translating RBI English documents with IndicTrans3 and training on the output teaches the model IndicTrans3's mistakes. It cannot learn to be better than its teacher on those examples.
- **Better main source:** for the many documents RBI publishes in both languages, collect both versions and *align* them. That produces human-translated pairs (tier Q4–Q5).
- **Good uses for IndicTrans3:**
  - an **alignment helper**, translating one side so that matching sentences can be found reliably;
  - a **candidate model** in the benchmark;
  - **back-translation** of documents that exist in only one language, tagged `synthetic: true` and capped as a share of training data;
  - a **second opinion**: segments where it disagrees with other models are sent to human review first.

### 12.4 What Claude Code can and cannot do

| Claude Code can write and run | Needs a person |
|---|---|
| Scripts that download RBI English and Hindi documents and parse PDF/HTML | Confirming RBI website terms of use and internal permission to use the data |
| Document matching and sentence alignment (multilingual embeddings) | Spot-checking alignment quality on a sample |
| Cleaning, deduplication, number/date checks, train/test split by document | Deciding the provenance tier of the existing 1 lakh pairs |
| Terminology store and glossary lookup | Approving disputed terms |
| Benchmark harness, QLoRA training scripts, evaluation scripts | Blind human rating of the evaluation set (Hindi reviewer; legal reviewer for high-risk subsets) |
| Local translation server with validators | Go/no-go decisions and release approval |

**Where to run it.** Claude Code has to run **on the RTX 5090 machine** (the Claude Code CLI installed locally), because training and inference need the GPU and the RBI website must be reachable.

**Confidentiality.** The code runs locally, but any file content Claude Code *reads* is sent to Anthropic's API as part of the conversation. For confidential RBI material, keep real data out of Claude's context: let it write and test code on public or sample data, and run the finished scripts yourself on confidential files. Check this against RBI's IT and data policy before starting.
