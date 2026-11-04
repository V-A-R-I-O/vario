# Local Demo Runbook (laptop C)

How to run the whole VARIO stack on one laptop and open it from the other laptops. Written for **laptop C**: Windows 11, i5-13th-gen HX, 24 GB RAM, Docker Desktop. Any machine with Docker and about 12 GB free for Docker works the same way.

**The setup:**
- Laptop C runs everything in Docker: PostgreSQL, the gateway, the frontend, the four mock systems, and three Rasa servers with their action servers.
- The other laptops only open a browser at `http://<C's IP>:3000`.
- Port 3000 is the only one other machines need. The frontend forwards `/api` to the gateway, and every other port stays private to laptop C.

| Service | Port on laptop C | Reachable from other laptops |
|---|---|---|
| frontend (Next.js) | 3000 | **Yes**, this is the demo URL |
| gateway (FastAPI) | 127.0.0.1:8000, see [/docs](http://localhost:8000/docs) | No |
| postgres | 127.0.0.1:5432 (`POSTGRES_PORT`) | No |
| mock-auth / hrms / itsm / admissions | 127.0.0.1:9001–9004 | No |
| rasa-hr / rasa-it / rasa-admissions | 127.0.0.1:5005 / 5006 / 5007 | No |

---

## 1. One-time setup on laptop C

### 1.1 Give Docker enough memory

The three Rasa servers need most of the RAM. Docker Desktop on Windows runs inside WSL 2, and WSL 2 takes only part of the RAM by default.

1. Create or edit `C:\Users\<you>\.wslconfig`:
   ```ini
   [wsl2]
   memory=14GB
   processors=8
   swap=4GB
   ```
2. In PowerShell, run `wsl --shutdown`, then start Docker Desktop again.
3. Check it worked: `docker info --format "{{.MemTotal}}"` should show about 14 GB, in bytes.

### 1.2 Get the code

```powershell
git clone https://github.com/V-A-R-I-O/vario.git
cd vario
```

`.gitattributes` keeps the shell scripts in LF line endings, so the containers start even on a Windows checkout.

### 1.3 Create `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Fill in the two required values. Any long random string works; to generate one in PowerShell, run this twice and paste one result into each:

```powershell
[guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N")
```

| Variable | Required? | What it does |
|---|---|---|
| `JWT_SECRET` | **Yes**. Compose refuses to start without it. | Signs login tokens. |
| `RETRAINING_INTERNAL_TOKEN` | Recommended | Protects each Rasa server's API. The gateway uses it when an admin clicks **Retrain**. |
| `POSTGRES_PASSWORD` | Yes (already `vario`) | Local database password. |
| `GEMINI_API_KEY` | Optional | Lets admins generate response variants and training phrases. Without it, admins type them by hand. |
| `POSTGRES_PORT` | Only if 5432 is taken | For example `5433`, if a native PostgreSQL is installed. |

**Optional talk-mode audio:** put the Google Cloud Text-to-Speech service-account file at `secrets\gcp-tts-sa.json`. Without it, talk mode still works but answers in text only. Never commit that file; `secrets/` is gitignored.

### 1.4 Build the images and train the models

```powershell
docker compose build
```

The first run takes about 15–25 minutes. It builds every image, and each Rasa image **trains its model during the build**, so a fresh clone needs no separate training step. The models live inside the images.

Re-run `docker compose build` after every `git pull` that changes a role pack (`rasa-*`), the gateway or the frontend.

If the build dies with `Killed` while training, Docker ran out of memory. Raise `memory` in `.wslconfig`, or build the packs one at a time:

```powershell
docker compose build rasa-hr
docker compose build rasa-it
docker compose build rasa-admissions
```

---

## 2. Start the stack

```powershell
docker compose up -d
docker compose ps
```

Wait until every service shows `healthy`. The Rasa servers take 1–2 minutes to load their models.

On the first start, the gateway migrates the database and seeds it with intents, templates and demo data. Later starts skip anything that already exists, so nothing is duplicated.

**Smoke test on laptop C:** open <http://localhost:3000>, log in as `emp1@org.example.com` / `password123`, and try one message per pack (see §5).

To stop the stack:
- `docker compose stop` keeps everything for the next `docker compose start`.
- `docker compose down` removes the containers but keeps the data volumes.

---

## 3. Let the other laptops in

### 3.1 Join the same network

All laptops must be on the same network as laptop C.

- **Phone hotspot (recommended):** connect all four laptops to one phone's hotspot.
- **Laptop C's own hotspot:** Settings → Network & internet → Mobile hotspot → On. Laptop C is then usually `192.168.137.1`.
- **College Wi-Fi:** often blocks laptops from reaching each other (client isolation). Test it first (§3.4). If it fails, switch to a hotspot.

### 3.2 Find laptop C's IP

```powershell
ipconfig
```

Use the **IPv4 Address** under the Wi-Fi adapter (or the hotspot adapter), for example `192.168.43.25`.

### 3.3 Allow port 3000 through Windows Firewall

Run PowerShell **as Administrator** once:

```powershell
New-NetFirewallRule -DisplayName "VARIO demo (3000)" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow -Profile Private
```

Then mark the network as private: Settings → Network & internet → Wi-Fi → (your network) → Network profile type → **Private**.

If you must stay on a network Windows treats as Public, add `-Profile Private,Public` to the rule, and remove the rule after the demo:

```powershell
Remove-NetFirewallRule -DisplayName "VARIO demo (3000)"
```

### 3.4 Test from another laptop

Open `http://<C's IP>:3000` in Chrome or Edge on another laptop. You should see the login page.

If it doesn't load, work through these in order:
- Check both laptops are on the same network.
- Check the firewall rule from §3.3.
- On laptop C, check `docker compose ps` shows the frontend healthy.
- Try a hotspot instead of college Wi-Fi.

### 3.5 The microphone (talk mode) on other laptops

Browsers only allow the microphone on `https://` pages or on `localhost`. On `http://<C's IP>:3000`, the mic button won't work until you do **one** of the following. Text chat works either way.

- **Chrome/Edge flag (simplest, per client laptop):**
  1. Open `chrome://flags/#unsafely-treat-insecure-origin-as-secure` (Edge: `edge://flags/...`).
  2. Enter `http://<C's IP>:3000` and set the flag to **Enabled**.
  3. Click **Relaunch**.
- **Cloudflare Quick Tunnel (optional, gives an HTTPS URL):** on laptop C, install `cloudflared` (`winget install --id Cloudflare.cloudflared`) and run:
  ```powershell
  cloudflared tunnel --url http://localhost:3000
  ```
  It prints a `https://<random>.trycloudflare.com` URL that works from any device with internet. No account is needed, the URL changes on every run, and it stops when you close the window.

  The tunnel needs internet on laptop C and on the device, so let the LAN laptops keep using `http://<C's IP>:3000`.

Chrome's speech recognition needs internet on the client laptop, even when VARIO itself is local.

---

## 4. Demo accounts

Every account's password is `password123`.

| Login | Who | Role | Notes |
|---|---|---|---|
| `emp1@org.example.com` | Employee One (EMP-1001) | Employee | IT security answer: `sunrise` |
| `pavan@org.example.com` | Pavan Kishor (EMP-1010) | Employee | IT security answer: `north campus` |
| `tahir@org.example.com` | Tahir (EMP-1011) | Employee | IT security answer: `north campus` |
| `rohith@org.example.com` | Rohith (EMP-1012) | Employee | IT security answer: `north campus` |
| `mitesh@org.example.com` | Mitesh (EMP-1013) | Employee | IT security answer: `north campus` |
| `applicant@org.example.com` | Applicant One (APP-2026-001) | Applicant | Admissions applications to look up: `APP-1001`…`APP-1004` |
| `hr@org.example.com` | HR Admin | Admin console, HR pack | |
| `it@org.example.com` | IT Admin | Admin console, IT pack | |
| `admissions@org.example.com` | Admissions Admin | Admin console, Admissions pack | |

Any signed-in user can chat with all three packs. HR and IT answer "my …" questions for the signed-in employee only.

Give each presenter their own login. Login attempts are limited per account (10 a minute), and chat per signed-in user, so presenters don't block each other. See `docs/demo/it-demo-accounts.md` for the ITSM fixture details.

---

## 5. Quick check per pack

| Pack | Try | Expect |
|---|---|---|
| HR | "what's my leave balance" | A balance card for the signed-in employee |
| HR | "apply for sick leave" → pick dates → reason → **Confirm** | A request ID; "cancel" at any step stops it |
| HR | "what is the maternity leave policy" | The maternity policy answer |
| IT | "my laptop screen is broken" → Hardware → description → **Confirm** | A ticket `IT-####` |
| IT | "what is the status of ticket IT-1002" | A status card |
| IT | "I forgot my password" → your employee ID (e.g. `EMP-1012`) → `north campus` | A reset for the signed-in account; the answer is never stored |
| Admissions | "what is the status of application APP-1001" | A status card |
| Admissions | "what documents do I need for btech" | A checklist |
| Admissions | "when is the last date to pay fees" | The fee deadlines |
| Admin | Log in as `hr@…` → Intents → new FAQ → **Retrain** → ask it as an employee | Answered after 1–3 minutes of training |

---

## 6. Reset between rehearsals

| What | Command |
|---|---|
| Everything: database, chat history, Rasa trackers, retrained models, ITSM attempts. The next `up` re-seeds. | `docker compose down -v` then `docker compose up -d` |
| Leave requests only (mock-HRMS keeps them in memory) | `docker compose restart mock-hrms` |
| Tickets only | `docker compose restart mock-itsm` |
| Just restart a pack | `docker compose restart rasa-hr` |

**Retrained models:** they live in each pack's volume (`rasa-hr-data`, etc.) and survive restarts. After a rebuild, the freshly trained image model takes over again. If an admin-created FAQ stops being answered after a rebuild, click **Retrain** once more; the FAQ is still in the database.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `required variable JWT_SECRET is missing a value` | `.env` is missing or `JWT_SECRET` is empty. See §1.3. |
| `Bind for 127.0.0.1:5432 failed: port is already allocated` | Set `POSTGRES_PORT=5433` (or any free port) in `.env`, then run `docker compose up -d` again. Do the same for `API_PORT` / `FRONTEND_PORT` if those clash. |
| A chat answers "The HR assistant is unavailable right now" | That Rasa server isn't ready or has crashed. Check `docker compose ps`, then `docker compose logs --tail 100 rasa-hr`. Right after `up`, wait 1–2 minutes. |
| A Rasa server keeps restarting | Usually out of memory. Raise `.wslconfig` memory (§1.1), then `docker compose up -d`. |
| `No trained model in this image` | The image was built without training. Run `docker compose build rasa-<pack>`. |
| `Rate limit exceeded` on login | 10 login attempts per minute per account (60 per minute in total through the proxy). Wait a minute. |
| Retrain stays **failed** | Check `docker compose logs gateway` and `docker compose logs rasa-<pack>`. The token is shared automatically from `RETRAINING_INTERNAL_TOKEN`. If you changed it, run `docker compose up -d` so every service gets the new value. |
| `exec ./docker-entrypoint.sh: no such file or directory` | The scripts were checked out with CRLF line endings. Run `git config core.autocrlf false`, then `git rm --cached -r . ; git reset --hard`, and rebuild. |
| Other laptops can't open the page | Work through §3.4. |
| Mic button does nothing on a client laptop | See §3.5 (flag or tunnel). Text chat still works. |
| Want to see the API directly | <http://localhost:8000/docs> on laptop C. |

To see what a service is doing: `docker compose logs -f gateway`, or any service name from `docker compose ps`.
