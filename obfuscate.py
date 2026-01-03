import zipfile
import os
import shutil
from pathlib import Path

# Configuration
BASE_DIR = Path(r'C:\Users\teiiamu\LLM\hash')
CRACKERS_DIR = BASE_DIR / 'crackers'
AGENT_ZIP = BASE_DIR / 'hashtopolis.zip'
AGENT_ZIP_BAK = BASE_DIR / 'hashtopolis.zip.bak'
NEW_EXE_NAME = 'pippo.bin'
OLD_EXE_NAME = 'hashcat.bin'

def rename_binaries():
    print("Searching for binaries to rename...")
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
    
    # Backup
    if not AGENT_ZIP_BAK.exists():
        shutil.copy2(AGENT_ZIP, AGENT_ZIP_BAK)

    temp_zip = BASE_DIR / 'hashtopolis.zip.tmp'
    
    files_to_patch = {
        'htpclient/hashcat_cracker.py': [
            # Patch HashcatCracker.__init__ to force pippo.bin if hashcat.bin is received
            ("self.executable_name = binary_download.get_version()['executable']", 
             "self.executable_name = binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
        ],
        'htpclient/generic_cracker.py': [
            # Patch GenericCracker.__init__
            ("self.executable_name = binary_download.get_version()['executable']",
             "self.executable_name = binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')"),
            ("binary_download.get_version()['executable']",
             "binary_download.get_version()['executable'].replace('hashcat.bin', 'pippo.bin')")
        ],
        'htpclient/binarydownload.py': [
            # Patching check_version to use pippo.bin strings during download/extraction logic if any
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
    rename_binaries()
    patch_agent()
    print("Done! You can now run the agent with: python hashtopolis.zip")
