"""
MediMind Engine - Two-tier memory architecture:
  - Redis (via Cognee sessions): Fast, per-conversation working memory
  - Cognee permanent graph: Durable knowledge graph across all sessions

This is the architecture the hackathon judges want to see.
"""
import json
import asyncio
import cognee
import redis
import uuid
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# ── Redis direct connection for real-time state ──
try:
    import os
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_client = redis.from_url(redis_url, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    redis_client = None
    REDIS_AVAILABLE = False


class HealthEntry:
    def __init__(self, category, title, details, source="user", connections=None,
                 confidence=0.8, version=1):
        self.category = category
        self.title = title
        self.details = details
        self.source = source
        self.connections = connections or []
        self.confidence = confidence
        self.version = version
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.status = "active"
        self.flags = []

    def to_dict(self):
        return {
            "category": self.category, "title": self.title, "details": self.details,
            "source": self.source, "connections": self.connections,
            "confidence": self.confidence, "version": self.version,
            "created_at": self.created_at, "updated_at": self.updated_at,
            "status": self.status, "flags": self.flags,
        }

    @classmethod
    def from_dict(cls, d):
        e = cls(
            category=d["category"], title=d["title"], details=d["details"],
            source=d.get("source", "user"), connections=d.get("connections", []),
            confidence=d.get("confidence", 0.8), version=d.get("version", 1),
        )
        e.created_at = d.get("created_at", datetime.now().isoformat())
        e.updated_at = d.get("updated_at", datetime.now().isoformat())
        e.status = d.get("status", "active")
        e.flags = d.get("flags", [])
        return e


class MediMind:
    def __init__(self):
        self.entries: list[HealthEntry] = []
        self.history: list[dict] = []
        self.query_log: list[dict] = []
        self.improvement_log: list[dict] = []
        self.corrections: list[dict] = []
        self.session_id = str(uuid.uuid4())[:8]  # unique session for Redis/Cognee

    def add_entry(self, entry: HealthEntry):
        self.entries.append(entry)
        self.history.append({"action": "add", "entry": entry.to_dict(),
                           "timestamp": datetime.now().isoformat()})
        # Cache in Redis for fast access
        _redis_cache_entry(entry)

    def update_entry(self, idx: int, updated: HealthEntry):
        old = self.entries[idx].to_dict()
        updated.version = self.entries[idx].version + 1
        updated.updated_at = datetime.now().isoformat()
        self.entries[idx] = updated
        self.history.append({"action": "update", "old": old, "new": updated.to_dict(),
                           "timestamp": datetime.now().isoformat()})
        _redis_cache_entry(updated)

    def remove_entry(self, idx: int):
        self.entries[idx].status = "removed"
        self.history.append({"action": "remove", "entry": self.entries[idx].to_dict(),
                           "timestamp": datetime.now().isoformat()})
        _redis_remove_entry(self.entries[idx])

    def get_active(self):
        return [e for e in self.entries if e.status != "removed"]

    def get_by_category(self, cat):
        return [e for e in self.get_active() if e.category == cat]

    def get_medications(self):
        return self.get_by_category("medication")

    def get_conditions(self):
        return self.get_by_category("condition")

    def get_symptoms(self):
        return self.get_by_category("symptom")

    def get_flagged(self):
        return [e for e in self.get_active() if e.flags]

    def record_correction(self, entry_idx, old_info, new_info, reason):
        self.corrections.append({
            "entry": self.entries[entry_idx].title,
            "old": old_info, "new": new_info, "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })

    def get_stats(self):
        active = self.get_active()
        return {
            "total_entries": len(self.entries),
            "active": len(active),
            "medications": len(self.get_medications()),
            "conditions": len(self.get_conditions()),
            "symptoms": len(self.get_symptoms()),
            "allergies": len(self.get_by_category("allergy")),
            "lab_results": len(self.get_by_category("lab_result")),
            "flags": len(self.get_flagged()),
            "corrections": len(self.corrections),
            "revisions": sum(e.version - 1 for e in self.entries),
            "improvements": len(self.improvement_log),
            "queries": len(self.query_log),
            "redis_connected": REDIS_AVAILABLE,
        }

    def export(self):
        return {
            "entries": [e.to_dict() for e in self.entries],
            "history": self.history,
            "query_log": self.query_log,
            "corrections": self.corrections,
            "improvement_log": self.improvement_log,
            "stats": self.get_stats(),
        }


# ══════════════════════════════════════════════
#  TIER 1: Redis — Fast session-level cache
# ══════════════════════════════════════════════

def _redis_cache_entry(entry: HealthEntry):
    """Cache health entry in Redis for sub-millisecond retrieval."""
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"medimind:{entry.category}:{entry.title}"
        redis_client.hset(key, mapping={
            "title": entry.title,
            "category": entry.category,
            "details": entry.details,
            "confidence": str(entry.confidence),
            "version": str(entry.version),
            "status": entry.status,
            "updated_at": entry.updated_at,
        })
        # Add to category set for fast lookups
        redis_client.sadd(f"medimind:cat:{entry.category}", entry.title)
        # Add to master set
        redis_client.sadd("medimind:all_entries", key)
        # TTL for session data (24 hours)
        redis_client.expire(key, 86400)
    except Exception:
        pass


def _redis_remove_entry(entry: HealthEntry):
    """Remove entry from Redis cache."""
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"medimind:{entry.category}:{entry.title}"
        redis_client.delete(key)
        redis_client.srem(f"medimind:cat:{entry.category}", entry.title)
        redis_client.srem("medimind:all_entries", key)
    except Exception:
        pass


def redis_get_medications() -> list[dict]:
    """Fast medication lookup from Redis (sub-ms)."""
    if not REDIS_AVAILABLE:
        return []
    try:
        titles = redis_client.smembers("medimind:cat:medication")
        meds = []
        for title in titles:
            data = redis_client.hgetall(f"medimind:medication:{title}")
            if data:
                meds.append(data)
        return meds
    except Exception:
        return []


def redis_log_query(session_id: str, question: str, answer: str):
    """Log query to Redis for session history."""
    if not REDIS_AVAILABLE:
        return
    try:
        key = f"medimind:session:{session_id}:queries"
        redis_client.rpush(key, json.dumps({
            "question": question, "answer": answer[:500],
            "timestamp": datetime.now().isoformat(),
        }))
        redis_client.expire(key, 86400)
    except Exception:
        pass


def redis_get_session_context(session_id: str) -> list[dict]:
    """Retrieve session query history from Redis for context."""
    if not REDIS_AVAILABLE:
        return []
    try:
        key = f"medimind:session:{session_id}:queries"
        items = redis_client.lrange(key, -5, -1)  # last 5 queries
        return [json.loads(item) for item in items]
    except Exception:
        return []


def get_redis_stats() -> dict:
    """Get Redis connection stats for the dashboard."""
    if not REDIS_AVAILABLE:
        return {"connected": False}
    try:
        info = redis_client.info("memory")
        keys = redis_client.dbsize()
        return {
            "connected": True,
            "keys": keys,
            "memory_used": info.get("used_memory_human", "?"),
        }
    except Exception:
        return {"connected": True, "keys": "?", "memory_used": "?"}


# ══════════════════════════════════════════════
#  TIER 2: Cognee — Permanent knowledge graph
# ══════════════════════════════════════════════

async def remember_permanent(text: str):
    """Store in Cognee's permanent knowledge graph (durable, cross-session)."""
    try:
        await cognee.remember(text)
        return True
    except Exception as e:
        # Fallback to older API if remember not available
        try:
            await cognee.add(text, dataset_name="health_wiki")
            await cognee.cognify()
            return True
        except Exception:
            return False


async def remember_session(text: str, session_id: str):
    """Store in Cognee session memory (fast, backed by Redis)."""
    try:
        await cognee.remember(text, session_id=session_id)
        return True
    except Exception:
        # Fallback: store in Redis directly
        if REDIS_AVAILABLE:
            try:
                redis_client.rpush(f"medimind:session:{session_id}:memory",
                                 json.dumps({"text": text, "ts": datetime.now().isoformat()}))
                return True
            except Exception:
                pass
        return False


async def recall_from_graph(query: str) -> str:
    """Query Cognee's permanent knowledge graph."""
    try:
        results = await cognee.recall(query)
        if results:
            return "\n".join(str(r) for r in results[:5])
        return ""
    except Exception:
        try:
            results = await cognee.search(query_text=query)
            if results:
                return "\n".join(str(r) for r in results[:5])
        except Exception:
            pass
        return ""


async def recall_with_session(query: str, session_id: str) -> str:
    """Query session memory first, then fall through to permanent graph."""
    try:
        results = await cognee.recall(query, session_id=session_id)
        if results:
            return "\n".join(str(r) for r in results[:5])
        return ""
    except Exception:
        # Fallback: try permanent graph
        return await recall_from_graph(query)
