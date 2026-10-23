#!/usr/bin/env python
"""Warm the 0.1.43.1 engine build (build/ + build-vision/) with the EXACT defs setup.py's
build_engine() would use, WITHOUT touching engine/ (the running binary is locked by the
live server). After this, a stop -> `sh setup.sh --update` is a ninja no-op + a seconds-long
copy + stamp. Run: .venv/bin/python warm-build-2026-10-13.py"""
import importlib.util, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("strata_setup", ROOT / "setup.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)  # safe: main is behind __main__ guard

toolkit = 13
eng = m.ROOT / "engine"
stamp = eng / "BUILD.json"
meta = json.loads(stamp.read_text(encoding="utf-8")) if stamp.exists() else {}
gpu = m.update_engine_gpu(toolkit)
llama = m.get_llama_cpp()
archs = sorted({int(x) for x in gpu.get("archs", [gpu["arch"]])} | {int(x) for x in meta.get("archs", [])})
nvcc, vcvars = m.install_build_tools({**gpu, "archs": archs, "toolkit": toolkit}, False)
cuda_archs = ";".join(str(x) for x in archs)
floor = m.cpu_floor(m.cpu_info()[1])
bdir, vdir = m.ROOT / "build", m.ROOT / "build-vision"
print(f"arch={archs} floor={floor!r} nvcc={nvcc} llama={llama}", flush=True)

defs = ["-DSTRATA_ENABLE_CUDA=ON", "-DSTRATA_BUILD_TESTS=OFF", f"-DCMAKE_CUDA_ARCHITECTURES={cuda_archs}",
        f"-DCMAKE_CUDA_COMPILER={nvcc}", *m.toolkit_root_defs(nvcc), f"-DSTRATA_GGML_DIR={llama}",
        *m.host_compiler_defs(True), *m.engine_defs(archs, toolkit), *m.isa_floor_defs(floor, bdir, meta)]
m.cmake_build(m.ROOT, bdir, "strata", defs, vcvars, "build-strata.bat")

defs_v = [f"-DLLAMA_DIR={llama}", "-DSTRATA_VISION_CUDA=ON", "-DSTRATA_PORTABLE=OFF",
          *m.host_compiler_defs(True), f"-DCMAKE_CUDA_ARCHITECTURES={cuda_archs}",
          f"-DCMAKE_CUDA_COMPILER={nvcc}", *m.toolkit_root_defs(nvcc)]
m.cmake_build(m.ROOT / "tools" / "vision", vdir, "strata-vision", defs_v, vcvars, "build-vision.bat")

print("WARM BUILD DONE: build/strata + build-vision/bin/strata-vision are current for this source", flush=True)
