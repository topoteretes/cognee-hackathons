# cognee-gtm-brain

**Cognee Hackathon — Warsaw, 26 June 2026**

This project builds a **GTM brain**: one searchable "memory" that pulls together
everything scattered across a go-to-market team's tools — meeting transcripts,
emails, a calendar, a spreadsheet of accounts and deals — into a single
knowledge graph you can ask questions in plain English.

Ask *"What's the status of the Clay sponsorship and what did Bruno want instead
of a booth?"* and you get one answer stitched from a deal row, a calendar invite,
a meeting transcript, an email thread, and a research note — all about the same
company.

It also shows how **two different people can each have their own private brain**,
and how one can **share** theirs with the other.

> Built on [Cognee](https://github.com/topoteretes/cognee) (open-source AI memory).
> Extends the earlier [`cognee-companybrain`](../cognee-companybrain-hackathon-2026-06-16)
> project and merges in the
> [modelguide GTM-week brain](https://github.com/modelguide/gtm-week-workshop/tree/main/brain).

---

# 🟢 Rebuild this from scratch (no coding experience needed)

Follow these steps top to bottom. Every command is meant to be **copy-pasted into
a Terminal**, one line at a time. On a Mac, open the app called **Terminal**
(press `Cmd+Space`, type "Terminal", hit Enter).

You do **not** need to understand the code. You need ~15 minutes and a credit
card for an AI key (this run costs a few cents).

### Step 0 — Install the two free tools this needs

You need **Python** (the programming language) and **uv** (a tool that sets
everything else up for you).

1. **Python** — most Macs already have it. Check by pasting this and pressing Enter:
   ```bash
   python3 --version
   ```
   If you see something like `Python 3.11.5` (3.11 or higher), you're good. If
   not, download it from <https://www.python.org/downloads/> and run the installer.

2. **uv** — paste this and press Enter (it's the official installer):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   Then **close and reopen Terminal** so it picks up the new tool. Check it:
   ```bash
   uv --version
   ```
   You should see something like `uv 0.11.x`.

### Step 1 — Go into the project folder

You should already have this project folder on your computer. Move into it
(adjust the path if yours is somewhere else):
```bash
cd ~/Projects/cognee-hackathons/cognee-gtm-brain-hackathon-2026-06-26
```
Tip: you can type `cd ` (with a space), then **drag the folder from Finder onto
the Terminal window**, then press Enter.

### Step 2 — Install the project (one command)

```bash
bash tutorial/setup.sh
```
This creates a private workspace (`.venv`) and downloads everything the project
needs. It takes a few minutes the first time. When it finishes it will also
create a settings file called `.env` for you.

Now **turn on** that workspace (do this every time you open a new Terminal):
```bash
source .venv/bin/activate
```
Your prompt will now start with `(.venv)`.

### Step 3 — Add your AI key

The brain uses an AI model to read the documents, so you need an **OpenAI API
key**.

1. Go to <https://platform.openai.com/account/api-keys>, sign in, and click
   **"Create new secret key"**. Copy the key — it's a long string that starts
   with `sk-`.
2. Open the `.env` file in this folder with any text editor (TextEdit is fine).
   Find the line:
   ```
   LLM_API_KEY=sk-...
   ```
   Replace `sk-...` with the key you copied, so it looks like
   `LLM_API_KEY=sk-proj-abc123...your-real-key...`. Save the file.

> ⚠️ The most common mistake: leaving the placeholder text in. The key **must**
> be your real key starting with `sk-`. If you see an "incorrect API key" error
> later, this is why.

### Step 4 — Build the brain

```bash
python scripts/run_gtm_ingest.py
```
This reads all the sample documents and builds the knowledge graph. It takes
about a minute. When it's done you'll see a line like:
```
gtm ingest done — companies=11 people=11 deals=9 signals=9 calendar=2 icps=2 threads=5 failures=0
```
`failures=0` means it worked. 🎉

### Step 5 — Ask the brain questions

```bash
python scripts/gtm_queries.py
```
This asks five questions that each need information from *several* documents at
once. You'll see answers print out, for example:
```
Q: What is the status of the Clay sponsorship and what did Bruno want?
 -> Clay is interested but not committed — they want a co-created, operator-first
    GTM-engineering track (not a generic booth)... Artur will send a one-pager...
```
That answer was assembled from a spreadsheet row + a meeting transcript + an
email thread — the whole point of the brain.

**Want to see it as a picture?** Build the visual graph (and the two-user demo)
in Step 6, then open the generated HTML files.

### Step 6 — Two people, two private brains, then sharing

This is the multi-user demo. Run:
```bash
python scripts/run_multiuser_demo.py
```
It tells a four-part story and prints each part:

1. **Ingest** — two people each get their *own* private brain:
   - **Artur** (`artur@gtm-week.com`) → the Warsaw GTM brain
   - **Dana** (`dana@devtools-day.com`) → a different Berlin developer-conference brain
2. **Isolate** — each person can only see their own data. When Dana asks about
   Clay (which is in Artur's brain) she gets **"no access — isolated"**.
3. **Share** — Artur grants Dana **read** access to his Warsaw brain.
4. **See** — Dana asks the *exact same* Clay question again — and now gets the
   full answer.

It also creates two pictures of the graphs in the `tutorial/` folder:
- `graph_user_a_warsaw.html` — Artur's brain
- `graph_user_b_berlin.html` — Dana's brain

**Open them**: find them in Finder and double-click — they open in your web
browser. You can drag nodes around to explore. (Artur's is visibly bigger —
more companies and deals — which is the isolation made visual.)

### If something goes wrong

| What you see | What it means / fix |
|---|---|
| `command not found: uv` | uv isn't installed or Terminal wasn't reopened. Redo Step 0.2 and open a fresh Terminal. |
| `command not found: python` | Use `python3` instead, or install Python (Step 0.1). |
| `Incorrect API key provided` | Your `.env` still has the placeholder. Paste your real `sk-...` key (Step 3) and save. |
| `No such file or directory` | You're not in the project folder. Redo Step 1. |
| Prompt doesn't show `(.venv)` | Run `source .venv/bin/activate` again (Step 2). |
| It's slow / seems stuck | Building the brain calls an AI model; ~1 minute is normal. |

That's the whole rebuild. Everything below is for people who want to understand
or extend how it works.

---

# 🔧 How it works (for the curious / technical)

## The merge: how the pieces become one graph

The pipeline takes **three shapes** of data and routes each differently. The
trick is *order*: the structured facts are loaded first, so the AI-extracted
conversations attach onto them instead of creating duplicates.

```
                          sample_data/gtm_brain/
                                   │
        ┌──────────────────────────┼───────────────────────────┐
        │                          │                            │
  STRUCTURED (no AI)         DOCUMENTS (no AI)           CONVERSATIONS (AI reads)
  tables/*.csv               icp_*.md                    granola_*.md  (meetings)
  calendar_*.ics             account-deep-dive_*.md      email-threads/*.md
        │                          │                            │
        ▼                          ▼                            ▼
  Company, Person,           ICP profiles,               each conversation →
  Deal, Signal,              account research            Person / Message / Topic /
  CalendarEvent, Event       notes                       Question / Issue / Decision
        │                          │                            │
        └──────────── loaded FIRST as fixed nodes ────┘          │
                                   │                             │
                                   ▼                             ▼
                         the canonical nodes ◄── attach onto ────┘
                    (one per email, one per company domain)
```

**Two anchors fuse everything:** a person is keyed by their **email**, a company
by its **website domain**. So "Bruno Estrella" spoken aloud in a meeting,
`bruno@clay.com` on an email, and a calendar attendee all become *one* person;
the account row, the deal, and the company a meeting is *about* all become *one*
`clay.com` company.

## Multi-user, under the hood

Cognee has access control built in: every brain is a **dataset** owned by a user,
stored in its own database, reachable by others only via an explicit grant. The
reusable building blocks live in `src/gtm_brain/multiuser.py`:

| Step | Function |
|------|----------|
| Turn on access control | `enable_access_control()` |
| Create / look up a user | `get_or_create_user(email)` |
| Build a user's own brain | `ingest_brain_for_user(folder, dataset_name, user)` |
| Ask, within that user's permissions | `recall_as(user, question, [dataset])` |
| **Share** a brain with someone | `share_dataset(owner, recipient, dataset_name, "read")` |
| List what a user can see | `list_readable_datasets(user)` |

Two things that bite if you build your own version (both already handled here):

- **Reach a shared brain by its id, not its name.** Cognee resolves a dataset
  *name* only for datasets you own; a shared one is reachable by its UUID.
  `recall_as` looks it up for you.
- **Choose where data is stored *before* importing cognee.** The demo sets the
  `SYSTEM_ROOT_DIRECTORY` / `DATA_ROOT_DIRECTORY` / `CACHE_ROOT_DIRECTORY`
  environment variables at the very top of the file (before the first cognee
  import) so all data stays inside this project and the demo can safely reset
  itself. Without this, cognee writes to a shared default location.

> Known limitation: drawing the picture of a *shared* brain from the borrower's
> side trips an internal cognee check, so the demo draws each person's own brain
> and proves the share through a question instead. After the grant Dana sees the
> same Warsaw graph Artur does.

## What's in the box

```
src/gtm_brain/
  schema.py            the node types: Person, Company, Event, Deal, Signal,
                       CalendarEvent, ICP + Thread/Message/Topic/Question/Issue/Decision
  sources/gtm_files.py reads the brain folder (markdown, .ics, CSV)
  gtm_people.py        matches spoken names to email addresses
  ingest.py            single-user build: load facts, then read conversations
  multiuser.py         per-user isolation + sharing
  cognee_client.py     thin wrapper over cognee (add / cognify / recall / seed)
  classifier.py        auto-tags each conversation (sponsorship / speaking / ...)
  sources/slack.py     live Slack source   (optional; off by default)
  sources/granola.py   live Granola source (optional; off by default)

scripts/
  run_gtm_ingest.py    Step 4 — build the brain (offline, sample data)
  gtm_queries.py       Step 5 — ask cross-source questions
  run_multiuser_demo.py Step 6 — isolation + sharing demo

sample_data/
  gtm_brain/           Artur's brain — GTM Tech Week (Warsaw → London)
  gtm_brain_user_b/    Dana's brain — DevTools Day Berlin (the "other user")
```

The CSVs are **synthesized** to match the transcripts and ICPs (Clay as the
anchor account, Pavilion as "do not approach", the Warsaw renewal set). The
meeting/email/calendar/ICP files in `gtm_brain/` come from the upstream brain.

## The graph model

| Node | Identified by | Comes from |
|------|----------|-----------|
| `Person` | email | staff roster, speaker CSV, email/calendar headers, transcript speakers |
| `Company` | website domain | `attio_companies.csv` (+ scores, tiers, do-not-approach, research notes) |
| `Event` | name | Warsaw 2026, GTM Tech Week London 2027 |
| `Deal` | name | `attio_deals.csv` → linked to a Company + Event |
| `Signal` | — | `signals_feed.csv` → a "why now" reason on a Company/Person |
| `CalendarEvent` | uid | `calendar_next-24h.ics` → attendees (Person) + the account it's about |
| `ICP` | name | `icp_speaker.md`, `icp_sponsor.md` |
| `Thread` | — | a meeting / email / Slack conversation → linked to a Company + Event |

## Ideas to build on top (hackathon tracks)

- **Account agent** — type a company domain, get a live 360 from every node.
- **Pre-meeting brief** — for each calendar event in the next 24h, auto-write a
  brief from the linked account, open deal, last meeting, and email thread.
- **Lookalike sponsors** — "20 companies like our best past sponsors."
- **Guardrail check** — block any outreach that touches a "do not approach"
  company and suggest the allowed relationship instead.

## Other ways to run it

- **Offline (default)** — `python scripts/run_gtm_ingest.py` reads
  `sample_data/gtm_brain/`. Only an AI key is required.
- **Live sources** — `gtm-brain-ingest` also pulls real Slack + Granola if you
  set their tokens in `.env`; set `GTM_BRAIN_DISABLED=1` to skip the sample
  brain, or `GTM_BRAIN_DIR=/path` to point at a different folder.

## License

Apache 2.0 — see [LICENSE](LICENSE). Same license as
[cognee](https://github.com/topoteretes/cognee). The vendored `brain/` markdown
originates from [modelguide/gtm-week-workshop](https://github.com/modelguide/gtm-week-workshop).
