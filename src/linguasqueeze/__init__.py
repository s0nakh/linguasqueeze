"""LinguaSqueeze: compress for your language, not just for your hardware."""

from linguasqueeze.pruning import (
    MoEBlock,
    PruneReport,
    build_mask,
    count_parameters,
    find_moe_blocks,
    language_frequency_score,
    masked_experts,
    masked_routing,
    prune_experts,
    row_share,
    top_experts,
)
from linguasqueeze.quant import (
    allocate_bits_by_coverage,
    allocate_like,
    expert_memory_bytes,
    fake_quantize,
    quantize_experts_,
    restore_experts,
    snapshot_experts,
)

__version__ = "0.8.2"

__all__ = [
    "allocate_bits_by_coverage",
    "allocate_like",
    "expert_memory_bytes",
    "fake_quantize",
    "quantize_experts_",
    "restore_experts",
    "snapshot_experts",
    "MoEBlock",
    "PruneReport",
    "build_mask",
    "count_parameters",
    "find_moe_blocks",
    "language_frequency_score",
    "masked_experts",
    "masked_routing",
    "prune_experts",
    "row_share",
    "top_experts",
]
