# Translation English → Kazakh: compressed for Kazakh + Russian vs. for English, same size

Qwen3-30B-A3B-Instruct-2507, two files written by `linguasqueeze compress --bits 4,3` (experts carrying 90% of the
calibration traffic at 4 bits, the rest at 3; attention 8-bit). Only the text given to `compress` differs:
64 Kazakh + 64 Russian Wikipedia articles (15.24 GB) or 128 English Wikipedia articles (15.36 GB).
That text decides two things together: the GPTQ calibration and which experts keep 4 bits. The result below is their
combined effect; this test does not separate them. (With every expert at 3 bits, calibration alone did not change
knowledge: see `experiments/calibration-language/`.)
Both files translate the same FLORES-200 devtest sentences English → Kazakh with GPTQModel on two T4 (greedy decoding).
Rule fixed before the run: corpus chrF of the Kazakh + Russian file minus the English file, paired bootstrap
(1,000 resamples) 95% interval above zero.

| File | chrF |
|---|---|
| Compressed for Kazakh + Russian, 15.24 GB | 45.5 |
| Compressed for English, 15.36 GB | 40.0 |
| Difference [95% CI] | **+5.5 [+3.9, +7.1]** |

136 of the 200 sampled sentences were translated by both files before the 60-minute limit per file; both files are
scored on the same 136. One model, one run. `translations.csv` holds every source, reference and both outputs.

FLORES-200 (CC BY-SA 4.0), NLLB Team et al., 2022: https://github.com/facebookresearch/flores
