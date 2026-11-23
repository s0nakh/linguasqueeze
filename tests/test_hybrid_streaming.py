"""Streaming a hybrid MoE (Qwen3.5/3.6 MoE: linear + full attention, shared expert) layer by layer must give the
same scores as the whole model, also when the checkpoint stores the language model under model.language_model."""
import json

import numpy as np

import pytest
import torch

transformers = pytest.importorskip("transformers")
if not hasattr(transformers, "Qwen3_5MoeForCausalLM"):
    pytest.skip("transformers without Qwen3.5 MoE", allow_module_level=True)

from safetensors.torch import save_file

from linguasqueeze.gptq import make_quantization_prepare, router_traffic
from linguasqueeze.streaming import ScoredSequence, StreamedModel, stream_evaluate


def tiny_model(seed: int = 0):
    from transformers import Qwen3_5MoeForCausalLM, Qwen3_5MoeTextConfig

    torch.manual_seed(seed)
    config = Qwen3_5MoeTextConfig(
        vocab_size=128, hidden_size=64, num_hidden_layers=4, num_attention_heads=4, num_key_value_heads=2, head_dim=16,
        moe_intermediate_size=32, shared_expert_intermediate_size=32, num_experts=8, num_experts_per_tok=2,
        linear_num_value_heads=4, linear_num_key_heads=2, linear_key_head_dim=16, linear_value_head_dim=16,
        full_attention_interval=2, max_position_embeddings=256, pad_token_id=0)
    model = Qwen3_5MoeForCausalLM(config).eval()
    with torch.no_grad():
        for p in model.parameters():  # avoid exactly-zero init (norm weights, A_log, ...) hiding mistakes
            p.add_(0.02 * torch.randn_like(p))
    return model


def save(model, folder, prefix: str):
    state = {k.replace("model.", prefix, 1) if k.startswith("model.") else k: v.contiguous()
             for k, v in model.state_dict().items()}
    save_file(state, folder / "model.safetensors")
    folder.joinpath("config.json").write_text(json.dumps(model.config.to_dict()))


def sequences():
    g = torch.Generator().manual_seed(1)
    out = []
    for n in (7, 12, 5):
        ids = tuple(torch.randint(1, 128, (n,), generator=g).tolist())
        out.append(ScoredSequence(ids, (1, n), (3, 4, 5)))
    return out


def reference(model, seqs):
    scores = []
    for s in seqs:
        with torch.no_grad():
            logits = model(torch.tensor([s.ids])).logits[0].float()
        start, end = s.span
        lp = torch.log_softmax(logits[start - 1:end - 1], -1).gather(1, torch.tensor(s.ids[start:end])[:, None]).sum()
        scores.append((lp.item(), logits[len(s.ids) - 1][list(s.choice_ids)].tolist()))
    return scores


@pytest.mark.parametrize("prefix", ["model.", "model.language_model."])
def test_streamed_hybrid_moe_matches_whole_model(tmp_path, prefix):
    model = tiny_model()
    save(model, tmp_path, prefix)
    streamed = StreamedModel(tmp_path, device="cpu", dtype=torch.float32)
    assert streamed.prefix == prefix and streamed.hybrid
    seqs = sequences()
    got = stream_evaluate(streamed, seqs, ["x"], log=lambda m: None)["x"]
    for g, (lp, choice) in zip(got, reference(model, seqs)):
        assert g.span_logprob == pytest.approx(lp, abs=1e-4)
        assert g.choice_logits == pytest.approx(choice, abs=1e-4)


def test_router_traffic_runs_on_hybrid_layers(tmp_path):
    model = tiny_model(seed=2)
    save(model, tmp_path, "model.language_model.")
    streamed = StreamedModel(tmp_path, device="cpu", dtype=torch.float32)
    seqs = sequences()
    counts = []

    def prepare(config, index, layer, inputs):
        counts.append(router_traffic(layer, inputs, lambda h, m: streamed.run_layer(index, h, m)))

    stream_evaluate(streamed, seqs, ["x"], prepare=prepare, log=lambda m: None, calibration={"x": seqs})
    assert len(counts) == 4 and all(c.sum() == sum(len(s.ids) for s in seqs) * 2 for c in counts)


def test_gptq_plan_runs_on_hybrid_layers_and_changes_only_its_config(tmp_path):
    model = tiny_model(seed=3)
    save(model, tmp_path, "model.language_model.")
    streamed = StreamedModel(tmp_path, device="cpu", dtype=torch.float32)
    seqs = sequences()
    bits = np.full((4, 8), 4)
    prepare, stats = make_quantization_prepare(streamed, {"q4": {"method": "gptq", "bits": bits}}, group_size=16,
                                               attention_bits=8, min_tokens=1, log=lambda m: None)
    got = stream_evaluate(streamed, seqs, ["original", "q4"], prepare=prepare, log=lambda m: None,
                          calibration={"q4": seqs})
    for g, (lp, choice) in zip(got["original"], reference(model, seqs)):
        assert g.span_logprob == pytest.approx(lp, abs=1e-4)        # untouched config stays exact
    assert len(stats["q4"]) == 4                                    # every layer, linear and full attention
    assert any(abs(a.span_logprob - b.span_logprob) > 1e-6 for a, b in zip(got["original"], got["q4"]))
