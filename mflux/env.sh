# Source this to use the project-local MFLUX toolchain. Nothing outside ~/Dev/photo-gen/mflux is written.
export MF=~/Dev/photo-gen/mflux
export UV_PYTHON_INSTALL_DIR=$MF/python
export UV_CACHE_DIR=$MF/cache/uv
export UV_TOOL_DIR=$MF/tools/uv-tools
export UV_PYTHON_PREFERENCE=only-managed
export UV_NO_CONFIG=1
export HF_HOME=$MF/hf
export HF_HUB_DISABLE_TELEMETRY=1
export PATH=$MF/tools:$PATH
export UV_PYTHON_BIN_DIR=$MF/python/bin
export UV_PYTHON_INSTALL_REGISTRY=0
