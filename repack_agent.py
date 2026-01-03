import zipfile
import os

source_dir = r'C:\Users\teiiamu\LLM\hash\hashtopolis-source'
output_zip = r'C:\Users\teiiamu\LLM\hash\hashtopolis.zip'

def repack():
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(source_dir):
            if '.git' in root or '.github' in root:
                continue
            for file in files:
                if file == '.gitignore' or file == 'README.md' or file == 'LICENSE':
                    continue
                path = os.path.join(root, file)
                arcname = os.path.relpath(path, source_dir)
                z.write(path, arcname)
    print(f"Repacked {output_zip} successfully.")

if __name__ == "__main__":
    repack()
