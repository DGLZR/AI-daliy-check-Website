from flask import Flask, send_from_directory, request, jsonify, session
import os
import json
import csv
import smtplib
import random
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from superadmin import superadmin_bp

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24).hex()
app.register_blueprint(superadmin_bp)

# ============ 配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
DATA_DIR = os.path.join(BASE_DIR, 'data')
USERS_CSV = os.path.join(DATA_DIR, 'users.csv')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
FILES_INFO_PATH = os.path.join(BASE_DIR, 'files_info.json')

# 管理员账号
ADMIN_USERNAME = 'frog'
ADMIN_PASSWORD = 'Ab130108'

# 验证码存储
verification_codes = {}

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 加载配置
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'site': {'name': '绿豆蛙日报助手'},
        'upload': {'max_size_mb': 500, 'allowed_extensions': ['exe', 'zip', 'rar', '7z']},
        'smtp': {'server': 'smtp.qq.com', 'port': 465, 'email': '', 'password': '', 'code_expire': 5}
    }

config = load_config()

# ============ CSV用户管理 ============
def init_csv():
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['邮箱', '密码', '注册时间', '状态', '最近登录时间'])

def read_users():
    init_csv()
    users = []
    with open(USERS_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            users.append(row)
    return users

def write_users(users):
    with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
        if users:
            writer = csv.DictWriter(f, fieldnames=users[0].keys())
            writer.writeheader()
            writer.writerows(users)
        else:
            csv.writer(f).writerow(['邮箱', '密码', '注册时间', '状态', '最近登录时间'])

def find_user(email):
    for user in read_users():
        if user['邮箱'] == email:
            return user
    return None

def add_user(email, password):
    users = read_users()
    users.append({
        '邮箱': email,
        '密码': password,
        '注册时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '状态': '正常',
        '最近登录时间': ''
    })
    write_users(users)

def update_user(email, updates):
    users = read_users()
    for user in users:
        if user['邮箱'] == email:
            user.update(updates)
    write_users(users)

def delete_user(email):
    write_users([u for u in read_users() if u['邮箱'] != email])

# ============ 文件管理 ============
def load_files_info():
    if os.path.exists(FILES_INFO_PATH):
        with open(FILES_INFO_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'current_version' not in data:
                data['current_version'] = None
            return data
    return {'files': [], 'current_version': None}

def save_files_info(info):
    with open(FILES_INFO_PATH, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in set(config['upload']['allowed_extensions'])

# ============ 邮件发送 ============
def generate_code():
    return ''.join(random.choices(string.digits, k=6))

def send_email(to_email, subject, content):
    smtp = config.get('smtp', {})
    if not smtp.get('email') or not smtp.get('password'):
        return False, 'SMTP邮箱未配置'
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp['email']
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'html', 'utf-8'))
        
        if smtp['port'] == 465:
            server = smtplib.SMTP_SSL(smtp['server'], smtp['port'])
        else:
            server = smtplib.SMTP(smtp['server'], smtp['port'])
            server.starttls()
        
        server.login(smtp['email'], smtp['password'])
        server.send_message(msg)
        server.quit()
        return True, '发送成功'
    except Exception as e:
        return False, f'发送失败: {str(e)}'

# ============ 静态文件路由 ============
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ============ 文件上传API ============
@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件被上传'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'不允许的文件类型'}), 400
        
        filename = secure_filename(file.filename) or f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.exe"
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        files_info = load_files_info()
        files_info['files'].append({
            'filename': filename,
            'original_name': file.filename,
            'size': os.path.getsize(filepath),
            'upload_time': datetime.now().isoformat(),
            'path': filepath
        })
        if len(files_info['files']) == 1:
            files_info['current_version'] = filename
        save_files_info(files_info)
        
        return jsonify({'message': '上传成功', 'filename': filename}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/<filename>', methods=['DELETE'])
def delete_file(filename):
    files_info = load_files_info()
    file_to_delete = next((f for f in files_info['files'] if f['filename'] == filename), None)
    
    if not file_to_delete:
        return jsonify({'error': '文件不存在'}), 404
    
    if os.path.exists(file_to_delete['path']):
        os.remove(file_to_delete['path'])
    
    files_info['files'] = [f for f in files_info['files'] if f['filename'] != filename]
    if files_info['current_version'] == filename:
        files_info['current_version'] = files_info['files'][-1]['filename'] if files_info['files'] else None
    save_files_info(files_info)
    
    return jsonify({'message': '删除成功'})

@app.route('/api/files/<filename>/set-current', methods=['POST'])
def set_current_version(filename):
    files_info = load_files_info()
    if not any(f['filename'] == filename for f in files_info['files']):
        return jsonify({'error': '文件不存在'}), 404
    
    files_info['current_version'] = filename
    save_files_info(files_info)
    return jsonify({'message': '设置成功'})

@app.route('/api/files', methods=['GET'])
def get_files():
    return jsonify(load_files_info())

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route('/api/latest', methods=['GET'])
def get_latest():
    files_info = load_files_info()
    if files_info['current_version']:
        for f in files_info['files']:
            if f['filename'] == files_info['current_version']:
                return jsonify(f)
    if files_info['files']:
        return jsonify(files_info['files'][-1])
    return jsonify({'message': '暂无可用版本'}), 404

@app.route('/api/config', methods=['GET'])
def get_config():
    safe_config = {k: v for k, v in config.items() if k != 'smtp'}
    return jsonify(safe_config)

# ============ 用户API ============
@app.route('/api/send-code', methods=['POST'])
def send_code():
    email = request.json.get('email', '').strip()
    if not email:
        return jsonify({'success': False, 'message': '请输入邮箱地址'})
    
    code = generate_code()
    verification_codes[email] = {
        'code': code,
        'expire': datetime.now() + timedelta(minutes=config.get('smtp', {}).get('code_expire', 5))
    }
    
    html = f'<div style="font-family:Arial;max-width:500px;margin:0 auto;"><h2 style="color:#4caf50;">绿豆蛙日报助手</h2><p>您的验证码：</p><div style="background:#f5f5f5;padding:20px;text-align:center;font-size:32px;font-weight:bold;letter-spacing:5px;">{code}</div><p style="color:#666;">5分钟内有效</p></div>'
    
    success, message = send_email(email, '验证码', html)
    return jsonify({'success': success, 'message': message if success else message})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email, password, code = data.get('email', '').strip(), data.get('password', '').strip(), data.get('code', '').strip()
    
    if not all([email, password, code]):
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    if email not in verification_codes:
        return jsonify({'success': False, 'message': '请先发送验证码'})
    
    stored = verification_codes[email]
    if datetime.now() > stored['expire']:
        del verification_codes[email]
        return jsonify({'success': False, 'message': '验证码已过期'})
    if stored['code'] != code:
        return jsonify({'success': False, 'message': '验证码错误'})
    
    if find_user(email):
        return jsonify({'success': False, 'message': '该邮箱已注册'})
    
    add_user(email, password)
    del verification_codes[email]
    return jsonify({'success': True, 'message': '注册成功'})

@app.route('/api/login', methods=['POST'])
def login():
    email, password = request.json.get('email', '').strip(), request.json.get('password', '').strip()
    
    if not email or not password:
        return jsonify({'success': False, 'message': '请填写邮箱和密码'})
    
    user = find_user(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'})
    if user['密码'] != password:
        return jsonify({'success': False, 'message': '密码错误'})
    if user['状态'] != '正常':
        return jsonify({'success': False, 'message': '账号已被禁用'})
    
    update_user(email, {'最近登录时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    return jsonify({'success': True, 'message': '登录成功'})

# ============ 管理员API ============
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    if request.json.get('username') == ADMIN_USERNAME and request.json.get('password') == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    return jsonify({'success': True})

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    return jsonify({'success': True, 'users': read_users()})

@app.route('/api/admin/users/<email>', methods=['DELETE'])
def admin_delete_user(email):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    delete_user(email)
    return jsonify({'success': True})

@app.route('/api/admin/users/<email>/status', methods=['POST'])
def admin_update_status(email):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    status = request.json.get('status')
    if status in ['正常', '禁用']:
        update_user(email, {'状态': status})
    return jsonify({'success': True})

@app.route('/api/admin/config', methods=['GET'])
def admin_get_config():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    smtp = config.get('smtp', {}).copy()
    if smtp.get('password'):
        smtp['password'] = '********'
    return jsonify({'success': True, 'config': smtp})

@app.route('/api/admin/config', methods=['POST'])
def admin_update_config():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    data = request.json
    if 'smtp' not in config:
        config['smtp'] = {}
    
    for key in ['server', 'port', 'email', 'password', 'code_expire']:
        if key in data:
            if key == 'password' and data[key] == '********':
                continue
            config['smtp'][key] = int(data[key]) if key in ['port', 'code_expire'] else data[key]
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return jsonify({'success': True, 'message': '配置已保存'})

@app.route('/api/admin/test-email', methods=['POST'])
def admin_test_email():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    email = request.json.get('email', '').strip()
    if not email:
        return jsonify({'success': False, 'message': '请输入测试邮箱'})
    
    html = '<div style="font-family:Arial;"><h2 style="color:#4caf50;">测试邮件</h2><p>SMTP配置正常！</p></div>'
    success, message = send_email(email, 'SMTP测试', html)
    return jsonify({'success': success, 'message': message})

if __name__ == '__main__':
    init_csv()
    app.run(host='0.0.0.0', port=5000, debug=True)