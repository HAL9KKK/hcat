import zipfile
import os
import shutil
import json
import stat
import re
from pathlib import Path

# Configuration
BASE_DIR = Path(r'C:\Users\teiiamu\LLM\hash')
CRACKERS_DIR = BASE_DIR / 'crackers'
AGENT_ZIP = BASE_DIR / 'hashtopolis.zip'
AGENT_ZIP_BAK = BASE_DIR / 'hashtopolis.zip.bak'
CONFIG_FILE = BASE_DIR / 'config.json'
NEW_EXE_NAME = 'pippo.bin'
OLD_EXE_NAME = 'hashcat.bin'

def fix_config_json():
    if not CONFIG_FILE.exists():
        return
    print("Fixing config.json paths and identity...")
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    path_keys = ["files-path", "crackers-path", "hashlists-path", "zaps-path", "preprocessors-path"]
    modified = False
    for key in path_keys:
        if key in config:
            val = config[key]
            # Convert Windows backslashes and relative paths to a clean relative format
            new_val = val.replace('\\', '/').rstrip('/')
            if ':' in new_val: # Windows absolute
                new_val = os.path.basename(new_val) if key != "zaps-path" else "."
            if new_val != val:
                config[key] = new_val
                modified = True
    
    if config.get("token") or config.get("uuid"):
        config["token"] = ""
        config["uuid"] = ""
        modified = True
        
    if modified:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print("  config.json updated.")

def rename_binaries():
    print("Renaming binaries...")
    if not CRACKERS_DIR.exists(): return
    for root, dirs, files in os.walk(CRACKERS_DIR):
        for file in files:
            if file == OLD_EXE_NAME:
                old_path = Path(root) / file
                new_path = Path(root) / NEW_EXE_NAME
                print(f"  {old_path} -> {new_path}")
                shutil.copy2(old_path, new_path)
                os.remove(old_path)
                try:
                    os.chmod(new_path, os.stat(new_path).st_mode | 0o111)
                except: pass

def patch_agent():
    if not AGENT_ZIP.exists(): return
    print(f"Patching {AGENT_ZIP}...")
    if not AGENT_ZIP_BAK.exists():
        shutil.copy2(AGENT_ZIP, AGENT_ZIP_BAK)

    # Use a fresh copy from backup for patching to avoid corrupted state from previous failed runs
    shutil.copy2(AGENT_ZIP_BAK, AGENT_ZIP)

    temp_zip = BASE_DIR / 'hashtopolis.zip.tmp'
    
    with zipfile.ZipFile(AGENT_ZIP, 'r') as zin, zipfile.ZipFile(temp_zip, 'w') as zout:
        for item in zin.infolist():
            content = zin.read(item.filename).decode('utf-8', errors='ignore')
            
            if item.filename == 'htpclient/config.py':
                # Force absolute paths for all directory settings
                # Ensure val is defined within the scope of existence check
                content = content.replace(
                    "return self.config[key]",
                    "val = self.config[key]\n            if key.endswith('-path'): return os.path.abspath(val)\n            return val"
                )
                # Ensure 'import os' is available (if only 'import os.path' exists)
                if 'import os\n' not in content and 'import os\r\n' not in content:
                    content = "import os\n" + content
            
            elif item.filename == 'htpclient/hashcat_cracker.py':
                # 1. Filename swap
                content = content.replace("['executable']", "['executable'].replace('hashcat.bin', 'pippo.bin')")
                # 2. Force absolute executable path
                content = content.replace("self.executable_name)", "self.executable_name).resolve()")
                # 3. Fix callPath (remove ./)
                content = content.replace("f'./{self.executable_name}'", "f'{self.executable_path}'")
                content = content.replace("f\"'./{self.executable_name}'\"", "f\"'{self.executable_path}'\"")
                # 4. Mandatory chmod before any usage
                content = re.sub(r"(self\.executable_path = .*?\n)", r"\1        try:\n            import os\n            os.chmod(str(self.executable_path), 0o755)\n        except: pass\n", content)

            elif item.filename == 'htpclient/generic_cracker.py':
                content = content.replace("['executable']", "['executable'].replace('hashcat.bin', 'pippo.bin')")
                # Specifically target the line where self.callPath is first assigned
                content = re.sub(r"(self\.callPath = )(.*?)(\n)", r"\1os.path.abspath(\2.replace('\"', '').replace(\"'\", ''))\n        try: os.chmod(self.callPath, 0o755)\n        except: pass\n", content)

            elif item.filename == 'htpclient/binarydownload.py':
                content = content.replace("ans['executable']", "ans['executable'].replace('hashcat.bin', 'pippo.bin')")

            zout.writestr(item, content.encode('utf-8'))

    os.remove(AGENT_ZIP)
    os.rename(temp_zip, AGENT_ZIP)
    print("Agent patched successfully.")

if __name__ == "__main__":
    fix_config_json()
    rename_binaries()
    patch_agent()
    print("Done! Push these changes and run on Colab.")
