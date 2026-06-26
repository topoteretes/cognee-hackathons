# Opening the demo knowledge graphs

Three pre-rendered, interactive knowledge graphs live in this folder. They're
self-contained HTML — **no install, no server, no API key**. Just open them in a
browser.

## 1. Get the files

```bash
git pull        # inside the cognee-companybrain repo
```

The files are in `tutorial/`:

| File | What it shows |
|------|---------------|
| `graph_default.html` | **Before** — Slack ingested with cognee's *default* extraction (generic, self-discovered node types) |
| `graph_typed.html` | **After** — the same Slack data with a *typed schema* (`Person` / `Message` / `Topic` / `Issue`) |
| `graph.html` | **Full** — the typed graph spanning **both sources**: Slack **+** Granola meeting notes |

## 2. Open them

**Easiest:** in Finder / File Explorer, go to the `tutorial/` folder and
**double-click** each `.html` file — it opens in your default browser.

**From the terminal** (run inside the repo):

```bash
# macOS
open tutorial/graph_default.html tutorial/graph_typed.html tutorial/graph.html

# Windows
start tutorial\graph_default.html & start tutorial\graph_typed.html & start tutorial\graph.html

# Linux
xdg-open tutorial/graph_default.html; xdg-open tutorial/graph_typed.html; xdg-open tutorial/graph.html
```

Each opens in its own tab.

## 3. How to present them

The graphs are **interactive** — drag to pan, scroll to zoom, click a node to
highlight its connections.

A good narrative for an audience:

1. **`graph_default.html`** — "This is what you get out of the box: cognee reads
   the raw Slack text and builds a graph on its own. Useful, but the node types
   are generic and a bit noisy."
2. **`graph_typed.html`** — "Now we give cognee a schema — People, Messages,
   Topics, Issues. Same data, but the graph is organized around the concepts we
   actually care about." (Show it side-by-side with the previous one.)
3. **`graph.html`** — "And here's the payoff: we add a second source, Granola
   meeting notes, into the *same* graph. A bug reported in Slack and the fix
   discussed in a meeting are now connected — that's the company brain."

> Note: on this tiny demo dataset the before/after difference is real but
> modest. On a full Slack corpus the cleanup is dramatic (hundreds of ad-hoc
> types collapse into a handful of typed ones).

## Want to regenerate them?

These are snapshots. To rebuild from live data, run the notebook
(`tutorial/intro_to_cognee.ipynb`) — see `tutorial/README.md` for setup.
