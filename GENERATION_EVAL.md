# GPT response evaluation

Run the live evaluation only after copying `.env.example` to `.env` and adding `OPENAI_API_KEY` locally, or setting that environment variable in the shell. The code loads `.env` automatically. Do not put the key in a profile or commit it.

```bash
HF_HOME=/path/to/model-cache .venv311/bin/python -m src.evaluate_generation --out work/generation-live.json
```

For a small smoke run, add `--case direct-03 --case plan-01 --case abstain-02`. The full development run executes 27 cases: 10 direct checks, five chain checks, five program questions, five uncertain/out-of-scope cases, and two extra plans. Only supported eligibility decisions and plans invoke the GPT writer; deterministic program answers and uncertain cases bypass it. A model failure or a rejected draft falls back to checked template wording.

The report records each generated candidate, accepted answer, decision, cited passages, structural verification result, fallback reason, and a blank `manual_review` record. Review each model-written answer against its cited passage and the checked rule trace. Set `supported` to `true` only if every factual claim is supported. Use `false` for invented prerequisites, course membership, credits, term availability, or an answer that changes the checked decision. Record the issue and the precise unsupported phrase in `notes`.

The summary counts mechanical checks and model usage. It does not calculate factual accuracy or citation support while reviews are pending. The 25 cases were used during implementation, so their decision match rate is a development regression score, not independent accuracy evidence. A later held-out set and human review are needed for a resume claim about GPT answer quality.
