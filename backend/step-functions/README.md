# Step Functions state machine

`ai-code-animator-state-machine.json` is the tracked ASL definition. Its
`RunFargateTask` container override includes `OPENAI_API_KEY` as a **placeholder**
(`REPLACE_WITH_OPENAI_API_KEY`) — the real key is never committed to git.

The live deployed state machine has the real key patched in directly.

**Never deploy this file to AWS as-is.** `aws stepfunctions update-state-machine`
replaces the *entire* definition, including the `OPENAI_API_KEY` value — pushing
the tracked file directly overwrites the real key with the placeholder and
breaks every render (TTS generation gets a 401 from OpenAI, and since the
container still exits non-zero, this happens for *every* scene regardless of
whether the scene's own code is broken).

Before any `update-state-machine` call:
1. Fetch the real key, e.g. from AIAgentLambda's env var:
   `aws lambda get-function-configuration --function-name AIAgentLambda --query "Environment.Variables.OPENAI_API_KEY" --output text`
2. Substitute it into a scratch copy of this file (not the tracked one).
3. Deploy the scratch copy, not `ai-code-animator-state-machine.json`.

This happened once already (2026-07-30, ~20 minutes of total outage) — worth
fixing properly at some point by moving the key to Secrets Manager/SSM and
referencing it via the ECS task definition's `secrets` block instead of a
plain literal in the Step Functions `Environment` override, which would make
this class of mistake impossible.
