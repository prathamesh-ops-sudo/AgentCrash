# AgentCrash

Crash-test your AI agent in a synthetic workplace.

See the tool actions an attack causes, then verify your fix. AgentCrash is an
open-source agent security test harness with synthetic tools, visual evidence,
and regression tests.

> **Scope honesty**: results apply to the listed scenarios and configuration.
> A passing test is a scoped result, **not** a guarantee that an agent is secure.

## Try the demo

The bundled replay needs no API key and makes no model calls. It runs offline.

```bash
uvx --from agentcrash==0.1.0 agentcrash demo
```

or install and run your own live test:

```bash
uv tool install agentcrash==0.1.0
agentcrash --version
agentcrash doctor --mode demo
```

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

## Test your agent

Start with the Python adapter recipe. Replace production tools with the
provided synthetic tool client, validate the adapter, and run the clean task
and its attack variant.

```bash
agentcrash init --template invoice
agentcrash auth set --provider PROVIDER_ID
agentcrash run --scenario invoice-confidential-note --trials 5
agentcrash report RUN_ID --format html
```

## Contribute

Add a synthetic scenario, improve an integration, or help someone complete
their first run. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

See [SECURITY.md](SECURITY.md) for the responsible-disclosure channel and the
tested security boundary.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).