"""Tool locations. Override any of these with environment variables."""
import os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.environ.get("ZKAPR_TOOLS", os.path.join(ROOT, "tools"))
WORK = os.environ.get("ZKAPR_WORK", os.path.join(ROOT, "work"))
RESULTS = os.environ.get("ZKAPR_RESULTS", os.path.join(ROOT, "results"))
_LOCAL_CBMC = os.path.join(TOOLS, "cbmc", "usr", "bin", "cbmc")   # installed by setup.sh when the system CBMC is too old
CBMC = os.environ.get("CBMC", _LOCAL_CBMC if os.path.exists(_LOCAL_CBMC) else (shutil.which("cbmc") or "cbmc"))
CADICAL = os.environ.get("CADICAL", os.path.join(TOOLS, "cadical/build/cadical"))
LRATTRIM = os.environ.get("LRATTRIM", os.path.join(TOOLS, "lrat-trim/lrat-trim"))
CIRCOM = os.environ.get("CIRCOM", os.path.join(TOOLS, "circom") if os.path.exists(os.path.join(TOOLS, "circom")) else (shutil.which("circom") or "circom"))
NODE_MODULES = os.environ.get("NODE_MODULES", os.path.join(TOOLS, "node_modules"))
CIRCOMLIB = os.path.join(NODE_MODULES, "circomlib/circuits")
ZKP = os.environ.get("ZKP", os.path.join(ROOT, "prover/target/release/zkp"))
