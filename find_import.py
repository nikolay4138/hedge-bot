import os
import re
import subprocess

PROJECT_PATH = "./"  # Proje kök dizini

imports = set()
pattern = re.compile(r'^\s*(?:from\s+([\w\.]+)|import\s+([\w\.]+))')

for root, _, files in os.walk(PROJECT_PATH):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                for line in f:
                    match = pattern.match(line)
                    if match:
                        module = match.group(1) or match.group(2)
                        if module:
                            imports.add(module.split('.')[0])

# Sadece 3. parti modülleri bul (standart kütüphaneleri çıkar)
output = subprocess.check_output(["pip", "freeze"]).decode()
installed_packages = {pkg.split("==")[0].lower() for pkg in output.splitlines()}

used_packages = {imp for imp in imports if imp.lower() in installed_packages}

# requirements.txt yaz
with open("requirements.txt", "w") as f:
    for pkg in sorted(used_packages):
        f.write(pkg + "\n")

print(f"Bulunan kütüphaneler: {', '.join(sorted(used_packages))}")
