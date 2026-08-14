"""
Local, non-Colab runner for the CORES + GETTEL pipeline.

Runs block1_data_prep.py -> block2_mindmap.py -> block3_dashboard.py ->
block4_assembly.py in sequence, entirely on local files — no browser upload
dialog, no notebook. block1 supports this directly (see the IN_COLAB check
near its top); blocks 2-4 already had no Colab dependency.

Usage:
    python run_pipeline.py <input_dir> [output_dir]

<input_dir>  Folder containing the Gettel .xlsx plus your CORES
              cores_companies*.csv / cores_directors*.csv batches (any
              number of batches, matched by filename the same way the
              Colab upload dialog does).
<output_dir>  Where the intermediate JSON/CSV files and the final
              cores_gettel_explorer.html get written. Defaults to
              <input_dir>/output.

Example:
    python run_pipeline.py ./my_gettel_upload
"""
import argparse
import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BLOCKS = [
    "block1_data_prep.py",
    "block2_mindmap.py",
    "block3_dashboard.py",
    "block4_assembly.py",
]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input_dir", help="Folder with the Gettel .xlsx + CORES CSVs")
    ap.add_argument("output_dir", nargs="?", default=None, help="Where outputs are written (default: <input_dir>/output)")
    args = ap.parse_args()

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.isdir(input_dir):
        sys.exit(f"Input directory not found: {input_dir}")

    output_dir = os.path.abspath(args.output_dir) if args.output_dir else os.path.join(input_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    for name in BLOCKS:
        src = os.path.join(SCRIPT_DIR, name)
        if not os.path.isfile(src):
            sys.exit(f"Missing pipeline script: {src}")
        shutil.copy(src, os.path.join(output_dir, name))

    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}\n")

    for i, name in enumerate(BLOCKS, 1):
        print("=" * 70)
        print(f"[{i}/{len(BLOCKS)}] Running {name}")
        print("=" * 70)
        cmd = [sys.executable, name] + ([input_dir] if name == "block1_data_prep.py" else [])
        result = subprocess.run(cmd, cwd=output_dir)
        if result.returncode != 0:
            sys.exit(f"\n{name} failed (exit code {result.returncode}) — stopping pipeline.")
        print()

    final_html = os.path.join(output_dir, "cores_gettel_explorer.html")
    if os.path.isfile(final_html):
        size_mb = os.path.getsize(final_html) / 1024 / 1024
        print("=" * 70)
        print(f"Done. {final_html} ({size_mb:.2f} MB)")
        print("=" * 70)
    else:
        sys.exit("Pipeline finished but cores_gettel_explorer.html was not produced — check the log above.")

if __name__ == "__main__":
    main()
