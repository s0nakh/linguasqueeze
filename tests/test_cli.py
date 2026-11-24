"""The `linguasqueeze compress` / `evaluate` workflow, end to end on a tiny real Qwen3-MoE."""

from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from linguasqueeze import pipeline
from linguasqueeze.cli import build_parser


class ByteTokenizer:
    """Stand-in tokenizer: one token per character, ids in [1, 127]."""

    class _Out:
        def __init__(self, ids):
            self.input_ids = ids

    def __call__(self, text, truncation=True, max_length=None, add_special_tokens=True):
        ids = [ord(ch) % 127 + 1 for ch in text]
        return self._Out(ids[:max_length] if max_length else ids)


def _write_docs(path, seed, count=4, chars=240):
    rng = np.random.default_rng(seed)
    docs = ["".join(chr(c) for c in rng.integers(97, 123, chars)) for _ in range(count)]
    path.write_text("\n\n".join(docs), encoding="utf-8")
    return path


def _tiny_qwen3(tmp_path):
    transformers = pytest.importorskip("transformers")
    if int(transformers.__version__.split(".")[0]) < 5:
        pytest.skip("needs transformers 5.x")
    from transformers import AutoModelForCausalLM, Qwen3MoeConfig

    config = Qwen3MoeConfig(vocab_size=128, hidden_size=64, intermediate_size=64, moe_intermediate_size=32,
                            num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2, head_dim=16,
                            num_experts=8, num_experts_per_tok=2, max_position_embeddings=2048, pad_token_id=0,
                            norm_topk_prob=True, decoder_sparse_step=1)
    torch.manual_seed(0)
    AutoModelForCausalLM.from_config(config, dtype=torch.bfloat16).eval().save_pretrained(tmp_path / "original")
    return tmp_path / "original"


def test_read_documents_splits_on_empty_lines_and_drops_short_ones(tmp_path):
    f = tmp_path / "kk.txt"
    f.write_text("a" * 250 + "\n\n   \nshort\n\n" + "b" * 300, encoding="utf-8")
    assert [len(d) for d in pipeline.read_documents(f)] == [250, 300]


def test_read_documents_refuses_a_file_without_usable_text(tmp_path):
    f = tmp_path / "empty.txt"
    f.write_text("too short", encoding="utf-8")
    with pytest.raises(ValueError, match="no document"):
        pipeline.read_documents(f)


def test_one_width_gives_every_expert_that_width():
    assert (pipeline.bit_plan([4], 0.9, 3, 5) == 4).all()


@pytest.mark.parametrize("widths,keep", [([5], 0.9), ([4, 3, 2], 0.9), ([4, 3], 1.0), ([4, 3], 0.0)])
def test_invalid_bit_plans_are_refused(widths, keep):
    with pytest.raises(ValueError):
        pipeline.bit_plan(widths, keep, 2, 4)


def test_paired_interval_is_zero_for_identical_answers_and_signed_for_a_loss():
    a = np.array([1, 0, 1, 1, 0, 1, 0, 1], dtype=float)
    assert pipeline.paired_ci(a, a) == (0.0, 0.0, 0.0)
    worse = a.copy()
    worse[[0, 2]] = 0
    diff, lo, hi = pipeline.paired_ci(a, worse)
    assert diff == pytest.approx(-25.0) and lo <= diff <= hi <= 0


def test_parser_reads_bits_and_language_texts():
    args = build_parser().parse_args(["compress", "--model", "m", "--calibration-data", "kk.txt", "ru.txt",
                                      "--output", "o", "--bits", "4,3"])
    assert args.bits == [4, 3] and args.calibration_data == ["kk.txt", "ru.txt"]
    args = build_parser().parse_args(["evaluate", "--original", "a", "--compressed", "b", "--text", "kk=x.txt"])
    assert args.text == [("kk", "x.txt")] and not args.exam


def test_version_flag_prints_the_package_version(capsys):
    from linguasqueeze import __version__

    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"linguasqueeze {__version__}"


def test_parser_rejects_malformed_values():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["evaluate", "--original", "a", "--compressed", "b", "--text", "kk"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["compress", "--model", "m", "--calibration-data", "x", "--output", "o",
                                   "--bits", "four"])


def test_compress_then_evaluate_end_to_end(tmp_path):
    source = _tiny_qwen3(tmp_path)
    tok = ByteTokenizer()
    calib = _write_docs(tmp_path / "kk.txt", seed=1, count=6)
    summary = pipeline.compress(source, [calib], tmp_path / "small", widths=[4, 3], keep=0.5, group_size=32,
                                device="cpu", tokenizer=tok, log=lambda _: None)

    written = json.loads((tmp_path / "small" / "linguasqueeze.json").read_text())
    assert written == json.loads(json.dumps(summary)) and not summary["dry_run"]
    assert summary["calibration_documents"] == 6 and summary["bits"] == [4, 3]
    used = {b for layer in summary["expert_bits_per_layer"] for b in layer}
    assert used <= {3, 4} and 3 in used and 4 in used
    assert json.loads((tmp_path / "small" / "config.json").read_text())["quantization_config"]["bits"] == 4

    items, meta = pipeline.build_items(tok, {"kk": _write_docs(tmp_path / "kk_test.txt", seed=2)})
    report = pipeline.compare(source, tmp_path / "small", items, meta, device="cpu", log=lambda _: None)
    ppl = report["perplexity"]["text kk"]
    assert np.isfinite(ppl["original"]) and np.isfinite(ppl["compressed"]) and ppl["compressed"] > 0
    assert report["size_gb"]["original"] > 0 and report["size_gb"]["compressed"] > 0
    assert "Perplexity text kk:" in pipeline.format_report(report)


def test_dense_models_are_refused_with_a_clear_message(tmp_path):
    transformers = pytest.importorskip("transformers")
    if int(transformers.__version__.split(".")[0]) < 5:
        pytest.skip("needs transformers 5.x")
    from transformers import AutoModelForCausalLM, Qwen3Config

    config = Qwen3Config(vocab_size=128, hidden_size=64, intermediate_size=64, num_hidden_layers=1,
                         num_attention_heads=4, num_key_value_heads=2, head_dim=16, pad_token_id=0)
    AutoModelForCausalLM.from_config(config).save_pretrained(tmp_path / "dense")
    calib = _write_docs(tmp_path / "kk.txt", seed=1)
    with pytest.raises(ValueError, match="Mixture-of-Experts"):
        pipeline.compress(tmp_path / "dense", [calib], tmp_path / "out", device="cpu", tokenizer=ByteTokenizer(),
                          log=lambda _: None)
