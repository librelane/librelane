import glob
import os
import subprocess

__dir__ = os.path.dirname(__file__)

pngs = glob.glob(os.path.join(__dir__, "**", "*.png"), recursive=True)
print(pngs)

for png in pngs:
    subprocess.check_call(["convert", png, png.replace(".png", ".webp")])
    os.unlink(png)
