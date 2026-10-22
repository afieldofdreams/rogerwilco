import subprocess, sys

HO_FILE = "/home/user/rogerwilco/research/chain/trials/B3-CHGBANK-clean-1-R-haiku55-k5-r1/hop1/ho_received.txt"
CODEC = "/home/user/rogerwilco/research/chain/tools/frozen/scripts/rogerwilco.py"
MY_ID = sys.argv[1] if len(sys.argv) > 1 else "coordinator-1"

with open(HO_FILE, encoding="utf-8") as f:
    ho = f.readline().rstrip("\n")

print("HO:", ho)
r = subprocess.run([sys.executable, "-I", CODEC, "make-rb", ho, MY_ID, "--profile", "pay"],
                   capture_output=True, text=True)
print("make-rb exit:", r.returncode)
print("stdout:", r.stdout)
print("stderr:", r.stderr)
