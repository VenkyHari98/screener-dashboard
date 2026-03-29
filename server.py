"""
server.py — Local scan server for India Stock Screener dashboard
Run this on your home laptop alongside the dashboard.
The HTML dashboard auto-detects localhost and calls this server.

Usage:
    python server.py

Then open:
    dashboard.html in your browser (double-click or use Live Server in VSCode)

The dashboard will call http://localhost:5000/scan?index=12&scan=7
"""

import json
import subprocess
import sys
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def get_market_data():
    try:
        import yfinance as yf
        ni = yf.Ticker("^NSEI").fast_info
        se = yf.Ticker("^BSESN").fast_info
        return {
            "nifty":     round(ni.last_price, 2),
            "niftyChg":  round(((ni.last_price - ni.previous_close) / ni.previous_close) * 100, 2),
            "sensex":    round(se.last_price, 2),
            "sensexChg": round(((se.last_price - se.previous_close) / se.previous_close) * 100, 2),
        }
    except Exception:
        return {"nifty": 0, "niftyChg": 0, "sensex": 0, "sensexChg": 0}

def run_pkscreener(index, scan):
    option = f"X:{index}:{scan}"
    print(f"[+] Running PKScreener: {option}")
    try:
        result = subprocess.run(
            ["pkscreener", "--testbuild", "-o", option, "-a", "Y"],
            capture_output=True, text=True, timeout=300
        )
        return result.stdout + result.stderr
    except Exception as e:
        print(f"[!] Error: {e}")
        return ""

def parse_output(raw, scan_type):
    stocks = []
    for line in raw.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        parts = re.split(r'\s{2,}|\t', stripped)
        if len(parts) < 6:
            continue
        symbol = parts[0].strip()
        if not re.match(r'^[A-Z&]{2,20}$', symbol):
            continue
        if symbol in ('STOCK','SYMBOL','NAME','SCRIP'):
            continue
        try:
            ltp  = float(re.sub(r'[^\d.]', '', parts[1])) if len(parts)>1 else 0
            chg  = float(re.sub(r'[^\d.\-]','', parts[2])) if len(parts)>2 else 0
            vol  = float(re.sub(r'[^\d.]', '', parts[3])) if len(parts)>3 else 1.0
            rsi  = float(re.sub(r'[^\d.]', '', parts[5])) if len(parts)>5 else 50.0
            w52h = float(re.sub(r'[^\d.]', '', parts[4])) if len(parts)>4 else ltp*1.2
            w52l = ltp * 0.7
            signal = "BUY" if chg>0 and rsi>50 else ("AVOID" if chg<-1 else "WATCH")
            d1 = round(chg*0.6+(rsi-50)*0.05, 1)
            d2 = round(d1*1.4, 1)
            stocks.append({
                "stock": symbol, "sector": "NSE",
                "ltp": round(ltp,2), "chg": round(chg,2),
                "vol": round(vol,1), "w52l": round(w52l,2), "w52h": round(w52h,2),
                "rsi": round(rsi,1), "pattern": scan_type,
                "signal": signal, "d1": d1, "d2": d2, "scan": scan_type,
            })
        except (ValueError, IndexError):
            continue
    return stocks

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET,OPTIONS')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == '/scan':
            index = params.get('index',['12'])[0]
            scan  = params.get('scan', ['7'])[0]

            scan_map = {
                '7':'BREAKOUT','29':'EMA','42':'BTST',
                '6':'VOLUME','3':'REVERSAL','1':'MA_CROSS',
                '9':'RSI','11':'MOMENTUM'
            }
            scan_type = scan_map.get(scan, 'SCAN')

            raw    = run_pkscreener(index, scan)
            stocks = parse_output(raw, scan_type)
            market = get_market_data()
            now    = datetime.now(IST)

            result = {
                "timestamp": now.strftime("%d %b %Y %I:%M %p IST"),
                "session":   "Pre-Market" if now.hour < 12 else "Post-Market",
                "market":    market,
                "stocks":    stocks,
                "total":     len(stocks),
                "buy_count": len([s for s in stocks if s["signal"]=="BUY"]),
                "watch_count":len([s for s in stocks if s["signal"]=="WATCH"]),
                "avoid_count":len([s for s in stocks if s["signal"]=="AVOID"]),
            }

            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(json.dumps({"status":"ok","mode":"local"}).encode())

        elif parsed.path in ('/', '/dashboard.html'):
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dashboard.html')
            if os.path.exists(html_path):
                with open(html_path, 'r', encoding='utf-8') as f:
                    body = f.read().encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'dashboard.html not found')

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        now = datetime.now(IST).strftime("%H:%M:%S")
        print(f"[{now}] {fmt % args}")

if __name__ == "__main__":
    port = 5000
    print(f"""
╔══════════════════════════════════════════════════╗
║     India Stock Screener — Local Server          ║
║     http://localhost:{port}                        ║
║                                                  ║
║     Open dashboard.html in your browser          ║
║     Unlimited scans · No GitHub Actions used     ║
╚══════════════════════════════════════════════════╝
""")
    server = HTTPServer(('localhost', port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Server stopped.")
