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
| Watch | **Bodhan AI Indic-Translate** (Sept 2026), **IndicTrans3-beta** | Worth testing, but not trusting yet | Only self-reported numbers so far. Human evaluation "in progress" |
| Avoid | NLLB-200, and general chat LLMs used as translators | — | See below |

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

## Recommendation for this pipeline

1. **Default:** `ai4bharat/indictrans2-en-indic-dist-200M` on CPU, or `indictrans2-en-indic-1B` if a GPU is available. Pre-process with IndicTransToolkit, split into sentences, and optionally convert to CTranslate2 as Wikimedia does. Headlines and summaries are short, formal news text, which is exactly IndicTrans2's strongest case.
2. **If a GPU (≥16 GB) is available:** run **TranslateGemma-12B/27B** alongside it and compare the two on your own feed.
3. **Do a 1-hour blind test before committing.** No independent Hindi human evaluation compares these three head to head. Take about 50 real feed items. Translate them with each model, shuffle the outputs, and have a native Hindi speaker rate adequacy (meaning kept?) and fluency (natural Hindi?) on a 1–5 scale. Pay close attention to named entities, numbers and dates, which are the usual failure points in news.
4. Re-evaluate Bodhan Indic-Translate once independent human evaluations are published.

## Caveats on this research
- Page fetching was blocked in the research environment. The findings come from search-engine excerpts of the sources linked above, not full-text reads. Verify key numbers against the originals before citing them.
- No large independent Reddit or community threads came up for Hindi MT specifically. The real-world signals used here are production deployments (Bhashini, Wikimedia MinT), independent academic human evaluations, and user reports on Hugging Face, GitHub and blogs.
