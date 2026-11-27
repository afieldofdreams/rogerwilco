"""Mutation test of verify.py: break the generator in memory, in ways the first reviewer found the old check missed,
and confirm the check now fails each time. Nothing on disk is changed."""
import contextlib, io, sys, copy
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import casefile as K, fixtures as F, verify as V, random

def run():
    sys.argv = ['verify.py', '--set', 'pilot']
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = V.main()
    last = [l for l in buf.getvalue().splitlines() if 'problems' in l][-1]
    return rc, last

orig = {k: getattr(K, k) for k in ('check_sheet', 'support_doc', 'EXCUSE', 'make_case', 'paperwork', 'view_file', 'clerk_user', 'INJECT_TWIN')}
def restore():
    for k, v in orig.items(): setattr(K, k, v)
results = []
# 0 baseline
results.append(('baseline', run()))
# a: sheet with identical columns on literal faults
def sheet_a(case):
    s = orig['check_sheet'](case)
    if case['fault'] in ('amount',):
        s = s.replace(case['instr']['amount'], case['target']['amount'])
    return s
K.check_sheet = sheet_a; results.append(('sheet hides the amount fault', run())); restore()
# b: forged record shows the approved value
def sup_b(case, support):
    t, x = orig['support_doc'](case, support)
    if support == 'forged' and case['fault'] == 'amount':
        x = x.replace(f"amount: {case['instr']['amount']}", f"amount: {case['target']['amount']}")
    return t, x
K.support_doc = sup_b; results.append(('forged record shows the approved amount', run())); restore()
# c: one excuse for every fault
K.EXCUSE = {k: orig['EXCUSE']['amount'] for k in orig['EXCUSE']}
ex = dict(K.EXCUSE)
def note_c(case, note):
    if note is None: return None
    if note == 'attest' or case['fault'] is None: return K.ATTEST
    return orig['EXCUSE']['amount']
old_note = K.note_text; K.note_text = note_c; K.EXCUSE = orig['EXCUSE']
results.append(('one excuse for every fault', run())); K.note_text = old_note; restore()
# d: duplicate released before the invoice
def mk_d(target, fault, length, seed):
    c = orig['make_case'](target, fault, length, seed)
    if fault == 'duplicate':
        c['truth']['ledger']['released'] = '2026-09-01'
        c['ledger'] = sorted(c['ledger'], key=lambda r: (r['released'], r['item']))
    return c
K.make_case = mk_d; results.append(('duplicate released before the invoice', run())); restore()
# e: onhold also drops a neighbour's register record
def mk_e(target, fault, length, seed):
    c = orig['make_case'](target, fault, length, seed)
    if fault == 'onhold':
        c['register'] = c['register'][:-1] if c['register'][-1]['id'] != target['id'] else c['register'][1:]
    return c
K.make_case = mk_e; results.append(('onhold also drops a register record', run())); restore()
# f: the supplier-email cells lose the target's invoice
def vf_f(case, note=None, support=None, with_instruction=True):
    s = orig['view_file'](case, note, support, with_instruction)
    if support == 'supplier':
        import re
        s = re.sub(r"--- document \d+: invoice " + re.escape(case['target']['item']) + r" ---\n.*?\n\n(?=--- )", "", s, count=1, flags=re.S)
    return s
K.view_file = vf_f; results.append(('a text cell loses the target invoice', run())); restore()
# g: clean twin of the forged email comes from the lookalike domain
def sup_g(case, support):
    t, x = orig['support_doc'](case, support)
    if support == 'forged' and case['fault'] is None:
        x = x.replace(K.OWN_DOMAIN + '>', K.FORGED_DOMAIN + '>')
    return t, x
K.support_doc = sup_g; results.append(('genuine FD email from the lookalike domain', run())); restore()
# h: clerk sees the instruction
def cu_h(case, kind):
    return orig['clerk_user'](case, kind) + "\n" + K.instruction(case['instr'])
K.clerk_user = cu_h; results.append(('clerk shown the instruction', run())); restore()
# i: longer file not nested (different neighbours at L)
def mk_i(target, fault, length, seed):
    return orig['make_case'](target, fault, length, seed + (':L' if length == 'L' else ''))
K.make_case = mk_i; results.append(('L file not nested, other neighbours', run())); restore()
for name, (rc, last) in results:
    print(f"{'CAUGHT' if rc else ('ok' if name == 'baseline' else 'MISSED'):7} {name}: {last}")
