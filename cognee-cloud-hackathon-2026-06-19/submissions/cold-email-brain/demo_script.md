# 3-Minute Demo Script — Cold Email Brain

**Speaker:** Morris Neiland · **Time:** 9:15pm CET · **Stage time:** 3:00 hard

---

## Opener (0:00 – 0:15)

> "I'm a BDR. I write 80 cold emails a day. Every BDR tool stores templates —
> mine stores **learnings**, and rewrites itself every time a prospect ignores me. Watch."

*Tone: confident, conversational. Don't apologize, don't introduce yourself with a long CV.*

---

## The pile (0:15 – 0:35)

*Click "Connect + ingest brain" — Streamlit shows the ingest stats.*

> "I fed it 10 of my own real cold emails from my Gmail. Outcomes? Almost all silent.
> One was forwarded internally — and then declined. Zero conversions.
> Plus 80 synthesized examples across other trades.
>
> The brain doesn't just store them. It runs a distillation rule:
> a pattern only gets promoted from session memory into the permanent graph
> if it shows up across **3+ prospects with an average score above 0.7**.
> That stops it overfitting to one quirky outcome."

---

## Run #1 — a real silent email (0:35 – 1:25)

*Type the persona on stage:*
- Branche: Dachdecker
- Region: Köln
- Team-Größe: 6
- Prozess: papierbasierte Auftragsabwicklung
- Vorher angerufen: ✓

*Click "Show baseline" — load the REAL email Morris sent to a prospect on 2026-06-05. Read it aloud — pause at the bad bits.*

> "This is a real email I sent two weeks ago. To a real prospect.
> Got. Ignored.
>
> 183 words. Generic 'Bürokram' opener — every SaaS BDR says that.
> Multi-step CTA: callback OR website. 5-step product explainer that nobody asked for.
> Critic scores it **0.46**."

*Highlight the critic's `fix_suggestion` on screen.*

> "The critic — which is itself a self-improving skill — already pinpointed why:
> *'reference the attempted call directly and name a trade-specific pain'*."

---

## Train (1:25 – 2:05)

*Click "Train on this run".*

> "Watch what happens. The brain records a `SkillRunEntry` —
> success score 0.3, feedback negative. Cognee proposes a rewrite of the
> writer skill. We click apply."

*Show the SKILL.md diff inline — green lines = new rules added.*

> "The brain just edited its own instructions. New rules added in green.
> This isn't fine-tuning a model — this is the brain rewriting its own playbook
> in plain text, in real time, on Cognee Cloud."

---

## Run #2 — the delta (2:05 – 2:45)

*Same persona. Click "Generate email v2".*

*Read the email aloud — let the audience hear the specificity.*

> "Same prospect. Same input. Different brain.
> Opens with *'wie beim Telefonat besprochen'* — the brain learned to reference the call.
> Names Dachdecker-specific pain: *'handschriftliche Aufmaß-Zettel bei Regen verlieren'*.
> One CTA. Two concrete time slots. 88 words.
>
> Critic scores it **1.00**."

*Pause. Let the delta land.*

> "From **0.46 to 1.00** — Δ +0.54 — in one feedback round.
> **No model retraining. Just the brain refining its own playbook.**"

---

## Kicker (2:45 – 3:00)

> "This is one BDR's brain after one round.
> Imagine 50 Freshworks BDRs writing into the same Cognee Cloud brain.
> Every team's outbound gets sharper every day — automatically.
> That's Karpathy's LLM Wiki, for a sales org.
>
> Thank you."

---

## Cue card (the 3 things to say no matter what)

1. **"It stores learnings, not templates."**
2. **"Distillation rule: 3 prospects, avg score 0.7."**
3. **"50 BDRs sharing one brain."**

If something breaks live: stay calm, say *"and here's where the brain learns from this run too"* and switch to pre-recorded screenshots.
