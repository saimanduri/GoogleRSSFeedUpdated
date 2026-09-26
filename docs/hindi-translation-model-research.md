# Hindi / Indic Translation Model Research — Consolidated Findings & Final Recommendation

*Consolidated: 26 Sep 2026. This file supersedes the incremental drafts written earlier in this research thread — it is the single reference going forward.*

## 1. Objective

Build a translation capability for this pipeline's English-language Google News RSS content into Hindi (and, where reusable, other Indian languages), that:
- Understands **context**, not just isolated sentences — resolves pronouns, keeps terminology and named entities consistent across a document, not just per-sentence adequacy.
- Is built by **fine-tuning an open-source base model on a proprietary dataset** (a large existing English–Hindi parallel corpus), not by calling a hosted API.
- Runs on **available hardware: one NVIDIA RTX 5090 (32GB GDDR7, 1.79TB/s bandwidth)**.

Everything below is organized around getting to a final, defensible answer for that objective — model selection, dataset construction, training method, and evaluation — while keeping the full evidence trail (including scenarios that don't apply to this exact setup, for reference if constraints change).

---

## 2. Final recommendation (read this first)

| Decision | Recommendation | Why |
|---|---|---|
| **Base model** | **`google/translategemma-12b-it`** (Gemma-3 backbone, already translation-specialized) | The only model in this review whose own evaluation explicitly targets document-level context — coherence, pronoun/reference consistency, lexical cohesion, cross-sentence adequacy. IndicTrans2, the otherwise best-proven model, is architecturally sentence-level and cannot do this (see §4.1). |
| **Training method** | **QLoRA (4-bit)**, not full fine-tuning | On a single 32GB RTX 5090, full fine-tuning a 12B model is tight-to-infeasible once gradients and optimizer state are added; QLoRA fits comfortably and leaves headroom for long context windows (§6). |
| **Second track (parallel, lower priority)** | `ai4bharat/IndicTrans3-beta` (also Gemma-3-based, document-level) | Best long-term ceiling — from the team with the strongest Indic accuracy track record — but still beta, no published fine-tuning recipe, no independent benchmark yet. Pilot, don't bet on it first. |
| **Scale-up path** | Try `translategemma-27b-it` + QLoRA on the same card once the 12B pipeline is validated; only consider a full fine-tune (needs 80GB-class or multi-GPU hardware) if 27B QLoRA still leaves quality on the table | Sequencing avoids burning time on the expensive option before the cheap one has told you whether it's worth it |
| **Data format** | Concatenated multi-sentence **context windows**, not flat isolated sentence pairs | This — not the base model choice — is what actually makes the fine-tune contextual (§5) |
| **Reference baseline to keep testing against** | `ai4bharat/indictrans2-en-indic-1B` | Still the best-proven *sentence-level* model; useful as a floor to beat, and as a fallback if the LLM route underdelivers |
| **Not a fit here** | Process9 Mox (closed SaaS), NLLB-200 (documented hallucination, non-commercial licence) | See §4.5, §4.6 |

---

## 3. How we got here (decision path)

The recommendation changed twice over the course of this research, each time because a stated constraint changed. This matters because it explains *why* the final answer differs from "just use the model with the most evidence":

1. **No stated GPU, no stated dataset, no stated context requirement** → **IndicTrans2** was the right default: cheapest, CPU-capable, most independently-verified accuracy for Hindi.
2. **GPU + large dataset available, but still asking generically about fine-tuning** → IndicTrans2 was still the lowest-risk *starting point* for fine-tuning, with TranslateGemma/IndicTrans3 as a secondary track, because LoRA + small-to-medium data is IndicTrans2's proven use case (conversational and legal-domain adaptations exist).
3. **Explicit requirement: contextual understanding, not just sentence accuracy** → this ruled out IndicTrans2 as the *base* to build on, regardless of dataset size or hardware, because it is architecturally sentence-level. This pushed the recommendation to a Gemma-3-based LLM (TranslateGemma or IndicTrans3-beta).
4. **Explicit hardware: one RTX 5090 (32GB)** → this ruled out full fine-tuning as the default method (viable in the abstract "large dataset + GPUs" scenario, but not on one 32GB consumer card) and settled the method on QLoRA.

Each step is evidenced below; §2 is the answer to all four constraints held simultaneously, which is your actual situation.

---

## 4. Model landscape reviewed

### 4.1 Why IndicTrans2 — despite being the best-proven model — is not the base to fine-tune here

**The case for it, generally:**
- Runs in production at national scale: India's **Bhashini** platform used it to live-translate the PM's Independence Day speech into 22 languages (Aug 2026) ([TechTimes](https://www.techtimes.com/articles/324582/20260815/india-deploys-homegrown-ai-red-fort-pledges-ai-training-ten-million-youth.htm)).
- Serves Wikipedia editors daily via Wikimedia's **MinT** service, on CPU, no GPU needed ([MediaWiki](https://www.mediawiki.org/wiki/MinT)).
- Independent human evaluation (11-factor scale) found it **better than Meta's NLLB** for English–Hindi ([Springer](https://link.springer.com/chapter/10.1007/978-3-031-91331-0_7)).
- On an 18k-sentence corpus + government FAQ text, it came a **close 2nd to Google Translate**, ahead of NLLB-200 and OPUS-MT ([arXiv 2505.19604](https://arxiv.org/abs/2505.19604)).
- MIT-licensed, 200M/1B parameter sizes, runs on CPU.

**Why it's disqualified as the base for *this* objective:** IndicTrans2 is a **sentence-level encoder-decoder**. It translates one sentence at a time with no visibility into neighboring sentences — it cannot resolve a pronoun referring back two sentences, or keep a name/term consistent across a paragraph. This is architectural, not a data problem, so no amount of fine-tuning data fixes it. A dedicated 2026 benchmark, **IndicDISCO-MT**, exists specifically because sentence-level Indic MT systems fail at this ([ACL Anthology](https://aclanthology.org/2026.eamt-1.15/)). Other known weaknesses: stiff/formal register on casual text (closes somewhat with conversational fine-tuning, +6.2 chrF: [arXiv 2606.29024](https://arxiv.org/abs/2606.29024)), and a base 200–256 token sequence cap (RoPE variant extends to 2048: [GitHub](https://github.com/AI4Bharat/IndicTrans2)). Notably, in the one independent multi-language human-evaluation study that included Hindi (ACL 2026 *ITEM*), **GPT-4o-mini beat IndicTrans2 specifically on Hindi** — the only language (of 6) where the dedicated NMT model lost ([ACL Anthology](https://aclanthology.org/2026.acl-long.1171/)). Hindi is high-resource enough that general LLMs are closing the gap.

**Keep it as:** the reference baseline in your evaluations (§7), and the fallback plan if the LLM fine-tuning route underdelivers on accuracy.

### 4.2 TranslateGemma (Google, Jan 2026) — the recommended base

- Fine-tuned from Gemma 3 for translation across 55 languages including Hindi, via a two-stage process: SFT on synthetic + human-translated parallel data, then RL with quality reward models (MetricX-QE, AutoMQM) ([alphaXiv](https://www.alphaxiv.org/overview/2601.09012)). The 12B model beats the Gemma 3 27B baseline on MetricX ([Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/)).
- **Its own evaluation explicitly measures document-level context**: coherence, pronoun/reference consistency, lexical cohesion, cross-sentence adequacy — directly matching this project's requirement.
- **Evidence gap:** the professional human evaluation (MQM) covered 10 language pairs including Marathi, but **not Hindi** ([report review](https://www.themoonlight.io/en/review/translategemma-technical-report)). For Hindi specifically, the evidence is automatic metrics plus anecdotal community reports, not controlled human evaluation.
- **User reports:** called "outstanding compared to any other offline model" by Ollama/Obsidian users; the 4B size is noticeably weaker — use 12B or 27B; quality degrades past ~2K tokens of context ([Medium](https://medium.com/free-or-open-source-software/demo-translategemma-ollama-obsidian-55-languages-offline-ai-powered-translation-global-indian-14ae927d8aa3), [AiCybr](https://aicybr.com/blog/translategemma-guide)).

**Bottom line:** best available combination of (a) already translation-specialized, (b) architecturally built for document context, (c) open weights, (d) fits a single 32GB GPU with QLoRA. Its main weakness is that nobody has independently verified Hindi quality with human judges yet — which is exactly what your own blind test (§7) needs to establish before you commit further.

### 4.3 IndicTrans3-beta (AI4Bharat) — promising, not yet provable

- A real architecture change, not a version bump: built on **Gemma 3**, fine-tuned for **document-level** translation (vs. IndicTrans2's sentence-level) ([HF](https://huggingface.co/ai4bharat/IndicTrans3-beta), [AIM](https://analyticsindiamag.com/ai-news-updates/ai4bharat-launches-indictrans3-for-22-indic-languages/)).
- Covers 15 Indic languages fully (including Hindi) plus 7 more in preview — narrower than IndicTrans2's full 22.
- Ships a vLLM-based inference script for sentence- and document-level serving.
- **What's missing:** no published chrF/BLEU comparison table against IndicTrans2/TranslateGemma/Sarvam, no independent human evaluation, no fine-tuning recipe, no production deployment yet — still labelled beta. One third-party HF comparison space reportedly showed a "newer AI4Bharat model" beating Sarvam-Translate on a large LLM-judged test, but the source doesn't unambiguously confirm this was IndicTrans3 rather than IndicTrans2 — treat as an unverified lead ([HF Space](https://huggingface.co/spaces/nithinshesh/indic-sarvam-translation-compare)).

**Bottom line:** architecturally, this is arguably the best long-term fit (Gemma-3 + document-level + AI4Bharat's Indic-accuracy pedigree) — but with zero independent verification today, it's a parallel pilot, not the primary bet.

### 4.4 Sarvam-Translate, Bodhan Indic-Translate, NLLB-200 — considered and set aside

| Model | Verdict | Why |
|---|---|---|
| **Sarvam-Translate** (Gemma-3-4B fine-tune) | Try as a reference point, not a base | Vendor's own expert evaluation claims it beats Gemma3-27B/Llama-4/Llama-3.1-405B ([Sarvam blog](https://www.sarvam.ai/blogs/sarvam-translate)), but users report output collapsing into repetition/gibberish on some inputs ([HF #7](https://huggingface.co/sarvamai/sarvam-translate/discussions/7), [#13](https://huggingface.co/sarvamai/sarvam-translate/discussions/13)) and stiff, literal idiom handling ([Thejesh GN](https://thejeshgn.com/2025/06/10/first-impressions-of-sarvam-indic-translate-model/)) |
| **Bodhan AI Indic-Translate** (Sept 2026) | Watch, re-check in 2–3 months | Claims 58.97 dBLEU vs. Sarvam's 47.44 and IndicTrans2's 31.93 on an **in-house, vendor-run** test ([HF](https://huggingface.co/bodhan-ai/indic-translate)); human evaluation "in progress"; under a month old with no independent evidence yet |
| **NLLB-200** (Meta) | Avoid | Independent studies document hallucination, repetition, omissions ([arXiv 2511.00486](https://arxiv.org/pdf/2511.00486)); loses to IndicTrans2 in human evaluation; **CC-BY-NC licence** — research use only, not for a production fine-tune |
| **General chat LLMs used ad hoc** (Sarvam-30B/105B, Qwen3, Llama, Gemma 4) | Avoid as translators | Mixed, inconsistent Indic results across models; e.g. Gemma 4 31B beat Sarvam-30B on every language in one benchmark ([Medium](https://medium.com/@indiai/india-first-llms-on-indian-languages-sarvam-30b-and-param2-17b-6676b637f3ab)), while also reported to code-switch into English on specialised topics ([DEV](https://dev.to/devsaquib/i-tested-gemma-4-and-gpt-4o-mini-on-indian-language-tasks-the-results-surprised-me-19g8)) — a dedicated translation model is cheaper and more predictable than an undirected chat LLM |

### 4.5 Process9 Mox (MoxVeda / MoxWave / MoxNMT) — not comparable, not a fit

Process9 sells a **closed, subscription SaaS** for website/app localization (MoxVeda), backed by a proprietary engine (MoxNMT) with human-in-the-loop review, translation memory, and glossaries ([MoxVeda](https://process9.com/mox-veda/), [Mox vs Bhashini](https://process9.com/mox-vs-bhashini/)).

- **Accuracy claim:** "95%+ accuracy in Hindi vs ~80% generic tools" — method and test set undisclosed, so it can't be checked against any benchmark used elsewhere ([Process9 FAQ](https://process9.com/faq-translation-tools-indian-languages/)).
- **Independent evidence: none found** — no academic benchmark appearance, no G2/Capterra/Reddit reviews (positive or negative).
- **Real customers are real** (Axis Bank, Tata 1mg, Startup India, Paytm, PolicyBazaar), but every quote and metric is vendor-published, and the numbers measure business engagement (session counts), not translation accuracy — with human reviewers in the loop doing real work on top of the raw MT output.
- **Not open source**, hosted (sends your content to a third party), and not fine-tunable — disqualified for this objective on every count.

### 4.6 Full model comparison table

| | IndicTrans2 | TranslateGemma 12B/27B | IndicTrans3-beta | Sarvam-Translate | Bodhan Indic-Translate | NLLB-200 | Process9 Mox |
|---|---|---|---|---|---|---|---|
| Architecture | Sentence-level encoder-decoder | Gemma-3, document-level | Gemma-3, document-level | Gemma-3-4B fine-tune | Unknown (Gemma-4-based per some listings) | Encoder-decoder, sentence-level | Proprietary, undisclosed |
| Licence | MIT | Gemma terms | Gemma terms (beta) | Check card | Check card (new) | CC-BY-NC (non-commercial) | Closed SaaS |
| Contextual/discourse capable | ❌ No | ✅ Designed for it | ✅ Designed for it | Partial (document input, but repetition issues) | Unknown | ❌ No | Unknown |
| Independent human evaluation (Hindi) | ✅ Beats NLLB; close 2nd to Google | ❌ MQM covered Marathi, not Hindi | ❌ None | ❌ Vendor-run only | ❌ "In progress" | ✅ Loses to IndicTrans2 | ❌ None |
| Real-world deployment | ✅ National scale (Bhashini), Wikipedia | Hobbyist/dev use | None yet | Sarvam API users | None (1 month old) | Wikipedia (other langs) | Axis Bank, Tata 1mg, Paytm, etc. (vendor-published) |
| Fine-tuning tooling | ✅ Official LoRA scripts + IndicTransToolkit | HF `SFTTrainer` / Unsloth QLoRA guides | ❌ None published | Unknown | Unknown | Unknown | N/A (closed) |
| Fits a single RTX 5090 | ✅ Even CPU-only | ✅ QLoRA yes, full FT tight/no | Presumed similar to Gemma | ✅ Likely (4B) | Needs vLLM/TensorRT | ✅ | N/A (hosted) |
| **Fit for this objective** | Reference baseline only — wrong architecture for "contextual" | **Primary recommendation** | Secondary pilot | Reference point | Re-check later | Avoid | Not applicable |

---

## 5. Dataset construction: making the fine-tune actually contextual

You have a large EN–Hindi dataset already. The base-model choice above is necessary but **not sufficient** — a Gemma-3-based model fed flat, shuffled (English sentence → Hindi sentence) pairs will not learn to use context any better than IndicTrans2 does. Contextual behavior has to be built into the training data itself:

1. **Preserve document/article boundaries.** Group sentence pairs back into their original article order. A flat, shuffled sentence-pair list — which is how most bulk parallel corpora, including scraped ones, are typically distributed — throws away exactly the information needed for context training. This is the first thing to check/fix in your existing dataset.
2. **Train on concatenated context windows, not single sentences.** Standard, well-validated approach: prepend the preceding 2–4 sentences to both the source and target side (with a clear separator token), and train the model to produce a correct translation of the *last* sentence given that preceding context ([survey, arXiv 1912.08494](https://arxiv.org/pdf/1912.08494)). This "concatenation" method is a strong, simple baseline that works especially well in high-resource settings — which a large dataset gives you.
3. **Vary the context window length during training** (mix in 1-sentence, 2-sentence, 3–4 sentence windows) so the model stays robust at inference when less context is available — e.g. the first sentence of an article has no prior context at all.
4. **Keep a slice of general-domain parallel data in the mix** (e.g. BPCC, the corpus IndicTrans2 itself trained on, or Samanantar: [arXiv 2104.05596](https://arxiv.org/pdf/2104.05596)) alongside your in-domain set — "experience replay" — so the model doesn't overfit narrowly to your corpus and lose general Hindi fluency. AI4Bharat used exactly this technique for their own conversational-domain adaptation of IndicTrans2 ([arXiv 2606.29024](https://arxiv.org/abs/2606.29024)).
5. **Human-quality Hindi only.** If any part of your large dataset was itself produced by machine translation (rather than human translation), filter or down-weight it — fine-tuning on MT output teaches the model to imitate that MT engine's errors, not to translate well.
6. **Named entities and numbers need explicit attention.** These are the most common failure point in news MT generally, and doubly important in a context-aware setup: an entity introduced in sentence 1 must be referred to consistently by sentence 3. If your dataset is thin on proper nouns/organizations relevant to your news domain, consider augmenting with a curated entity list or additional in-domain pairs specifically covering them.

---

## 6. Training method and hardware plan (single RTX 5090, 32GB GDDR7)

| Target model | Full fine-tune (BF16) | QLoRA (4-bit) |
|---|---|---|
| **TranslateGemma-12B** | Tight to infeasible — BF16 weights alone are ~24GB before gradients/optimizer state and a real batch/sequence length are added ([Spheron sizing guide](https://www.spheron.network/blog/gpu-vram-requirements-fine-tune-llm-2026/)) | **Comfortable** — 4-bit weights need well under 16GB, leaving headroom for long context windows and a decent batch size |
| **TranslateGemma-27B** | **Not feasible** on one 32GB card | **Feasible with care** — reported working with gradient checkpointing, ~4K sequence length on a 32GB card ([ai.rs](https://ai.rs/ai-developer/gemma-4-lora-fine-tuning-rtx-5090)); smaller batch size, slower training |

**Recommendation: QLoRA, not full fine-tuning, on this hardware.** The general finding that "full fine-tuning beats LoRA on translation quality" ([arXiv 2504.01919](https://arxiv.org/pdf/2504.01919); [Gradient Flow](https://gradientflow.com/lora-or-full-fine-tuning/)) was measured against *low-rank* LoRA; a well-configured QLoRA run (higher rank, adapters on all linear layers, sufficient training steps over your large dataset) closes most of that gap — and it's the only realistic option for the 27B model on this card regardless.

**Sequenced plan:**
1. **Fine-tune `translategemma-12b-it` with QLoRA first.** It fits comfortably and trains fast, letting you iterate quickly on the context-window data format from §5 — that's where most of the actual quality gain will come from, not from model size.
2. Once the pipeline and data format are validated, **repeat with `translategemma-27b-it` + QLoRA** on the same card (expect to trade off sequence length/batch size, with gradient checkpointing on) for a direct quality comparison.
3. **Only pursue a full fine-tune if 27B QLoRA still leaves quality on the table**, and only with different hardware — an 80GB-class card (rented A100/H100) or multiple GPUs. Not something this single 5090 can do; cross that bridge after QLoRA has told you it's worth the jump.
4. **In parallel**, pilot `IndicTrans3-beta` on the same context-window dataset once you can adapt to whatever fine-tuning approach AI4Bharat documents for it (none published as of this writing — check for updates before starting this track).
5. Inference: the 12B fine-tune serves comfortably on one 5090; the 27B model will also run, with less headroom for concurrent requests.

---

## 7. Evaluation plan

Run all of the following against: your fine-tuned model, the un-fine-tuned TranslateGemma baseline, and `ai4bharat/indictrans2-en-indic-1B` as the sentence-level reference point.

1. **Native-speaker blind test.** Take ~50 real feed items (or article-length excerpts, to actually test context). Translate with each candidate model, shuffle so the rater doesn't know which model produced which output, and have a native Hindi speaker score adequacy (meaning kept?) and fluency (natural Hindi?) on a 1–5 scale.
2. **Discourse-specific evaluation, not just BLEU/chrF.** Standard sentence-level metrics don't reward correct pronoun resolution or consistent terminology across a document — that's precisely why IndicDISCO-MT exists. Build (or reuse, if licensing allows) a small discourse-focused eval set: the same entity referred to across sentences, ambiguous pronouns, and repeated terms that must stay consistent — and score those specifically.
3. **Generic-domain regression check.** Evaluate on a public set like FLORES or IN22 to confirm the fine-tune hasn't regressed general Hindi fluency while specializing on your corpus.
4. **Named entity / number accuracy spot-check.** Because these are the most common real-world failure point, sample specifically for entities, dates, and figures in the discourse-eval and blind-test sets.

---

## 8. All findings, by source and independence

| # | Finding | Model / vendor | Source | Independent of vendor? |
|---|---|---|---|---|
| 1 | Live-translated PM's Hindi speech into 22 languages in production (Aug 2026) | IndicTrans2 | [TechTimes](https://www.techtimes.com/articles/324582/20260815/india-deploys-homegrown-ai-red-fort-pledges-ai-training-ten-million-youth.htm) | ✅ |
| 2 | Serves Wikipedia editors via MinT on CPU | IndicTrans2, NLLB | [MediaWiki MinT](https://www.mediawiki.org/wiki/MinT) | ✅ |
| 3 | Human 11-factor evaluation: IndicTrans2 better than NLLB for En–Hi | IndicTrans2 vs NLLB | [Springer](https://link.springer.com/chapter/10.1007/978-3-031-91331-0_7) | ✅ |
| 4 | En–Hi comparison: Google 1st, IndicTrans2 close 2nd, NLLB and OPUS trail | IndicTrans2, NLLB | [arXiv 2505.19604](https://arxiv.org/abs/2505.19604) | ✅ |
| 5 | GPT-4o-mini beats IndicTrans2 on Hindi; IndicTrans2 wins in most other languages | IndicTrans2 | [ACL 2026 ITEM](https://aclanthology.org/2026.acl-long.1171/) | ✅ |
| 6 | Stiff on conversational text; +6.2 chrF after adaptation | IndicTrans2 | [arXiv 2606.29024](https://arxiv.org/abs/2606.29024) | ✅ |
| 7 | 200–256-token limit; long-context RoPE variant Jan 2025; users ask about batching documents | IndicTrans2 | [GitHub](https://github.com/AI4Bharat/IndicTrans2), [#58](https://github.com/AI4Bharat/IndicTrans2/issues/58) | ✅ |
| 8 | Sentence-level Indic MT fails discourse phenomena (pronoun resolution, lexical cohesion) — dedicated benchmark built to measure this | IndicTrans2 and peers | [ACL Anthology 2026.eamt-1.15](https://aclanthology.org/2026.eamt-1.15/) | ✅ |
| 9 | 12B beats Gemma 3 27B baseline on MetricX; two-stage SFT+RL training | TranslateGemma | [Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/), [alphaXiv](https://www.alphaxiv.org/overview/2601.09012) | ❌ vendor |
| 10 | MQM human evaluation covered Marathi, not Hindi | TranslateGemma | [Tech report review](https://www.themoonlight.io/en/review/translategemma-technical-report) | ❌ vendor |
| 11 | Users: "outstanding vs other offline models"; use 12B/27B, not 4B; worse past 2K tokens | TranslateGemma | [Medium](https://medium.com/free-or-open-source-software/demo-translategemma-ollama-obsidian-55-languages-offline-ai-powered-translation-global-indian-14ae927d8aa3), [AiCybr](https://aicybr.com/blog/translategemma-guide) | ✅ (anecdotal) |
| 12 | Expert pairwise evaluation: better than Gemma3-27B, Llama-4 Scout, Llama-3.1-405B | Sarvam-Translate | [Sarvam blog](https://www.sarvam.ai/blogs/sarvam-translate) | ❌ vendor |
| 13 | Output-token repetition / gibberish reported by users | Sarvam-Translate | [HF #7](https://huggingface.co/sarvamai/sarvam-translate/discussions/7), [HF #13](https://huggingface.co/sarvamai/sarvam-translate/discussions/13) | ✅ |
| 14 | Literal, unnatural idiom rendering (Kannada) | Sarvam-Translate | [Thejesh GN](https://thejeshgn.com/2025/06/10/first-impressions-of-sarvam-indic-translate-model/) | ✅ |
| 15 | 58.97 dBLEU vs Sarvam 47.44 vs IndicTrans2 31.93 on in-house set; human evaluation pending | Bodhan Indic-Translate | [HF](https://huggingface.co/bodhan-ai/indic-translate), [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2026/09/bodhan-ai-indic-models/) | ❌ vendor |
| 16 | Gemma-3-based, document-level translation, 15+7 languages, still beta, no fine-tuning recipe published | IndicTrans3-beta | [HF](https://huggingface.co/ai4bharat/IndicTrans3-beta), [AIM](https://analyticsindiamag.com/ai-news-updates/ai4bharat-launches-indictrans3-for-22-indic-languages/) | ❌ vendor (AIM coverage is press, largely restating AI4Bharat's framing) |
| 17 | Unverified: a newer AI4Bharat-side model "clearly beats" Sarvam-Translate on a 500-doc LLM-judged test | IndicTrans3 (unconfirmed) or IndicTrans2 | [HF Space](https://huggingface.co/spaces/nithinshesh/indic-sarvam-translation-compare) | ⚠️ Third-party space, but which model isn't confirmed |
| 18 | Hallucination, repetition, omissions; research-only licence | NLLB-200 | [arXiv 2511.00486](https://arxiv.org/pdf/2511.00486), [HF card](https://huggingface.co/facebook/nllb-200-3.3B) | ✅ |
| 19 | Gemma 4 31B beats Sarvam-30B across Indic languages; Gemma 4 code-switches into English | General LLMs | [Medium](https://medium.com/@indiai/india-first-llms-on-indian-languages-sarvam-30b-and-param2-17b-6676b637f3ab), [DEV](https://dev.to/devsaquib/i-tested-gemma-4-and-gpt-4o-mini-on-indian-language-tasks-the-results-surprised-me-19g8) | ✅ (anecdotal) |
| 20 | "95%+ accuracy in Hindi vs ~80% generic"; method not disclosed | Process9 MoxNMT | [Process9 FAQ](https://process9.com/faq-translation-tools-indian-languages/) | ❌ vendor |
| 21 | MoxVeda = website localization layer; works with any MT engine; human-in-the-loop | Process9 MoxVeda | [MoxVeda](https://process9.com/mox-veda/) | ❌ vendor |
| 22 | Axis Bank Hindi support site live Jan 2022; chose Mox after evaluating options | Process9 | [Case study](https://process9.com/case-study/axis-bank-case-study/) | ❌ vendor-published testimonial |
| 23 | Tata 1mg: 500k+ products in Hindi; Hindi sessions 2× in a month | Process9 | [Case study](https://process9.com/case-study/tata-1mg/) | ❌ vendor-published |
| 24 | Startup India: ~5 years of use, "good accuracy" at volume | Process9 | [Process9 site](https://process9.com/) | ❌ vendor-published |
| 25 | Customers incl. Paytm, PolicyBazaar, MakeMyTrip, BookMyShow; PolicyBazaar 3× interest in Hindi | Process9 | [YourStory](https://yourstory.com/2020/10/raise-2020-startup-indic-language-interface-paytm-policybazaar) | ⚠️ press, based on company interview |
| 26 | No independent benchmark, academic evaluation, or public user review found | Process9 | Searches of academic, G2/Capterra, community sources | — (absence of evidence) |
| 27 | RTX 5090 specs: 32GB GDDR7, 1.79TB/s bandwidth | Hardware | [Runpod](https://www.runpod.io/articles/guides/nvidia-rtx-5090), [Spheron](https://www.spheron.network/blog/nvidia-rtx-5090-specs/) | ✅ |
| 28 | 12B model: ~24GB BF16 weights, full FT tight on 32GB; QLoRA needs <16GB | Hardware sizing | [Spheron sizing guide](https://www.spheron.network/blog/gpu-vram-requirements-fine-tune-llm-2026/) | ✅ |
| 29 | 27B QLoRA feasible on 32GB card with gradient checkpointing, ~4K sequence length | Hardware sizing | [ai.rs](https://ai.rs/ai-developer/gemma-4-lora-fine-tuning-rtx-5090) | ✅ (practitioner writeup) |
| 30 | Full fine-tuning outperforms LoRA on translation perplexity/BLEU in general comparisons | Fine-tuning method | [arXiv 2504.01919](https://arxiv.org/pdf/2504.01919), [Gradient Flow](https://gradientflow.com/lora-or-full-fine-tuning/) | ✅ |
| 31 | Domain-adaptation fine-tuning needs only thousands of in-domain pairs vs. millions for base training | Fine-tuning / dataset sizing | [arXiv 2104.06951](https://arxiv.org/pdf/2104.06951) | ✅ |
| 32 | Sentence-concatenation is a standard, effective document-level MT training method, esp. in high-resource settings | Document-level MT method | [Survey, arXiv 1912.08494](https://arxiv.org/pdf/1912.08494) | ✅ |
| 33 | IndicTrans2 has official LoRA fine-tuning scripts + IndicTransToolkit; legal-domain fine-tune (InLegalTrans) exists as precedent | IndicTrans2 fine-tuning | [GitHub](https://github.com/ai4bharat/IndicTrans2), [InLegalTrans HF](https://huggingface.co/law-ai/InLegalTrans-En2Indic-1B) | ✅ |

---

## 9. Caveats on this research

- Page fetching (WebFetch) was blocked throughout this research; every finding above comes from search-engine result excerpts of the linked sources, not full-text reads. **Verify key numbers against the originals** — especially the Bodhan dBLEU figures, the IndicTrans3/Sarvam comparison (finding #17), and any TranslateGemma/IndicTrans3 fine-tuning specifics — before basing engineering decisions solely on this document.
- No substantial independent community discussion (Reddit, forums) was found specifically for Hindi MT quality. The real-world signal used here rests on production deployments (Bhashini, Wikimedia MinT), a small number of independent academic human-evaluation studies, and scattered user reports on Hugging Face, GitHub, and blogs — treat conclusions as directionally reliable, not as a large-sample consensus.
- No fine-tuning recipe or benchmark exists yet for IndicTrans3-beta; its section here is necessarily thinner than IndicTrans2/TranslateGemma and should be re-checked before committing engineering time to that track.
- Dataset-size and hardware-feasibility numbers (§6, findings #27–29) come from general sizing guides and one practitioner writeup, not from an IndicTrans2/TranslateGemma-specific benchmark on an RTX 5090 — validate with a short smoke-test training run before committing to a full experiment plan.
