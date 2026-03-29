# PKScreener Dashboard

Auto-updating NSE stock screener dashboard hosted on GitHub Pages.
Scans run automatically at **8:30 AM** and **3:45 PM IST** on weekdays.

## Live Dashboard
👉 `https://[YOUR-USERNAME].github.io/pkscreener-dashboard/dashboard.html`

---

## One-Time Setup (15 minutes)

### Step 1 — Create the GitHub Repo

1. Go to [github.com](https://github.com) and log in
2. Click **New repository**
3. Name it: `pkscreener-dashboard`
4. Set to **Public** (required for free GitHub Pages)
5. Click **Create repository**

---

### Step 2 — Upload These Files

Upload all these files to your repo root:
```
pkscreener-dashboard/
├── dashboard.html        ← your UI dashboard
├── scan.py               ← runs PKScreener scans
├── inject.py             ← injects data into HTML
├── data.json             ← auto-generated, commit an empty one first
└── .github/
    └── workflows/
        └── scan.yml      ← automation schedule
```

To upload: Go to your repo → **Add file** → **Upload files**

For the `.github/workflows/` folder, you need to create it via GitHub's web editor:
1. Click **Add file** → **Create new file**
2. Type `.github/workflows/scan.yml` as the filename
3. Paste the contents of `scan.yml`
4. Click **Commit**

---

### Step 3 — Enable GitHub Pages

1. Go to your repo → **Settings** → **Pages**
2. Under **Source**: select `Deploy from a branch`
3. Branch: `main` | Folder: `/ (root)`
4. Click **Save**
5. Wait 2 minutes — your URL will appear:
   `https://[your-username].github.io/pkscreener-dashboard/`

---

### Step 4 — Create Empty data.json

Create a file called `data.json` in your repo with this content:
```json
{"stocks": [], "total": 0, "timestamp": "Pending first scan", "market": {}}
```

---

### Step 5 — Trigger First Scan Manually

1. Go to your repo → **Actions** tab
2. Click **PKScreener Auto Scan** on the left
3. Click **Run workflow** → **Run workflow**
4. Watch it run (takes ~3-5 minutes)
5. After it finishes, open your GitHub Pages URL

---

## Access From Anywhere

Once set up, open this URL from **any device, any laptop, anywhere**:
```
https://[your-username].github.io/pkscreener-dashboard/dashboard.html
```

No installation needed. Just a browser.

---

## Schedule

| Time (IST) | Session | Days |
|---|---|---|
| 8:30 AM | Pre-Market | Mon–Fri |
| 3:45 PM | Post-Market | Mon–Fri |

You can also trigger manually anytime from the **Actions** tab.

---

## Troubleshooting

**Scan ran but no stocks showing?**
PKScreener output format may differ — check the Actions log for details.

**GitHub Actions failing?**
Go to Actions tab → click the failed run → read the error log.

**GitHub Pages not loading?**
Wait 5 minutes after enabling Pages. Clear browser cache.
