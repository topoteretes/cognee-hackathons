# Hooks

Hooks are small ingestion or transformation entry points used by the wiki agent.

## User Preference Profile

`user_preference_profile.py` turns user/community text into a structured Linux preference profile.
It captures technical level, workloads, interests, hardware, comfort level, and Linux preferences.

It is designed for the hackathon memory loop:

```text
conversation or community message
        ↓
profile extraction hook
        ↓
Redis profile record
        ↓
personalized discovery/debug/customization answer
```

Create or overwrite a profile with JSON lines on standard input:

```bash
printf '%s\n' '{"text":"I am a programmer and video editor. I like theming, Wayland, and low maintenance."}' \
  | python hooks/user_preference_profile.py create --user-id demo
```

Run this hook directly with `python hooks/user_preference_profile.py`.
Do not wrap it with project runners such as `uv run`.

For Upstash, use the REST credentials from your Upstash Redis database:

```bash
export UPSTASH_REDIS_REST_URL="https://..."
export UPSTASH_REDIS_REST_TOKEN="..."
```

The hook uses `python-dotenv` to load these values from `.env` or `hooks/.env`.

When both Upstash env vars are set, the hook writes the profile to Upstash.

Without Upstash credentials, the hook prints the profile JSON.

The hook also writes a brief Markdown summary to `wiki/profile/<profile-id>.md`.
Redis remains the source of truth for full profile data.

Manage stored profiles with the profile command:

```bash
python hooks/user_preference_profile.py select demo
python hooks/user_preference_profile.py get
python hooks/user_preference_profile.py list
python hooks/user_preference_profile.py delete demo
```
