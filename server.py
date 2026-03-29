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
import threading

IST = timezone(timedelta(hours=5, minutes=30))

# Global error log storage
LOGS = []
MAX_LOGS = 100
SCAN_LOCK = threading.Lock()

SCAN_STATE = {
    "status": "idle",   # idle | running | completed | failed
    "started": None,
    "completed": None,
    "error": None,
    "stocks_found": 0,
}


class ThreadingHTTPServer(HTTPServer):
    daemon_threads = True

def log_event(level, message, details=""):
    """Log events to both console and memory."""
    now = datetime.now(IST).strftime("%H:%M:%S")
    log_entry = {
        "timestamp": now,
        "level": level,
        "message": message,
        "details": details
    }
    LOGS.append(log_entry)
    if len(LOGS) > MAX_LOGS:
        LOGS.pop(0)
    
    prefix = f"[{level}]" if level != "INFO" else "[+]"
    print(f"{prefix} {message}", file=sys.stderr if level == "ERROR" else sys.stdout)
    if details:
        print(f"    {details}", file=sys.stderr if level == "ERROR" else sys.stdout)

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
    log_event("INFO", f"Running PKScreener scan: {option}")
    
    # Patch MenuOptions.py before running
    try:
        import site
        from pathlib import Path
        site_packages = site.getsitepackages()[0]
        menu_file = os.path.join(site_packages, "pkscreener", "classes", "MenuOptions.py")
        
        if os.path.exists(menu_file):
            with open(menu_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Apply the patch if not already applied
            if "self.is_subscription_enabled = bool(int(" in content and "# PATCHED" not in content:
                patched = content.replace(
                    "self.is_subscription_enabled = bool(int(PKEnvironment().SUBSCRIPTION_ENABLED))",
                    "self.is_subscription_enabled = False  # PATCHED"
                )
                with open(menu_file, "w", encoding="utf-8") as f:
                    f.write(patched)
                log_event("INFO", "Applied MenuOptions.py patch")
    except Exception as e:
        log_event("WARN", "Failed to patch MenuOptions.py", str(e))
    
    try:
        result = subprocess.run(
            ["py", "-3.11", "-m", "pkscreener.pkscreenercli",
             "--testbuild", "--systemlaunched", "-e", "-o", option, "-a", "Y"],
            capture_output=True, text=True, timeout=120, cwd=os.path.dirname(os.path.abspath(__file__))
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            log_event("WARN", f"PKScreener returned non-zero exit code: {result.returncode}")
        if output:
            log_event("INFO", f"PKScreener output received ({len(output)} bytes)")
        else:
            log_event("WARN", "PKScreener returned empty output")
        return output
    except subprocess.TimeoutExpired:
        log_event("ERROR", "PKScreener scan timed out", "Timeout after 120 seconds")
        return ""
    except Exception as e:
        log_event("ERROR", "PKScreener execution failed", str(e))
        return ""

def parse_output(raw, scan_type):
    stocks = []
    lines_parsed = 0
    errors = []
    
    # Log first 30 lines for debugging
    first_lines = raw.split("\n")[:30]
    log_event("DEBUG", f"PKScreener output first 30 lines:", "\n".join(first_lines[:5]))
    
    for line_num, line in enumerate(raw.split("\n"), 1):
        stripped = line.strip()
        if not stripped:
            continue
        
        # Debug: log first 10 non-empty lines
        if line_num <= 10:
            log_event("DEBUG", f"Line {line_num}: {stripped[:100]}")
        
        parts = re.split(r'\s{2,}|\t', stripped)
        if len(parts) < 6:
            continue
        
        symbol = parts[0].strip()
        
        # Debug symbol extraction
        if line_num <= 10 and symbol:
            log_event("DEBUG", f"Extracted symbol '{symbol}'", f"Full parts: {parts[:3]}")
        
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
            lines_parsed += 1
        except (ValueError, IndexError) as e:
            errors.append(f"Line {line_num}: {str(e)}")
            continue
    
    log_event("INFO", f"Parse result", f"Found {len(stocks)} stocks from {lines_parsed} matching lines. Total lines: {len(raw.split(chr(10)))}")
    if errors and len(stocks) == 0:
        log_event("WARN", "Parse errors occurred", "; ".join(errors[:5]))
    
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
            if not SCAN_LOCK.acquire(blocking=False):
                body = json.dumps({
                    "error": "A scan is already running. Please wait for it to finish.",
                    "stocks": [],
                    "total": 0,
                }).encode()
                self.send_response(429)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            index = params.get('index',['12'])[0]
            scan  = params.get('scan', ['7'])[0]

            scan_map = {
                '7':'BREAKOUT','29':'EMA','42':'BTST',
                '6':'VOLUME','3':'REVERSAL','1':'MA_CROSS',
                '9':'RSI','11':'MOMENTUM'
            }
            scan_type = scan_map.get(scan, 'SCAN')

            SCAN_STATE.update({"status": "running", "started": datetime.now(IST).strftime("%H:%M:%S"), "completed": None, "error": None, "stocks_found": 0})
            try:
                raw    = run_pkscreener(index, scan)
                stocks = parse_output(raw, scan_type)
                market = get_market_data()
                now    = datetime.now(IST)
                SCAN_STATE.update({"status": "completed", "completed": now.strftime("%H:%M:%S"), "stocks_found": len(stocks)})

                result = {
                    "timestamp": now.strftime("%d %b %Y %I:%M %p IST"),
                    "session":   "Pre-Market" if now.hour < 12 else "Post-Market",
                    "market":    market,
                    "stocks":    stocks,
                    "total":     len(stocks),
                    "buy_count": len([s for s in stocks if s["signal"]=="BUY"]),
                    "watch_count":len([s for s in stocks if s["signal"]=="WATCH"]),
                    "avoid_count":len([s for s in stocks if s["signal"]=="AVOID"]),
                    "errors": [l for l in LOGS if l["level"] in ("ERROR", "WARN")],
                    "debug_output": raw[:1500] if raw else "No output from PKScreener",
                    "all_logs": LOGS[-10:],
                }

                body = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Access-Control-Allow-Origin','*')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as scan_err:
                SCAN_STATE.update({"status": "failed", "error": str(scan_err), "completed": datetime.now(IST).strftime("%H:%M:%S")})
                raise
            finally:
                SCAN_LOCK.release()

        elif parsed.path == '/health':
            body = json.dumps({
                "status": "ok",
                "scan_state": SCAN_STATE["status"],
                "scan_started": SCAN_STATE["started"],
                "scan_completed": SCAN_STATE["completed"],
                "stocks_found": SCAN_STATE["stocks_found"],
            }).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == '/status':
            body = json.dumps(SCAN_STATE).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == '/logs':
            body = json.dumps({"logs": LOGS}).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(body)

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
    server = ThreadingHTTPServer(('localhost', port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Server stopped.")
