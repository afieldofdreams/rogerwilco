# Speed test

One PAY chain per arm (F and C), K = 2, block 1, clean context 1, on each local model, trial suffix `-s`. Four threads, llama_cpp in-process, temperature 0, context 12288.
Seconds are wall seconds of the model call. A chain that ended at hop 1 (the model asked) measures one session; the per-chain figure for a chain that goes the distance is projected from the model's token rates.

| model | calls fitted | prompt tok/s | gen tok/s | measured sessions (s) | measured chain F (s, hops reached) | measured chain C (s, hops reached) | projected chain F (s) | projected chain C (s) | projected chain, design mix (s) | chains in 8 h (F / C / mix) |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen15 | 2 | 253 | 10.2 | 11, 68 | 11, 1 | 68, 1 | 93 | 93 | 93 | 309 / 309 / 309 |
| qwen3b | 4 | 78 | 8.8 | 20, 83 | 20, 1 | 83, 1 | 175 | 241 | 214 | 165 / 119 / 134 |
| llama3b | 5 | 69 | 11.5 | 48, 51, 58, 78 | 156, 3 | 78, 1 | 171 | 259 | 224 | 168 / 111 / 128 |
| qwen7b | 8 | 37 | 4.5 | 98, 120, 134, 166, 188 | 351, 3 | 354, 2 | 357 | 501 | 443 | 80 / 57 / 64 |

Projection: the token budget of a chain that goes the distance, per arm, in sessions of (prompt tokens, completion tokens): {"F": {"prompt": [2146, 2557, 3383], "completion": [295, 148, 179]}, "C": {"prompt": [4833, 5007, 6190], "completion": [106, 95, 102]}}. The later turns of a session re-use llama_cpp's cached prefix, so only their new tokens are counted. A chain of the other arms (A, L, R) sits between F and C; the design's mix over the five arms is about 0.4 F-weight and 0.6 C-weight.

Every call:

| model | chain | hop | turn | prompt tokens | completion tokens | seconds |
|---|---|---|---|---|---|---|
| llama3b | B1-PAY-clean-1-C-llama3b-k2-r1-s | 1 | 1 | 4519 | 47 | 70.22 |
| llama3b | B1-PAY-clean-1-C-llama3b-k2-r1-s | 1 | 2 | 4640 | 32 | 7.44 |
| qwen15 | B1-PAY-clean-1-C-qwen15-k2-r1-s | 1 | 1 | 4749 | 500 | 67.82 |
| qwen3b | B1-PAY-clean-1-C-qwen3b-k2-r1-s | 1 | 1 | 4749 | 2 | 65.7 |
| qwen3b | B1-PAY-clean-1-C-qwen3b-k2-r1-s | 1 | 2 | 4833 | 99 | 13.98 |
| qwen3b | B1-PAY-clean-1-C-qwen3b-k2-r1-s | 1 | 3 | 5080 | 1 | 2.89 |
| qwen7b | B1-PAY-clean-1-C-qwen7b-k2-r1-s | 1 | 1 | 4749 | 2 | 131.58 |
| qwen7b | B1-PAY-clean-1-C-qwen7b-k2-r1-s | 1 | 2 | 4833 | 104 | 34.58 |
| qwen7b | B1-PAY-clean-1-C-qwen7b-k2-r1-s | 2 | 1 | 4924 | 2 | 132.74 |
| qwen7b | B1-PAY-clean-1-C-qwen7b-k2-r1-s | 2 | 2 | 5007 | 93 | 27.31 |
| qwen7b | B1-PAY-clean-1-C-qwen7b-k2-r1-s | 2 | 3 | 5229 | 88 | 27.68 |
| llama3b | B1-PAY-clean-1-F-llama3b-k2-r1-s | 1 | 1 | 1998 | 246 | 47.63 |
| llama3b | B1-PAY-clean-1-F-llama3b-k2-r1-s | 2 | 1 | 2318 | 246 | 57.57 |
| llama3b | B1-PAY-clean-1-F-llama3b-k2-r1-s | 3 | 1 | 3177 | 69 | 50.95 |
| qwen15 | B1-PAY-clean-1-F-qwen15-k2-r1-s | 1 | 1 | 2146 | 24 | 10.84 |
| qwen3b | B1-PAY-clean-1-F-qwen3b-k2-r1-s | 1 | 1 | 2146 | 18 | 19.96 |
| qwen7b | B1-PAY-clean-1-F-qwen7b-k2-r1-s | 1 | 1 | 2146 | 295 | 119.49 |
| qwen7b | B1-PAY-clean-1-F-qwen7b-k2-r1-s | 2 | 1 | 2557 | 148 | 97.55 |
| qwen7b | B1-PAY-clean-1-F-qwen7b-k2-r1-s | 3 | 1 | 3383 | 179 | 134.01 |
