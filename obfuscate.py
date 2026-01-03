import zipfile
import os
import shutil
import json
import stat
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
                
                try:
                    st = os.stat(new_path)
                    os.chmod(new_path, st.st_mode | stat.S_IEXEC | 0o111)
                except Exception as e:
                    print(f"  Warning: could not set permission on {new_path}: {e}")

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
            # 1. Intercept executable name from server
            ("self.executable_name = binary_download.get_version()['executable']", 
             "self.executable_name = binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
            
            # 2. Ensure absolute path resolution
            ("self.executable_path = Path(self.cracker_path, self.executable_name)",
             "self.executable_path = Path(self.cracker_path, self.executable_name).resolve()"),
            
            # 3. Use absolute path for callPath (avoiding ./ issues)
            ("self.callPath = f\"'./{self.executable_name}'\"",
             "self.callPath = f\"'{self.executable_path}'\""),
            
            # 4. Injected chmod before version check or usage
            ("cmd = [str(self.executable_path), \"--version\"]",
             "try: os.chmod(str(self.executable_path), 0o755)\n        except: pass\n        cmd = [str(self.executable_path), \"--version\"]"),
            
            # 5. Fix for keyspace measure (sometimes it uses raw callPath)
            ("full_cmd = f\"{self.callPath} --keyspace --quiet {files} {task['cmdpars']}\"",
             "try: os.chmod(str(self.executable_path), 0o755)\n        except: pass\n        full_cmd = f\"{self.callPath} --keyspace --quiet {files} {task['cmdpars']}\""),
        ],
        'htpclient/generic_cracker.py': [
            ("self.executable_name = binary_download.get_version()['executable']",
             "self.executable_name = binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
            ("binary_download.get_version()['executable']",
             "binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
            # Robust absolute callPath and chmod
            ("self.callPath = self.config.get_value('crackers-path') + \"/\" + str(cracker_id) + \"/\" + binary_download.get_version()['executable']",
             "self.callPath = os.path.abspath(self.config.get_value('crackers-path') + \"/\" + str(cracker_id) + \"/\" + binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin'))\n        try: os.chmod(self.callPath, 0o755)\n        except: pass")
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
                    # Simple but effective replacements
                    for old_code, new_code in files_to_patch[item.filename]:
                        text = text.replace(old_code, new_code)
                    zout.writestr(item, text.encode('utf-8'))
                else:
                    zout.writestr(item, content)

    os.remove(AGENT_ZIP)
    os.rename(temp_zip, AGENT_ZIP)
    print("Agent patched successfully.")

if __name__ == "__main__":
    fix_config_paths()
    rename_binaries()
    patch_agent()
    print("Done! You can now run the agent with: python hashtopolis.zip --voucher VOUCHER")
