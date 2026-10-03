#!/usr/bin/env bash
# Installs the toolchain into ./tools and builds the prover. Linux (x86_64) and macOS. Re-runnable.
set -euo pipefail
cd "$(dirname "$0")"; ROOT="$PWD"; T="$ROOT/tools"; mkdir -p "$T"
NPROC="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 2)"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1 ($2)"; exit 1; }; }
need git "git"; need make "build tools (build-essential)"; need curl "curl"; need python3 "Python >= 3.8"
need node "Node.js >= 16 (e.g. via https://github.com/nvm-sh/nvm)"; need npm "npm"
need cargo "Rust >= 1.75 (https://rustup.rs)"
ver_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }   # ver_ge A B: A >= B
RUSTV="$(rustc --version | awk '{print $2}')"
ver_ge "$RUSTV" 1.75.0 || { echo "rustc $RUSTV is too old; install a current toolchain: curl https://sh.rustup.rs -sSf | sh"; exit 1; }
NODEV="$(node --version | tr -d v)"
ver_ge "$NODEV" 16.0.0 || { echo "Node.js $NODEV is too old (>= 16 needed), e.g.: nvm install 20"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' || { echo "Python >= 3.8 needed"; exit 1; }

# 1. CBMC (encoder F). Tested with 5.95.1; older versions (e.g. Ubuntu 20.04's apt package) do not work.
cbmc_ok() { [ -x "$1" ] || command -v "$1" >/dev/null 2>&1 || return 1; v="$("$1" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)"; [ -n "$v" ] && ver_ge "$v" 5.95.0; }
if cbmc_ok "$T/cbmc/usr/bin/cbmc"; then echo "CBMC: $T/cbmc/usr/bin/cbmc"
elif cbmc_ok cbmc; then echo "CBMC: $(command -v cbmc)"
else
  case "$(uname -s)" in
    Linux)
      . /etc/os-release 2>/dev/null || true
      case "${VERSION_ID:-}" in 20.04) DEB=ubuntu-20.04 ;; *) DEB=ubuntu-22.04 ;; esac
      URL="https://github.com/diffblue/cbmc/releases/download/cbmc-5.95.1/$DEB-cbmc-5.95.1-Linux.deb"
      echo "Installing CBMC 5.95.1 ($DEB package) into $T/cbmc (no root needed)"
      curl -fsSL -o "$T/cbmc.deb" "$URL" && rm -rf "$T/cbmc" && dpkg-deb -x "$T/cbmc.deb" "$T/cbmc" && rm -f "$T/cbmc.deb"
      cbmc_ok "$T/cbmc/usr/bin/cbmc" || { echo "CBMC install failed; install CBMC >= 5.95 and set CBMC=/path/to/cbmc"; exit 1; } ;;
    Darwin) brew install cbmc ;;
    *) echo "Install CBMC (>= 5.95) and set CBMC=/path/to/cbmc"; exit 1 ;;
  esac
fi

# 2. CaDiCaL (LRAT proofs) and lrat-trim, pinned revisions.
if [ ! -x "$T/cadical/build/cadical" ]; then
  rm -rf "$T/cadical"; git clone https://github.com/arminbiere/cadical.git "$T/cadical"
  (cd "$T/cadical" && git checkout c60730422e758ef1cebe7aeddf2dda31c996bf04 && ./configure && make -j"$NPROC")
fi
if [ ! -x "$T/lrat-trim/lrat-trim" ]; then
  rm -rf "$T/lrat-trim"; git clone https://github.com/arminbiere/lrat-trim.git "$T/lrat-trim"
  (cd "$T/lrat-trim" && git checkout b30f400f4ee5c32b77ee566a7c006081b521534f && ./configure && make)
fi

# 3. Circom 2.2.2: the release binary if it runs here (it needs glibc >= 2.34), otherwise built from source.
if ! "$T/circom" --version >/dev/null 2>&1; then
  rm -f "$T/circom"
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64)  curl -fsSL -o "$T/circom" https://github.com/iden3/circom/releases/download/v2.2.2/circom-linux-amd64 || true ;;
    Darwin-x86_64) curl -fsSL -o "$T/circom" https://github.com/iden3/circom/releases/download/v2.2.2/circom-macos-amd64 || true ;;
  esac
  chmod +x "$T/circom" 2>/dev/null || true
  if ! "$T/circom" --version >/dev/null 2>&1; then
    echo "The Circom release binary does not run on this system; building Circom 2.2.2 from source (a few minutes)"
    rm -f "$T/circom"
    cargo install --locked --git https://github.com/iden3/circom.git --tag v2.2.2 --root "$T/circom-build" circom
    cp "$T/circom-build/bin/circom" "$T/circom"
  fi
fi
"$T/circom" --version

# 4. circomlib (Poseidon, Num2Bits, IsZero) and circomlibjs (native Poseidon for the commitment)
(cd "$T" && { [ -f package.json ] || npm init -y >/dev/null; } && npm install --silent circomlib@2.0.5 circomlibjs@0.1.7)

# 5. Groth16 prover (arkworks 0.4, BN254)
(cd "$ROOT/prover" && cargo build --release)

# 6. Python packages for the report and figure
python3 -c "import numpy, matplotlib" 2>/dev/null || echo "Please install: python3 -m pip install --user numpy matplotlib"
echo "Setup complete."
