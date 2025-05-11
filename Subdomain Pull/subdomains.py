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
ENV_FILE   = pathlib.Path(r"/media/sf_main/Scripts/0xGodaddy/Subdomain Pull/.env")
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

# Standard browser user-agent to avoid API blocking
STANDARD_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

session = requests.Session()
session.headers.update({"User-Agent": STANDARD_USER_AGENT})

# Set default timeout for all requests (60 seconds - increased to avoid timeouts)
REQUEST_TIMEOUT = 60  # seconds
MAX_RETRIES = 5       # increased number of retries for failed requests
BACKOFF_FACTOR = 1.5  # exponential backoff factor between retries

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

def is_test_domain(domain: str) -> bool:
    """Check if domain is a test/example domain that should be filtered out."""
    test_domains = [
        "example.com", "example.org", "example.net",
        "test.com", "test.org", "test.net",
        "domain.com", "domain.org", "domain.net",
        "localhost", "invalid", "example", "test"
    ]
    
    # Check exact matches
    if domain.lower() in test_domains:
        return True
    
    # Check for common test patterns
    if domain.startswith("test-") or domain.startswith("example-"):
        return True
        
    return False

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
    retry_count = 0
    params_dict = dict(params or {})
    
    while url:
        try:
            with spin():
                resp = session.get(url, headers=hdr, params=params_dict, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            # Reset retry count on success
            retry_count = 0
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
                    params_dict["page"] = page + 1
            url = nxt or ""  # Ensure url is always a string
            if not url:  # Break the loop if url is empty
                break
            page += 1
            
        except RequestException as e:
            retry_count += 1
            if retry_count <= MAX_RETRIES:
                # Use exponential backoff for retries
                sleep_time = BACKOFF_FACTOR ** retry_count
                info(f"⚠️  API request failed, retrying in {sleep_time:.1f}s ({retry_count}/{MAX_RETRIES}): {e}")
                time.sleep(sleep_time)
                # Continue with the current URL (retry)
                continue
            else:
                # Log the error and break out of the pagination loop
                info(f"⚠️  API request failed after {MAX_RETRIES} retries: {e}")
                break

# ───────────── main
def fetch_all_godaddy_domains() -> List[str]:
    """Fetch all domains from GoDaddy across all pages"""
    info("📥 Fetching all GoDaddy domains across all pages...")
    all_domains: List[str] = []
    domains_seen = set()  # Track domains we've seen to prevent duplicates
    
    # First, check if the API is accessible
    session.get("https://api.godaddy.com/v1/domains",
                headers=GD_HEADERS,
                params={"limit":1},
                timeout=REQUEST_TIMEOUT).raise_for_status()
    
    # Use marker-based pagination which is more reliable than page numbers
    marker = None
    page_num = 1
    while True:
        # Set up params with marker if we have one
        params = {
            "limit": 1000,  # Fetch more domains per request
            "statuses": "ACTIVE"
        }
        if marker:
            params["marker"] = marker
        
        domain_batch = []
        new_marker = None
        for pg in paginate("https://api.godaddy.com/v1/domains", GD_HEADERS, 
                          f"domains (page {page_num})", params=params):
            # Check for pagination marker in response
            if isinstance(pg, dict) and "_metadata" in pg and "nextMarker" in pg["_metadata"]:
                new_marker = pg["_metadata"]["nextMarker"]
                domain_data = pg.get("domains", [])
            else:
                domain_data = cast(List[GodaddyDomainRecord], pg)
            
            # Filter out test domains and already seen domains
            for d in domain_data:
                domain = d.get("domain", None) if isinstance(d, dict) else None
                if domain and not is_test_domain(domain) and domain not in domains_seen:
                    domains_seen.add(domain)
                    domain_batch.append(domain)
        
        # If we got new domains, add them
        if domain_batch:
            info(f"  ➡ Page {page_num}: Found {len(domain_batch)} new domains")
            all_domains.extend(domain_batch)
            page_num += 1
            
            # If we have a new marker, continue; otherwise we're done
            if new_marker and new_marker != marker:
                marker = new_marker
            else:
                # No new marker or same marker, we're done
                break
        else:
            # No new domains, we're done
            break
    
    info(f"  ✓ Total: {len(all_domains)} domains")
    return all_domains

def fetch_dns_records_for_domain(dom: str) -> List[DNSRecord]:
    """Fetch all DNS records for a single domain with pagination"""
    domain_records: List[DNSRecord] = []
    dns_url = f"https://api.godaddy.com/v1/domains/{quote_plus(dom)}/records"
    
    try:
        # Use only the batched approach with offset which is more reliable
        offset = 0
        max_limit = 100  # Reasonable batch size (GoDaddy's API has issues with large limits)
        all_records = []
        page_num = 1
        
        info(f"📄 Fetching DNS records for {dom} with pagination...")
        while True:
            params = {"limit": max_limit, "offset": offset}
            batch_records = []
            batch_success = False
            
            try:
                for pg in paginate(dns_url, GD_HEADERS, f"{dom} (page {page_num}, offset {offset})", params=params):
                    dns_records = cast(List[GodaddyDNSRecord], pg)
                    batch_records.extend(dns_records)
                    batch_success = True
            except RequestException as e:
                # If we hit an error, try with a smaller limit
                if max_limit > 25 and "422" in str(e):
                    info(f"  ⚠️ Reducing batch size for {dom} due to API error")
                    max_limit = 25  # Try with a smaller limit
                    continue  # Retry this batch with smaller limit
                else:
                    # If we still have errors or it's not a 422, log and continue
                    info(f"  ⚠️ Error fetching records for {dom} at offset {offset}: {e}")
                    # Try next batch anyway
            
            # If successful, add batch to all records
            if batch_success and batch_records:
                info(f"  ℹ️ {dom}: Got {len(batch_records)} records at offset {offset}")
                all_records.extend(batch_records)
                
                # If we got fewer records than the limit, we're done
                if len(batch_records) < max_limit:
                    break
                    
                # Otherwise, move to the next batch
                offset += max_limit
                page_num += 1
            else:
                # No records in this batch or error
                break
        
        # Report total records found
        if all_records:
            info(f"  ✓ Got {len(all_records)} total records for {dom}")
        else:
            info(f"  ⚠️ No DNS records found for {dom}")
        
        # Convert all records to our standard format
        for r in all_records:
            domain_records.append(cast(DNSRecord, {
                "domain": dom,
                "subdomain": "" if r["name"] == "@" else r["name"],
                "type":      r["type"],
                "data":      r["data"],
                "source":    "GoDaddy",
                "discovery_date": TODAY,
                "status":    "active"
            }))
            
    except RequestException as e:
        info(f"⚠️  Error fetching records for {dom}: {e}")
    
    return domain_records

def main() -> tuple[List[DNSRecord], bool, bool]:
    recs: List[DNSRecord] = []
    gd_ok = cf_ok = False

    # GoDaddy
    if args.godaddy:
        info("🔗 Checking GoDaddy …")
        try:
            # Step 1: Fetch all domains first
            all_domains = fetch_all_godaddy_domains()
            gd_ok = True
            
            # Step 2: Fetch DNS records for each domain
            total_domains = len(all_domains)
            for i, dom in enumerate(all_domains, 1):
                log(f"  ↳ Processing {i}/{total_domains}: {dom}")
                try:
                    domain_records = fetch_dns_records_for_domain(dom)
                    recs.extend(domain_records)
                except Exception as e:
                    info(f"  ⛔ Failed to process domain {dom}: {e}")
                    # Continue with next domain
                
            info(f"✔ GoDaddy records: {sum(r['source']=='GoDaddy' for r in recs)}")
        except RequestException as e:
            info(f"⚠️  GoDaddy unreachable: {e}")

    # Cloudflare
    if args.cloudflare:
        info("\n🔗 Checking Cloudflare …")
        try:
            session.get("https://api.cloudflare.com/client/v4/user/tokens/verify",
                        headers=CF_HEADERS,
                        timeout=REQUEST_TIMEOUT).raise_for_status()
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
