import zipfile
import os
import shutil
import json
from pathlib import Path

# Configuration
BASE_DIR = Path(r'C:\Users\teiiamu\LLM\hash')
CRACKERS_DIR = BASE_DIR / 'crackers'
AGENT_ZIP = BASE_DIR / 'hashtopolis.zip'
AGENT_ZIP_BAK = BASE_DIR / 'hashtopolis.zip.bak'
CONFIG_FILE = BASE_DIR / 'config.json'
NEW_EXE_NAME = 'pippo.bin'
OLD_EXE_NAME = 'hashcat.bin'

def fix_config_paths():
    if not CONFIG_FILE.exists():
        print("config.json not found, skipping path fix.")
        return
    
    print("Fixing paths and resetting identity in config.json...")
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    path_map = {
        "files-path": "files",
        "crackers-path": "crackers",
        "hashlists-path": "hashlists",
        "zaps-path": ".",
        "preprocessors-path": "preprocessors"
    }

    modified = False
    for key, rel_val in path_map.items():
        if key in config:
            if ':' in config[key] or '\\' in config[key] or config[key].startswith('/'):
                print(f"  {key}: {config[key]} -> {rel_val}")
                config[key] = rel_val
                modified = True
    
    if config.get("token") or config.get("uuid"):
        print("  Clearing token and uuid for fresh registration...")
        config["token"] = ""
        config["uuid"] = ""
        modified = True
    
    if modified:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print("config.json updated.")
    else:
        print("config.json already cleaned.")

def rename_binaries():
    print("Searching for binaries to rename...")
    if not CRACKERS_DIR.exists():
        print("Crackers directory not found.")
        return
        
    for root, dirs, files in os.walk(CRACKERS_DIR):
        for file in files:
            if file == OLD_EXE_NAME:
                old_path = Path(root) / file
                new_path = Path(root) / NEW_EXE_NAME
                print(f"Renaming {old_path} -> {new_path}")
                shutil.copy2(old_path, new_path)
                os.remove(old_path)

def patch_agent():
    if not AGENT_ZIP.exists():
        print(f"Error: {AGENT_ZIP} not found.")
        return

    print(f"Patching {AGENT_ZIP}...")
    
    if not AGENT_ZIP_BAK.exists():
        shutil.copy2(AGENT_ZIP, AGENT_ZIP_BAK)

    temp_zip = BASE_DIR / 'hashtopolis.zip.tmp'
    
    files_to_patch = {
        'htpclient/hashcat_cracker.py': [
            # 1. Rename logic
            ("self.executable_name = binary_download.get_version()['executable']", 
             "self.executable_name = binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
            # 2. Path resolution fix (crucial for Linux/Colab)
            ("self.executable_path = Path(self.cracker_path, self.executable_name)",
             "self.executable_path = Path(self.cracker_path, self.executable_name).resolve()"),
        ],
        'htpclient/generic_cracker.py': [
            ("self.executable_name = binary_download.get_version()['executable']",
             "self.executable_name = binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
            ("binary_download.get_version()['executable']",
             "binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
            # Fix callPath to be absolute
            ("self.callPath = self.config.get_value('crackers-path') + \"/\" + str(cracker_id) + \"/\" + binary_download.get_version()['executable']",
             "self.callPath = os.path.abspath(self.config.get_value('crackers-path') + \"/\" + str(cracker_id) + \"/\" + binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin'))")
        ],
        'htpclient/binarydownload.py': [
             ("ans['executable']", "ans['executable'].replace('hashcat.bin', 'pippo.bin')")
        ]
    }

    with zipfile.ZipFile(AGENT_ZIP, 'r') as zin:
        with zipfile.ZipFile(temp_zip, 'w') as zout:
            for item in zin.infolist():
                content = zin.read(item.filename)
                
                if item.filename in files_to_patch:
                    print(f"  Patching {item.filename}...")
                    text = content.decode('utf-8')
                    for old_code, new_code in files_to_patch[item.filename]:
                        text = text.replace(old_code, new_code)
                    zout.writestr(item, text.encode('utf-8'))
                else:
                    zout.writestr(item, content)

    os.remove(AGENT_ZIP)
    os.rename(temp_zip, AGENT_ZIP)
    print("Agent patched successfully.")

if __name__ == "__main__":
    # Ensure backups or fresh state if needed
    fix_config_paths()
    rename_binaries()
    patch_agent()
    print("Done! You can now run the agent with: python hashtopolis.zip --voucher VOUCHER")
