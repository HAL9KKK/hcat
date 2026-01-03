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
            # Convert Windows backslashes to relative forward slashes
            new_val = str(val).replace('\\', '/').rstrip('/')
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
                if new_path.exists(): os.remove(new_path)
                shutil.copy2(old_path, new_path)
                os.remove(old_path)
                try:
                    os.chmod(new_path, os.stat(new_path).st_mode | 0o111)
                except: pass

def patch_agent():
    if not AGENT_ZIP.exists(): return
    print(f"Patching {AGENT_ZIP}...")

    # We expect AGENT_ZIP to be the restored clean version from git
    # If backup doesn't exist, create it from current
    if not AGENT_ZIP_BAK.exists():
        shutil.copy2(AGENT_ZIP, AGENT_ZIP_BAK)
    
    temp_zip = BASE_DIR / 'hashtopolis.zip.tmp'
    
    with zipfile.ZipFile(AGENT_ZIP, 'r') as zin, zipfile.ZipFile(temp_zip, 'w') as zout:
        for item in zin.infolist():
            content = zin.read(item.filename).decode('utf-8', errors='ignore')
            lines = content.splitlines()
            new_lines = []
            patched = False
            
            for line in lines:
                indent = line[:len(line) - len(line.lstrip())]
                
                # 1. config.py patch (preserve original indentation)
                if item.filename == 'htpclient/config.py':
                    if "return self.config[key]" in line:
                        new_lines.append(f"{indent}val = self.config[key]")
                        new_lines.append(f"{indent}if key.endswith('-path'): return os.path.abspath(val)")
                        new_lines.append(f"{indent}return val")
                        patched = True
                        continue
                
                # 2. binarydownload.py patch
                elif item.filename == 'htpclient/binarydownload.py':
                    if "ans['executable']" in line and 'pippo.bin' not in line:
                        line = line.replace("ans['executable']", "ans['executable'].replace('hashcat.bin', 'pippo.bin')")
                        patched = True
                
                # 3. hashcat_cracker.py patch
                elif item.filename == 'htpclient/hashcat_cracker.py':
                    if "['executable']" in line and "pippo.bin" not in line:
                        line = line.replace("['executable']", "['executable'].replace('hashcat.bin', 'pippo.bin')")
                        patched = True
                    if "self.executable_path = Path(self.cracker_path, self.executable_name)" in line:
                        line = line.replace("self.executable_name)", "self.executable_name).resolve()")
                        new_lines.append(line)
                        new_lines.append(f"{indent}try: os.chmod(str(self.executable_path), 0o755)")
                        new_lines.append(f"{indent}except: pass")
                        patched = True
                        continue
                    if "f'./{self.executable_name}'" in line or "f\"'./{self.executable_name}'\"" in line:
                        line = f"{indent}self.callPath = f'{{self.executable_path}}'"
                        patched = True
                    elif "self.callPath = f'\"' + './' + self.executable_name + '\"'" in line:
                        line = f"{indent}self.callPath = f'{{self.executable_path}}'"
                        patched = True

                # 4. generic_cracker.py patch
                elif item.filename == 'htpclient/generic_cracker.py':
                    if "['executable']" in line and "pippo.bin" not in line:
                        line = line.replace("['executable']", "['executable'].replace('hashcat.bin', 'pippo.bin')")
                        patched = True
                    if "self.callPath = " in line and "binary_download.get_version()['executable']" in line:
                        line = f"{indent}self.callPath = os.path.abspath(self.config.get_value('crackers-path') + \"/\" + str(cracker_id) + \"/\" + binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin'))"
                        new_lines.append(line)
                        new_lines.append(f"{indent}try: os.chmod(self.callPath, 0o755)")
                        new_lines.append(f"{indent}except: pass")
                        patched = True
                        continue

                new_lines.append(line)
            
            if patched:
                print(f"  Applied patches to {item.filename}")
                new_content = "\n".join(new_lines)
                if "os." in new_content and "import os" not in new_content:
                    new_content = "import os\n" + new_content
                zout.writestr(item, new_content.encode('utf-8'))
            else:
                zout.writestr(item, zin.read(item.filename))

    os.remove(AGENT_ZIP)
    os.rename(temp_zip, AGENT_ZIP)
    print("Agent patched successfully.")

if __name__ == "__main__":
    fix_config_json()
    rename_binaries()
    patch_agent()
    print("Done!")
