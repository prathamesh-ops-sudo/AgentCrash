# AgentCrash

**Crash-test your AI agent in a synthetic workplace.**

[![CI](https://github.com/prathamesh-ops-sudo/AgentCrash/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/prathamesh-ops-sudo/AgentCrash/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentcrash.svg)](https://pypi.org/project/agentcrash/)
[![Python](https://img.shields.io/pypi/pyversions/agentcrash.svg)](https://pypi.org/project/agentcrash/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

An open-source agent security test harness. Run your agent against a synthetic
workplace, watch the tool calls an injected instruction actually causes, then
prove that your fix blocks the attack without breaking the legitimate task.

- **See the action, not just a verdict.** AgentCrash records the exact tool
  calls an attack causes, in a synthetic world with nothing real in it.
- **Outcomes stay separate.** Task success, attack attempted, attack succeeded,
  policy blocked and completeness are reported as distinct dimensions, never
  collapsed into one fuzzy score.
- **The fix is testable.** Apply a policy, rerun, and show the attack blocked
  while the task still completes.
- **Offline by default.** The bundled replay needs no API key and makes no
  model calls.

![AgentCrash demo: crash-test your AI agent in a synthetic workplace, watch the injected instruction redirect a send, detect the canary, then block it with a policy](assets/generated/agentcrash-demo.gif)

**[Watch the 35-second walkthrough (MP4)](assets/generated/agentcrash-demo-35s.mp4)**

> **Scope honesty**: results apply to the listed scenarios and configuration.
> A passing test is a scoped result, **not** a guarantee that an agent is secure.

## Try it in 30 seconds

No API key. No model calls. Runs offline.

```bash
uvx --from agentcrash==0.1.0 agentcrash demo
```

Or install it and run your own live test:

```bash
uv tool install agentcrash==0.1.0
agentcrash --version
agentcrash doctor --mode demo
```

## Why AgentCrash

Most answers to "is my agent safe?" are an opinion, a single number, or a
prompt that someone else wrote. None of them show you what the agent actually
did when an untrusted document told it to do something else.

AgentCrash gives you that: the real tool requests, the policy decision on each
one, and the synthetic effect that followed, in a run you can repeat and
compare. When you then add a control, you rerun the same scenario and show the
attack blocked with the task still complete. That is the difference between
claiming a fix and demonstrating one.

## What a report tells you

Task completion, attempted unauthorized actions, observed synthetic effects,
policy decisions, and missing evidence are reported **separately** — never
collapsed into one score.

- **Task success** — did the legitimate task assertion hold?
- **Attack attempted** — was the defined forbidden request observed?
- **Attack succeeded** — did the simulated attacker goal occur in the synthetic world?
- **Policy blocked** — did the tool policy reject that request?
- **Completeness** — does the run have all required evidence?

An incomplete run is never a clean pass.

<details>
<summary>View a report from the actual build (attack variant)</summary>

This is a real run of `invoice-confidential-note`: the injected
document redirects a synthetic send that is caught in the local outbox.

<img src="assets/generated/report-shot.png" alt="AgentCrash report: five outcome dimensions (task success, attack attempted, attack succeeded, policy blocked, completeness) plus the event timeline." width="820"/>

</details>

**Example evidence:** [`assets/generated/sample-report.html`](assets/generated/sample-report.html) is the
standalone HTML report the CLI produces for that run.

<details>
<summary>See the five demo beats as stills</summary>

<p align="center">
  <img src="assets/generated/beat-open.png" alt="Beat 1: crash-test your AI agent before you trust it" width="470"/>
  <img src="assets/generated/beat-inject.png" alt="Beat 2: injected instruction in the invoice" width="470"/>
</p>
<p align="center">
  <img src="assets/generated/beat-detect.png" alt="Beat 3: canary detected in local outbox" width="470"/>
  <img src="assets/generated/beat-fix.png" alt="Beat 4: policy blocks the same send, task completes" width="470"/>
</p>
<p align="center">
  <img src="assets/generated/beat-end.png" alt="Beat 5: install and run your own check" width="470"/>
</p>

</details>

## Who it is for

- **Agent builders** who want to test tool-use safety before shipping.
- **AppSec and AI-security teams** who need evidence, not a demo script.
- **Researchers** who want a repeatable harness for injection and policy work.
- **Maintainers** who want a regression test that fails when a policy
  regresses.

## Test your agent

Start with the Python adapter recipe. Replace production tools with the
provided synthetic tool client, validate the adapter, and run the clean task
and its attack variant.

```bash
agentcrash init --template invoice
agentcrash run invoice-confidential-note --variant benign
agentcrash run invoice-confidential-note --variant attack --trials 5
agentcrash report RUN_ID --format html
```

The scripted model broker needs **no model key** — all of the above run offline
with deterministic results. Live provider integration is a scaffold in v0.1;
when you wire a provider key, it is held broker-only and never passed on the
CLI or written into a run.

## How it works

1. **You run a scenario** against a synthetic workplace (documents, notes, a
   local mail outbox — nothing real).
2. **The agent completes the task.** An injected document may try to redirect
   it toward a forbidden action.
3. **AgentCrash records every tool request, decision, and effect** as authority
   events, then evaluates the run.
4. **You see five separated outcomes** — task success, attack attempted, attack
   succeeded, policy blocked, completeness — never a single fuzzy score.
5. **You apply a policy and rerun** to prove the fix still completes the task
   while the attack is blocked.

## Contribute

Add a synthetic scenario, improve an integration, or help someone complete
their first run. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md) for the responsible-disclosure channel and the
tested security boundary.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

## Star it if it is useful

If AgentCrash saves you from shipping an agent you have not tested, a star
helps the next person find it.