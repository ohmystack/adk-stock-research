"""Interactive credentials setup; no key is printed or sent to a model."""
import argparse
import getpass
import os
from pathlib import Path
from dotenv import set_key

p=argparse.ArgumentParser()
p.add_argument("--local",action="store_true",help="Use the workshop author's local HTTP proxy")
args=p.parse_args()
root=Path(__file__).resolve().parents[1]
key=getpass.getpass("Gemini API key (hidden): ").strip()
if not key: raise SystemExit("Empty key; configuration unchanged")
path=root/".env"
path.touch(mode=0o600,exist_ok=True)
os.chmod(path,0o600)
set_key(path,"GEMINI_API_KEY",key)
set_key(path,"GEMINI_MODEL","gemini-3.8-flash")
set_key(path,"LOCAL_PROXY","http://127.0.0.1:1080" if args.local else "")
print("Saved private .env. Run doctor to check presence; the key will not be displayed.")
