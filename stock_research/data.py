from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.parse import quote
from email.utils import parsedate_to_datetime
from .compatibility import ROOT

def target_week(as_of: str) -> dict:
    import exchange_calendars as xc
    day = datetime.fromisoformat(as_of).astimezone(ZoneInfo("America/New_York")).date()
    monday = day + timedelta(days=7-day.weekday())
    sessions = xc.get_calendar("XNYS").sessions_in_range(str(monday), str(monday+timedelta(days=6)))
    return {"start": str(sessions[0].date()), "end": str(sessions[-1].date()), "sessions": len(sessions)}

def indicators(rows: list[dict]) -> dict:
    import pandas as pd
    if len(rows) < 61:
        raise ValueError("need at least 61 complete daily bars")
    df = pd.DataFrame(rows)
    values = df[["open","high","low","close","volume"]].astype(float)
    if values.isna().any().any() or (values.volume < 0).any() or values.volume.tail(20).mean() <= 0:
        raise ValueError("invalid OHLCV/missing volume")
    if (values.high < values[["open","close","low"]].max(axis=1)).any() or (values.low > values[["open","close","high"]].min(axis=1)).any():
        raise ValueError("inconsistent high/low bars")
    close = df.close.astype(float)
    if close.isna().any() or (close <= 0).any() or len(set(df.date)) != len(df):
        raise ValueError("invalid or duplicate bars")
    if list(df.date) != sorted(df.date):
        raise ValueError("bars must be ordered")
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False, min_periods=14).mean().iloc[-1]
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False, min_periods=14).mean().iloc[-1]
    rsi = 100 if loss == 0 and gain > 0 else (50 if loss == 0 else 100-100/(1+gain/loss))
    tr = pd.concat([df.high-df.low, (df.high-close.shift()).abs(), (df.low-close.shift()).abs()], axis=1).max(axis=1)
    result = {"last_close": close.iloc[-1], "sma20": close.tail(20).mean(), "sma60": close.tail(60).mean(),
              "rsi14": rsi, "atr14": tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean().iloc[-1],
              "return_5d": close.iloc[-1]/close.iloc[-6]-1, "return_20d": close.iloc[-1]/close.iloc[-21]-1,
              "volume_ratio20": float(df.volume.iloc[-1])/float(df.volume.tail(20).mean()),
              "first_bar": df.date.iloc[0], "last_bar": df.date.iloc[-1], "count": len(df)}
    return {k: round(float(v), 6) if isinstance(v, (int, float)) or hasattr(v, "item") else v for k,v in result.items()}

def load_bundle(mode: str, ticker: str, refresh: bool = False) -> dict:
    if mode == "fixture":
        bundle = json.loads((ROOT / "data/fixtures/demo.json").read_text())
        if ticker != bundle["ticker"]:
            raise ValueError("fixture only supports DEMO; use --mode live for real tickers")
    else:
        import yfinance as yf
        import exchange_calendars as xc
        import pandas as pd
        now = datetime.now(ZoneInfo("America/New_York"))
        cache = ROOT / "data/cache" / f"{ticker}-{now.date()}.json"
        if cache.exists() and not refresh:
            cached = json.loads(cache.read_text())
            cached["indicators"] = indicators(cached["prices"])
            cached["target_week"] = target_week(cached["as_of"])
            cached["sha256"] = hashlib.sha256(json.dumps(cached, sort_keys=True).encode()).hexdigest()
            return cached
        hist = yf.Ticker(ticker).history(period="1y", auto_adjust=True)
        calendar = xc.get_calendar("XNYS")
        rows = []
        for stamp, row in hist.iterrows():
            d = str(stamp.date())
            if not calendar.is_session(d) or calendar.session_close(d) > pd.Timestamp(now):
                continue
            rows.append({"date":d, **{k.lower():float(row[k]) for k in ["Open","High","Low","Close","Volume"]}})
        if not rows:
            raise ValueError("provider returned no complete bars")
        expected = calendar.sessions_in_range(str(now.date()-timedelta(days=14)), str(now.date()))
        complete = [s for s in expected if calendar.session_close(s) <= pd.Timestamp(now)]
        if not complete or rows[-1]["date"] != str(complete[-1].date()):
            raise ValueError("provider's latest bar is stale; refusing to label it live")
        rows = rows[-126:]
        news, warnings = [], []
        try:
            url = "https://news.google.com/rss/search?q="+quote(ticker+" stock when:7d")+"&hl=en-US&gl=US&ceid=US:en"
            with urlopen(Request(url,headers={"User-Agent":"ADK-Skills-Workshop/0.1"}), timeout=20) as response:
                xml = ET.fromstring(response.read(500_000))
            for item in xml.findall("./channel/item"):
                published = parsedate_to_datetime(item.findtext("pubDate", ""))
                if now-timedelta(days=7) <= published <= now:
                    news.append({"id":f"N{len(news)+1}", "title":item.findtext("title"), "url":item.findtext("link"), "published_at":published.isoformat(),"headline_only":True,"publisher":item.findtext("source")})
                if len(news) >= 5: break
        except Exception as exc:
            warnings.append(f"news unavailable: {type(exc).__name__}")
        if not news: warnings.append("No eligible news; event analysis must report missing evidence")
        else: warnings.append("Google News RSS headlines only; full articles not verified, do not treat headlines as confirmed detailed events")
        bundle = {"ticker":ticker, "as_of":now.isoformat(), "mode":"live", "synthetic":False,
                  "price_basis":"Yahoo auto-adjusted OHLC", "prices":rows, "news":news, "warnings":warnings,
                  "sources":[{"id":"P1", "url":f"https://finance.yahoo.com/quote/{ticker}/history/", "provider":"Yahoo via yfinance", "retrieved_at":now.isoformat()}]}
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(bundle, ensure_ascii=False, indent=2))
    bundle["indicators"] = indicators(bundle["prices"])
    bundle["target_week"] = target_week(bundle["as_of"])
    bundle["sha256"] = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()
    return bundle
