# Open-source models for Hindi and Indian-language translation (September 2026)

**Question:** Which open-source model translates Indian languages, especially Hindi, most accurately today? The answer should rest on real-world use and human evaluation, not on leaderboards or vendor pages.

**Context for this repo:** The pipeline collects Google News RSS items (headlines and short summaries), often in English, and is built to run offline. So the target is mostly **English → Hindi news text**, run locally, ideally on modest hardware.

---

## TL;DR

| Rank | Model | Use it when | Evidence quality |
|---|---|---|---|
| **1 (default)** | **AI4Bharat IndicTrans2** (`indictrans2-en-indic-1B`, or `-dist-200M` for CPU) | Accurate, predictable English→Hindi on CPU or a small GPU, offline | **Strongest.** Runs in production at national scale, and independent human evaluations back it |
| 2 | **Google TranslateGemma 12B / 27B** | You have a GPU and want more natural, context-aware Hindi for whole paragraphs | Good automatic metrics and positive but anecdotal user reports. No published human evaluation for Hindi |
| 3 | **Sarvam-Translate** (Gemma-3-4B fine-tune) | Document-level or formatted text (markdown, lists) across 22 languages | Expert human evaluation, but run by the vendor. Users report repetition loops |
| Watch | **Bodhan AI Indic-Translate** (Sept 2026), **IndicTrans3-beta** (Gemma-3 backbone, document-level) | Worth testing, but not trusting yet | No published benchmark table or human evaluation found for either. Still beta/"in progress" |
| Avoid | NLLB-200, and general chat LLMs used as translators | — | See below |
| Not comparable | **Process9 Mox (MoxVeda / MoxWave / MoxNMT)** | You're paying for a managed, human-reviewed website or app localization service | **Weak for accuracy.** It's proprietary and not open source, with no independent benchmark. Its adoption is real, but the evidence is vendor-published (see [Process9 section](#comparison-with-process9-mox-moxveda--moxwave--moxnmt)) |

**Bottom line:** For accurate, low-risk Hindi translation today, **IndicTrans2 is still the best-proven open model.** It is not the most fluent. LLM-based translators, especially TranslateGemma-27B, often read more naturally. But IndicTrans2 has the most real-world proof: it runs in production at national scale, and independent human evaluators preferred it to other open systems. The newer LLM-based models have not yet shown that kind of accuracy for Hindi in independent tests.

---

## Why IndicTrans2 wins on real-world evidence

1. **It runs in production at national scale.** India's government platform **Bhashini** uses IndicTrans2 in production. The Prime Minister's Independence Day speech (15 Aug 2026) was live-translated from Hindi into all 22 scheduled languages with IndicTrans2 ([TechTimes](https://www.techtimes.com/articles/324582/20260815/india-deploys-homegrown-ai-red-fort-pledges-ai-training-ten-million-youth.htm)).
2. **Wikipedia editors use it.** Wikimedia's **MinT** service serves IndicTrans2 to Content Translation users for Indic languages. It runs through CTranslate2 on CPU, with no GPU ([MediaWiki: MinT](https://www.mediawiki.org/wiki/MinT)). Editors post-edit this output every day, which makes it one of the few real-world feedback loops for open MT.
3. **Independent human evaluation.** A study scored translations by hand on 11 quality factors (0–4 scale). It found **IndicTrans2 better than Meta's NLLB** for English–Hindi ([Rupkatha / Springer](https://link.springer.com/chapter/10.1007/978-3-031-91331-0_7)).
4. **Independent English–Hindi comparison.** On an 18k-sentence corpus plus government FAQ text, **Google Translate ranked first and IndicTrans2 a close second.** NLLB-200 and OPUS-MT trailed ([arXiv 2505.19604](https://arxiv.org/abs/2505.19604)).
5. **Permissive licence (MIT)** and small sizes: 1B, or a 200M distilled model. It is easy to run offline.

**Known weaknesses, from practitioners and follow-up papers:**

- **Stiff, formal register.** It sounds wooden on casual or conversational text. A 2026 paper fine-tuned it for conversation and gained +6.2 chrF on average ([arXiv 2606.29024](https://arxiv.org/abs/2606.29024)). Formal register is fine for news.
- **Sentence-level model.** The original models truncate input at about 200–256 tokens. You must split text into sentences. RoPE long-context variants (up to 2048 tokens) came out in January 2025 ([GitHub](https://github.com/AI4Bharat/IndicTrans2)). Users have asked how to batch whole documents ([issue #58](https://github.com/AI4Bharat/IndicTrans2/issues/58)).
- **Hindi is where LLMs are catching up.** In the ACL 2026 *ITEM* study, **GPT-4o-mini beat IndicTrans2 for Hindi**, while IndicTrans2 won in most other Indian languages ([ACL Anthology](https://aclanthology.org/2026.acl-long.1171/)). Hindi has so much training data that large LLMs now match or beat specialised MT models on it. This is why TranslateGemma-27B is a real contender for Hindi specifically.

---

## IndicTrans2 (dedicated NMT) vs. a best-in-class LLM (Gemma / GPT-4o-class)

This is the real fork in the road: a small, purpose-built translation model vs. a general-purpose LLM used as a translator. Evidence is thinner than either side's own marketing suggests, but here's what independent sources show.

| | IndicTrans2 (dedicated NMT) | Gemma 3/4-class or GPT-4o-class LLM |
|---|---|---|
| What it is | 1B (or 200M) encoder-decoder, trained only to translate | 4B–400B general model, translating via instructions |
| Hindi accuracy, independent test | Close 2nd to Google Translate, ahead of NLLB/OPUS ([arXiv 2505.19604](https://arxiv.org/abs/2505.19604)) | In the ACL 2026 **ITEM** study, **GPT-4o-mini beat IndicTrans2 specifically on Hindi** — the one language in that 6-language study where the dedicated model lost ([ACL Anthology](https://aclanthology.org/2026.acl-long.1171/)) |
| Other Indic languages | Usually wins ([ITEM study](https://aclanthology.org/2026.acl-long.1171/); [IndicTrans2 paper](https://arxiv.org/abs/2305.16307): beats open/commercial baselines by 4–8 BLEU/chrF++ En→Indic) | Loses to dedicated NMT models outside Hindi/high-resource languages |
| Fluency / naturalness | Reads stiff, "translated," and drops casual register (conversational fine-tune closed some of that gap: [arXiv 2606.29024](https://arxiv.org/abs/2606.29024)) | Reads more natural; GPT-4o is noted for handling idiom and cultural nuance better than dedicated MT ([listicle survey, treat as vendor-adjacent](https://www.edenai.co/post/best-machine-translation-apis)) |
| Document/long-context handling | Needs sentence splitting; base models cap at ~200–256 tokens, RoPE variant extends to 2048 ([GitHub](https://github.com/AI4Bharat/IndicTrans2)) | Handles paragraphs/whole documents natively, keeps context across sentences |
| Consistency / hallucination risk | Low — it's a narrow, constrained decoder, not prone to inventing content | Higher — general LLMs can paraphrase, drop, or add content, over-explain, or refuse; TranslateGemma users report degraded quality past ~2K tokens ([AiCybr](https://aicybr.com/blog/translategemma-guide)) |
| Hardware | Runs on CPU, ~200M–1B params | Needs a real GPU for 12B+; 4B-class models are noted as noticeably weaker |
| Cost to run at scale | Very low | Higher — bigger model, more compute per sentence |
| Real-world, independent evidence | Strong (Bhashini national deployment, Wikipedia MinT, 2 independent human-evaluation studies) | Thin for Hindi specifically — the "Gemma 3 12B is best for low-resource languages" and "GPT-4o leads FLORES-200" claims mostly trace back to vendor benchmarks or SEO comparison sites, not independent human evaluation of Hindi ([example](https://www.hakunamatatatech.com/our-resources/blog/best-llm-for-translation)) |

**Reading it straight:** for Hindi specifically, the one solid independent result (ITEM, ACL 2026) has a general LLM (GPT-4o-mini) edging out IndicTrans2 — but that's a single study, on a 150-sentence FLORES-based set, and it's the *exception* the paper itself calls out (IndicTrans2 wins the other five languages it tested). Everywhere else, "LLMs are better at Hindi" claims trace back to vendor blog posts or marketing-style listicles, not controlled human evaluation. For a fully offline news pipeline, IndicTrans2 is still the lower-risk pick: cheap, predictable, CPU-friendly, and proven at national scale. If you can run a 12B+ GPU model and care more about fluent, context-aware prose than about guaranteed literal fidelity, TranslateGemma-12B/27B is the LLM-side pick worth A/B testing against it — not a generic chat LLM used ad hoc.

---

## IndicTrans3 — what's actually known

IndicTrans3-beta is AI4Bharat's newest release (still labelled **beta**), and it's a real architecture change, not just a version bump:

- **Built on Gemma 3**, not the encoder-decoder Transformer that IndicTrans1/2 used. It's fine-tuned for **document-level** translation rather than sentence-level ([HF model card](https://huggingface.co/ai4bharat/IndicTrans3-beta), [AIM coverage](https://analyticsindiamag.com/ai-news-updates/ai4bharat-launches-indictrans3-for-22-indic-languages/)).
- **Languages:** 15 Indic languages fully supported, including Hindi, plus 7 more (Bodo, Dogri, Kashmiri, Konkani, Manipuri, Santali, Sindhi) in preliminary support — narrower than IndicTrans2's full 22-language coverage for now.
- **Inference:** ships with a vLLM-based script for scalable serving, sentence- and document-level modes ([GitHub/HF space](https://huggingface.co/spaces/ai4bharat/IndicTrans3-beta)).
- **AI4Bharat's own framing:** aims to be "on par with leading global translation models" and plans to release training data ([AIM](https://analyticsindiamag.com/ai-news-updates/ai4bharat-launches-indictrans3-for-22-indic-languages/)).

**What's missing:**
- **No published chrF/BLEU comparison table** against IndicTrans2, TranslateGemma or Sarvam-Translate was found. Search results repeatedly point back to the same model card and one AIM article; no benchmark numbers surfaced.
- **No independent human evaluation.** Nothing on Hindi accuracy specifically.
- One relevant third-party signal: a public Hugging Face comparison space (`nithinshesh/indic-sarvam-translation-compare`) ran a large-scale LLM-judged test (500 documents × 22 languages, two independent judges, ≥75/100 pass bar) and reported that a newer AI4Bharat-side model "clearly beats Sarvam-Translate on every measure" ([HF Space](https://huggingface.co/spaces/nithinshesh/indic-sarvam-translation-compare)). The search excerpts don't unambiguously confirm this run was IndicTrans3 rather than IndicTrans2 — treat this as a **lead to verify**, not a confirmed result, and check the space directly before citing it.
- Still tagged **beta**. No production deployment (Bhashini, Wikimedia, or otherwise) was found yet — unlike IndicTrans2, which already has a national-scale track record.

**Verdict:** IndicTrans3 is the most promising thing on this list architecturally (a Gemma-3 backbone gets it LLM-level fluency and document context, from the team with the best track record on Indic accuracy). But it is **unproven today** — no independent benchmark, no human evaluation, no production deployment. Worth piloting alongside IndicTrans2, not worth switching to blind.

---

## The contenders

### TranslateGemma (Google, Jan 2026; 4B / 12B / 27B)
- Fine-tuned from Gemma 3 for translation across 55 languages, including Hindi. The 12B model beats the Gemma 3 27B baseline on MetricX ([Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/)).
- **Gap:** the tech report's professional human evaluation (MQM) covered 10 language pairs. That included **Marathi but not Hindi** ([report review](https://www.themoonlight.io/en/review/translategemma-technical-report)). For Hindi, the only evidence is automatic metrics plus community reports.
- **User feedback** (Ollama and Obsidian users): translations are called "outstanding compared to any other offline model." Users also say **the 4B model is noticeably worse, so use 12B or 27B**. Quality drops past about 2K tokens of context ([Medium demo](https://medium.com/free-or-open-source-software/demo-translategemma-ollama-obsidian-55-languages-offline-ai-powered-translation-global-indian-14ae927d8aa3), [AiCybr guide](https://aicybr.com/blog/translategemma-guide)).
- Easy to run: `ollama run translategemma:27b`.

### Sarvam-Translate (Sarvam AI, Jun 2025; Gemma-3-4B fine-tune)
- Sarvam's own blind evaluation with professional translators rated it **significantly better than Gemma3-27B, Llama-4 Scout and Llama-3.1-405B** ([Sarvam blog](https://www.sarvam.ai/blogs/sarvam-translate)). The evaluation was expert-run, but it was done by the vendor.
- **Real-world complaints:** output collapses into repeated tokens or gibberish on some inputs ([HF discussion #7](https://huggingface.co/sarvamai/sarvam-translate/discussions/7), [#13](https://huggingface.co/sarvamai/sarvam-translate/discussions/13)). One hands-on reviewer found stiff, literal renderings of idioms (in Kannada) ([Thejesh GN](https://thejeshgn.com/2025/06/10/first-impressions-of-sarvam-indic-translate-model/)). The chat template must be called with `add_generation_prompt=True`, or quality suffers.
- Strength: document-level input with preserved formatting.
- Check the licence on the model card before commercial use.

### Bodhan AI Indic-Translate (Bodhan AI + AI4Bharat + NVIDIA, Sept 2026)
- On Bodhan's **in-house** document test it scores 58.97 dBLEU, against 47.44 for Sarvam-Translate and 31.93 for IndicTrans2-1B. **Human evaluation is still in progress**, and the model is under a month old ([HF](https://huggingface.co/bodhan-ai/indic-translate), [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2026/09/bodhan-ai-indic-models/)). Promising: AI4Bharat, the IndicTrans2 team, is involved. But there is no real-world signal yet, so re-check in 2–3 months.

### IndicTrans3-beta (AI4Bharat)
- A Gemma-3-based model for document-level translation. It supports 15 languages fully and 7 more in preview ([HF](https://huggingface.co/ai4bharat/IndicTrans3-beta)). It is still labelled beta, with no published human evaluation.

### Why not the others
- **NLLB-200:** Independent studies document hallucination, repetition and omissions ([arXiv 2511.00486](https://arxiv.org/pdf/2511.00486)). It loses to IndicTrans2 in human evaluation. Its licence is **CC-BY-NC**, and Meta calls it a research model, not for production.
- **General LLMs (Sarvam-30B/105B, Qwen3, Llama, Gemma 4):** SEO "best LLM for Hindi" listicles recommend them, but those lists are not translation evaluations. Independent tests show mixed Indic results. For example, Gemma 4 31B beat Sarvam-30B on a multilingual benchmark in every language ([Medium](https://medium.com/@indiai/india-first-llms-on-indian-languages-sarvam-30b-and-param2-17b-6676b637f3ab)). Users also report Gemma 4 **code-switching into English** on specialised topics ([DEV](https://dev.to/devsaquib/i-tested-gemma-4-and-gpt-4o-mini-on-indian-language-tasks-the-results-surprised-me-19g8)). For pure translation, a dedicated model is cheaper and more predictable.

---

## Comparison with Process9 Mox (MoxVeda / MoxWave / MoxNMT)

**What it is.** Process Nine Technologies is a Gurugram localization company, founded in 2009. It had about 74 staff in Aug 2025 and has raised about $1.13M ([Tracxn](https://tracxn.com/d/companies/process9/__3TYOJxGK4MIefKX83cR_0B4GSVIV6HiLtE6T9DgoATE)). It sells the **Mox suite**:
- **MoxVeda** is a website and app localization layer. It translates a live site with no code or database changes and keeps it in sync with the English source ([MoxVeda](https://process9.com/mox-veda/)). It is a *platform*, not a model, and "can integrate with any machine translation engine of your choice."
- **MoxWave** is the translation API ([MoxWave](https://process9.com/mox-wave/)).
- **MoxNMT** is the proprietary Indic translation engine underneath ([Azure Marketplace sheet](https://catalogartifact.azureedge.net/publicartifacts/processninetechnologiespvtltd1640269656476.mox_nmt_01-c7b98300-c120-485b-b98b-a54f62394d46/Artifacts/Documents/Process9_MoxNMT.pdf)).
- The suite adds human-in-the-loop review, translation memory, glossaries and style guides. It is ISO 27001 certified ([Mox vs Bhashini](https://process9.com/mox-vs-bhashini/)).

**It is not open source.** Mox is a closed, subscription SaaS. It is not a like-for-like alternative to IndicTrans2 or TranslateGemma. The fair comparison is with a *commercial service* (Google or Azure Translate plus human post-editing).

**Accuracy evidence found:**
- **Vendor claim:** "95%+ accuracy in Hindi, Tamil, Bengali vs ~80% in generic tools," trained on 100M+ Indian-language phrases ([Process9 FAQ](https://process9.com/faq-translation-tools-indian-languages/)). The metric, test set and method are **not disclosed**, so the figure cannot be checked or compared with BLEU, chrF or human-evaluation scores elsewhere.
- **Independent benchmarks:** **none found.** MoxNMT does not appear in any academic comparison (IN22, FLORES, WMT, the ITEM study) or in any public leaderboard. The English–Hindi comparison studies cited above tested Google, IndicTrans2, NLLB, OPUS-MT, Bing and Anuvad, not Process9.
- **Independent user reviews:** **none found** on G2, Capterra, Reddit or blogs. No complaints were found either. The public signal is simply thin.

**Real-world adoption, all vendor-published:**
- **Axis Bank:** Hindi customer-support site went live in Jan 2022 on MoxVeda. Axis said it "carefully evaluated many options… chose Process9" for ease of use, security, speed and quality ([case study](https://process9.com/case-study/axis-bank-case-study/)).
- **Tata 1mg:** 500k+ healthcare product listings localized into Hindi. Hindi user sessions "more than doubled in a month" ([case study](https://process9.com/case-study/tata-1mg/)).
- **Startup India:** has used Process9 for about 5 years across 22 Indian and 19 foreign languages; describes "good accuracy" at high volume ([Process9 site](https://process9.com/)).
- **Paytm, PolicyBazaar, MakeMyTrip, BookMyShow** are named as customers. PolicyBazaar saw 3× interest in bike insurance after selling in Hindi ([YourStory](https://yourstory.com/2020/10/raise-2020-startup-indic-language-interface-paytm-policybazaar)).
- **How to read this:** long-term, regulated-industry customers (a bank, a pharmacy platform, a government programme) are a meaningful signal that the output is *acceptable in production*. But:
  - The quotes are vendor-published.
  - The numbers measure *business engagement* (sessions, interest), not translation accuracy.
  - The final quality depends heavily on the **human reviewers** in the workflow, not only the machine output.

**Fit for this repo:** poor. The pipeline is built to be offline or air-gapped, and Mox is a hosted SaaS. No on-premise or offline model release was found. It also costs a subscription and sends feed content to a third party.

### Comparison table

| | IndicTrans2 | TranslateGemma 12B/27B | Sarvam-Translate | Bodhan Indic-Translate | NLLB-200 | **Process9 Mox** |
|---|---|---|---|---|---|---|
| Type | Open model (MIT) | Open weights (Gemma terms) | Open weights (check card) | Open weights (new) | Open, **non-commercial** (CC-BY-NC) | **Proprietary SaaS + human review** |
| Hindi-specific | Yes (22 langs) | Yes (55 langs) | Yes (22 langs) | Yes (22 langs) | Yes (200 langs) | Yes (22+ langs claimed) |
| **Independent human evaluation for Hindi** | ✅ Beat NLLB (11-factor human study); close 2nd to Google | ❌ Not for Hindi (MQM covered Marathi) | ❌ Vendor-run only | ❌ "In progress" | ✅ Loses to IndicTrans2 | ❌ None |
| Vendor accuracy claim | chrF++ on public IN22 (reproducible) | MetricX on WMT24++ (reproducible) | Expert pairwise preference | dBLEU 58.97 on in-house set | chrF on FLORES (reproducible) | "95%+ accuracy" (**method not disclosed**) |
| Real-world deployment | Bhashini (national, e.g. Red Fort speech 2026); Wikipedia MinT | Hobbyist and dev use (Ollama) | Sarvam API users | None yet (1 month old) | Wikipedia MinT (other langs) | Axis Bank, Tata 1mg, Startup India, Paytm, PolicyBazaar |
| Is the real-world evidence independent? | ✅ Yes (govt and Wikimedia public records) | Partly (blogs, anecdotal) | Partly (HF discussions) | ❌ | ✅ (academic papers) | ❌ Vendor case studies only |
| Reported problems | Stiff register; sentence splitting needed; 200–256-token limit (fixed in RoPE variant) | 4B weak; worse past 2K tokens | Repetition/gibberish loops; literal idioms | Unknown | Hallucination, repetition, omissions | None public (no independent reviews found) |
| Runs offline / on CPU | ✅ Yes (200M on CPU; CTranslate2) | ⚠️ GPU needed for 12B/27B | ⚠️ GPU preferred | ⚠️ GPU (vLLM / TensorRT) | ✅ Yes | ❌ Hosted service |
| Cost | Free | Free (hardware) | Free (hardware) | Free (hardware) | Free, non-commercial only | Paid subscription |
| Human-in-the-loop / TM / glossary | DIY | DIY | DIY | DIY | DIY | ✅ Built in |
| **Verdict for this repo** | **Use (default)** | Use if GPU; A/B vs IndicTrans2 | Try, watch for loops | Re-check in 2–3 months | Avoid | Not suitable (closed, online, unverifiable accuracy); consider only for customer-facing sites needing human review |

### All findings, by source and independence

| # | Finding | Model / vendor | Source | Independent of vendor? |
|---|---|---|---|---|
| 1 | Live-translated PM's Hindi speech into 22 languages in production (Aug 2026) | IndicTrans2 | [TechTimes](https://www.techtimes.com/articles/324582/20260815/india-deploys-homegrown-ai-red-fort-pledges-ai-training-ten-million-youth.htm) | ✅ |
| 2 | Serves Wikipedia editors via MinT on CPU | IndicTrans2, NLLB | [MediaWiki MinT](https://www.mediawiki.org/wiki/MinT) | ✅ |
| 3 | Human 11-factor evaluation: IndicTrans2 better than NLLB for En–Hi | IndicTrans2 vs NLLB | [Springer](https://link.springer.com/chapter/10.1007/978-3-031-91331-0_7) | ✅ |
| 4 | En–Hi comparison: Google 1st, IndicTrans2 close 2nd, NLLB and OPUS trail | IndicTrans2, NLLB | [arXiv 2505.19604](https://arxiv.org/abs/2505.19604) | ✅ |
| 5 | GPT-4o-mini beats IndicTrans2 on Hindi; IndicTrans2 wins in most other languages | IndicTrans2 | [ACL 2026 ITEM](https://aclanthology.org/2026.acl-long.1171/) | ✅ |
| 6 | Stiff on conversational text; +6.2 chrF after adaptation | IndicTrans2 | [arXiv 2606.29024](https://arxiv.org/abs/2606.29024) | ✅ |
| 7 | 200–256-token limit; long-context RoPE variant Jan 2025; users ask about batching documents | IndicTrans2 | [GitHub](https://github.com/AI4Bharat/IndicTrans2), [#58](https://github.com/AI4Bharat/IndicTrans2/issues/58) | ✅ |
| 8 | 12B beats Gemma 3 27B on MetricX | TranslateGemma | [Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/translategemma/) | ❌ vendor |
| 9 | MQM human evaluation covered Marathi, not Hindi | TranslateGemma | [Tech report review](https://www.themoonlight.io/en/review/translategemma-technical-report) | ❌ vendor |
| 10 | Users: "outstanding vs other offline models"; use 12B/27B, not 4B; worse past 2K tokens | TranslateGemma | [Medium](https://medium.com/free-or-open-source-software/demo-translategemma-ollama-obsidian-55-languages-offline-ai-powered-translation-global-indian-14ae927d8aa3), [AiCybr](https://aicybr.com/blog/translategemma-guide) | ✅ (anecdotal) |
| 11 | Expert pairwise evaluation: better than Gemma3-27B, Llama-4 Scout, Llama-3.1-405B | Sarvam-Translate | [Sarvam blog](https://www.sarvam.ai/blogs/sarvam-translate) | ❌ vendor |
| 12 | Output-token repetition / gibberish reported by users | Sarvam-Translate | [HF #7](https://huggingface.co/sarvamai/sarvam-translate/discussions/7), [HF #13](https://huggingface.co/sarvamai/sarvam-translate/discussions/13) | ✅ |
| 13 | Literal, unnatural idiom rendering (Kannada) | Sarvam-Translate | [Thejesh GN](https://thejeshgn.com/2025/06/10/first-impressions-of-sarvam-indic-translate-model/) | ✅ |
| 14 | 58.97 dBLEU vs Sarvam 47.44 vs IndicTrans2 31.93 on in-house set; human evaluation pending | Bodhan Indic-Translate | [HF](https://huggingface.co/bodhan-ai/indic-translate), [Analytics Vidhya](https://www.analyticsvidhya.com/blog/2026/09/bodhan-ai-indic-models/) | ❌ vendor |
| 15 | Gemma-3-based, document-level, still beta | IndicTrans3-beta | [HF](https://huggingface.co/ai4bharat/IndicTrans3-beta) | ❌ vendor |
| 16 | Hallucination, repetition, omissions; research-only licence | NLLB-200 | [arXiv 2511.00486](https://arxiv.org/pdf/2511.00486), [HF card](https://huggingface.co/facebook/nllb-200-3.3B) | ✅ |
| 17 | Gemma 4 31B beats Sarvam-30B across Indic languages; Gemma 4 code-switches into English | General LLMs | [Medium](https://medium.com/@indiai/india-first-llms-on-indian-languages-sarvam-30b-and-param2-17b-6676b637f3ab), [DEV](https://dev.to/devsaquib/i-tested-gemma-4-and-gpt-4o-mini-on-indian-language-tasks-the-results-surprised-me-19g8) | ✅ (anecdotal) |
| 18 | "95%+ accuracy in Hindi vs ~80% generic"; method not disclosed | Process9 MoxNMT | [Process9 FAQ](https://process9.com/faq-translation-tools-indian-languages/) | ❌ vendor |
| 19 | MoxVeda = website localization layer; works with any MT engine; human-in-the-loop | Process9 MoxVeda | [MoxVeda](https://process9.com/mox-veda/) | ❌ vendor |
| 20 | Axis Bank Hindi support site live Jan 2022; chose Mox after evaluating options | Process9 | [Case study](https://process9.com/case-study/axis-bank-case-study/) | ❌ vendor-published testimonial |
| 21 | Tata 1mg: 500k+ products in Hindi; Hindi sessions 2× in a month | Process9 | [Case study](https://process9.com/case-study/tata-1mg/) | ❌ vendor-published |
| 22 | Startup India: about 5 years of use, "good accuracy" at volume | Process9 | [Process9 site](https://process9.com/) | ❌ vendor-published |
| 23 | Customers incl. Paytm, PolicyBazaar, MakeMyTrip, BookMyShow; PolicyBazaar 3× interest in Hindi | Process9 | [YourStory](https://yourstory.com/2020/10/raise-2020-startup-indic-language-interface-paytm-policybazaar) | ⚠️ press, based on company interview |
| 24 | No independent benchmark, academic evaluation or public user review found | Process9 | Searches of academic, G2/Capterra and community sources | — (absence of evidence) |
| 25 | Small company: about 74 staff, about $1.13M raised | Process9 | [Tracxn](https://tracxn.com/d/companies/process9/__3TYOJxGK4MIefKX83cR_0B4GSVIV6HiLtE6T9DgoATE) | ✅ |

---

## Recommendation for this pipeline

1. **Default:** `ai4bharat/indictrans2-en-indic-dist-200M` on CPU, or `indictrans2-en-indic-1B` if a GPU is available. Pre-process with IndicTransToolkit, split into sentences, and optionally convert to CTranslate2 as Wikimedia does. Headlines and summaries are short, formal news text, which is exactly IndicTrans2's strongest case.
2. **If a GPU (≥16 GB) is available:** run **TranslateGemma-12B/27B** alongside it and compare the two on your own feed.
3. **Do a 1-hour blind test before committing.** No independent Hindi human evaluation compares these three head to head. Take about 50 real feed items. Translate them with each model, shuffle the outputs, and have a native Hindi speaker rate adequacy (meaning kept?) and fluency (natural Hindi?) on a 1–5 scale. Pay close attention to named entities, numbers and dates, which are the usual failure points in news.
4. Re-evaluate Bodhan Indic-Translate once independent human evaluations are published.

## Caveats on this research
- Page fetching was blocked in the research environment. The findings come from search-engine excerpts of the sources linked above, not full-text reads. Verify key numbers against the originals before citing them.
- No large independent Reddit or community threads came up for Hindi MT specifically. The real-world signals used here are production deployments (Bhashini, Wikimedia MinT), independent academic human evaluations, and user reports on Hugging Face, GitHub and blogs.
