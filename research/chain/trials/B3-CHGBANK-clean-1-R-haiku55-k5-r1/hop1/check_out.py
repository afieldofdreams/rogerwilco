import subprocess, sys

OUT_FILE = "/home/user/rogerwilco/research/chain/trials/B3-CHGBANK-clean-1-R-haiku55-k5-r1/hop1/out.txt"
CODEC = "/home/user/rogerwilco/research/chain/tools/frozen/scripts/rogerwilco.py"

with open(OUT_FILE, encoding="utf-8") as f:
    line = f.readline().rstrip("\n")

print("OUT:", line)
r = subprocess.run([sys.executable, "-I", CODEC, "validate", line, "--profile", "pay"],
                   capture_output=True, text=True)
print("validate exit:", r.returncode)
print("stdout:", r.stdout)
print("stderr:", r.stderr)
