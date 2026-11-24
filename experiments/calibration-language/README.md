# Does the calibration language change knowledge?

Qwen3.6-35B-A3B, every routed expert GPTQ 3-bit (group 128), full-attention projections 8-bit, same file size for both variants.
Calibration: 512 English Wikipedia articles vs. 256 Kazakh + 256 Russian Wikipedia articles (512 tokens each).
Exam: KazMMLU, 3,000 Kazakh and 1,200 Russian questions, seeded sample. Rule fixed before the run: Kazakh + Russian
calibration must beat English with the paired 95% bootstrap interval above zero on Kazakh. It did not.

| | English calibration | Kazakh + Russian calibration | Difference, points [95% CI] |
|---|---|---|---|
| KazMMLU kk (n = 3,000) | 64.2% | 64.6% | +0.4 [−1.1, +1.8] |
| KazMMLU ru (n = 1,200) | 73.0% | 74.8% | +1.8 [−0.2, +3.6] |

`scores.csv`: one row per question with both variants' choices; `summary.json`: the numbers above.
