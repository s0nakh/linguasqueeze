"""Hy-MT3 (transformers `hy_v3`): a first dense layer, a sigmoid router with a correction bias, shared experts and
checkpoint names that differ from the module names (router.gate, expert_bias, shared_mlp, one tensor per expert)."""

from __future__ import annotations

import json

import numpy as np
import pytest
import torch

transformers = pytest.importorskip("transformers")
if int(transformers.__version__.split(".")[0]) < 5 or not hasattr(transformers, "HYV3Config"):
    pytest.skip("needs transformers 5.x with hy_v3", allow_module_level=True)

from safetensors.torch import load_file, save_file  # noqa: E402
from transformers import AutoModelForCausalLM, HYV3Config  # noqa: E402

from linguasqueeze import pipeline  # noqa: E402
from linguasqueeze.streaming import ScoredSequence, StreamedModel, stream_evaluate  # noqa: E402



class ByteTokenizer:  # same stand-in as in test_cli.py: one token per character, ids in [1, 127]
    class _Out:
        def __init__(self, ids):
            self.input_ids = ids

    def __call__(self, text, truncation=True, max_length=None, add_special_tokens=True):
        ids = [ord(ch) % 127 + 1 for ch in text]
        return self._Out(ids[:max_length] if max_length else ids)


def _write_docs(path, seed, count=4, chars=240):
    rng = np.random.default_rng(seed)
    path.write_text("\n\n".join("".join(chr(c) for c in rng.integers(97, 123, chars)) for _ in range(count)), encoding="utf-8")
    return path


def reference_scores(model, seq: ScoredSequence):  # same reference as in test_streaming.py
    with torch.no_grad():
        logits = model(torch.tensor([seq.ids])).logits[0].float()
    start, end = seq.span
    logprob = torch.log_softmax(logits[start - 1:end - 1], -1).gather(1, torch.tensor(seq.ids[start:end])[:, None]).sum()
    return logprob.item(), logits[-1, list(seq.choice_ids)].tolist()

TO_CHECKPOINT = (("mlp.gate.weight", "mlp.router.gate.weight"), ("mlp.e_score_correction_bias", "mlp.expert_bias"),
                 ("mlp.shared_experts.", "mlp.shared_mlp."))


def _tiny_hy(tmp_path):
    """A tiny random Hy-MT3 saved with the tensor names of the published checkpoint."""
    config = HYV3Config(vocab_size=128, hidden_size=64, intermediate_size=64, moe_intermediate_size=32,
                        num_hidden_layers=3, num_attention_heads=4, num_key_value_heads=2, head_dim=16,
                        num_experts=8, num_experts_per_tok=2, num_shared_experts=1, max_position_embeddings=64,
                        pad_token_id=0)
    assert config.mlp_layer_types[0] == "dense" and config.mlp_layer_types[1] == "sparse"
    torch.manual_seed(0)
    model = AutoModelForCausalLM.from_config(config, dtype=torch.float32).eval()
    with torch.no_grad():  # a non-zero correction bias, so a router that ignores it routes differently
        for layer in model.model.layers[1:]:
            layer.mlp.e_score_correction_bias.copy_(torch.linspace(-0.3, 0.3, 8))
    out = tmp_path / "hy"
    model.save_pretrained(out)
    tensors = {}
    for key, value in load_file(out / "model.safetensors").items():
        for module_part, checkpoint_part in TO_CHECKPOINT:
            key = key.replace(module_part, checkpoint_part)
        if key.endswith("mlp.experts.gate_up_proj"):
            base, half = key[: -len("gate_up_proj")], value.shape[1] // 2
            for e in range(value.shape[0]):
                tensors[f"{base}{e}.gate_proj.weight"] = value[e, :half].contiguous()
                tensors[f"{base}{e}.up_proj.weight"] = value[e, half:].contiguous()
        elif key.endswith("mlp.experts.down_proj"):
            base = key[: -len("down_proj")]
            for e in range(value.shape[0]):
                tensors[f"{base}{e}.down_proj.weight"] = value[e].contiguous()
        else:
            tensors[key] = value.contiguous()
    assert "model.layers.1.mlp.router.gate.weight" in tensors and "model.layers.1.mlp.expert_bias" in tensors
    assert "model.layers.1.mlp.experts.3.up_proj.weight" in tensors and "model.layers.1.mlp.shared_mlp.up_proj.weight" in tensors
    save_file(tensors, out / "model.safetensors", metadata={"format": "pt"})
    return model, out


def test_checkpoint_names_load_back_into_transformers(tmp_path):
    model, path = _tiny_hy(tmp_path)
    loaded = AutoModelForCausalLM.from_pretrained(path, dtype=torch.float32).eval()
    ids = torch.tensor([[5, 9, 17, 33, 2, 64, 7]])
    with torch.no_grad():
        assert torch.allclose(loaded(ids).logits, model(ids).logits, atol=1e-5)


def test_streamed_scores_match_normal_forward(tmp_path):
    model, path = _tiny_hy(tmp_path)
    gen = torch.Generator().manual_seed(1)
    sequences = [ScoredSequence(ids=tuple(torch.randint(1, 128, (n,), generator=gen).tolist()), span=(2, n),
                                choice_ids=(5, 6, 7)) for n in (7, 12, 20, 9)]
    streamed = StreamedModel(path, device="cpu", dtype=torch.float32)
    assert torch.allclose(streamed.read_layer_state(1)["mlp.e_score_correction_bias"], torch.linspace(-0.3, 0.3, 8))
    results = stream_evaluate(streamed, sequences, configs=["original"], max_tokens=40, log=lambda _: None)
    for seq, got in zip(sequences, results["original"]):
        want_logprob, want_choices = reference_scores(model, seq)
        assert got.span_logprob == pytest.approx(want_logprob, abs=1e-4)
        assert got.choice_logits == pytest.approx(want_choices, abs=1e-4)


def test_compress_then_evaluate_end_to_end(tmp_path):
    _, source = _tiny_hy(tmp_path)
    tok = ByteTokenizer()
    calib = _write_docs(tmp_path / "kk.txt", seed=1, count=6)
    summary = pipeline.compress(source, [calib], tmp_path / "small", widths=[4, 3], keep=0.5, group_size=32,
                                device="cpu", tokenizer=tok, log=lambda _: None)
    assert summary["expert_bits_per_layer"][0] == []  # the dense first layer has no experts
    used = {b for layer in summary["expert_bits_per_layer"][1:] for b in layer}
    assert used == {3, 4}
    written = json.loads((tmp_path / "small" / "model.safetensors.index.json").read_text())["weight_map"]
    assert "model.layers.1.mlp.e_score_correction_bias" in written  # the router bias is kept, unquantized
    assert "model.layers.1.mlp.experts.0.gate_proj.qweight" in written
    assert "model.layers.0.mlp.gate_proj.weight" in written  # dense MLP copied unchanged
    reloaded = StreamedModel(tmp_path / "small", device="cpu", dtype=torch.float32)
    assert torch.allclose(reloaded.read_layer_state(1)["mlp.e_score_correction_bias"], torch.linspace(-0.3, 0.3, 8))

    items, meta = pipeline.build_items(tok, {"kk": _write_docs(tmp_path / "kk_test.txt", seed=2)})
    report = pipeline.compare(source, tmp_path / "small", items, meta, device="cpu", log=lambda _: None)
    ppl = report["perplexity"]["text kk"]
    assert np.isfinite(ppl["original"]) and np.isfinite(ppl["compressed"]) and ppl["compressed"] > 0


def test_route_picks_the_same_experts_as_the_model_with_its_bias(tmp_path):
    from linguasqueeze.gptq import route, router_traffic

    model, _ = _tiny_hy(tmp_path)
    mlp = model.model.layers[1].mlp
    seen = {}
    handle = mlp.gate.register_forward_hook(lambda _m, _a, out: seen.update(chosen=out[2]))
    x = torch.randn(1, 10, 64, generator=torch.Generator().manual_seed(3))
    with torch.no_grad():
        mlp(x)
        handle.remove()  # keep only the model's own routing call
        ours = route(mlp, x.reshape(-1, 64))[2]
        unbiased = mlp.gate(x.reshape(-1, 64), torch.zeros(8))[2]
    assert torch.equal(ours.sort(-1).values, seen["chosen"].sort(-1).values)
    assert not torch.equal(unbiased.sort(-1).values, ours.sort(-1).values)  # the bias really changes the choice

    layer = model.model.layers[1]
    traffic = router_traffic(layer, lambda: iter([(x, torch.ones(1, 10))]), lambda h, m: layer.mlp(h))
    assert traffic.sum() == 10 * 2  # top-2 of 10 tokens
    assert router_traffic(model.model.layers[0], lambda: iter([]), None).size == 0  # dense first layer


def test_rtn_plan_skips_the_dense_layer(tmp_path):
    from linguasqueeze.gptq import make_quantization_prepare

    _, path = _tiny_hy(tmp_path)
    streamed = StreamedModel(path, device="cpu", dtype=torch.float32)
    seq = [ScoredSequence(ids=tuple(range(1, 30)), span=(2, 29), choice_ids=(5,))]
    prepare, _ = make_quantization_prepare(streamed, {"rtn": {"method": "rtn", "bits": np.full((3, 8), 3)}},
                                           group_size=32, log=lambda _: None)
    results = stream_evaluate(streamed, seq, configs=["original", "rtn"], prepare=prepare, log=lambda _: None)
    assert np.isfinite(results["rtn"][0].span_logprob)
    assert results["rtn"][0].span_logprob != results["original"][0].span_logprob
