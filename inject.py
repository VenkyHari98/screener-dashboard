"""
inject.py
Reads data.json produced by scan.py and injects it into dashboard.html
so the final HTML file is fully self-contained with fresh data.
"""

import json
import os
import re

DATA_FILE      = "data.json"
TEMPLATE_FILE  = "dashboard.html"
OUTPUT_FILE    = "dashboard.html"

def main():
    if not os.path.exists(DATA_FILE):
        print("[!] data.json not found. Run scan.py first.")
        return

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Inject the data as a JS variable right before </script> closing tag
    injection = f"""
// ─── INJECTED BY GITHUB ACTIONS ──────────────────────────────────────────────
const LIVE_DATA = {json.dumps(data, indent=2)};

// Override SAMPLE_DATA with live data on page load
window.addEventListener('DOMContentLoaded', function() {{
  // Update market values
  if (LIVE_DATA.market && LIVE_DATA.market.nifty) {{
    document.getElementById('niftyVal').textContent  = LIVE_DATA.market.nifty.toLocaleString('en-IN', {{minimumFractionDigits:2}});
    document.getElementById('sensexVal').textContent = LIVE_DATA.market.sensex.toLocaleString('en-IN', {{minimumFractionDigits:2}});
    const nChg = LIVE_DATA.market.niftyChg;
    const sChg = LIVE_DATA.market.sensexChg;
    document.getElementById('niftyChg').textContent  = (nChg >= 0 ? '+' : '') + nChg.toFixed(2) + '%';
    document.getElementById('sensexChg').textContent = (sChg >= 0 ? '+' : '') + sChg.toFixed(2) + '%';
    document.getElementById('niftyChg').style.color  = nChg >= 0 ? 'var(--bull)' : 'var(--bear)';
    document.getElementById('sensexChg').style.color = sChg >= 0 ? 'var(--bull)' : 'var(--bear)';
  }}

  // Update last updated timestamp
  document.getElementById('lastUpdated').textContent = 'Last scan: ' + LIVE_DATA.timestamp;

  // Add session badge
  const sessionBadge = document.createElement('span');
  sessionBadge.textContent = LIVE_DATA.session;
  sessionBadge.style.cssText = 'font-size:10px;padding:2px 8px;border-radius:4px;background:rgba(0,212,170,0.15);color:var(--accent);font-family:var(--font-mono);margin-left:8px;';
  document.getElementById('lastUpdated').appendChild(sessionBadge);

  // Load stock data
  currentData = LIVE_DATA.stocks;
  renderTable(currentData);

  // Update scan tag
  const scanTags = LIVE_DATA.scan_summary.map(s => s.label + ' (' + s.count + ')').join(' · ');
  document.getElementById('scanTag').textContent = scanTags;
  document.getElementById('resultsMeta').textContent =
    LIVE_DATA.total + ' stocks · ' + LIVE_DATA.date;
}});
// ─────────────────────────────────────────────────────────────────────────────
"""

    # Insert injection just before the closing </script> tag at the end
    html = html.replace("// ── INIT ──────────────────────────────────────────────────────────────────────",
                        injection + "\n// ── INIT ──────────────────────────────────────────────────────────────────────")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[+] Injected {data['total']} stocks into {OUTPUT_FILE}")
    print(f"[+] Session: {data['session']} | {data['timestamp']}")

if __name__ == "__main__":
    main()
