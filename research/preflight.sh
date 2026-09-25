#!/bin/zsh
# Read-only preflight for Qwen-Image-2.1 on Apple Silicon.
# Installs, downloads, and modifies nothing. Safe to re-run.
# Usage: zsh research/preflight.sh | tee research/preflight-$(date +%Y%m%d-%H%M).log

hr() { print -- "\n=== $1 ==="; }

hr "Date / OS"
date
sw_vers                                   # expect macOS 26.x or 27.x
uname -m                                  # expect: arm64

hr "Chip / memory / GPU"
sysctl -n machdep.cpu.brand_string        # expect: Apple M5
print "RAM bytes: $(sysctl -n hw.memsize)" # 17179869184 = 16 GiB
print "P-cores: $(sysctl -n hw.perflevel0.physicalcpu)  E-cores: $(sysctl -n hw.perflevel1.physicalcpu)"
system_profiler SPDisplaysDataType 2>/dev/null | grep -E "Chipset|Total Number of Cores|Metal"
sysctl iogpu.wired_limit_mb               # 0 = macOS default GPU wired limit (do NOT change it)

hr "Metal working-set limits (compiles a throwaway Swift snippet in \$TMPDIR)"
if command -v swift >/dev/null; then
  f=$(mktemp -t mtl).swift
  cat > "$f" <<'EOF'
import Metal
let d = MTLCreateSystemDefaultDevice()!
print("device:", d.name)
print(String(format: "recommendedMaxWorkingSetSize: %.2f GB", Double(d.recommendedMaxWorkingSetSize)/1e9))
print(String(format: "maxBufferLength: %.2f GB", Double(d.maxBufferLength)/1e9))
print("hasUnifiedMemory:", d.hasUnifiedMemory)
EOF
  swift "$f" 2>&1 | tail -4; rm -f "$f"
else
  print "swift not found (install Xcode Command Line Tools to run this check)"
fi

hr "Memory pressure / swap / free pages"
memory_pressure | tail -1                 # "System-wide memory free percentage: NN%"
sysctl vm.swapusage                       # swap in use; macOS grows swap dynamically
vm_stat | head -12
print "Sum of process RSS (GB, overcounts shared pages): $(ps -A -o rss= | awk '{s+=$1} END {printf "%.1f", s/1048576}')"
print "Top 8 memory users:"
ps -A -o rss=,comm= | sort -rn | head -8 | awk '{printf "  %6.2f GB  %s\n", $1/1048576, $2}'

hr "Disk"
df -h ~ | tail -1                         # need ~40 GB free for models + envs + outputs

hr "Toolchain"
for t in git brew clang cmake uv python3 python3.12 python3.13 llama-cli sd-cli; do
  p=$(command -v $t 2>/dev/null); print "  $t: ${p:-MISSING}"
done
xcode-select -p 2>&1
clang --version 2>&1 | head -1
python3 -c 'import sys,platform;print("  system python3:",sys.version.split()[0],platform.machine())'
# ComfyUI v0.37.0 pyproject: requires-python >=3.10 -> system 3.9 is too old

hr "Python ML stack in the *current* python3 (expected: not installed)"
python3 - <<'EOF'
for m in ("torch","mlx","gguf","diffusers","transformers"):
    try:
        mod=__import__(m); print(f"  {m}: {getattr(mod,'__version__','?')}")
    except Exception as e:
        print(f"  {m}: not importable ({type(e).__name__})")
try:
    import torch; print("  torch.backends.mps.is_available():", torch.backends.mps.is_available())
except Exception: pass
EOF

hr "Thermal / power"
pmset -g therm 2>&1 | head -5             # "No ... warning level has been recorded" = OK
pmset -g batt | head -2                   # run benchmarks on AC power
print "\nDone. Nothing was changed."
