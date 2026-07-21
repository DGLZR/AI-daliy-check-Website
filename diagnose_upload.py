import os
import sys

print("=" * 50)
print("上传功能诊断")
print("=" * 50)

# 1. 检查uploads目录
print("\n1. 检查uploads目录:")
upload_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if os.path.exists(upload_dir):
    print(f"   [OK] 目录存在: {upload_dir}")
    if os.access(upload_dir, os.W_OK):
        print("   [OK] 目录可写")
    else:
        print("   [ERROR] 目录不可写，请检查权限")
else:
    print(f"   [ERROR] 目录不存在: {upload_dir}")
    try:
        os.makedirs(upload_dir, exist_ok=True)
        print("   [OK] 已创建目录")
    except Exception as e:
        print(f"   [ERROR] 创建目录失败: {e}")

# 2. 检查配置文件
print("\n2. 检查配置文件:")
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
if os.path.exists(config_path):
    import json
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"   [OK] 配置文件存在")
    print(f"   允许的文件类型: {config['upload']['allowed_extensions']}")
    print(f"   最大文件大小: {config['upload']['max_size_mb']}MB")
else:
    print("   [ERROR] 配置文件不存在")

# 3. 检查Flask导入
print("\n3. 检查Flask:")
try:
    from flask import Flask
    print(f"   [OK] Flask已安装")
except ImportError:
    print("   [ERROR] Flask未安装，请运行: pip install flask")

# 4. 测试文件创建
print("\n4. 测试文件写入:")
test_file = os.path.join(upload_dir, 'test_write.txt')
try:
    with open(test_file, 'w') as f:
        f.write('test')
    os.remove(test_file)
    print("   [OK] 文件写入测试成功")
except Exception as e:
    print(f"   [ERROR] 文件写入测试失败: {e}")

# 5. 检查secure_filename
print("\n5. 检查secure_filename:")
try:
    from werkzeug.utils import secure_filename
    test_name = secure_filename("test.exe")
    print(f"   [OK] secure_filename正常: test.exe -> {test_name}")
except Exception as e:
    print(f"   [ERROR] secure_filename失败: {e}")

print("\n" + "=" * 50)
print("诊断完成")
print("=" * 50)