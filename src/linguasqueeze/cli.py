"""Command line: `linguasqueeze compress` and `linguasqueeze evaluate`.

    linguasqueeze compress --model ./Qwen3-30B-A3B --calibration-data kk.txt ru.txt --bits 4,3 --output ./small
    linguasqueeze evaluate --original ./Qwen3-30B-A3B --compressed ./small --text kk=kk_test.txt --exam
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _bits(value: str) -> list[int]:
    try:
        return [int(v) for v in value.split(",") if v.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"--bits expects numbers like 4 or 4,3, got {value!r}") from None


def _text(value: str) -> tuple[str, str]:
    lang, sep, path = value.partition("=")
    if not sep or not lang or not path:
        raise argparse.ArgumentTypeError(f"--text expects LANG=FILE, e.g. kk=kazakh.txt, got {value!r}")
    return lang, path


def _default_device() -> str:
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="linguasqueeze",
                                     description="Compress for your language, not just for your hardware.")
    sub = parser.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compress", help="write a GPTQ checkpoint calibrated on your language")
    c.add_argument("--model", required=True, help="folder of a Hugging Face MoE checkpoint (safetensors)")
    c.add_argument("--calibration-data", nargs="+", required=True,
                   help="UTF-8 text files in your language(s); documents separated by an empty line")
    c.add_argument("--output", required=True, help="folder for the compressed checkpoint")
    c.add_argument("--bits", type=_bits, default=[4], help="one width (4) or two (4,3); default 4")
    c.add_argument("--keep", type=float, default=0.9,
                   help="with two widths: share of your language's expert traffic kept at the higher width")
    c.add_argument("--group-size", type=int, default=128)
    c.add_argument("--attention-bits", type=int, default=8)
    c.add_argument("--device", default=None, help="cuda, cuda:0 or cpu (default: cuda if available)")
    c.add_argument("--layer-limit", type=int, default=None, help="dry run: only the first N layers")

    e = sub.add_parser("evaluate", help="compare a compressed model with the original on your language")
    e.add_argument("--original", required=True)
    e.add_argument("--compressed", required=True)
    e.add_argument("--text", type=_text, action="append", default=[], metavar="LANG=FILE",
                   help="perplexity on your own text; repeat per language")
    e.add_argument("--exam", action="store_true",
                   help="also run the fixed Belebele (kk, ru, en) + KazMMLU (kk, ru) exam")
    e.add_argument("--report", default=None, help="write the full report as JSON to this file")
    e.add_argument("--device", default=None)
    return parser


def _check_paths(parser: argparse.ArgumentParser, paths) -> None:
    missing = [str(p) for p in paths if not Path(p).exists()]
    if missing:
        parser.error(f"not found: {', '.join(missing)}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    from linguasqueeze import pipeline

    device = args.device or _default_device()
    try:
        if args.command == "compress":
            _check_paths(parser, [args.model, *args.calibration_data])
            summary = pipeline.compress(args.model, args.calibration_data, args.output, widths=args.bits,
                                        keep=args.keep, group_size=args.group_size,
                                        attention_bits=args.attention_bits, device=device,
                                        layer_limit=args.layer_limit)
            print(f"Written {args.output} ({pipeline.disk_gb(args.output):.1f} GB); "
                  f"{summary['rtn_fallback_experts']} experts saw too few tokens and were rounded instead of GPTQ."
                  + (" DRY RUN: incomplete model." if summary["dry_run"] else ""))
            return 0
        from transformers import AutoTokenizer
        _check_paths(parser, [args.original, args.compressed, *(p for _, p in args.text)])
        tokenizer = AutoTokenizer.from_pretrained(args.original)
        items, meta = pipeline.build_items(tokenizer, dict(args.text), exam=args.exam)
        report = pipeline.compare(args.original, args.compressed, items, meta, device=device)
        print(pipeline.format_report(report))
        if args.report:
            Path(args.report).write_text(json.dumps(report, indent=2))
        return 0
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
