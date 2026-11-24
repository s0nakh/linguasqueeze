# %% [markdown]
# # Translation test: English vs Kazakh+Russian calibration at the same size
# Qwen3-30B-A3B-Instruct-2507, `linguasqueeze compress --bits 4,3` (90% of calibration traffic at 4 bits), twice:
# calibration = 64 kk + 64 ru Wikipedia articles, or 128 English Wikipedia articles (seed 1, >= 500 chars).
# Each file translates the same 200 FLORES-200 devtest sentences English -> Kazakh (greedy, GPTQModel on 2x T4).
# Rule (fixed before the run): corpus chrF(kk+ru) - chrF(en) > 0 with the paired 95% bootstrap interval above 0.
# FL_DRY=1: the whole chain on a tiny random Qwen3-MoE (no meaning in the scores).

# %%
import glob, json, os, random, re, shutil, subprocess, sys, tarfile, time
from pathlib import Path
DRY = os.environ.get("FL_DRY", "0") == "1"
N_SENT, SEED, MAX_NEW, BATCH, BOOT = (8 if DRY else 200), 0, (16 if DRY else 160), 8, 1000
CAP_MIN = 60  # per file: quota guard; both files are then scored on the same completed sentences
pip = [sys.executable, "-m", "pip", "install", "-q"]
subprocess.check_call(pip + ["transformers==5.23.0", "sacrebleu==2.4.3"])  # pinned: supply-chain cooldown
subprocess.check_call(pip + ["--no-deps", "gptqmodel==7.6.0"])  # the version notebook 08 ran on Kaggle
subprocess.check_call(pip + ["device-smi>=0.5.7", "logbar>=0.4.14", "tokenicer>=0.0.14", "pypcre>=0.6.2",
                             "defuser>=0.0.28", "torchao>=0.18.0", "threadpoolctl>=3.6.0", "dill>=0.3.8"])
src = glob.glob("/kaggle/input/**/src_wip.tgz", recursive=True)  # package source at the tested commit (or: pip install git+https://github.com/s0nakh/linguasqueeze@v0.8.1)
tarfile.open(src[0]).extractall("/kaggle/working/pkg", filter="data")
subprocess.check_call(pip + ["--no-deps", "-e", "/kaggle/working/pkg"])
sys.path.insert(0, "/kaggle/working/pkg/src")
OUT = Path("/kaggle/working/results"); OUT.mkdir(parents=True, exist_ok=True)
WORK = Path("/kaggle/tmp"); WORK.mkdir(parents=True, exist_ok=True)
started = time.time()
log = lambda m: print(f"[{(time.time() - started) / 60:6.1f} min] {m}", flush=True)
print("free disk GB", shutil.disk_usage(WORK).free / 1e9)

# %%
import urllib.request
urllib.request.urlretrieve("https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz", WORK / "flores.tgz")
with tarfile.open(WORK / "flores.tgz") as t:
    t.extractall(WORK, filter="data")
root = next(WORK.glob("flores200_dataset"))
en_all = (root / "devtest" / "eng_Latn.devtest").read_text(encoding="utf-8").splitlines()
kk_all = (root / "devtest" / "kaz_Cyrl.devtest").read_text(encoding="utf-8").splitlines()
assert len(en_all) == len(kk_all) == 1012, (len(en_all), len(kk_all))
idx = sorted(random.Random(SEED).sample(range(len(en_all)), N_SENT))
src_en, ref_kk = [en_all[i] for i in idx], [kk_all[i] for i in idx]
log(f"{len(idx)} FLORES devtest sentences")

# %%
import datasets
def wiki(config, n, seed):
    out = []
    for row in datasets.load_dataset("wikimedia/wikipedia", config, split="train", streaming=True).shuffle(seed=seed, buffer_size=10_000):
        text = row["text"].strip()
        if len(text) >= 500:
            out.append(re.sub(r"\n\s*\n", "\n", text))
        if len(out) == n:
            return out
docs = 4 if DRY else 64
(WORK / "kkru.txt").write_text("\n\n".join(wiki("20231101.kk", docs, 1) + wiki("20231101.ru", docs, 1)), encoding="utf-8")
(WORK / "en.txt").write_text("\n\n".join(wiki("20231101.en", 2 * docs, 1)), encoding="utf-8")

# %%
if DRY:  # tiny random Qwen3-MoE with the real Qwen3 tokenizer
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, Qwen3MoeConfig
    tok_dir = Path(glob.glob("/kaggle/input/**/30b-a3b-instruct-2507/*/tokenizer.json", recursive=True)[0]).parent
    cfg = Qwen3MoeConfig(vocab_size=151936, hidden_size=128, intermediate_size=128, moe_intermediate_size=64,
                         num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2, head_dim=32,
                         num_experts=8, num_experts_per_tok=2, max_position_embeddings=2048, norm_topk_prob=True)
    torch.manual_seed(0)
    MODEL = WORK / "tiny"
    AutoModelForCausalLM.from_config(cfg, dtype=torch.bfloat16).save_pretrained(MODEL)
    AutoTokenizer.from_pretrained(tok_dir).save_pretrained(MODEL)
    MODEL = str(MODEL)
else:
    MODEL = str(Path(glob.glob("/kaggle/input/**/30b-a3b-instruct-2507/*/config.json", recursive=True)[0]).parent)

def compress(name):
    t = time.time()
    r = subprocess.run(["linguasqueeze", "compress", "--model", MODEL, "--calibration-data", str(WORK / f"{name}.txt"),
                        "--bits", "4,3", "--output", str(WORK / name)] + (["--group-size", "32"] if DRY else []),
                       capture_output=True, text=True)
    (OUT / f"compress_{name}.log").write_text(r.stdout + "\n" + r.stderr)
    print(r.stdout[-1500:], r.stderr[-1500:])
    if r.returncode:
        raise RuntimeError(f"compress {name} failed")
    return (time.time() - t) / 60

minutes = {n: compress(n) for n in ("kkru", "en")}
log(f"compressed {minutes}")

# %%
import gc, torch
from transformers import AutoTokenizer
from gptqmodel import BACKEND, GPTQModel
from linguasqueeze.export import convert_to_gptq_v2

PROMPT = "Translate the following English sentence into Kazakh. Reply with the Kazakh translation only.\n\n{}"

def translate(name):
    path = str(WORK / name)
    convert_to_gptq_v2(path)
    tok = AutoTokenizer.from_pretrained(path)
    tok.padding_side = "left"
    model = GPTQModel.load(path, device_map="auto", backend=BACKEND.TORCH, dtype=torch.float16)
    outs, t = [], time.time()
    for b in range(0, len(src_en), BATCH):
        prompts = [tok.apply_chat_template([{"role": "user", "content": PROMPT.format(s)}], tokenize=False,
                                           add_generation_prompt=True) for s in src_en[b:b + BATCH]]
        enc = tok(prompts, return_tensors="pt", padding=True).to("cuda:0")
        with torch.inference_mode():
            gen = model.model.generate(**enc, max_new_tokens=MAX_NEW, do_sample=False, pad_token_id=tok.pad_token_id)
        for row in gen[:, enc.input_ids.shape[1]:]:
            text = tok.decode(row, skip_special_tokens=True).strip()
            outs.append(text.split("\n")[0].strip())
        log(f"{name}: {len(outs)}/{len(src_en)}")
        if (time.time() - t) / 60 > CAP_MIN:
            log(f"{name}: time cap reached"); break
    secs = time.time() - t
    del model; gc.collect(); torch.cuda.empty_cache()
    return outs, secs

hyp = {}
for name in ("kkru", "en"):
    hyp[name], secs = translate(name)
    minutes[f"translate_{name}"] = secs / 60

# %%
import numpy as np
import pandas as pd
from sacrebleu.metrics import CHRF
chrf = CHRF()
def score(h, ids):
    return chrf.corpus_score([h[i] for i in ids], [[ref_kk[i] for i in ids]]).score
n_done = min(len(h) for h in hyp.values())
src_en, ref_kk = src_en[:n_done], ref_kk[:n_done]
hyp = {k: v[:n_done] for k, v in hyp.items()}
base = {n: score(hyp[n], range(len(ref_kk))) for n in hyp}
rng = np.random.default_rng(0)
diffs = []
for _ in range(BOOT):
    ids = rng.integers(0, len(ref_kk), len(ref_kk))
    diffs.append(score(hyp["kkru"], ids) - score(hyp["en"], ids))
lo, hi = np.percentile(diffs, [2.5, 97.5])
pd.DataFrame({"source_en": src_en, "reference_kk": ref_kk, "kkru": hyp["kkru"], "en": hyp["en"]}).to_csv(OUT / "translations.csv", index=False)
summary = {"dry": DRY, "sentences": len(ref_kk), "chrF": base, "diff_kkru_minus_en": base["kkru"] - base["en"],
           "ci95": [float(lo), float(hi)], "passed": bool(lo > 0), "minutes": minutes,
           "sizes_gb": {n: sum(p.stat().st_size for p in (WORK / n).rglob("*.safetensors")) / 1e9 for n in hyp}}
(OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
print(json.dumps(summary, indent=1, ensure_ascii=False))
