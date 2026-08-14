# Reaction Dynamics

### Most misunderstandings at work aren't disagreements. They're translation errors.

**Cognee × Qdrant Hack Night, Berlin — 2026-08-14. Solo entry, Martin Kaiser.**

## Team

- **Team name:** Reaction Dynamics (solo)
- **Participants:** Martin Kaiser ([@kaiser-data](https://github.com/kaiser-data))
- **Project name:** Reaction Dynamics

## Links

| | |
|---|---|
| **Repo** | https://github.com/kaiser-data/reaction-dynamics |
| **Live dashboard** | https://reaction-dynamics-berlin.netlify.app |
| **Knowledge graph** | https://reaction-dynamics-berlin.netlify.app/graph.html |

---

## What it does

Every team runs on two invisible cultures:

- **Emoji culture** — what a 👍 actually *does* here. "On it"? Or "I'm ignoring
  you politely"?
- **Answer culture** — whether an ask gets answered, or just acknowledged and
  dropped.

Reaction Dynamics measures both, and answers questions a keyword search cannot:
*which asks did nobody answer? who does this room follow? where did we disagree
without noticing?*

## The insight

**Slack cannot tell you when a reaction happened.** The Web API returns
reactions as `{name, users, count}` — no timestamps, no ordering. Per-reaction
timing exists **only** in the live `reaction_added` event.

That means the signal is excluded by construction, not overlooked. No export, no
batch tool, no competitor's corpus can contain it. If you weren't listening at
the moment someone reacted, it is gone permanently.

So the listener is the first thing that starts, and it is the half of this
product nobody can reconstruct after the fact.

## Four shapes, identical counts

| Shape | Pattern | Reads as |
|---|---|---|
| **Cascade** | burst right after the first | social proof — the room followed whoever moved first |
| **Trickle** | even, independent arrivals | the trustworthy kind of agreement |
| **Stall then burst** | silence, then everyone at once | deference — they waited to see what one person thought |
| **Split** | opposed emoji interleaved | live disagreement, which final counts hide completely |

Classification is a hypothesis test, not a threshold picked by eye: arrival times
are tested against uniform with a one-sample **Kolmogorov–Smirnov** statistic
(critical value `1.36/√n`), so *trickle* means "we cannot reject independent
arrival". Burstiness uses **Goh & Barabási (2008)**, `B = (σ−μ)/(σ+μ)`.

**We claim nothing about what anyone felt.** Timing has no valence — a cascade
is not "happy". We describe only how a group behaved in time.

## What we measured

**36,779 timestamped reactions**, 24 threads, 2,294 messages, 16,725 distinct
reactors, spanning 2016 → 2026 — from the GitHub Reactions API, the only public
source carrying per-reaction identity, content *and* timestamp.

### The same emoji does different work in different rooms

| | microsoft/vscode | kubernetes/kubernetes |
|---|---|---|
| 👍 `+1` | 52% | 69% |
| 👎 `-1` | **27%** | **6%** |
| `split` shapes | **12%** | **0%** |
| `trickle` | 65% | 90% |

vscode is a contested product-feature room: a quarter of all reactions are
dissent, and one message in eight is an active disagreement. kubernetes is a
consensus room — dissent is 6%, with no split shape at all.

*Honest limit:* the emoji-mix difference rests on 11,654 kubernetes reactions and
is robust. The **shape**-mix difference rests on 21 classified kubernetes
messages against 211 for vscode — suggestive, not established.

### The finding that justifies the architecture

**The seconds-scale cascade is not on GitHub.** Median cascade span across 36,779
reactions is **23.4 hours**. We went looking for the six-second burst in the
largest public corpus of timestamped reactions that exists, and it is not there.

That shape exists only where a room is live, and only if you were listening.

## The stack, and why

```
Slack (Socket Mode)  ──┐
                       ├──► one corpus schema ──► shape classifier ──┐
GitHub Reactions API ──┘                                             │
                                                                     ▼
                                        typed DataPoints ──► cognee ──► Qdrant
                                        (embed_triplets=True)
                                                                     │
                                              4-tool agent ◄─────────┘
```

- **cognee** — `ReactionShape`, `UnansweredAsk`, `Message`, `Person`, `Room` as
  typed `DataPoint` subclasses, so the *finding* is a first-class node with edges
  to the message, the room and the person who moved first. Not a bag of text with
  entities guessed by an LLM.
- **Qdrant** — written with `embed_triplets=True`, which embeds the
  **relationship**, not just the nodes either side of it. **64 indexed triplets**;
  `Triplet_text` wins 3 of 4 relationship queries. We are not searching messages,
  we are searching the edges between them.
- **Agent** — four tools (`ghosted_asks`, `bellwether`, `room_dialect`,
  `shapes_like`). The LLM only routes and writes prose; **every number comes from
  a tool**. If the LLM is unavailable it falls back to keyword routing and still
  answers.

Live Slack and ten years of GitHub go through **one schema and one classifier**,
so "cascade" means the same thing in both. The only difference is timescale —
which is the finding, not a bug to normalise away.

## Ready to use on Monday

```bash
cp .env.example .env       # 6 values, each documented inline
pip install slack_sdk
python seed/listen_slack.py     # start this first, leave it running
python seed/fetch_github.py
python seed/ask.py "which asks did nobody answer?"
```

**No public host, no ngrok, no OAuth server, no frontend.** Socket Mode was
chosen deliberately: clone, fill in `.env`, run one process.

(For contrast, the official cognee Slack integration takes the HTTP-webhook
route — it needs all four, and subscribes to `app_uninstalled` / `tokens_revoked`
/ `app_home_opened`, so it cannot observe reactions at all.)

## Evidence base

Emoji meaning is local, contested, and currently shifting — which is the
empirical case for *measuring* behaviour rather than assuming meaning.

- **Miller et al., ICWSM 2016** — shown an *identical* rendering, people disagreed
  on its sentiment **25%** of the time
- **Zhukova & Herring, Indiana University** — Gen Z and non-binary respondents
  read 👍 and 😂 as significantly more sarcastic and passive-aggressive; older
  respondents rated 🔥 and 💣 worse. The same 👍 means different things to two
  people in the same channel *today*
- **Glikson et al., SPPS 2018** — smileys in work email lowered perceived
  competence; held at **N=847** in a preregistered replication (**Lai & Mayiwar,
  Collabra 2023**), where the claimed formality moderation did *not*
- **Atlassian/YouGov** — **65%** of 10,000 workers across 5 countries use emoji to
  convey tone at work

Build implication we followed: do **not** ship a feature that nudges people to
use more emoji. Help teams disambiguate the ones they already use.

## What is real, and what isn't

| Piece | State |
|---|---|
| GitHub corpus, 36,779 timestamped reactions | ✅ reproducible from the API |
| Shape classifier, KS-tested | ✅ |
| Socket Mode listener, live capture | ✅ running tonight in a consented channel |
| cognee → Qdrant, typed DataPoints, 64 triplets | ✅ 206 points in Qdrant Cloud |
| 4-tool query agent | ✅ |
| Cognee Cloud graph, ingested + answering | ✅ live, `graph.html` |
| Judge-facing dashboard | ✅ [reaction-dynamics-berlin.netlify.app](https://reaction-dynamics-berlin.netlify.app) |
| Generation / country emoji breakdown | 📚 cited literature only — **not measured**, no age or country field exists in reaction data |

Live capture happened in **#emojie-lab**, a channel created for this, opened with
a consent notice, joined voluntarily. `#all-hacknight` was deliberately **not**
ingested.

## Not a monitor

Nobody is ranked. Colour encodes duration, never virtue. A person is named only
when carrying load — *"Maya has answered 40% of everything, that's a lot to
carry"* — framed as fragile for her, never as praise or blame.

**Reactions are not outcomes.** This is a triage signal, not a decision driver.
It exists to prevent a misunderstanding, not to score a person.
