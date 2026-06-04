# Job Autopilot

Scrapes LinkedIn, Indeed, and RemoteOK every 8 minutes. Analyzes each listing against your resume with Claude AI. Tailors your resume + writes a cover letter for every qualified job. Auto-applies via LinkedIn Easy Apply and Indeed Quick Apply.

---

## What it does

```
Every 8 minutes:
  1. Scrape LinkedIn + Indeed + RemoteOK for new listings
  2. Deduplicate (skip already-seen jobs)
  3. Claude scores each job against your resume (0-100)
  4. Jobs below your threshold → skipped
  5. Qualified jobs → Claude tailors your resume + writes cover letter
  6. Saves a PDF of the tailored resume
  7. Submits via LinkedIn Easy Apply or Indeed Quick Apply
  8. Logs everything to logs/ and SQLite DB
```

---

## Requirements

- Ubuntu 20.04+ (or any Linux VPS) — DigitalOcean, Linode, AWS EC2, etc.
- Python 3.10+
- Anthropic API key (get one at console.anthropic.com)
- LinkedIn and/or Indeed account

---

## Setup

### 1. Clone / upload to your server

```bash
scp -r job_autopilot/ user@your-server:~/
ssh user@your-server
cd ~/job_autopilot
```

### 2. Run setup

```bash
bash setup.sh
```

This installs all Python packages, Playwright + Chromium, and registers a systemd service.

### 3. Edit config.yaml

```yaml
anthropic_api_key: "sk-ant-..."     # required
linkedin:
  email: "you@email.com"
  password: "yourpassword"
job_search:
  keywords:
    - "Software Engineer"
    - "Python Developer"
  location: "Remote"
filters:
  min_match_score: 65               # only apply to 65%+ matches
```

### 4. Edit resume.txt

Replace the placeholder content with your actual resume in plain text.

### 5. Start

```bash
# Run directly (shows live logs)
python3 main.py

# Or as a background service (auto-restarts, survives reboots)
sudo systemctl start  job-autopilot
sudo systemctl enable job-autopilot   # start on boot
```

---

## Monitoring

```bash
# Live logs
tail -f logs/autopilot_$(date +%Y-%m-%d).log

# Service logs
sudo journalctl -u job-autopilot -f

# Stats (open Python shell)
python3 -c "from database import get_stats; import json; print(json.dumps(get_stats(), indent=2))"
```

---

## Database

All data is stored in `autopilot.db` (SQLite). Two tables:

| Table | What it stores |
|---|---|
| `jobs` | Every listing seen — title, company, URL, match score |
| `applications` | Every application — status, tailored resume, cover letter |

Query examples:
```sql
-- All applications
SELECT j.title, j.company, a.status, a.applied_at
FROM applications a JOIN jobs j ON j.id=a.job_id
ORDER BY a.applied_at DESC;

-- Top matches not yet applied
SELECT title, company, match_score, url FROM jobs
WHERE match_score >= 70
AND id NOT IN (SELECT job_id FROM applications)
ORDER BY match_score DESC;
```

---

## Tailored resumes

Each application generates a PDF saved to `resumes/`. Named like:
```
resumes/Software_Engineer_20250605_143022.pdf
```

---

## Notes on auto-apply

- **LinkedIn Easy Apply** — works best; standardized multi-step form
- **Indeed Quick Apply** — supported; varies by employer
- **Other sites** (RemoteOK, Greenhouse, Lever, etc.) — logged as "manual apply needed"; the tailored resume + cover letter are still generated and saved for you to apply manually
- Sites with CAPTCHAs may block headless browsers. If this happens, set `easy_apply_only: true` in config.yaml and stick to LinkedIn Easy Apply

---

## Cost estimate

Each job analysis = ~500 tokens. Resume tailoring = ~2000 tokens. Cover letter = ~700 tokens.
At 20 qualified jobs/day × 3 API calls = ~64k tokens/day ≈ $0.10–0.20/day.

---

## VPS recommendation

A $6/month DigitalOcean Droplet (1 vCPU, 1GB RAM) handles this easily.
```bash
# Quick DigitalOcean setup
doctl compute droplet create autopilot \
  --image ubuntu-22-04-x64 \
  --size s-1vcpu-1gb \
  --region nyc1
```
