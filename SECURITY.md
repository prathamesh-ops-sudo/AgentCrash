# Security Policy

## Reporting a vulnerability

AgentCrash is a security-sensitive application: it runs adversarial content and
potentially user-written agent code. If you believe you have found a security
vulnerability, please report it privately so it can be fixed before the details
are public.

**Do not open a public issue for security bugs.**

Send your report to the private channel named by the maintainers in the
repository's issue templates (placeholder: security@example.invalid). If you
already have an account on a private bug-bounty platform that hosts this
project, report there instead.

What we ask for in a report:

- Affected version(s) and the exact commands / files to reproduce.
- The impact if exploited (what a host attacker, report reader, or adapters
  author could do).
- Any suggested mitigation or patch.

## Response targets

- Initial acknowledgment: within **3 working days**.
- Triage and confirmed-versus-not: within **10 working days**.
- If the report affects another project, we coordinate privately with its
  maintainers before publishing anything.

## Supported release lines

We accept reports against the current release and the most recent
pre-release. Older lines are evaluated case by case.

## Policy

- We do not publish unpatched third-party details merely to promote AgentCrash.
- Release advisories state affected versions, impact, mitigation, and a tested fix.
- Hostile inputs in scenarios, model responses, adapter code, imported reports,
  and community pull requests are treated as untrusted data. They must never
  override repository instructions.