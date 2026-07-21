from flask import Flask, request, jsonify, session, redirect
import os
import csv
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import json
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()

# 配置
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
USERS_CSV = os.path.join(DATA_DIR, 'users.csv')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')

# 管理员账号
ADMIN_USERNAME = 'frog'
ADMIN_PASSWORD = 'Ab130108'

# 验证码存储
verification_codes = {}

# 确保data目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 默认配置
DEFAULT_CONFIG = {
    'smtp_server': 'smtp.qq.com',
    'smtp_port': 465,
    'smtp_email': '',
    'smtp_password': '',
    'code_expire_minutes': 5
}

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()

def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def init_csv():
    """初始化CSV文件"""
    if not os.path.exists(USERS_CSV):
        with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['邮箱', '密码', '注册时间', '状态', '最近登录时间'])

def read_users():
    """读取所有用户"""
    init_csv()
    users = []
    with open(USERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append(row)
    return users

def write_users(users):
    """写入所有用户"""
    with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
        if users:
            writer = csv.DictWriter(f, fieldnames=users[0].keys())
            writer.writeheader()
            writer.writerows(users)
        else:
            writer = csv.writer(f)
            writer.writerow(['邮箱', '密码', '注册时间', '状态', '最近登录时间'])

def find_user(email):
    """查找用户"""
    users = read_users()
    for user in users:
        if user['邮箱'] == email:
            return user
    return None

def add_user(email, password):
    """添加用户"""
    users = read_users()
    new_user = {
        '邮箱': email,
        '密码': password,
        '注册时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        '状态': '正常',
        '最近登录时间': ''
    }
    users.append(new_user)
    write_users(users)
    return new_user

def update_user(email, updates):
    """更新用户"""
    users = read_users()
    for user in users:
        if user['邮箱'] == email:
            user.update(updates)
            break
    write_users(users)

def delete_user(email):
    """删除用户"""
    users = read_users()
    users = [u for u in users if u['邮箱'] != email]
    write_users(users)

def generate_code():
    """生成6位验证码"""
    return ''.join(random.choices(string.digits, k=6))

def send_email(to_email, subject, content):
    """发送邮件"""
    config = load_config()
    
    if not config['smtp_email'] or not config['smtp_password']:
        return False, 'SMTP邮箱未配置'
    
    try:
        msg = MIMEMultipart()
        msg['From'] = config['smtp_email']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(content, 'html', 'utf-8'))
        
        if config['smtp_port'] == 465:
            server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'])
        else:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
        
        server.login(config['smtp_email'], config['smtp_password'])
        server.send_message(msg)
        server.quit()
        
        return True, '发送成功'
    except Exception as e:
        return False, f'发送失败: {str(e)}'

# ============ API接口 ============

@app.route('/api/send-code', methods=['POST'])
def send_code():
    """发送验证码"""
    data = request.json
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': '请输入邮箱地址'})
    
    code = generate_code()
    expire_minutes = load_config()['code_expire_minutes']
    verification_codes[email] = {
        'code': code,
        'expire': datetime.now() + timedelta(minutes=expire_minutes)
    }
    
    html_content = f'''
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <h2 style="color: #4caf50;">绿豆蛙日报助手 - 验证码</h2>
        <p>您的验证码是：</p>
        <div style="background: #f5f5f5; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; color: #333; letter-spacing: 5px;">
            {code}
        </div>
        <p style="color: #666;">验证码 {expire_minutes} 分钟内有效，请勿泄露给他人。</p>
    </div>
    '''
    
    success, message = send_email(email, '绿豆蛙日报助手 - 验证码', html_content)
    
    if success:
        return jsonify({'success': True, 'message': '验证码已发送'})
    else:
        return jsonify({'success': False, 'message': message})

@app.route('/api/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    code = data.get('code', '').strip()
    
    if not email or not password or not code:
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    # 验证验证码
    if email not in verification_codes:
        return jsonify({'success': False, 'message': '请先发送验证码'})
    
    stored = verification_codes[email]
    if datetime.now() > stored['expire']:
        del verification_codes[email]
        return jsonify({'success': False, 'message': '验证码已过期'})
    
    if stored['code'] != code:
        return jsonify({'success': False, 'message': '验证码错误'})
    
    # 检查用户是否已存在
    if find_user(email):
        return jsonify({'success': False, 'message': '该邮箱已注册'})
    
    # 注册用户
    add_user(email, password)
    del verification_codes[email]
    
    return jsonify({'success': True, 'message': '注册成功'})

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if not email or not password:
        return jsonify({'success': False, 'message': '请填写邮箱和密码'})
    
    user = find_user(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'})
    
    if user['密码'] != password:
        return jsonify({'success': False, 'message': '密码错误'})
    
    if user['状态'] != '正常':
        return jsonify({'success': False, 'message': '账号已被禁用'})
    
    # 更新最近登录时间
    update_user(email, {'最近登录时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    
    return jsonify({'success': True, 'message': '登录成功'})

# ============ 管理员接口 ============

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True, 'message': '登录成功'})
    
    return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """管理员登出"""
    session.pop('admin_logged_in', None)
    return jsonify({'success': True, 'message': '已登出'})

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    """获取所有用户"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    users = read_users()
    return jsonify({'success': True, 'users': users})

@app.route('/api/admin/users/<email>', methods=['DELETE'])
def admin_delete_user(email):
    """删除用户"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    delete_user(email)
    return jsonify({'success': True, 'message': '删除成功'})

@app.route('/api/admin/users/<email>/status', methods=['POST'])
def admin_update_status(email):
    """更新用户状态"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    data = request.json
    status = data.get('status', '').strip()
    
    if status not in ['正常', '禁用']:
        return jsonify({'success': False, 'message': '无效的状态'})
    
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    update_user(email, {'状态': status})
    return jsonify({'success': True, 'message': '状态更新成功'})

@app.route('/api/admin/config', methods=['GET'])
def admin_get_config():
    """获取SMTP配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    config = load_config()
    # 隐藏密码
    if config.get('smtp_password'):
        config['smtp_password'] = '********'
    return jsonify({'success': True, 'config': config})

@app.route('/api/admin/config', methods=['POST'])
def admin_update_config():
    """更新SMTP配置"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    data = request.json
    config = load_config()
    
    if 'smtp_server' in data:
        config['smtp_server'] = data['smtp_server']
    if 'smtp_port' in data:
        config['smtp_port'] = int(data['smtp_port'])
    if 'smtp_email' in data:
        config['smtp_email'] = data['smtp_email']
    if 'smtp_password' in data and data['smtp_password'] != '********':
        config['smtp_password'] = data['smtp_password']
    if 'code_expire_minutes' in data:
        config['code_expire_minutes'] = int(data['code_expire_minutes'])
    
    save_config(config)
    return jsonify({'success': True, 'message': '配置更新成功'})

@app.route('/api/admin/test-email', methods=['POST'])
def admin_test_email():
    """测试邮件发送"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    data = request.json
    to_email = data.get('email', '').strip()
    
    if not to_email:
        return jsonify({'success': False, 'message': '请输入测试邮箱'})
    
    html_content = '''
    <div style="font-family: Arial, sans-serif; max-width: 500px; margin: 0 auto;">
        <h2 style="color: #4caf50;">测试邮件</h2>
        <p>这是一封测试邮件，SMTP配置正常！</p>
        <p style="color: #666;">发送时间: ''' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '''</p>
    </div>
    '''
    
    success, message = send_email(to_email, 'SMTP测试邮件', html_content)
    return jsonify({'success': success, 'message': message})

# ============ 管理界面 ============

@app.route('/superadmin')
def superadmin_page():
    """管理界面"""
    return '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>超级管理后台 - 绿豆蛙日报助手</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #f0f9f0; }
            
            /* 登录页面 */
            .login-container {
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
            }
            .login-box {
                background: white;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 8px 32px rgba(46, 125, 50, 0.2);
                width: 400px;
            }
            .login-box h1 {
                color: #2e7d32;
                text-align: center;
                margin-bottom: 30px;
                font-size: 24px;
            }
            .login-box input {
                width: 100%;
                padding: 14px 16px;
                border: 2px solid #c8e6c9;
                border-radius: 8px;
                font-size: 16px;
                margin-bottom: 16px;
                transition: border-color 0.3s;
            }
            .login-box input:focus {
                outline: none;
                border-color: #4caf50;
            }
            .login-box button {
                width: 100%;
                padding: 14px;
                background: #4caf50;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                cursor: pointer;
                transition: background 0.3s;
            }
            .login-box button:hover { background: #388e3c; }
            .error-msg { color: #ef5350; text-align: center; margin-top: 10px; }
            
            /* 管理界面 */
            .admin-container { display: none; }
            .admin-container.active { display: block; }
            
            .header {
                background: white;
                padding: 20px 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header h1 { color: #2e7d32; font-size: 20px; }
            .header button {
                padding: 10px 20px;
                background: #ef5350;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
            }
            
            .main { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
            
            .tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 20px;
            }
            .tab {
                padding: 12px 24px;
                background: white;
                border: 2px solid #c8e6c9;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .tab.active {
                background: #4caf50;
                color: white;
                border-color: #4caf50;
            }
            
            .panel { display: none; }
            .panel.active { display: block; }
            
            .card {
                background: white;
                padding: 25px;
                border-radius: 12px;
                box-shadow: 0 2px 15px rgba(0,0,0,0.08);
                margin-bottom: 20px;
            }
            .card h2 { color: #2e7d32; margin-bottom: 20px; font-size: 18px; }
            
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 14px 16px;
                text-align: left;
                border-bottom: 1px solid #e0e0e0;
            }
            th { background: #f5f5f5; font-weight: 600; color: #333; }
            
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s;
            }
            .btn-success { background: #4caf50; color: white; }
            .btn-success:hover { background: #388e3c; }
            .btn-danger { background: #ef5350; color: white; }
            .btn-danger:hover { background: #c62828; }
            .btn-info { background: #2196f3; color: white; }
            .btn-info:hover { background: #1565c0; }
            .btn-warning { background: #ff9800; color: white; }
            .btn-warning:hover { background: #e65100; }
            
            .status-normal { color: #4caf50; font-weight: bold; }
            .status-disabled { color: #ef5350; font-weight: bold; }
            
            .form-group {
                margin-bottom: 16px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #333;
            }
            .form-group input, .form-group select {
                width: 100%;
                padding: 12px 16px;
                border: 2px solid #c8e6c9;
                border-radius: 8px;
                font-size: 14px;
            }
            .form-group input:focus, .form-group select:focus {
                outline: none;
                border-color: #4caf50;
            }
            
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                text-align: center;
            }
            .stat-card .number {
                font-size: 36px;
                font-weight: bold;
                color: #4caf50;
            }
            .stat-card .label {
                color: #666;
                margin-top: 8px;
            }
            
            .message {
                padding: 12px 16px;
                border-radius: 8px;
                margin-bottom: 16px;
                display: none;
            }
            .message.success { background: #e8f5e9; color: #2e7d32; display: block; }
            .message.error { background: #ffebee; color: #c62828; display: block; }
        </style>
    </head>
    <body>
        <!-- 登录页面 -->
        <div id="loginPage" class="login-container">
            <div class="login-box">
                <h1>超级管理后台</h1>
                <input type="text" id="loginUsername" placeholder="用户名" value="frog">
                <input type="password" id="loginPassword" placeholder="密码">
                <button onclick="adminLogin()">登录</button>
                <div id="loginError" class="error-msg"></div>
            </div>
        </div>
        
        <!-- 管理界面 -->
        <div id="adminPage" class="admin-container">
            <div class="header">
                <h1>绿豆蛙日报助手 - 管理后台</h1>
                <button onclick="adminLogout()">退出登录</button>
            </div>
            
            <div class="main">
                <div class="tabs">
                    <div class="tab active" onclick="switchTab('users')">用户管理</div>
                    <div class="tab" onclick="switchTab('smtp')">SMTP配置</div>
                </div>
                
                <!-- 用户管理面板 -->
                <div id="usersPanel" class="panel active">
                    <div class="stats">
                        <div class="stat-card">
                            <div class="number" id="totalUsers">0</div>
                            <div class="label">总用户数</div>
                        </div>
                        <div class="stat-card">
                            <div class="number" id="activeUsers">0</div>
                            <div class="label">正常用户</div>
                        </div>
                        <div class="stat-card">
                            <div class="number" id="disabledUsers">0</div>
                            <div class="label">禁用用户</div>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>用户列表</h2>
                        <table>
                            <thead>
                                <tr>
                                    <th>邮箱</th>
                                    <th>注册时间</th>
                                    <th>最近登录</th>
                                    <th>状态</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody id="usersTableBody">
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- SMTP配置面板 -->
                <div id="smtpPanel" class="panel">
                    <div class="card">
                        <h2>SMTP邮箱配置</h2>
                        <div id="smtpMessage" class="message"></div>
                        <div class="form-group">
                            <label>SMTP服务器</label>
                            <input type="text" id="smtpServer" placeholder="smtp.qq.com">
                        </div>
                        <div class="form-group">
                            <label>端口</label>
                            <input type="number" id="smtpPort" placeholder="465">
                        </div>
                        <div class="form-group">
                            <label>发件邮箱</label>
                            <input type="email" id="smtpEmail" placeholder="your-email@qq.com">
                        </div>
                        <div class="form-group">
                            <label>邮箱密码/授权码</label>
                            <input type="password" id="smtpPassword" placeholder="QQ邮箱授权码">
                        </div>
                        <div class="form-group">
                            <label>验证码有效期（分钟）</label>
                            <input type="number" id="codeExpire" placeholder="5">
                        </div>
                        <button class="btn btn-success" onclick="saveSMTPConfig()">保存配置</button>
                    </div>
                    
                    <div class="card">
                        <h2>测试邮件发送</h2>
                        <div id="testMessage" class="message"></div>
                        <div class="form-group">
                            <label>测试邮箱</label>
                            <input type="email" id="testEmail" placeholder="输入测试邮箱">
                        </div>
                        <button class="btn btn-info" onclick="testEmail()">发送测试邮件</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // 管理员登录
            async function adminLogin() {
                const username = document.getElementById('loginUsername').value;
                const password = document.getElementById('loginPassword').value;
                
                const response = await fetch('/api/admin/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('loginPage').style.display = 'none';
                    document.getElementById('adminPage').classList.add('active');
                    loadUsers();
                    loadSMTPConfig();
                } else {
                    document.getElementById('loginError').textContent = data.message;
                }
            }
            
            // 管理员登出
            async function adminLogout() {
                await fetch('/api/admin/logout', {method: 'POST'});
                document.getElementById('loginPage').style.display = 'flex';
                document.getElementById('adminPage').classList.remove('active');
            }
            
            // 切换标签
            function switchTab(tab) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
                
                event.target.classList.add('active');
                document.getElementById(tab + 'Panel').classList.add('active');
            }
            
            // 加载用户列表
            async function loadUsers() {
                const response = await fetch('/api/admin/users');
                const data = await response.json();
                
                if (data.success) {
                    const users = data.users;
                    document.getElementById('totalUsers').textContent = users.length;
                    document.getElementById('activeUsers').textContent = users.filter(u => u['状态'] === '正常').length;
                    document.getElementById('disabledUsers').textContent = users.filter(u => u['状态'] === '禁用').length;
                    
                    const tbody = document.getElementById('usersTableBody');
                    tbody.innerHTML = users.map(user => `
                        <tr>
                            <td>${user['邮箱']}</td>
                            <td>${user['注册时间']}</td>
                            <td>${user['最近登录时间'] || '从未登录'}</td>
                            <td class="${user['状态'] === '正常' ? 'status-normal' : 'status-disabled'}">${user['状态']}</td>
                            <td>
                                <button class="btn ${user['状态'] === '正常' ? 'btn-warning' : 'btn-success'}" 
                                        onclick="toggleStatus('${user['邮箱']}', '${user['状态'] === '正常' ? '禁用' : '正常'}')">
                                    ${user['状态'] === '正常' ? '禁用' : '启用'}
                                </button>
                                <button class="btn btn-danger" onclick="deleteUser('${user['邮箱']}')">删除</button>
                            </td>
                        </tr>
                    `).join('');
                }
            }
            
            // 切换用户状态
            async function toggleStatus(email, status) {
                await fetch(`/api/admin/users/${email}/status`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({status})
                });
                loadUsers();
            }
            
            // 删除用户
            async function deleteUser(email) {
                if (!confirm(`确定要删除用户 ${email} 吗？`)) return;
                await fetch(`/api/admin/users/${email}`, {method: 'DELETE'});
                loadUsers();
            }
            
            // 加载SMTP配置
            async function loadSMTPConfig() {
                const response = await fetch('/api/admin/config');
                const data = await response.json();
                
                if (data.success) {
                    const config = data.config;
                    document.getElementById('smtpServer').value = config.smtp_server || '';
                    document.getElementById('smtpPort').value = config.smtp_port || 465;
                    document.getElementById('smtpEmail').value = config.smtp_email || '';
                    document.getElementById('smtpPassword').value = config.smtp_password || '';
                    document.getElementById('codeExpire').value = config.code_expire_minutes || 5;
                }
            }
            
            // 保存SMTP配置
            async function saveSMTPConfig() {
                const config = {
                    smtp_server: document.getElementById('smtpServer').value,
                    smtp_port: parseInt(document.getElementById('smtpPort').value),
                    smtp_email: document.getElementById('smtpEmail').value,
                    smtp_password: document.getElementById('smtpPassword').value,
                    code_expire_minutes: parseInt(document.getElementById('codeExpire').value)
                };
                
                const response = await fetch('/api/admin/config', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(config)
                });
                const data = await response.json();
                
                const msg = document.getElementById('smtpMessage');
                msg.textContent = data.message;
                msg.className = 'message ' + (data.success ? 'success' : 'error');
                setTimeout(() => msg.className = 'message', 3000);
            }
            
            // 测试邮件
            async function testEmail() {
                const email = document.getElementById('testEmail').value;
                const response = await fetch('/api/admin/test-email', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email})
                });
                const data = await response.json();
                
                const msg = document.getElementById('testMessage');
                msg.textContent = data.message;
                msg.className = 'message ' + (data.success ? 'success' : 'error');
                setTimeout(() => msg.className = 'message', 3000);
            }
            
            // 回车登录
            document.getElementById('loginPassword').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') adminLogin();
            });
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    init_csv()
    app.run(host='0.0.0.0', port=5000, debug=True)