"""Quiet timing pass: sequential setup / prove2 / verify per benchmark, peak RSS per process."""
import subprocess, json, os, sys, resource, time, tempfile
from config import ZKP as Z, WORK
TOUT = os.path.join(tempfile.gettempdir(), "zkapr_tout")
def run(args, cwd):
    pid = os.fork()
    if pid == 0:
        os.chdir(cwd); fd = os.open(TOUT, os.O_WRONLY | os.O_CREAT | os.O_TRUNC); os.dup2(fd, 1)
        os.execv(args[0], args)
    t0 = time.time(); _, status, ru = os.wait4(pid, 0)
    out = open(TOUT).read().strip().splitlines()
    return status, (json.loads(out[-1]) if out else {}), ru.ru_maxrss / 1024.0, time.time() - t0
names = sys.argv[1:]
for n in names:
    w = os.path.join(WORK, n)
    if os.path.exists(w + "/timing.json"):
        continue
    res = {"name": n}
    st, o, mem, wall = run([Z, "setup2", "main.r1cs", "pk.bin", "vk.bin", "aux.bin"], w)
    res.update(setup_status=st, setup_mem_mb=mem, **o)
    st, o, mem, wall = run([Z, "crscheck", "main.r1cs", "pk.bin", "aux.bin"], w)
    res.update(crscheck_status=st, crscheck_mem_mb=mem, **o)
    st, o, mem, wall = run([Z, "prove2", "main.r1cs", "input.wtns", "pk.bin", "proof.bin", "public.bin"], w)
    res.update(prove_status=st, prove_mem_mb=mem, prove_wall=wall, **o)
    if st == 0:
        st, o, mem, wall = run([Z, "verify", "vk.bin", "proof.bin", "public.bin"], w)
        res.update(verify_status=st, **o)
    json.dump(res, open(w + "/timing.json", "w"), indent=1); print(json.dumps(res), flush=True)
