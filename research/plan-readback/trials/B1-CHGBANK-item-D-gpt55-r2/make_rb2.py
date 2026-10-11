import subprocess, pathlib
ho = pathlib.Path('/home/user/rogerwilco/research/plan-readback/trials/B1-CHGBANK-item-D-gpt55-r2/ho2.txt').read_text().rstrip('\n')
cmd = ['python3','/home/user/rogerwilco/rogerwilco/scripts/rogerwilco.py','make-rb',ho,'payer-2','--profile','pay']
r = subprocess.run(cmd, text=True, capture_output=True)
print(r.stdout, end='')
print(r.stderr, end='')
raise SystemExit(r.returncode)
