# %% [markdown]
# # The two README commands on the real Qwen3-30B-A3B (Kaggle, one T4)
# Runs `linguasqueeze compress` and `linguasqueeze evaluate` exactly as the README shows, with the calibration of
# notebook 07 (64 + 64 kk/ru Wikipedia articles, seed 1, >= 500 chars, 512 tokens), bits 4,3 @ 90%.
# Pass: compressed size ~15.2 GB and evaluate numbers close to notebook 07 (kk +1.3%, ru +0.4% Belebele perplexity).
# Articles are written with blank lines collapsed (the CLI splits documents on blank lines), so tokens differ slightly.

# %%
import glob, json, os, re, subprocess, sys, tarfile, time
from pathlib import Path
pip = [sys.executable, "-m", "pip", "install", "-q"]
subprocess.check_call(pip + ["transformers==5.23.0"])  # pinned: supply-chain cooldown
src = glob.glob("/kaggle/input/**/src_wip.tgz", recursive=True)  # the package source at the commit under test (or: pip install git+https://github.com/s0nakh/linguasqueeze@v0.8.0)
tarfile.open(src[0]).extractall("/kaggle/working/pkg", filter="data")
subprocess.check_call(pip + ["--no-deps", "-e", "/kaggle/working/pkg"])
OUT = Path("/kaggle/working/results"); OUT.mkdir(parents=True, exist_ok=True)
WORK = Path("/kaggle/tmp"); WORK.mkdir(parents=True, exist_ok=True)
MODEL = str(Path(glob.glob("/kaggle/input/**/30b-a3b-instruct-2507/*/config.json", recursive=True)[0]).parent)
print("model", MODEL)

# %%
import datasets

def wiki(config, n, seed, skip=0):
    stream = datasets.load_dataset("wikimedia/wikipedia", config, split="train", streaming=True)
    out = []
    for row in stream.shuffle(seed=seed, buffer_size=10_000):
        text = row["text"].strip()
        if len(text) < 500:
            continue
        out.append(re.sub(r"\n\s*\n", "\n", text))
        if len(out) == n + skip:
            return out[skip:]

for lang in ("kk", "ru"):
    (WORK / f"{lang}.txt").write_text("\n\n".join(wiki(f"20231101.{lang}", 64, 1)), encoding="utf-8")
    (WORK / f"{lang}_test.txt").write_text("\n\n".join(wiki(f"20231101.{lang}", 20, 7)), encoding="utf-8")

# %%
def run(cmd):
    t = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(r.stdout[-4000:]); print(r.stderr[-4000:])
    (OUT / f"{cmd[1]}.log").write_text(r.stdout + "\n" + r.stderr)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[1]} failed with code {r.returncode}")
    return (time.time() - t) / 60

m_compress = run(["linguasqueeze", "compress", "--model", MODEL, "--calibration-data", str(WORK / "kk.txt"), str(WORK / "ru.txt"),
                  "--bits", "4,3", "--output", str(WORK / "small")])
m_eval = run(["linguasqueeze", "evaluate", "--original", MODEL, "--compressed", str(WORK / "small"),
              "--text", f"kk={WORK / 'kk_test.txt'}", "--text", f"ru={WORK / 'ru_test.txt'}", "--exam",
              "--report", str(OUT / "report.json")])
meta = json.loads((WORK / "small" / "linguasqueeze.json").read_text())
summary = {"minutes_compress": m_compress, "minutes_evaluate": m_eval, "rtn_fallback_experts": meta["rtn_fallback_experts"],
           "calibration_documents": meta["calibration_documents"], "calibration_tokens": meta["calibration_tokens"],
           "report": json.loads((OUT / "report.json").read_text())}
(OUT / "summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
