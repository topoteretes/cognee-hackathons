"""Slack agent (Socket Mode) — the Company Brain in your support channel.

Flow:
  1. A user @mentions the bot with a question.
  2. The bot queries the brain (query.ask). It keeps per-thread working memory
     via session_id = the Slack thread ts.
  3. If the brain is confident -> it replies in-thread with the answer and adds
     a 👍 / 👎 prompt so a human can rate it.
  4. If not confident -> it escalates by @tagging the RESPONSIBLE_PERSON expert.
  5. Feedback loop:
       - Expert reacts 👎 on the bot's answer, then posts the correct answer in
         the thread  ->  we remember the correction into the wiki AND propose+apply
         a qa-answerer skill improvement (feedback.record_correction).
       - Expert reacts 👍  ->  we log a positive SkillRunEntry.

Run:
    python -m src.slack_app
"""

from __future__ import annotations

import asyncio
import os
import re

from dotenv import load_dotenv
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from .feedback import record_correction
from .query import ask

load_dotenv()

ANSWERER_SKILL = "qa-answerer"

app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

# Remember which messages were bot answers, and to which question, so a later
# reaction/reply can be tied back to the original run.
#   bot_answers[(channel, message_ts)] = {"question", "thread_ts", "user"}
bot_answers: dict[tuple[str, str], dict] = {}


def _clean(text: str) -> str:
    """Strip the leading <@BOTID> mention from the message text."""
    return re.sub(r"<@[\w]+>", "", text or "").strip()


def _expert_mention() -> str:
    person = os.getenv("RESPONSIBLE_PERSON", "").strip()
    return f"<@{person}>" if person else "an available expert"


@app.event("app_mention")
async def handle_mention(event, say, client):
    question = _clean(event.get("text", ""))
    channel = event["channel"]
    thread_ts = event.get("thread_ts") or event["ts"]

    if not question:
        await say(text="Ask me a question about Cashly and I'll check the Company Brain.",
                  thread_ts=thread_ts)
        return

    # Per-thread working memory lives in the session tier.
    ans = await ask(question, session_id=thread_ts, skills=[ANSWERER_SKILL])

    # Always post the brain's best answer AND tag the responsible expert to
    # verify. 👍 = good (logged). 👎 + a threaded reply = correction -> the wiki
    # learns it and the answerer skill improves.
    posted = await say(
        text=(
            f"{ans.text}\n\n"
            f"———\n"
            f"{_expert_mention()} please verify. React 👍 if correct, or 👎 and "
            f"reply with the right answer so I can update the Company Brain."
        ),
        thread_ts=thread_ts,
    )
    bot_answers[(channel, posted["ts"])] = {
        "question": question,
        "thread_ts": thread_ts,
        "user": event.get("user"),
    }


@app.event("reaction_added")
async def handle_reaction(event, client):
    reaction = event["reaction"]
    if reaction not in ("+1", "-1", "thumbsup", "thumbsdown"):
        return

    item = event.get("item", {})
    key = (item.get("channel"), item.get("ts"))
    meta = bot_answers.get(key)
    if not meta:
        return  # reaction wasn't on a tracked bot message

    positive = reaction in ("+1", "thumbsup")

    if positive:
        await record_correction(
            question=meta["question"],
            correct_answer="",          # nothing to add to the wiki
            skill_name=ANSWERER_SKILL,
            thumbs_up=True,
            session_id=meta["thread_ts"],
        )
        await client.chat_postMessage(
            channel=item["channel"],
            thread_ts=meta["thread_ts"],
            text=":white_check_mark: Thanks — logged this as a good answer.",
        )
        return

    # 👎 : look for a human correction posted in the thread.
    correction = await _latest_human_reply(client, item["channel"], meta["thread_ts"])
    expert = event.get("user")
    result = await record_correction(
        question=meta["question"],
        correct_answer=correction or "",
        skill_name=ANSWERER_SKILL,
        thumbs_up=False,
        session_id=meta["thread_ts"],
        expert=f"<@{expert}>" if expert else None,
    )

    if correction and result.get("error"):
        msg = (
            ":warning: I received the correction but couldn't write it to the "
            "Company Brain (LLM backend error). It will index once the LLM key "
            "is healthy."
        )
    elif correction and result.get("remembered"):
        msg = (
            ":brain: Got it — I learned the correct answer and updated the "
            "Company Brain"
        )
        if result.get("applied"):
            msg += ", and improved the answerer skill from this feedback."
        else:
            msg += "."
    else:
        msg = (
            ":memo: Logged the 👎. Post the correct answer in this thread and I'll "
            "add it to the Company Brain."
        )
    await client.chat_postMessage(
        channel=item["channel"], thread_ts=meta["thread_ts"], text=msg
    )


async def _latest_human_reply(client, channel: str, thread_ts: str) -> str | None:
    """Return the most recent non-bot reply text in the thread, if any."""
    resp = await client.conversations_replies(channel=channel, ts=thread_ts, limit=50)
    msgs = resp.get("messages", [])
    for m in reversed(msgs):
        if m.get("bot_id"):
            continue
        if m.get("ts") == thread_ts:
            continue  # skip the original question
        text = _clean(m.get("text", ""))
        if text:
            return text
    return None


async def main():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    print("[slack] Company Brain bot is running (Socket Mode). Ctrl-C to stop.")
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
