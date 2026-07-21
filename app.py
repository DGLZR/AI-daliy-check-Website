from flask import Flask, send_from_directory, request, jsonify, redirect, url_for
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

# 加载配置文件
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    config = {
        'upload': {
            'max_size_mb': 500,
            'allowed_extensions': ['exe', 'zip', 'rar', '7z'],
            'upload_folder': 'uploads'
        }
    }

app = Flask(__name__, static_folder='static')

# 配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), config['upload']['upload_folder'])
ALLOWED_EXTENSIONS = set(config['upload']['allowed_extensions'])
MAX_CONTENT_LENGTH = config['upload']['max_size_mb'] * 1024 * 1024

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 存储文件信息的JSON文件
FILES_INFO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files_info.json')

def load_files_info():
    if os.path.exists(FILES_INFO_PATH):
        with open(FILES_INFO_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 确保有current_version字段
            if 'current_version' not in data:
                data['current_version'] = None
            return data
    return {'files': [], 'current_version': None}

def save_files_info(info):
    with open(FILES_INFO_PATH, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 静态文件路由
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# 文件上传API
@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件被上传'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({'error': f'不允许的文件类型，支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # 处理文件名
        filename = secure_filename(file.filename)
        if not filename:
            filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.exe"
        
        # 添加时间戳避免重名
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}{ext}"
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # 保存文件
        file.save(filepath)
        
        # 验证文件是否保存成功
        if not os.path.exists(filepath):
            return jsonify({'error': '文件保存失败'}), 500
        
        # 保存文件信息
        files_info = load_files_info()
        file_info = {
            'filename': filename,
            'original_name': file.filename,
            'size': os.path.getsize(filepath),
            'upload_time': datetime.now().isoformat(),
            'path': filepath
        }
        files_info['files'].append(file_info)
        
        # 如果是第一个文件，自动设为当前版本
        if len(files_info['files']) == 1:
            files_info['current_version'] = filename
        
        save_files_info(files_info)
        
        print(f"文件上传成功: {filename} ({file_info['size']} bytes)")
        
        return jsonify({
            'message': '文件上传成功',
            'filename': filename,
            'size': file_info['size']
        }), 200
        
    except Exception as e:
        print(f"上传错误: {str(e)}")
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

# 删除文件API
@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    try:
        files_info = load_files_info()
        
        # 查找文件
        file_to_delete = None
        for f in files_info['files']:
            if f['filename'] == filename:
                file_to_delete = f
                break
        
        if not file_to_delete:
            return jsonify({'error': '文件不存在'}), 404
        
        # 删除实际文件
        filepath = file_to_delete['path']
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # 从列表中移除
        files_info['files'] = [f for f in files_info['files'] if f['filename'] != filename]
        
        # 如果删除的是当前版本，重置当前版本
        if files_info['current_version'] == filename:
            files_info['current_version'] = files_info['files'][-1]['filename'] if files_info['files'] else None
        
        save_files_info(files_info)
        
        print(f"文件删除成功: {filename}")
        
        return jsonify({'message': '文件删除成功'}), 200
        
    except Exception as e:
        print(f"删除错误: {str(e)}")
        return jsonify({'error': f'删除失败: {str(e)}'}), 500

# 设置当前版本API
@app.route('/api/files/<filename>/set-current', methods=['POST'])
def set_current_version(filename):
    try:
        files_info = load_files_info()
        
        # 查找文件
        file_exists = any(f['filename'] == filename for f in files_info['files'])
        
        if not file_exists:
            return jsonify({'error': '文件不存在'}), 404
        
        # 设置当前版本
        files_info['current_version'] = filename
        save_files_info(files_info)
        
        print(f"设置当前版本: {filename}")
        
        return jsonify({'message': '设置成功', 'current_version': filename}), 200
        
    except Exception as e:
        print(f"设置错误: {str(e)}")
        return jsonify({'error': f'设置失败: {str(e)}'}), 500

# 获取文件列表
@app.route('/api/files', methods=['GET'])
def get_files():
    files_info = load_files_info()
    return jsonify(files_info), 200

# 下载文件
@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# 获取最新版本（当前版本）
@app.route('/api/latest', methods=['GET'])
def get_latest():
    files_info = load_files_info()
    
    # 优先返回当前版本
    if files_info['current_version']:
        for f in files_info['files']:
            if f['filename'] == files_info['current_version']:
                return jsonify(f), 200
    
    # 如果没有当前版本，返回最后一个
    if files_info['files']:
        latest = files_info['files'][-1]
        return jsonify(latest), 200
    
    return jsonify({'message': '暂无可用版本'}), 404

# 管理页面
@app.route('/admin')
def admin():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>版本管理 - 绿豆蛙日报助手</title>
        <meta charset="UTF-8">
        <link rel="icon" href="/favicon.jpg" type="image/jpeg">
        <style>
            * { box-sizing: border-box; }
            body { 
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; 
                max-width: 900px; 
                margin: 0 auto; 
                padding: 20px; 
                background: #f0f9f0; 
                color: #333;
            }
            h1 { 
                color: #2e7d32; 
                display: flex;
                align-items: center;
                gap: 15px;
            }
            h1 img {
                width: 50px;
                height: 50px;
                border-radius: 50%;
                object-fit: cover;
            }
            .upload-form { 
                background: white; 
                padding: 25px; 
                border-radius: 12px; 
                margin: 20px 0; 
                box-shadow: 0 2px 15px rgba(46, 125, 50, 0.1); 
                border: 1px solid #c8e6c9;
            }
            .file-list { margin-top: 30px; }
            .file-list h2 { color: #2e7d32; }
            .file-item { 
                background: white; 
                padding: 20px; 
                margin: 15px 0; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(46, 125, 50, 0.1); 
                border: 1px solid #c8e6c9;
                transition: all 0.3s ease;
            }
            .file-item:hover {
                box-shadow: 0 4px 20px rgba(46, 125, 50, 0.2);
                transform: translateY(-2px);
            }
            .file-item.current {
                border-left: 4px solid #4caf50;
                background: #f1f8e9;
            }
            .file-info {
                margin-bottom: 15px;
            }
            .file-info strong {
                font-size: 16px;
                color: #1b5e20;
            }
            .file-info small {
                display: block;
                margin-top: 5px;
                color: #666;
            }
            .file-actions {
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }
            button { 
                background: #4caf50; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 6px; 
                cursor: pointer; 
                font-size: 14px;
                transition: all 0.3s ease;
            }
            button:hover { 
                background: #388e3c; 
                transform: translateY(-1px);
            }
            button.danger { background: #ef5350; }
            button.danger:hover { background: #c62828; }
            button.secondary { background: #78909c; }
            button.secondary:hover { background: #546e7a; }
            button.success { background: #66bb6a; }
            button:disabled {
                background: #ccc;
                cursor: not-allowed;
                transform: none;
            }
            input[type="file"] { 
                padding: 12px; 
                margin-right: 10px; 
                border: 2px dashed #a5d6a7;
                border-radius: 8px;
                background: #f1f8e9;
                width: 100%;
                margin-bottom: 15px;
            }
            .info-box { 
                background: #e8f5e9; 
                padding: 15px 20px; 
                border-radius: 8px; 
                margin: 15px 0; 
                border-left: 4px solid #4caf50;
            }
            .error-box { 
                background: #ffebee; 
                color: #c62828; 
                padding: 15px 20px; 
                border-radius: 8px; 
                margin: 15px 0; 
                border-left: 4px solid #ef5350;
            }
            .success-box { 
                background: #e8f5e9; 
                color: #2e7d32; 
                padding: 15px 20px; 
                border-radius: 8px; 
                margin: 15px 0; 
                border-left: 4px solid #4caf50;
            }
            .badge {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                margin-left: 10px;
            }
            .badge-current {
                background: #4caf50;
                color: white;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #4caf50;
                text-decoration: none;
            }
            .back-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <a href="/" class="back-link">← 返回首页</a>
        
        <h1>
            <img src="/favicon.jpg" alt="绿豆蛙">
            版本管理
        </h1>
        
        <div class="info-box">
            <strong>提示：</strong>支持上传 .exe, .zip, .rar, .7z 格式的文件，最大 500MB。您可以删除旧版本并选择用户下载的版本。
        </div>
        
        <div class="upload-form">
            <h2>上传新版本</h2>
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" name="file" accept=".exe,.zip,.rar,.7z" required>
                <button type="submit">上传新版本</button>
            </form>
            <div id="uploadResult"></div>
        </div>
        
        <div class="file-list">
            <h2>已上传版本</h2>
            <div id="fileList"></div>
        </div>

        <script>
            // 上传文件
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const formData = new FormData(e.target);
                const result = document.getElementById('uploadResult');
                const fileInput = e.target.querySelector('input[type="file"]');
                const file = fileInput.files[0];
                
                const allowedTypes = ['.exe', '.zip', '.rar', '.7z'];
                const fileName = file.name.toLowerCase();
                const isValidType = allowedTypes.some(type => fileName.endsWith(type));
                
                if (!isValidType) {
                    result.innerHTML = '<div class="error-box">错误: 不支持的文件类型，请上传 .exe, .zip, .rar, .7z 格式的文件</div>';
                    return;
                }
                
                if (file.size > 500 * 1024 * 1024) {
                    result.innerHTML = '<div class="error-box">错误: 文件太大，最大支持 500MB</div>';
                    return;
                }
                
                result.innerHTML = '<p>正在上传...</p>';
                
                try {
                    const response = await fetch('/api/upload', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (response.ok) {
                        result.innerHTML = '<div class="success-box">上传成功: ' + data.filename + ' (' + (data.size / 1024 / 1024).toFixed(2) + ' MB)</div>';
                        fileInput.value = '';
                        loadFiles();
                    } else {
                        result.innerHTML = '<div class="error-box">错误: ' + data.error + '</div>';
                    }
                } catch (error) {
                    result.innerHTML = '<div class="error-box">上传失败: ' + error.message + '</div>';
                }
            });

            // 加载文件列表
            async function loadFiles() {
                const response = await fetch('/api/files');
                const data = await response.json();
                const fileList = document.getElementById('fileList');
                
                if (data.files && data.files.length > 0) {
                    fileList.innerHTML = data.files.reverse().map(file => {
                        const isCurrent = data.current_version === file.filename;
                        return `
                            <div class="file-item ${isCurrent ? 'current' : ''}">
                                <div class="file-info">
                                    <strong>${file.original_name}</strong>
                                    ${isCurrent ? '<span class="badge badge-current">当前版本</span>' : ''}
                                    <br>
                                    <small>大小: ${(file.size / 1024 / 1024).toFixed(2)} MB</small>
                                    <small>上传时间: ${new Date(file.upload_time).toLocaleString()}</small>
                                    <small>文件名: ${file.filename}</small>
                                </div>
                                <div class="file-actions">
                                    <a href="/download/${file.filename}" download>
                                        <button class="secondary">下载</button>
                                    </a>
                                    ${!isCurrent ? `<button class="success" onclick="setCurrentVersion('${file.filename}')">设为当前版本</button>` : ''}
                                    <button class="danger" onclick="deleteFile('${file.filename}', '${file.original_name}')">删除</button>
                                </div>
                            </div>
                        `;
                    }).join('');
                } else {
                    fileList.innerHTML = '<p>暂无文件</p>';
                }
            }

            // 删除文件
            async function deleteFile(filename, originalName) {
                if (!confirm(`确定要删除 "${originalName}" 吗？此操作不可撤销。`)) {
                    return;
                }
                
                try {
                    const response = await fetch(`/api/files/${filename}`, {
                        method: 'DELETE'
                    });
                    const data = await response.json();
                    if (response.ok) {
                        alert('删除成功');
                        loadFiles();
                    } else {
                        alert('删除失败: ' + data.error);
                    }
                } catch (error) {
                    alert('删除失败: ' + error.message);
                }
            }

            // 设置当前版本
            async function setCurrentVersion(filename) {
                try {
                    const response = await fetch(`/api/files/${filename}/set-current`, {
                        method: 'POST'
                    });
                    const data = await response.json();
                    if (response.ok) {
                        alert('设置成功，用户将下载此版本');
                        loadFiles();
                    } else {
                        alert('设置失败: ' + data.error);
                    }
                } catch (error) {
                    alert('设置失败: ' + error.message);
                }
            }

            loadFiles();
        </script>
    </body>
    </html>
    '''

# 获取配置信息
@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(config), 200

if __name__ == '__main__':
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host=config['server']['host'], port=config['server']['port'], debug=debug)