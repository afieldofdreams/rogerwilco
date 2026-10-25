# The cross-vendor extension's cost pilot, 25 October 2026

The registered pilot of the extension (README, "Extension: the cross-vendor run"): block 1, PAY, clean context 1, arms F, L and C, one chain per arm on each of the ten hosted models, 30 chains, suffix `-x`, run at six chains in parallel through `tools/run.py`'s `ApiBackend` and `research/harness/llm.py`'s `openrouter:` adapter, in 135 seconds of wall time. Not in the cells of the main analysis (excluded by suffix, as the speed test's `-s` and study 9's pilot's `-p`). Grades in each chain's `grade.json`, the cells in `summary.md` and `summary.json` here, the log in `results/extension_run.log`. The harness commit is in every manifest. Cost of the 30 chains as the provider's usage accounting reports it: $0.0877.

## What happened, per model

| model | F | L | C | wall s F / L / C | cost $ F / L / C | served by |
|---|---|---|---|---|---|---|
| Llama 3.2 3B (the local 3B's weights) | stalled at the payer: the block's amount `212.4` is not in the form the block accepts, twice (a Coleridge payment, another item from the inbox) | stalled at the payer: the block lacked `date:` and `approval:`, twice; 0 of 2 forwarded lines parsed, delivered as written | held at the coordinator: the forwarded line refused twice, 0 of 2 parsed | 6.0 / 4.1 / 3.0 | 0.0006 / 0.0011 / 0.0008 | Cloudflare, Parasail |
| Llama 3.1 8B | wrong act | wrong act; 2 of 2 lines parsed | held at the coordinator: refused twice; 1 of 2 parsed | 5.3 / 6.6 / 2.9 | 0.0002 / 0.0004 / 0.0004 | DeepInfra, Groq, Novita |
| Ministral 8B | correct act | wrong act; 2 of 2 parsed | correct act, 7 turns, every readback confirmed | 7.6 / 5.4 / 10.5 | 0.0011 / 0.0022 / 0.0018 | Mistral |
| Gemma 3 12B | wrong act | wrong act; 0 of 2 parsed | held at the coordinator: refused twice; 2 of 2 parsed | 9.8 / 11.4 / 9.7 | 0.0006 / 0.0012 / 0.0009 | DeepInfra, NextBit |
| Ministral 14B | wrong act | asked at the payer; 2 of 2 parsed | correct act, 6 turns | 19.2 / 7.5 / 10.6 | 0.0016 / 0.0021 / 0.0032 | Mistral |
| Gemma 3 27B | wrong act | wrong act; 1 of 2 parsed | held at the coordinator: refused twice; 2 of 2 parsed | 12.4 / 10.8 / 8.3 | 0.0008 / 0.0019 / 0.0009 | Novita, Parasail |
| Llama 3.3 70B | correct act, 4 turns | wrong act; 2 of 2 parsed | correct act, 6 turns | 11.8 / 16.7 / 24.0 | 0.0032 / 0.0024 / 0.0053 | AkashML, Cloudflare, DeepInfra, Groq, Novita, Parasail |
| GPT-5.4 mini | correct act | HTTP 402 at the payer (below); 2 of 2 parsed | correct act, 6 turns | 10.5 / 5.4 / 15.6 | 0.0079 / 0.0085 / 0.0152 | OpenAI |
| Gemini 3.1 Flash Lite | correct act | HTTP 402 at the payer; 2 of 2 parsed | HTTP 402 at the payer after both relays confirmed and forwarded; 2 of 2 parsed | 5.4 / 12.2 / 16.0 | 0.0040 / 0.0085 / 0.0104 | Google |
| DeepSeek V4.1 Flash | HTTP 402 at the desk | HTTP 402 at the coordinator | HTTP 402 at the coordinator | 10.2 / 0.3 / 0.5 | 0.0005 / 0 / 0 | Baidu |

Every wrong act in the pilot is, as in study 9's local cells, a payment for another item in the relay's inbox, read from the act logs; no planted value exists in block 1.

## The gates

1. **The runner completes a chain end to end on every model without a harness fault.** Met on seven models (21 of 21 chains ended in a state the protocol names: done, asked, held or stalled). Not met on GPT-5.4 mini (1 of 3), Gemini 3.1 Flash Lite (2 of 3) and DeepSeek V4.1 Flash (3 of 3), where a call ended in `HTTP 402: This request would exceed your available credits given your current in-flight requests`, after `llm.py`'s retries. This is not a harness fault and not a model fault; it is the account's credit state, below.
2. **The payer's act block parses on each model in at least one arm.** Met on nine of ten; DeepSeek's payer was never reached.
3. Valid lines, as information: Ministral 8B, Ministral 14B, Llama 70B, GPT-5.4 mini and Gemini Flash Lite 4 of 4 each across L and C; Gemma 27B 3 of 4; Llama 8B 3 of 4; Gemma 12B 2 of 4; Llama 3.2 3B 0 of 4, as the local Q4 3B wrote 0 of 2 in study 9's pilot.

## The credit state, and why the main run did not start

`GET /api/v1/key` shows the key with a limit of $100 and $99.91 remaining; `GET /api/v1/credits` shows the account behind it with `total_credits: 0` and `total_usage: 0.0878`. The key's $100 is a cap on what the key may spend, not a balance; the account holds no purchased credits, and the 21 clean chains ran on the small negative allowance OpenRouter extends. Two probes after the pilot (one call each, "reply OK") fixed the threshold: a request reserving about half a cent of credit in flight passes (DeepSeek at a 500-token cap, Llama 8B), a request reserving about $0.004 or more is refused (DeepSeek at the 4,000-token reasoning cap, GPT-5.4 mini at a 1,000-token cap). That is why the 402s fell on the three reasoning models, whose raised cap multiplies the output price into the reservation, and on the payer turn, the longest, and why six chains in parallel made it worse. The main run was not started: running 1,980 chains against an unfunded account would drive it negative on the owner's behalf and would be cut off by the provider at an unknown point in the design. The registration, the sizing and the harness stand; the run resumes, from the first chain, when the account is funded.

## What the pilot says about the sizing

Cost per chain in block 1, over the chains that ran clean, mean of the three arms: Llama 3.2 3B $0.0008, Llama 8B $0.0003, Ministral 8B $0.0017, Gemma 12B $0.0009, Ministral 14B $0.0023, Gemma 27B $0.0012, Llama 70B $0.0036, GPT-5.4 mini $0.0116, Gemini 3.1 Flash Lite $0.0040 (its F chain alone), DeepSeek V4.1 Flash not measured (its one clean call cost $0.0005, consistent with the listing). The registered aim of 198 chains per model (three repeats in blocks 1 and 5, two in block 3, one in block 6), with half as much again per chain for block 3's confuser contexts and block 5's longer inbox, projects to $7.86 for the ten models, GPT-5.4 mini $3.43 of it; the whole extension fits the $70 budget about nine times over and no repeat has to be cut. Wall time: 3 to 24 seconds a chain at six in parallel, about 2.5 hours for the 1,980 chains.

## What the pilot showed that the main run should know

- **OpenRouter routes an open-weight model across several hosts, call by call.** The `provider` field returned on each call, kept in `turns.json`, names Cloudflare and Parasail for the Llama 3.2 3B's nine calls, six different hosts for the Llama 70B's, and the vendor's own service for the Mistral, OpenAI, Google and DeepSeek models. The serving precision of those hosts is not promised by the listing, so "full precision" in H10 is not a fact of the pilot's chains. The main run asks for an unquantised serving (`provider: {"quantizations": ["bf16", "fp16", "fp32"]}`) for the seven open-weight models, recorded in every manifest, and the host as served stays recorded per call; the pilot ran without it.
- **The reasoning cap and the reservation.** The 4,000-token cap for the three reasoning models is what the registration says, and it is what the provider reserves against; on a funded account it costs nothing extra (the usage accounting bills tokens used), so it stands.
- **The shape in the pilot, for what one chain per cell is worth:** the four smallest open-weight models and the two Gemmas act on another item in prose and in the unchecked line, and are held at the coordinator with the checked line (their forwarded line refused twice), as the local models were; the Ministrals, the 70B and the two frontier models that completed reach a correct act in F and in C and a wrong one in L. The main run measures it.
