#!/usr/bin/env python3
"""
subdomains.py — GoDaddy + Cloudflare DNS inventory

• Spinner so the user knows it’s working
• Robust GoDaddy pagination (Link: rel="next")
• --log / -g / -c / --debug flags
• Searchable, collapsible DataTables-v2 HTML report
• Ctrl-C exits cleanly
"""
from __future__ import annotations

# ───────────── stdlib
import argparse, html, json, sys, time, threading, pathlib
from datetime import date
from urllib.parse import quote_plus
from typing import (Any, Dict, List, Mapping, Optional, TypedDict, Callable, Generator, cast, Union)

# ───────────── 3-party
import requests
from dotenv import dotenv_values
from requests.exceptions import RequestException

# ───────────── paths / CLI
ENV_FILE   = pathlib.Path(r"../secrets.txt")
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DATA_DIR   = SCRIPT_DIR / "data"; DATA_DIR.mkdir(exist_ok=True)
MASTER_JSON = DATA_DIR / "dns_records_master.json"
HTML_OUT    = SCRIPT_DIR / "DNS_Inventory.html"
TODAY       = date.today().isoformat()

p = argparse.ArgumentParser(description="Inventory every DNS record in your "
                                        "GoDaddy and/or Cloudflare account")
p.add_argument("--log", action="store_true")
p.add_argument("-g", "--godaddy", action="store_true")
p.add_argument("-c", "--cloudflare", action="store_true")
p.add_argument("--debug", action="store_true")
args = p.parse_args()
if not (args.godaddy or args.cloudflare):
    args.godaddy = args.cloudflare = True       # default = both

log  : Callable[..., None] = print if args.log else (lambda *_: None)
info : Callable[..., None] = print

# ───────────── secrets
if not ENV_FILE.exists():
    sys.exit(f"[!] .env not found at {ENV_FILE}")
env = dotenv_values(ENV_FILE)
try:
    GD_KEY, GD_SECRET = env["GODADDY_API_KEY"], env["GODADDY_API_SECRET"]
    CF_TOKEN          = env["CLOUDFLARE_API_TOKEN"]
except KeyError as e:
    sys.exit(f"[!] Missing {e} in .env")

GD_HEADERS = {"Authorization": f"sso-key {GD_KEY}:{GD_SECRET}"}
CF_HEADERS = {"Authorization": f"Bearer {CF_TOKEN}"}

session = requests.Session()
session.headers.update({"User-Agent": "dns-inventory/1.7"})

# ───────────── spinner
_spin = False
def _loop():
    frames = "⠋⠙⠚⠞⠖⠦⠴⠲⠳⠓"
    i = 0
    while _spin:
        sys.stdout.write("\r" + frames[i] + " ")
        sys.stdout.flush()
        i = (i + 1) % len(frames)
        time.sleep(0.07)

class spin:                    #   with spin(): slow_call()
    def __enter__(self):  # start
        global _spin; _spin = True
        threading.Thread(target=_loop, daemon=True).start()
    def __exit__(self, *_):     # stop
        global _spin; _spin = False
        sys.stdout.write("\r   \r"); sys.stdout.flush()

# ───────────── helpers
class DNSRecord(TypedDict):
    domain: str; subdomain: str; type: str; data: str
    source: str; discovery_date: str; status: str

def sig(r: DNSRecord) -> str:
    return "|".join(str(r[k]) for k in
                    ("domain", "subdomain", "type", "data", "source"))

# More specific type definitions for different API responses
GodaddyDomainRecord = TypedDict('GodaddyDomainRecord', {'domain': str})
GodaddyDNSRecord = TypedDict('GodaddyDNSRecord', {
    'name': str, 'type': str, 'data': str
})
CloudflareDNSRecord = TypedDict('CloudflareDNSRecord', {
    'name': str, 'type': str, 'content': str
})
CloudflareZone = TypedDict('CloudflareZone', {'id': str, 'name': str})
CloudflareResponse = TypedDict('CloudflareResponse', {
    'result': List[Any], 
    'result_info': Dict[str, int]
})

# Replace TypeVar with more specific Union type
GodaddyOrCloudflareResponse = Union[List[Dict[str, Any]], Dict[str, Any]]
def paginate(url: str, hdr: dict[str, str], label: str,
             params: Optional[Mapping[str, Any]] = None
             ) -> Generator[GodaddyOrCloudflareResponse, None, None]:
    """Yield successive pages; understands GoDaddy ‘Link’ & CF ‘result_info’."""
    page = 1
    while url:
        with spin():
            resp = session.get(url, headers=hdr, params=params)
        resp.raise_for_status()
        data = resp.json()
        # Fix for "Argument type is partially unknown"
        if isinstance(data, list):
            count = len(data)
        else:
            # Create a properly typed empty list as default
            default_empty: List[Any] = []
            result = data.get("result", default_empty)
            # Ensure result is actually a list
            if not isinstance(result, list):
                result = default_empty
            count = len(result)
        info(f"{label} page {page}: {count} items")
        yield data

        nxt: Optional[str] = None
        if "Link" in resp.headers and 'rel="next"' in resp.headers["Link"]:
            nxt = resp.headers["Link"].split(";")[0].strip(" <>")
        elif isinstance(data, dict) and "result_info" in data:
            result_info = cast(Dict[str, int], data["result_info"])
            if page < result_info["total_pages"]:
                nxt = url
                params = dict(params or {})
                params["page"] = page + 1
        url = nxt or ""  # Ensure url is always a string
        if not url:  # Break the loop if url is empty
            break
        page += 1

# ───────────── main
def main() -> tuple[List[DNSRecord], bool, bool]:
    recs: List[DNSRecord] = []
    gd_ok = cf_ok = False

    # GoDaddy
    if args.godaddy:
        info("🔗 Checking GoDaddy …")
        try:
            session.get("https://api.godaddy.com/v1/domains",
                        headers=GD_HEADERS,
                        params={"limit":1}).raise_for_status()
            gd_ok = True
            info("📥 GoDaddy domains …")
            doms: List[str] = []
            for pg in paginate("https://api.godaddy.com/v1/domains",
                               GD_HEADERS, "domains", params={"limit":100}):
                domain_data = cast(List[GodaddyDomainRecord], pg)
                doms.extend(d["domain"] for d in domain_data)
            info(f"➡  {len(doms)} domains")
            for i, dom in enumerate(doms, 1):
                log(f"  ↳ {i}/{len(doms)} {dom}")
                for pg in paginate(f"https://api.godaddy.com/v1/domains/"
                                   f"{quote_plus(dom)}/records",
                                   GD_HEADERS, dom):
                    dns_records = cast(List[GodaddyDNSRecord], pg)
                    for r in dns_records:
                        recs.append(cast(DNSRecord, {
                            "domain": dom,
                            "subdomain": "" if r["name"] == "@" else r["name"],
                            "type":      r["type"],
                            "data":      r["data"],
                            "source":    "GoDaddy",
                            "discovery_date": TODAY,
                            "status":    "active"
                        }))
            info(f"✔ GoDaddy records: {sum(r['source']=='GoDaddy' for r in recs)}")
        except RequestException as e:
            info(f"⚠️  GoDaddy unreachable: {e}")

    # Cloudflare
    if args.cloudflare:
        info("\n🔗 Checking Cloudflare …")
        try:
            session.get("https://api.cloudflare.com/client/v4/user/tokens/verify",
                        headers=CF_HEADERS).raise_for_status()
            cf_ok = True
            info("📥 Cloudflare zones …")
            zones: List[CloudflareZone] = []
            for pg in paginate("https://api.cloudflare.com/client/v4/zones",
                               CF_HEADERS, "zones", params={"per_page":50}):
                cf_response = cast(CloudflareResponse, pg)
                zones.extend(cast(List[CloudflareZone], cf_response["result"]))
            info(f"➡  {len(zones)} zones")
            for i, z in enumerate(zones, 1):
                zid, zname = z["id"], z["name"]
                log(f"  ↳ {i}/{len(zones)} {zname}")
                for pg in paginate(f"https://api.cloudflare.com/client/v4/zones/"
                                   f"{zid}/dns_records",
                                   CF_HEADERS, zname, params={"per_page":1000}):
                    cf_response = cast(CloudflareResponse, pg)
                    for r in cast(List[CloudflareDNSRecord], cf_response["result"]):
                        sub: str = "" if r["name"] == zname else r["name"][:-len(zname)-1]
                        recs.append(cast(DNSRecord, {
                            "domain": zname,
                            "subdomain": sub,
                            "type":      r["type"],
                            "data":      r["content"],
                            "source":    "Cloudflare",
                            "discovery_date": TODAY,
                            "status":    "active"
                        }))
            info(f"✔ Cloudflare records: {sum(r['source']=='Cloudflare' for r in recs)}")
        except RequestException as e:
            info(f"⚠️  Cloudflare unreachable: {e}")

    # Merge with history –—————————————————————————
    previous: List[DNSRecord] = []
    if MASTER_JSON.exists():
        try:
            previous = json.loads(MASTER_JSON.read_text())
        except json.JSONDecodeError:
            info(f"⚠️  {MASTER_JSON.name} is corrupt – starting fresh")

    now_map: Dict[str, DNSRecord] = {sig(r): r for r in recs}   # new run first
    for old in previous:
        s = sig(old)
        if s in now_map:            # new copy wins → keep its status
            continue
        src = old["source"]
        checked = (src=="GoDaddy" and gd_ok) or (src=="Cloudflare" and cf_ok)
        if checked:
            old["status"] = "removed"
        now_map[s] = old            # keep old (active or removed)

    merged = sorted(now_map.values(), key=lambda r: (r["domain"], r["subdomain"]))
    MASTER_JSON.write_text(json.dumps(merged, indent=2))
    info(f"🗄  Inventory saved → {MASTER_JSON.name}")
    return merged, gd_ok, cf_ok

# ───────────── HTML (DataTables v2 bundle + SearchBuilder)
def build_html(merged: List[DNSRecord], gd_ok: bool, cf_ok: bool) -> None:
    head = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>DNS Inventory – {TODAY}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="static/style.css"></head><body>
<header>
  <h1>DNS Inventory – {TODAY}</h1>
  <p><strong>Total domains:</strong> {len({r['domain'] for r in merged})}
     &nbsp;•&nbsp; <strong>Active records:</strong>
     {sum(r['status']=='active' for r in merged)}
     &nbsp;•&nbsp; Sources:
     GoDaddy {'✅' if gd_ok else '❌'} &nbsp; Cloudflare {'✅' if cf_ok else '❌'}
  </p>
  <input id="globalSearch" placeholder="🔎 global search across all records">
</header><main>
"""
    
    # Create a single table with all records
    rows = "\n".join(
        f'<tr class="{"removed" if r["status"]=="removed" else ""}">' 
        f'<td>{html.escape(r["domain"])}</td>'
        f'<td>{html.escape(r["subdomain"] or "@")}</td>'
        f'<td>{r["type"]}</td>'
        f'<td>{html.escape(r["data"])}</td>'
        f'<td>{r["source"]}</td>'
        f'<td>{r["status"]}</td>'
        f'<td>{r["discovery_date"]}</td></tr>'
        for r in sorted(merged, key=lambda x:(x["domain"], x["subdomain"], x["type"]))
    )
    
    table = f"""
<div class="table-container">
  <table id="dns_records" class="dns">
   <thead>
     <tr>
       <th>Domain</th>
       <th>Subdomain</th>
       <th>Type</th>
       <th>Data</th>
       <th>Source</th>
       <th>Status</th>
       <th>Date</th>
     </tr>
   </thead>
   <tbody>{rows}</tbody>
  </table>
</div>"""
    

    tail = """
<script src="static/datatables.js"></script>
</main></body></html>"""

    HTML_OUT.write_text(head + table + tail, encoding="utf-8")
    info(f"✅  HTML saved → {HTML_OUT.name}")

# ───────────── run
if __name__ == "__main__":
    try:
        t0 = time.time()
        merged, gd_ok, cf_ok = main()
        build_html(merged, gd_ok, cf_ok)
        m,s = divmod(int(time.time()-t0), 60)
        info(f"\n✔ Finished in {m}m {s}s — open {HTML_OUT.name}")
    except KeyboardInterrupt:
        print("\n⏹  Aborted by user (Ctrl-C)")
        sys.exit(130)
