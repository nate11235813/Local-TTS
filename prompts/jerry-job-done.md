# Jerry Job Done

When Nate asks for a "job done" line:

1. Generate one new line in a dry, observational-comedy tone.
2. Keep it short: 1 sentence, 10-18 words.
3. Start with `Nate,`.
4. Light teasing only. No profanity, insults, or personal attacks.
5. Make it different from previous lines in this session.

Then run this command with the generated line in `LINE`:

```bash
cd /Users/nhunt/Documents/GitHub/Local-TTS && LINE='Nate, job done. You called it a process, but it looked like vibes and panic.' && curl -sS -X POST "http://127.0.0.1:8000/v1/audio/speech" -H "Content-Type: application/json" -d "$(python3 - <<'PY'
import json, os
print(json.dumps({
    "input": os.environ["LINE"],
    "voice": "default",
    "response_format": "wav",
    "exaggeration": 0.75
}))
PY
)" --output /tmp/job_done.wav && afplay /tmp/job_done.wav
```
