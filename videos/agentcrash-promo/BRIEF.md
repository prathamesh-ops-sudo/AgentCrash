---
workflow: product-launch-video
flow: automation
storyboard: no
message: "See the tool action an injection causes, then prove your fix — crash-test your AI agent before you trust it."
destination: yt
aspect: 1920x1080
language: en
length: 35s
angle: product
length: 35s
---

## Intent

A 35-second, **silent**, caption-driven product launch video for AgentCrash —
an open-source agent security test harness. It shows the flagship story: a
clean invoice-summary task, an injected document that tries to redirect the
agent, the canary leak caught in the local outbox, and then a policy that
blocks the same attack while the task still completes. Tone is dark, modern,
"developer SOC": deep navy, electric blue/indigo accents, monospace terminal
text, crisp high-contrast captions readable with audio off. No voices, no music.

## Assets

- C:\Users\prath\OneDrive\Desktop\AgentCrash\assets\generated\social-preview.png — hero visual, launch end-card background mood
- C:\Users\prath\OneDrive\Desktop\AgentCrash\assets\generated\report-shot.png — authentic report screenshot showing 5 outcome dimensions
- C:\Users\prath\OneDrive\Desktop\AgentCrash\assets\generated\viewer-shot.png — authentic viewer UI screenshot
- C:\Users\prath\OneDrive\Desktop\AgentCrash\assets\source\logo.svg — AgentCrash wordmark/mark

## Customizations

- Silent video (`music: none`, no narration) — captions carry the message; every beat must be legible without audio.
- Use authentic product screenshots (report-shot.png, viewer-shot.png) for the evidence beats, not rebuilt mockups.

## Notes

- The blueprint's flagship storyboard: 0–5s task+clean invoice; 5–13s injection highlights + attempted send; 13–20s canary detected in local outbox; 20–28s policy applied + blocked comparison; 28–35s install command + end card.
- Brand tokens: bg #0b1220, electric blue #38bdf8, indigo #6366f1, mono #c9d6ef, canary/red #c62828, pass green #2e7d32, amber warn #f59e0b.
- Keep captions readable with audio off (accessibility requirement). All addresses/accounts/records are synthetic fixtures (example.invalid).
- Install command to feature: `uvx --from agentcrash==0.1.0 agentcrash demo`.
- No fabricated benchmark or live-capture claims — screenshots are from the real build.