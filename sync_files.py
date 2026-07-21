import os
import json
from datetime import datetime

print("=" * 50)
print("同步uploads目录到files_info.json")
print("=" * 50)

# 获取uploads目录中的所有文件
upload_dir = "uploads"
files_info = {"files": []}

if os.path.exists(upload_dir):
    for filename in os.listdir(upload_dir):
        if filename == ".gitkeep":
            continue
        
        filepath = os.path.join(upload_dir, filename)
        if os.path.isfile(filepath):
            file_info = {
                "filename": filename,
                "original_name": filename,
                "size": os.path.getsize(filepath),
                "upload_time": datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                "path": filepath
            }
            files_info["files"].append(file_info)
            print(f"[OK] {filename} ({file_info['size'] / 1024 / 1024:.2f} MB)")

# 保存到files_info.json
with open("files_info.json", "w", encoding="utf-8") as f:
    json.dump(files_info, f, ensure_ascii=False, indent=2)

print(f"\n共同步 {len(files_info['files'])} 个文件")
print("=" * 50)