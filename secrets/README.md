# secrets/

Local key files that must never be committed. Everything here except this README is gitignored.

| File | Used for | Needed? |
|---|---|---|
| `gcp-tts-sa.json` | Google Cloud Text-to-Speech service account (talk-mode audio) | Optional. Without it, talk mode answers in text only. |

Docker Compose mounts this folder read-only into the gateway at `/run/secrets/vario`. Ask a maintainer for the key file; don't share it in chat or commit it.
