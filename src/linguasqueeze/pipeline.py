"""The two-command workflow behind the `linguasqueeze` CLI.

`compress`: calibrate GPTQ on text in *your* language, give more bits to the experts your language uses,
and write a standard GPTQ checkpoint, one layer at a time (fits a single small GPU).
`compare`: score the original and the compressed model on the same items and report what your language lost.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
import torch

from linguasqueeze.streaming import ScoredSequence, SequenceScore, StreamedModel, stream_evaluate

MIN_DOC_CHARS = 200
CALIB_MAX_TOKENS = 512  # per calibration document, as in notebooks 06-07
EVAL_MAX_TOKENS = 1024
SUPPORTED_BITS = (2, 3, 4, 8)
BOOTSTRAP_SAMPLES = 2000
CONFIG = "compressed"

Log = Callable[[str], None]


def read_documents(path: str | Path, min_chars: int = MIN_DOC_CHARS) -> list[str]:
    """Documents of a UTF-8 text file, separated by blank lines; shorter ones are dropped."""
    text = Path(path).read_text(encoding="utf-8")
    docs = [d.strip() for d in re.split(r"\n\s*\n", text)]
    docs = [d for d in docs if len(d) >= min_chars]
    if not docs:
        raise ValueError(f"{path}: no document of at least {min_chars} characters "
                         "(separate documents with an empty line)")
    return docs


def encode(tokenizer, text: str, max_tokens: int) -> tuple[int, ...]:
    return tuple(tokenizer(text, truncation=True, max_length=max_tokens).input_ids)


def bit_plan(widths: Sequence[int], keep: float, num_layers: int, num_experts: int):
    """One width -> every expert gets it. Two widths (high, low) -> per layer, the experts that receive
    `keep` of the calibration tokens get the high width, the rest the low one (measured during the run)."""
    from linguasqueeze.gptq import router_traffic
    from linguasqueeze.quant import allocate_bits_by_coverage

    widths = sorted(set(int(w) for w in widths), reverse=True)
    unsupported = [w for w in widths if w not in SUPPORTED_BITS]
    if unsupported:
        raise ValueError(f"bit widths {unsupported} not supported; use {SUPPORTED_BITS}")
    if len(widths) == 1:
        return np.full((num_layers, num_experts), widths[0])
    if len(widths) != 2:
        raise ValueError("give one bit width (e.g. 4) or two (e.g. 4,3)")
    if not 0 < keep < 1:
        raise ValueError("keep must be between 0 and 1 (share of your language's tokens kept at the high width)")

    def choose(config, index, layer, inputs, run_layer):
        traffic = router_traffic(layer, inputs, run_layer).astype(float)
        if traffic.sum() == 0:  # no calibration token reached this layer's router: stay safe
            return np.full(num_experts, widths[0])
        return allocate_bits_by_coverage(traffic[None, :], (keep,), tuple(widths))[0]

    return choose


def compress(model_dir: str | Path, calibration_files: Sequence[str | Path], output: str | Path,
             widths: Sequence[int] = (4,), keep: float = 0.9, group_size: int = 128, attention_bits: int | None = 8,
             device: str = "cuda", layer_limit: int | None = None, tokenizer=None, log: Log = print) -> dict:
    """Write a language-calibrated GPTQ checkpoint of a Mixture-of-Experts model to `output`."""
    from linguasqueeze.export import GPTQCheckpointWriter
    from linguasqueeze.gptq import make_quantization_prepare

    streamed = StreamedModel(model_dir, device=device, dtype=torch.float32)  # fp32 per layer: no fp16 overflow
    if streamed.num_experts == 0:
        raise ValueError("only Mixture-of-Experts models (Qwen3-MoE layout) are supported for now")
    if streamed.prefix != "model." or getattr(streamed, "hybrid", False):
        raise ValueError("writing a compressed file is supported for the Qwen3-MoE layout only for now; "
                         "Qwen3.5/3.6-MoE checkpoints can be scored with `evaluate` but not yet compressed")
    if tokenizer is None:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
    docs = [d for f in calibration_files for d in read_documents(f)]
    calibration = [ScoredSequence(ids=encode(tokenizer, d, CALIB_MAX_TOKENS)) for d in docs]
    plan = bit_plan(widths, keep, streamed.num_layers, streamed.num_experts)
    description = {"base_model": str(model_dir), "bits": sorted(set(widths), reverse=True),
                   "keep": keep if len(set(widths)) == 2 else None,
                   "calibration_files": [Path(f).name for f in calibration_files],
                   "calibration_documents": len(docs), "calibration_tokens": sum(len(s.ids) for s in calibration)}
    writer = GPTQCheckpointWriter(output, streamed.reader, group_size=group_size, default_bits=max(widths),
                                  attention_bits=attention_bits, description=description)
    prepare, stats = make_quantization_prepare(
        streamed, {CONFIG: {"method": "gptq", "bits": plan}}, group_size=group_size,
        attention_bits=attention_bits, log=log,
        on_quantized=lambda config, index, layer, record: writer.write_layer(config, index, layer, record))
    stream_evaluate(streamed, [], [CONFIG], prepare=prepare, calibration={CONFIG: calibration},
                    layer_limit=layer_limit, log=log)
    layers = streamed.num_layers if layer_limit is None else min(layer_limit, streamed.num_layers)
    summary = writer.finish(num_layers=layers)
    summary["rtn_fallback_experts"] = int(sum(s["rtn_fallback_experts"] for s in stats[CONFIG]))
    summary["dry_run"] = layers < streamed.num_layers
    (Path(output) / "linguasqueeze.json").write_text(json.dumps(summary, indent=2))
    return summary


# ---- compare ------------------------------------------------------------------------------------------------

def disk_gb(model_dir: str | Path) -> float:
    return sum(p.stat().st_size for p in Path(model_dir).rglob("*.safetensors")) / 1e9


def build_items(tokenizer, texts: dict[str, str | Path], exam: bool = False
                ) -> tuple[list[ScoredSequence], list[dict]]:
    """Perplexity items from your own text files ({language: file}) and, with `exam`, the fixed
    Belebele + KazMMLU exam of notebook 07 (kk, ru, en; downloads the datasets)."""
    items, meta = [], []
    for lang, path in texts.items():
        for doc in read_documents(path):
            ids = encode(tokenizer, doc, EVAL_MAX_TOKENS)
            if len(ids) >= 2:
                items.append(ScoredSequence(ids=ids, span=(1, len(ids))))
                meta.append({"task": "text", "lang": lang})
    if exam:
        from linguasqueeze.exam import build_exam
        for item in build_exam(tokenizer):
            if item.meta["task"] in ("belebele", "kazmmlu"):
                items.append(ScoredSequence(ids=item.ids, span=item.span, choice_ids=item.choice_ids or ()))
                meta.append(item.meta)
    if not items:
        raise ValueError("nothing to evaluate: give --text LANG=FILE and/or --exam")
    return items, meta


def score_model(model_dir: str | Path, items: Sequence[ScoredSequence], device: str, log: Log) -> list[SequenceScore]:
    return stream_evaluate(StreamedModel(model_dir, device=device, dtype=torch.float32), items, ["m"], log=log)["m"]


def perplexity(scores: Sequence[SequenceScore], meta: Sequence[dict], task: str, lang: str) -> float:
    chosen = [s for s, m in zip(scores, meta) if m["task"] == task and m["lang"] == lang]
    return float(np.exp(-sum(s.span_logprob for s in chosen) / sum(s.span_tokens for s in chosen)))


def correct(scores: Sequence[SequenceScore], meta: Sequence[dict], task: str, lang: str) -> np.ndarray:
    return np.array([int(np.argmax(s.choice_logits)) == m["label"] for s, m in zip(scores, meta)
                     if m["task"] == task and m["lang"] == lang], dtype=float)


def paired_ci(before: np.ndarray, after: np.ndarray, samples: int = BOOTSTRAP_SAMPLES, seed: int = 0
              ) -> tuple[float, float, float]:
    """Mean of (after - before) in percentage points with a 95% paired bootstrap interval."""
    diff = (np.asarray(after, dtype=float) - np.asarray(before, dtype=float)) * 100
    rng = np.random.default_rng(seed)
    means = diff[rng.integers(0, len(diff), (samples, len(diff)))].mean(axis=1)
    return float(diff.mean()), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def compare(original: str | Path, compressed: str | Path, items: Sequence[ScoredSequence], meta: Sequence[dict],
            device: str = "cuda", log: Log = print) -> dict:
    """Score both models on the same items; every number of the compressed model comes from its files."""
    before, after = score_model(original, items, device, log), score_model(compressed, items, device, log)
    sizes = {"original": disk_gb(original), "compressed": disk_gb(compressed)}
    report = {"size_gb": sizes, "compression": sizes["original"] / sizes["compressed"],
              "perplexity": {}, "accuracy": {}}
    for task, lang in sorted({(m["task"], m["lang"]) for m in meta}):
        if task in ("text", "belebele"):
            p0, p1 = perplexity(before, meta, task, lang), perplexity(after, meta, task, lang)
            report["perplexity"][f"{task} {lang}"] = {"original": p0, "compressed": p1, "growth": p1 / p0 - 1}
        if task in ("belebele", "kazmmlu"):
            a0, a1 = correct(before, meta, task, lang), correct(after, meta, task, lang)
            diff, lo, hi = paired_ci(a0, a1)
            report["accuracy"][f"{task} {lang}"] = {"n": len(a0), "original": a0.mean(), "compressed": a1.mean(),
                                                    "diff_pts": diff, "ci95_pts": [lo, hi]}
    return report


def format_report(report: dict) -> str:
    sizes = report["size_gb"]
    lines = [f"Original size:     {sizes['original']:.1f} GB",
             f"Compressed size:   {sizes['compressed']:.1f} GB",
             f"Compression:       {report['compression']:.1f}x"]
    for name, p in report["perplexity"].items():
        lines.append(f"Perplexity {name + ':':<16} {100 * p['growth']:+.1f}%  ({p['original']:.3f} -> {p['compressed']:.3f})")
    for name, a in report["accuracy"].items():
        lo, hi = a["ci95_pts"]
        lines.append(f"Accuracy {name + ':':<18} {a['diff_pts']:+.1f} pts [{lo:+.1f}, {hi:+.1f}]  "
                     f"({100 * a['original']:.1f}% -> {100 * a['compressed']:.1f}%, n={a['n']})")
    lines.append("Speed and runtime memory depend on your inference engine; measure them there.")
    return "\n".join(lines)
