"""Download prices and exchange rates for FXFix.

Usage: python scripts/fetch.py [OUTPUT_DIR]   (default: docs/data)

Prices come from Yahoo Finance's chart API: dividend- and split-adjusted daily
closes since 2010, plus the latest session at 5-minute intervals. Exchange rates
are the European Central Bank's daily reference rates via frankfurter.dev.
Writes one JSON file per ticker, fx.json and index.json.
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "docs", "data")
START = dt.datetime(2010, 1, 1, tzinfo=dt.timezone.utc)
UA = {"User-Agent": "Mozilla/5.0 (FXFix data build)"}
HOSTS = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]


def tickers():
    with open(os.path.join(ROOT, "tickers.txt")) as f:
        out = []
        for line in f:
            t = line.split("#")[0].strip().upper()
            if t and t not in out:
                out.append(t)
        return out


def get(url, tries=5):
    err = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            err = e
        except Exception as e:
            err = e
        time.sleep(3 * (i + 1))
    raise err


def chart(t, query):
    err = None
    for h in HOSTS:
        try:
            return get(f"https://{h}/v8/finance/chart/{t}?{query}")["chart"]["result"][0]
        except Exception as e:
            err = e
    raise err


def listing(t, p1, p2):
    d = chart(t, f"period1={p1}&period2={p2}&interval=1d&events=div,split&includeAdjustedClose=true")
    m, ts = d["meta"], d["timestamp"]
    adj = d["indicators"]["adjclose"][0]["adjclose"]
    vol = d["indicators"]["quote"][0]["volume"]
    off = m.get("gmtoffset", 0)
    rows = {}
    for a, b, v in zip(ts, adj, vol):
        if b is None:
            continue
        day = dt.datetime.fromtimestamp(a + off, dt.timezone.utc).strftime("%Y-%m-%d")
        rows[day] = [float(f"{b:.5g}"), int(v or 0)]
    days = sorted(rows)
    cur, scale = m["currency"], 1
    if cur in ("GBp", "GBX"):  # London quotes in pence
        cur, scale = "GBP", 100
    if cur == "ZAc":
        cur, scale = "ZAR", 100
    intr = chart(t, "range=1d&interval=5m")
    q = intr["indicators"]["quote"][0]
    iv = [[a, float(f"{c:.6g}"), int(v or 0)]
          for a, c, v in zip(intr.get("timestamp") or [], q["close"], q["volume"]) if c is not None]
    return {
        "t": t, "name": m.get("longName") or m.get("shortName") or t, "cur": cur, "scale": scale,
        "ex": m.get("fullExchangeName", ""), "type": m.get("instrumentType", ""),
        "d": days, "p": [rows[x][0] for x in days], "v": [rows[x][1] for x in days],
        "intra": iv, "iprev": intr["meta"].get("chartPreviousClose") or intr["meta"].get("previousClose"),
    }


def fx():
    rates = {}
    for y in range(2010, dt.date.today().year + 1):
        r = get(f"https://api.frankfurter.dev/v1/{y}-01-01..{y}-12-31?base=EUR")
        rates.update(r["rates"])
    days = sorted(rates)
    # keep currencies still quoted today and present for most of the history
    curs = sorted(c for c in rates[days[-1]] if sum(c in rates[d] for d in days) > 0.9 * len(days))
    return {"base": "EUR", "d": days, "r": {c: [rates[d].get(c) for d in days] for c in curs}}


def main():
    os.makedirs(OUT, exist_ok=True)
    p1, p2 = int(START.timestamp()), int(time.time())
    index, failed = [], []
    for t in tickers():
        try:
            rec = listing(t, p1, p2)
            with open(os.path.join(OUT, f"{t}.json"), "w") as f:
                json.dump(rec, f, separators=(",", ":"))
            index.append({"t": t, "name": rec["name"], "cur": rec["cur"], "ex": rec["ex"],
                          "type": rec["type"], "from": rec["d"][0], "to": rec["d"][-1]})
            print(f"{t:12} {rec['cur']} {rec['d'][0]} → {rec['d'][-1]}")
        except Exception as e:
            failed.append(t)
            print(f"{t:12} FAILED: {e}", file=sys.stderr)
        time.sleep(0.5)
    f = fx()
    unknown = sorted({l["cur"] for l in index} - set(f["r"]) - {"EUR"})
    if unknown:
        print("No ECB rate for", unknown, "— dropping those listings", file=sys.stderr)
        index = [l for l in index if l["cur"] not in unknown]
    with open(os.path.join(OUT, "fx.json"), "w") as fh:
        json.dump(f, fh, separators=(",", ":"))
    built = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(os.path.join(OUT, "index.json"), "w") as fh:
        json.dump({"built": built, "listings": index}, fh, separators=(",", ":"))
    print(f"\n{len(index)} listings, {len(f['r']) + 1} currencies, ECB to {f['d'][-1]}. Failed: {failed or 'none'}")
    if len(index) < 0.8 * len(tickers()):
        sys.exit("Too many listings failed; not publishing this build.")


if __name__ == "__main__":
    main()
