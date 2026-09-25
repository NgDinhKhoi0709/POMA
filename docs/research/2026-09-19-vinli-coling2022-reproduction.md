# ViNLI (COLING 2022): research note for a closest-possible reproduction

Research date: 2026-09-19. Scope: the paper named in the request, **not** a
new Vietnamese TableQA method. The authoritative experimental source is Huynh,
Nguyen, and Nguyen, *ViNLI: A Vietnamese Corpus for Studies on Open-Domain
Natural Language Inference*, COLING 2022, pp. 3858--3872 ([ACL record](https://aclanthology.org/2022.coling-1.339/), [paper PDF](https://aclanthology.org/2022.coling-1.339.pdf)). Page references below refer to that PDF.

## Bottom line

The closest faithful reproduction is a **four-way Vietnamese NLI classifier**
fine-tuned for 10 epochs on the authors' 24,376-example training split, with
the exact supplied dev/test files; the paper's strongest reported system is
XLM-R Large. It reached 85.99 accuracy / 86.10 macro-F1 on the four-label test
set, and 81.36 / 81.31 after excluding `OTHER`. Those are paper-reported target
numbers, not results reproduced in this repository. [Paper, Table 6, p. 3865](https://aclanthology.org/2022.coling-1.339.pdf)

Exact numerical reproduction is currently blocked by data/provenance rather
than model code: the paper gives the split **counts**, but no split IDs, random
seed, data schema, checkpoint identifiers, or released training code. Its
official group site currently has a dataset catalogue, but it does not list
ViNLI; an on-page search returns no occurrence. The paper only says that the
corpus is public for research, without a dataset URL. [Paper, abstract and
§3.5, pp. 3858, 3862](https://aclanthology.org/2022.coling-1.339.pdf)
[UIT NLP Group dataset catalogue](https://nlp.uit.edu.vn/datasets)

Therefore: obtain the authors' original files/split manifest before treating a
score as a reproduction. Reconstructing a fresh 80/10/10 split is a useful
**replication-style** experiment, but it is not comparable to Table 6.

## What was evaluated

ViNLI contains 30,376 Vietnamese premise--hypothesis pairs from more than 800
VnExpress news articles across 13 topics. It has four labels:
`ENTAILMENT`, `CONTRADICTION`, `NEUTRAL`, and `OTHER`. `OTHER` means a premise
and hypothesis have no connection in event, subject, or object; it is not the
same as a hypothesis that might be true but is undetermined (`NEUTRAL`).
[Paper, §1 and §3.2--3.3, pp. 3858, 3861](https://aclanthology.org/2022.coling-1.339.pdf)

For each 3--5-paragraph article, the authors chose the topic sentence of every
paragraph as a premise (three to five premises/article). An annotator then
wrote **eight** hypotheses per premise: two for each of the four labels.
[Paper, §3.2--3.3, p. 3861](https://aclanthology.org/2022.coling-1.339.pdf)

The original corpus was randomly divided into Train/Dev/Test as 80%/10%/10%,
with topic counts intentionally kept even on Dev and Test. The exact
four-label totals are below. [Paper, §3.5 and Table 9, pp. 3862, 3869](https://aclanthology.org/2022.coling-1.339.pdf)

| split | pairs | label counts: E / C / N / O | premise / hypothesis mean length (words) |
| --- | ---: | --- | --- |
| train | 24,376 | 6,094 / 6,094 / 6,094 / 6,094 | 24.5 / 18.3 |
| dev | 3,009 | 739 / 764 / 752 / 754 | 24.6 / 17.9 |
| test | 2,991 | 750 / 737 / 777 / 727 | 24.3 / 18.1 |
| total | 30,376 | 7,583 / 7,595 / 7,623 / 7,575 | 24.5 / 18.1 |

`Test300` is a random 300-example subset of Test used for comparison with five
newly trained native-speaker annotators. It is not a training or model-selection
split. Human majority-vote accuracy was 95.34% for three labels and 95.78% for
four. [Paper, §4.3 and Table 6, pp. 3864--3865](https://aclanthology.org/2022.coling-1.339.pdf)

## Faithful data and preprocessing protocol

1. Use the supplied pair-level splits unchanged. Keep the four labels for the
   primary run; make a second three-label run by removing `OTHER` from each
   split, as in the paper. [Paper, §4.1, p. 3864](https://aclanthology.org/2022.coling-1.339.pdf)
2. For transformer runs, the paper describes both syllable-level inputs (space
   separates Vietnamese syllables) and word-level inputs. Do **not** add an
   undocumented tokenizer/normalizer beyond the selected pretrained model's
   own tokenizer. [Paper, §4.1, p. 3864](https://aclanthology.org/2022.coling-1.339.pdf)
3. For the word-level CBoW, BiLSTM, and ESIM baselines, segment Vietnamese
   with VnCoreNLP first, then use the word-level 300-dimensional PhoW2V;
   their syllable counterparts use the 300-dimensional syllable PhoW2V.
   [Paper, §4.1, p. 3864](https://aclanthology.org/2022.coling-1.339.pdf)
4. Do not regenerate labels for a headline result. The paper validated every
   Dev/Test pair with five annotators distinct from the hypothesis author,
   chose majority vote, and excluded pairs without at least 3/5 agreement;
   99.4% had a three-or-more-label agreement. [Paper, §3.4 and Table 4,
   pp. 3862--3863](https://aclanthology.org/2022.coling-1.339.pdf)

## Training configuration explicitly reported

All baselines were trained with Adam on a Tesla P100-PCIE-16GB Google Colab
GPU. Neural baselines are CBoW, ESIM, and BiLSTM; transformer baselines are
mBERT, XLM-R (base and large), and PhoBERT (base and large). PhoBERT is
described as a RoBERTa architecture with 135M (base) and 370M (large)
parameters. [Paper, §4.1, p. 3864](https://aclanthology.org/2022.coling-1.339.pdf)

| family | representation / library | LR | batch | epochs | max sequence length |
| --- | --- | ---: | ---: | ---: | ---: |
| CBoW, ESIM, BiLSTM | PhoW2V, syllable and VnCoreNLP-word versions | 0.001 | 16 | 10 | 80 |
| mBERT, XLM-R, PhoBERT | Hugging Face Transformers | 1e-5 | 16 | 10 | not reported |

The settings in the table are exactly those published. [Paper, §4.1,
p. 3864](https://aclanthology.org/2022.coling-1.339.pdf)

### Required pins/decisions that the paper does not report

These must be recorded in any new run because they can move the result, but
they cannot be presented as recovered paper settings: pretrained checkpoint
revision and tokenizer revision; optimizer beta/epsilon/weight decay; learning
rate schedule/warm-up; dropout; seed(s); maximum pair length and truncation
policy for transformers; gradient accumulation/clipping/mixed precision;
classification-head initialization; early-stopping/checkpoint selection; and
the implementations/hyperparameters of CBoW, ESIM, and BiLSTM. The paper
reports only the configurations above, so none of these omitted values may be
inferred from its results. [Paper, §4.1, p. 3864](https://aclanthology.org/2022.coling-1.339.pdf)

For a closest operational run once the original dataset is obtained, pin a
current Transformers release, save its full config and tokenizer hashes, use a
single linear head over the encoder pair representation, Adam/AdamW at the
reported `1e-5`, batch 16, 10 epochs, and select only by Dev macro-F1. This is a
documented engineering completion of missing details, **not** a claim about the
authors' hidden implementation.

## Evaluation and expected reference results

Compute plain classification accuracy as the primary metric and unweighted
macro-F1 as the second metric. The near equality in reported accuracy and F1 is
expected from the approximately balanced corpus; do not substitute weighted-F1
or micro-F1 for the headline. [Paper, §4.2 and §4.4, pp. 3864--3865](https://aclanthology.org/2022.coling-1.339.pdf)

| model | 3-label dev acc/F1 | 3-label test acc/F1 | 4-label dev acc/F1 | 4-label test acc/F1 |
| --- | --- | --- | --- | --- |
| mBERT | 67.41 / 67.46 | 64.84 / 64.83 | 73.91 / 73.83 | 73.45 / 73.62 |
| XLM-R Base | 72.02 / 71.99 | 71.59 / 71.51 | 76.97 / 76.93 | 76.83 / 77.01 |
| **XLM-R Large** | **83.02 / 82.98** | **81.36 / 81.31** | **86.77 / 86.76** | **85.99 / 86.10** |
| PhoBERT Base | 75.07 / 75.08 | 72.87 / 72.79 | 79.79 / 79.75 | 78.00 / 78.05 |
| PhoBERT Large | 77.33 / 77.34 | 75.93 / 75.87 | 80.72 / 80.72 | 80.67 / 80.69 |

These are transcriptions of the transformer rows in the paper's Table 6.
[Paper, Table 6, p. 3865](https://aclanthology.org/2022.coling-1.339.pdf)

The strongest XLM-R Large score on `Test300` was 81.14% (three labels) and
88.85% (four labels), leaving the reported human gaps of 14.20 and 6.93 points,
respectively. [Paper, §4.4 and Table 6, p. 3865](https://aclanthology.org/2022.coling-1.339.pdf)

## Data/code artefact audit

- The ACL anthology is the official publication record and provides the PDF,
  metadata, and citation, but no code/data link is present on the record.
  [ACL Anthology record](https://aclanthology.org/2022.coling-1.339/)
- The paper cites the UIT NLP Group home page as the corpus's public-research
  location, rather than a versioned archive, code repository, DOI, or licence.
  [Paper, p. 3858 footnote 1](https://aclanthology.org/2022.coling-1.339.pdf)
- The current official UIT dataset catalogue is reachable, but it has no
  ViNLI entry, download, user agreement, or author contact specific to ViNLI.
  That is an observation of the cited current page, not evidence that the
  historical corpus never existed. [UIT NLP Group datasets](https://nlp.uit.edu.vn/datasets)
- The public repository of coauthor Kiet Van Nguyen contains other Vietnamese
  datasets but has no ViNLI material. The paper itself gives the most concrete
  acquisition route available here: `tinhv@uit.edu.vn`, `kietnv@uit.edu.vn`,
  and `ngannlt@uit.edu.vn`. [Kiet Nguyen's VietnameseDatasets
  repository](https://github.com/kietnv/VietnameseDatasets) [Paper, p. 3858](https://aclanthology.org/2022.coling-1.339.pdf)
- A focused GitHub search for the full title surfaces citations and downstream
  projects, not an author-owned release of this paper's code/data. Treat any
  such mirror as third-party until its file hashes and split provenance are
  confirmed against the authors. [GitHub search](https://github.com/search?q=%22ViNLI%3A+A+Vietnamese+Corpus+for+Studies+on+Open-Domain+Natural+Language+Inference%22&type=code)

Do not silently substitute the later `ViANLI` adversarial benchmark or ViSP
paraphrase data for ViNLI: they are different corpora and do not implement this
paper's four-label split/evaluation. [Paper, §3.3--§4.2, pp. 3861--3864](https://aclanthology.org/2022.coling-1.339.pdf)

## Reproduction acceptance checklist

- [ ] Original corpus acquisition is documented (source, permission/licence,
      file checksums, retrieval date).
- [ ] Four supplied labels map unambiguously to `0..3`, with mapping stored in
      the run metadata.
- [ ] Split IDs/counts exactly match Table 9: 24,376 / 3,009 / 2,991.
- [ ] Three-label evaluation removes, rather than merges, `OTHER`.
- [ ] The model, tokenizer, dependency versions, random seeds, hardware,
      batch semantics and effective batch are logged.
- [ ] Evaluation reports accuracy and macro-F1 on Dev/Test, and keeps Test300
      separate from ordinary Test.
- [ ] Any score on recreated data/splits is labeled `replication-style`, not
      `paper reproduction`.

## Source discipline

Browser inspection was used for the ACL record, the authors' current group
site, and a focused public-code search. Quantitative and method claims in this
note are attributed to the primary paper. No blog, model card, or third-party
dataset mirror was used to fill in unreported hyperparameters or claim an
official artefact exists.
