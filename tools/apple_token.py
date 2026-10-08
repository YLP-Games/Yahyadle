#!/usr/bin/env python3
"""Make the Apple Music (MusicKit) developer token for Songdle's "Add to Apple Music" button.

You need a paid Apple Developer account and a MusicKit key:
  developer.apple.com → Certificates, Identifiers & Profiles
    1. Identifiers → + → Media IDs → register one (e.g. "Yahyadle") with MusicKit ticked.
    2. Keys → + → name it, tick "Media Services (MusicKit, ShazamKit, Apple Music Feed)" → Configure → pick that
       Media ID → Register → Download the .p8 file (Apple only lets you download it once) and note the Key ID.
    3. Your Team ID is under Membership details.

Then:
    pip install cryptography
    python3 tools/apple_token.py --team TEAMID --key-id KEYID --key AuthKey_KEYID.p8 --write

--write puts the token into index.html (const AM_TOKEN). The token only works on the site's address (origin) and
lasts up to 180 days (Apple's maximum); run this again before it runs out. Never commit the .p8 key itself.
"""
import argparse, base64, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")

def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_token(team, key_id, key_pem, days, origins):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
    key = serialization.load_pem_private_key(key_pem, password=None)
    now = int(time.time())
    header = {"alg": "ES256", "kid": key_id}
    payload = {"iss": team, "iat": now, "exp": now + min(days, 180) * 86400}
    if origins:
        payload["origin"] = origins
    signing_input = b64(json.dumps(header, separators=(",", ":")).encode()) + "." + b64(json.dumps(payload, separators=(",", ":")).encode())
    der = key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)                       # JWT wants the raw r||s form, not DER
    sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return signing_input + "." + b64(sig), payload["exp"]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", required=True, help="Apple Developer Team ID")
    ap.add_argument("--key-id", required=True, help="MusicKit key ID")
    ap.add_argument("--key", required=True, help="path to the AuthKey_XXXX.p8 file")
    ap.add_argument("--days", type=int, default=180, help="how long the token lasts (max 180)")
    ap.add_argument("--origin", action="append", default=None, help="site address the token works on (default: the GitHub Pages site)")
    ap.add_argument("--write", action="store_true", help="put the token into index.html")
    a = ap.parse_args()
    origins = a.origin or ["https://ylp-games.github.io"]
    token, exp = make_token(a.team, a.key_id, open(a.key, "rb").read(), a.days, origins)
    print(f"Token valid until {time.strftime('%d %b %Y', time.gmtime(exp))} for {', '.join(origins)}", file=sys.stderr)
    if a.write:
        html = open(INDEX, encoding="utf-8").read()
        new, n = re.subn(r'const AM_TOKEN="[^"]*";', f'const AM_TOKEN="{token}";', html, count=1)
        if not n:
            sys.exit("Couldn't find const AM_TOKEN in index.html")
        open(INDEX, "w", encoding="utf-8").write(new)
        print("Written to index.html", file=sys.stderr)
    else:
        print(token)

if __name__ == "__main__":
    main()
