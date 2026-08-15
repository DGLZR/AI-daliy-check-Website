from flask import Flask, send_from_directory, request, jsonify, session, redirect, render_template
import os
import json
import csv
import smtplib
import random
import string
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.utils import secure_filename
from superadmin import superadmin_bp
import platform
import socket
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False
import threading
import time
import re
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

# 东八区时区
CHINA_TZ = timezone(timedelta(hours=8))

def get_china_time():
    """获取东八区当前时间"""
    return datetime.now(CHINA_TZ)

def get_china_time_str(fmt='%Y-%m-%d %H:%M:%S'):
    """获取东八区当前时间字符串"""
    return get_china_time().strftime(fmt)

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24).hex()
app.register_blueprint(superadmin_bp)

# ============ 配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
DATA_DIR = os.path.join(BASE_DIR, 'data')
USERS_CSV = os.path.join(DATA_DIR, 'users.csv')
DETAIL_CSV = os.path.join(DATA_DIR, 'detail_person_data.csv')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
FILES_INFO_PATH = os.path.join(BASE_DIR, 'files_info.json')
VERSIONS_FILE = os.path.join(BASE_DIR, 'versions.json')

# 管理员账号
ADMIN_USERNAME = 'frog'
ADMIN_PASSWORD = 'Ab130108'

# 验证码存储
verification_codes = {}

# 工作类型列表
WORK_TYPES = ['开发', '沟通', '生活', '学习', '设计', '管理', '文档', '娱乐', '产品', '会议', '运维', '测试', '数据分析', '其他']

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
    
    if not os.path.exists(DETAIL_CSV):
        with open(DETAIL_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['邮箱', '昵称', '密码', '最近登录时间', '今日专注时长(分钟)',
                           '今日开发时长(分钟)', '今日沟通时长(分钟)', '今日生活时长(分钟)',
                           '今日学习时长(分钟)', '今日设计时长(分钟)', '今日管理时长(分钟)',
                           '今日文档时长(分钟)', '今日娱乐时长(分钟)', '今日产品时长(分钟)',
                           '今日会议时长(分钟)', '今日运维时长(分钟)', '今日测试时长(分钟)',
                           '今日数据分析时长(分钟)', '今日其他时长(分钟)',
                           '今日记录条数', '总共记录条数', '今日生成报告数', '总共生成报告数'])

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

def create_user_folder(email):
    """创建用户文件夹和初始化CSV文件"""
    # 邮箱中的特殊字符替换为下划线作为文件夹名
    folder_name = email.replace('@', '_at_').replace('.', '_')
    user_folder = os.path.join(DATA_DIR, 'users', folder_name)
    os.makedirs(user_folder, exist_ok=True)
    
    # 创建records.csv
    records_file = os.path.join(user_folder, 'records.csv')
    if not os.path.exists(records_file):
        with open(records_file, 'w', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(['ID', '日期', '时间', '工作类型', '工作描述', '持续时长(分钟)'])
    
    # 创建daily_summary.csv
    summary_file = os.path.join(user_folder, 'daily_summary.csv')
    if not os.path.exists(summary_file):
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['日期', '记录条数', '使用时长(小时)', '主要工作', '最早使用时间', '最晚使用时间']
            for wt in WORK_TYPES:
                header.append(f'{wt}时长(小时)')
            for i in range(24):
                header.append(f'{i:02d}:00记录数')
            writer.writerow(header)
    
    # 初始化detail_person_data.csv中的用户数据
    init_user_detail(email)
    
    return user_folder

def init_user_detail(email):
    """初始化用户详细数据"""
    users = read_users()
    user = next((u for u in users if u['邮箱'] == email), None)
    if not user:
        return
    
    # 检查是否已存在
    detail_data = read_detail_data()
    if any(d['邮箱'] == email for d in detail_data):
        return
    
    # 添加新用户
    new_detail = {
        '邮箱': email,
        '昵称': email.split('@')[0],
        '密码': user['密码'],
        '最近登录时间': '',
        '今日专注时长(分钟)': 0,
        '今日开发时长(分钟)': 0,
        '今日沟通时长(分钟)': 0,
        '今日生活时长(分钟)': 0,
        '今日学习时长(分钟)': 0,
        '今日设计时长(分钟)': 0,
        '今日管理时长(分钟)': 0,
        '今日文档时长(分钟)': 0,
        '今日娱乐时长(分钟)': 0,
        '今日产品时长(分钟)': 0,
        '今日会议时长(分钟)': 0,
        '今日运维时长(分钟)': 0,
        '今日测试时长(分钟)': 0,
        '今日数据分析时长(分钟)': 0,
        '今日其他时长(分钟)': 0,
        '今日记录条数': 0,
        '总共记录条数': 0,
        '今日生成报告数': 0,
        '总共生成报告数': 0
    }
    detail_data.append(new_detail)
    write_detail_data(detail_data)

def read_detail_data():
    """读取用户详细数据"""
    init_csv()
    data = []
    if os.path.exists(DETAIL_CSV):
        with open(DETAIL_CSV, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                data.append(row)
    return data

def write_detail_data(data):
    """写入用户详细数据"""
    if not data:
        return
    with open(DETAIL_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)

def add_user(email, password):
    users = read_users()
    users.append({
        '邮箱': email,
        '密码': password,
        '注册时间': get_china_time_str('%Y-%m-%d %H:%M:%S'),
        '状态': '正常',
        '最近登录时间': ''
    })
    write_users(users)
    # 创建用户文件夹
    create_user_folder(email)

def update_user(email, updates):
    users = read_users()
    for user in users:
        if user['邮箱'] == email:
            user.update(updates)
    write_users(users)
    
    # 同步更新detail_person_data.csv
    if '最近登录时间' in updates:
        detail_data = read_detail_data()
        for d in detail_data:
            if d['邮箱'] == email:
                d['最近登录时间'] = updates['最近登录时间']
        write_detail_data(detail_data)

def delete_user(email):
    write_users([u for u in read_users() if u['邮箱'] != email])
    # 也从detail_person_data.csv中删除
    detail_data = read_detail_data()
    detail_data = [d for d in detail_data if d['邮箱'] != email]
    write_detail_data(detail_data)

# ============ 用户数据计算 ============
def get_user_folder(email):
    """获取用户文件夹路径"""
    folder_name = email.replace('@', '_at_').replace('.', '_')
    return os.path.join(DATA_DIR, 'users', folder_name)

def cleanup_records_file(records_file, max_size_bytes=1*1024*1024):
    """清理records.csv文件，确保不超过指定大小"""
    if not os.path.exists(records_file):
        return
    
    # 检查文件大小
    file_size = os.path.getsize(records_file)
    if file_size <= max_size_bytes:
        return
    
    print(f"records.csv文件大小 ({file_size} bytes) 超过限制 ({max_size_bytes} bytes)，开始清理...")
    
    # 读取所有记录
    records = []
    with open(records_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        records = list(reader)
    
    # 按日期和时间排序（从新到旧）
    records.sort(key=lambda x: (x.get('日期', ''), x.get('时间', '')), reverse=True)
    
    # 逐步删除最旧的记录，直到文件大小小于限制
    while len(records) > 0:
        # 先写入测试看看大小
        temp_content = 'ID,日期,时间,工作类型,工作描述,持续时长(分钟)\n'
        for record in records:
            temp_content += f"{record['ID']},{record['日期']},{record['时间']},{record['工作类型']},{record['工作描述']},{record['持续时长(分钟)']}\n"
        
        if len(temp_content.encode('utf-8')) <= max_size_bytes:
            break
        
        # 删除最旧的一条记录
        records.pop()
    
    # 重新写入文件
    with open(records_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', '日期', '时间', '工作类型', '工作描述', '持续时长(分钟)'])
        writer.writeheader()
        writer.writerows(records)
    
    print(f"清理完成，剩余 {len(records)} 条记录")

def get_records_file_size(email):
    """获取用户records.csv文件大小"""
    user_folder = get_user_folder(email)
    records_file = os.path.join(user_folder, 'records.csv')
    
    if os.path.exists(records_file):
        return os.path.getsize(records_file)
    return 0

def get_report_folder_size(email):
    """获取用户report文件夹总大小"""
    user_folder = get_user_folder(email)
    report_folder = os.path.join(user_folder, 'report')
    
    total_size = 0
    if os.path.exists(report_folder):
        for filename in os.listdir(report_folder):
            filepath = os.path.join(report_folder, filename)
            if os.path.isfile(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

def cleanup_report_folder(email, max_size_bytes=1*1024*1024):
    """清理report文件夹，确保不超过指定大小"""
    user_folder = get_user_folder(email)
    report_folder = os.path.join(user_folder, 'report')
    
    if not os.path.exists(report_folder):
        return
    
    # 获取所有报告文件及其信息
    files_info = []
    for filename in os.listdir(report_folder):
        filepath = os.path.join(report_folder, filename)
        if os.path.isfile(filepath):
            files_info.append({
                'filename': filename,
                'filepath': filepath,
                'size': os.path.getsize(filepath),
                'mtime': os.path.getmtime(filepath)
            })
    
    # 计算总大小
    total_size = sum(f['size'] for f in files_info)
    
    if total_size <= max_size_bytes:
        return
    
    print(f"report文件夹大小 ({total_size} bytes) 超过限制 ({max_size_bytes} bytes)，开始清理...")
    
    # 按修改时间排序（从旧到新）
    files_info.sort(key=lambda x: x['mtime'])
    
    # 逐步删除最旧的文件，直到总大小小于限制
    for file_info in files_info:
        if total_size <= max_size_bytes:
            break
        
        os.remove(file_info['filepath'])
        total_size -= file_info['size']
        print(f"删除报告: {file_info['filename']}")
    
    print(f"清理完成，剩余大小: {total_size} bytes")

def calculate_user_stats(email):
    """计算用户统计数据"""
    user_folder = get_user_folder(email)
    records_file = os.path.join(user_folder, 'records.csv')
    summary_file = os.path.join(user_folder, 'daily_summary.csv')
    report_folder = os.path.join(user_folder, 'report')
    
    today = get_china_time_str('%Y-%m-%d')
    
    stats = {
        'today_focus_minutes': 0,
        'today_type_minutes': {wt: 0 for wt in WORK_TYPES},
        'today_records': 0,
        'total_records': 0,
        'today_reports': 0,
        'total_reports': 0
    }
    
    # 读取records.csv计算今日数据
    if os.path.exists(records_file):
        with open(records_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats['total_records'] += 1
                if row['日期'] == today:
                    stats['today_records'] += 1
                    try:
                        duration = float(row['持续时长(分钟)'])
                        work_type = row['工作类型']
                        stats['today_focus_minutes'] += duration
                        if work_type in stats['today_type_minutes']:
                            stats['today_type_minutes'][work_type] += duration
                    except (ValueError, KeyError):
                        pass
    
    # 统计报告数量
    if os.path.exists(report_folder):
        for filename in os.listdir(report_folder):
            if filename.endswith('.md'):
                stats['total_reports'] += 1
                # 从文件名中提取日期
                try:
                    # 文件名格式: title_YYYYMMDD_HHMMSS.md
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        date_str = parts[-2]  # YYYYMMDD
                        if len(date_str) == 8:
                            file_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            if file_date == today:
                                stats['today_reports'] += 1
                except:
                    pass
    
    return stats

def update_detail_data_on_login(email):
    """登录时更新用户详细数据"""
    stats = calculate_user_stats(email)
    detail_data = read_detail_data()
    
    for d in detail_data:
        if d['邮箱'] == email:
            d['最近登录时间'] = get_china_time_str('%Y-%m-%d %H:%M:%S')
            d['今日专注时长(分钟)'] = round(stats['today_focus_minutes'], 1)
            for wt in WORK_TYPES:
                d[f'今日{wt}时长(分钟)'] = round(stats['today_type_minutes'][wt], 1)
            d['今日记录条数'] = stats['today_reports']
            d['总共记录条数'] = stats['total_reports']
            break
    
    write_detail_data(detail_data)

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

@app.route('/admin')
def admin_redirect():
    """重定向到管理后台"""
    return redirect('/superadmin')

@app.route('/login')
def login_page():
    return send_from_directory('static', 'login.html')

@app.route('/versions')
def versions_page():
    """版本更新与历史版本下载页面"""
    return send_from_directory('static', 'versions.html')

@app.route('/user/<email>')
def user_profile_page(email):
    """用户个人详情页面（需要登录状态）"""
    # 检查用户是否已登录
    if session.get('logged_user') != email:
        return redirect('/login')
    
    # 检查用户是否存在
    user = find_user(email)
    if not user:
        session.pop('logged_user', None)
        return redirect('/login')
    
    # 获取用户详情数据
    detail_data = read_detail_data()
    detail = next((d for d in detail_data if d['邮箱'] == email), {})
    
    # 计算统计数据
    stats = calculate_user_stats(email)
    
    # 更新详情数据
    detail['今日专注时长(分钟)'] = round(stats['today_focus_minutes'], 1)
    for wt in WORK_TYPES:
        detail[f'今日{wt}时长(分钟)'] = round(stats['today_type_minutes'][wt], 1)
    detail['今日记录条数'] = stats['today_records']
    detail['总共记录条数'] = stats['total_records']
    detail['今日生成报告数'] = stats['today_reports']
    detail['总共生成报告数'] = stats['total_reports']
    
    return render_template('user_profile.html', user=user, detail=detail, work_types=WORK_TYPES)

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
        
        filename = secure_filename(file.filename) or f"upload_{get_china_time_str('%Y%m%d_%H%M%S')}.exe"
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{get_china_time_str('%Y%m%d_%H%M%S')}{ext}"
        
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        files_info = load_files_info()
        files_info['files'].append({
            'filename': filename,
            'original_name': file.filename,
            'size': os.path.getsize(filepath),
            'upload_time': get_china_time().isoformat(),
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
        'expire': get_china_time() + timedelta(minutes=config.get('smtp', {}).get('code_expire', 5))
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
    if get_china_time() > stored['expire']:
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
    
    # 确保用户文件夹存在
    user_folder = get_user_folder(email)
    if not os.path.exists(user_folder):
        create_user_folder(email)
    
    update_user(email, {'最近登录时间': get_china_time_str('%Y-%m-%d %H:%M:%S')})
    # 更新详细数据
    update_detail_data_on_login(email)
    
    # 设置登录状态
    session['logged_user'] = email
    
    return jsonify({'success': True, 'message': '登录成功'})

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """重置密码"""
    data = request.json
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not all([email, code, new_password]):
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码至少需要6位'})
    
    if email not in verification_codes:
        return jsonify({'success': False, 'message': '请先发送验证码'})
    
    stored = verification_codes[email]
    if get_china_time() > stored['expire']:
        del verification_codes[email]
        return jsonify({'success': False, 'message': '验证码已过期'})
    if stored['code'] != code:
        return jsonify({'success': False, 'message': '验证码错误'})
    
    user = find_user(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'})
    
    # 更新密码
    update_user(email, {'密码': new_password})
    del verification_codes[email]
    
    return jsonify({'success': True, 'message': '密码已重置，请重新登录'})

@app.route('/api/user/change-password', methods=['POST'])
def change_password():
    """修改密码（需要登录状态）"""
    data = request.json
    email = data.get('email', '').strip()
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    
    # 验证登录状态
    if session.get('logged_user') != email:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    if not all([email, current_password, new_password]):
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密码至少需要6位'})
    
    if current_password == new_password:
        return jsonify({'success': False, 'message': '新密码不能与当前密码相同'})
    
    user = find_user(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'})
    
    if user['密码'] != current_password:
        return jsonify({'success': False, 'message': '当前密码错误'})
    
    # 更新密码
    update_user(email, {'密码': new_password})
    
    # 同步更新detail_person_data.csv中的密码
    detail_data = read_detail_data()
    for d in detail_data:
        if d['邮箱'] == email:
            d['密码'] = new_password
            break
    write_detail_data(detail_data)
    
    return jsonify({'success': True, 'message': '密码修改成功'})

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.pop('logged_user', None)
    return jsonify({'success': True, 'message': '已登出'})

@app.route('/api/user/stats/<email>', methods=['GET'])
def get_user_stats_api(email):
    """获取用户统计数据（需要登录状态）"""
    if session.get('logged_user') != email:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    stats = calculate_user_stats(email)
    return jsonify({
        'success': True,
        'stats': {
            'today_focus_minutes': round(stats['today_focus_minutes'], 1),
            'today_records': stats['today_records'],
            'total_records': stats['total_records'],
            'today_reports': stats['today_reports'],
            'total_reports': stats['total_reports']
        }
    })

@app.route('/api/user/storage/<email>', methods=['GET'])
def get_user_storage(email):
    """获取用户存储空间使用情况"""
    if session.get('logged_user') != email:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    # 截图记录存储
    records_size = get_records_file_size(email)
    records_max = 1 * 1024 * 1024  # 1MB
    records_percentage = (records_size / records_max * 100) if records_max > 0 else 0
    
    # 报告存储
    report_size = get_report_folder_size(email)
    report_max = 1 * 1024 * 1024  # 1MB
    report_percentage = (report_size / report_max * 100) if report_max > 0 else 0
    
    return jsonify({
        'success': True,
        'records_storage': {
            'current_bytes': records_size,
            'max_bytes': records_max,
            'current_mb': round(records_size / 1024 / 1024, 2),
            'max_mb': 1,
            'percentage': round(records_percentage, 1)
        },
        'report_storage': {
            'current_bytes': report_size,
            'max_bytes': report_max,
            'current_mb': round(report_size / 1024 / 1024, 2),
            'max_mb': 1,
            'percentage': round(report_percentage, 1)
        }
    })

# ============ 用户数据接收接口 ============
@app.route('/api/user/record', methods=['POST'])
def add_user_record():
    """添加用户记录"""
    data = request.json
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': '缺少邮箱参数'})
    
    # 如果用户不存在，自动创建
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    # 获取或创建用户文件夹
    user_folder = get_user_folder(email)
    if not os.path.exists(user_folder):
        create_user_folder(email)
    
    records_file = os.path.join(user_folder, 'records.csv')
    
    # 清理文件，确保不超过1MB
    cleanup_records_file(records_file)
    
    # 读取现有记录获取最大ID
    max_id = 0
    with open(records_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                max_id = max(max_id, int(row['ID']))
            except ValueError:
                pass
    
    # 添加新记录
    new_record = {
        'ID': max_id + 1,
        '日期': data.get('date', get_china_time_str('%Y-%m-%d')),
        '时间': data.get('time', get_china_time_str('%H:%M:%S')),
        '工作类型': data.get('work_type', '其他'),
        '工作描述': data.get('description', ''),
        '持续时长(分钟)': data.get('duration', 0)
    }
    
    with open(records_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['ID', '日期', '时间', '工作类型', '工作描述', '持续时长(分钟)'])
        writer.writerow(new_record)
    
    return jsonify({'success': True, 'message': '记录添加成功', 'id': new_record['ID']})

@app.route('/api/user/daily-summary', methods=['POST'])
def update_user_daily_summary():
    """更新用户每日汇总（同一天刷新）"""
    data = request.json
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': '缺少邮箱参数'})
    
    # 如果用户不存在，返回错误
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    # 获取或创建用户文件夹
    user_folder = get_user_folder(email)
    if not os.path.exists(user_folder):
        create_user_folder(email)
    
    summary_file = os.path.join(user_folder, 'daily_summary.csv')
    
    date = data.get('date', get_china_time_str('%Y-%m-%d'))
    
    # 读取现有数据
    summaries = []
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            summaries = list(reader)
    
    # 查找是否已存在该日期的数据
    existing_index = None
    for i, s in enumerate(summaries):
        if s['日期'] == date:
            existing_index = i
            break
    
    # 构建新数据
    new_summary = {
        '日期': date,
        '记录条数': data.get('record_count', 0),
        '使用时长(小时)': data.get('usage_hours', 0),
        '主要工作': data.get('main_work', ''),
        '最早使用时间': data.get('earliest_time', ''),
        '最晚使用时间': data.get('latest_time', '')
    }
    
    # 添加各工作类型时长
    for wt in WORK_TYPES:
        new_summary[f'{wt}时长(小时)'] = data.get(f'{wt}_hours', 0)
    
    # 添加每小时记录数
    for i in range(24):
        new_summary[f'{i:02d}:00记录数'] = data.get(f'hour_{i:02d}', 0)
    
    # 更新或添加
    if existing_index is not None:
        summaries[existing_index] = new_summary
    else:
        summaries.append(new_summary)
    
    # 写入文件
    if summaries:
        with open(summary_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=summaries[0].keys())
            writer.writeheader()
            writer.writerows(summaries)
    
    return jsonify({'success': True, 'message': '每日汇总更新成功'})

@app.route('/api/user/stats/<email>', methods=['GET'])
def get_user_stats(email):
    """获取用户统计数据"""
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    stats = calculate_user_stats(email)
    return jsonify({
        'success': True,
        'stats': {
            'today_focus_minutes': round(stats['today_focus_minutes'], 1),
            'today_type_minutes': {k: round(v, 1) for k, v in stats['today_type_minutes'].items()},
            'today_reports': stats['today_reports'],
            'total_reports': stats['total_reports']
        }
    })

@app.route('/api/user/records/<email>', methods=['GET'])
def get_user_records(email):
    """获取用户记录（支持日期筛选）"""
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    
    user_folder = get_user_folder(email)
    records_file = os.path.join(user_folder, 'records.csv')
    
    records = []
    if os.path.exists(records_file):
        with open(records_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                record_date = row.get('日期', '')
                if start_date and record_date < start_date:
                    continue
                if end_date and record_date > end_date:
                    continue
                records.append(row)
    
    return jsonify({'success': True, 'records': records})

@app.route('/api/user/report-generated', methods=['POST'])
def report_generated():
    """记录报告生成事件"""
    data = request.json
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': '缺少邮箱参数'})
    
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    # 更新用户详情中的报告数量（不是记录数量）
    detail_data = read_detail_data()
    for d in detail_data:
        if d['邮箱'] == email:
            d['今日生成报告数'] = str(int(d.get('今日生成报告数', '0')) + 1)
            d['总共生成报告数'] = str(int(d.get('总共生成报告数', '0')) + 1)
            break
    write_detail_data(detail_data)
    
    return jsonify({'success': True, 'message': '报告生成记录已保存'})

# ============ 报告管理接口 ============
@app.route('/api/user/upload-report', methods=['POST'])
def upload_report():
    """上传报告（Markdown格式）"""
    data = request.json
    email = data.get('email', '').strip()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    report_type = data.get('type', '日报').strip()
    
    if not email:
        return jsonify({'success': False, 'message': '缺少邮箱参数'})
    
    if not content:
        return jsonify({'success': False, 'message': '缺少报告内容'})
    
    # 如果用户不存在，自动创建
    if not find_user(email):
        add_user(email, 'default123')
    
    # 获取或创建用户文件夹
    user_folder = get_user_folder(email)
    if not os.path.exists(user_folder):
        create_user_folder(email)
    
    # 创建report文件夹
    report_folder = os.path.join(user_folder, 'report')
    os.makedirs(report_folder, exist_ok=True)
    
    # 清理report文件夹，确保不超过1MB
    cleanup_report_folder(email)
    
    # 生成文件名
    now = get_china_time()
    if not title:
        title = f"{report_type}_{now.strftime('%Y%m%d_%H%M%S')}"
    
    # 清理文件名中的非法字符
    safe_title = "".join(c for c in title if c.isalnum() or c in ('_', '-', ' ')).strip()
    filename = f"{safe_title}_{now.strftime('%Y%m%d_%H%M%S')}.md"
    
    filepath = os.path.join(report_folder, filename)
    
    # 添加元信息到报告内容
    meta_content = f"""# {title}

**报告类型：** {report_type}
**生成时间：** {now.strftime('%Y-%m-%d %H:%M:%S')}
**用户邮箱：** {email}

---

{content}
"""
    
    # 保存报告
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(meta_content)
    
    # 更新报告计数（不是记录计数）
    detail_data = read_detail_data()
    for d in detail_data:
        if d['邮箱'] == email:
            d['今日生成报告数'] = str(int(d.get('今日生成报告数', '0')) + 1)
            d['总共生成报告数'] = str(int(d.get('总共生成报告数', '0')) + 1)
            break
    write_detail_data(detail_data)
    
    return jsonify({'success': True, 'message': '报告上传成功', 'filename': filename})

@app.route('/api/user/reports/<email>', methods=['GET'])
def get_user_reports(email):
    """获取用户报告列表"""
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    user_folder = get_user_folder(email)
    report_folder = os.path.join(user_folder, 'report')
    
    reports = []
    if os.path.exists(report_folder):
        for filename in os.listdir(report_folder):
            if filename.endswith('.md'):
                filepath = os.path.join(report_folder, filename)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 解析元信息
                    title = filename.replace('.md', '')
                    report_type = '日报'
                    generate_time = ''
                    word_count = len(content)
                    date = ''
                    
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith('# '):
                            title = line[2:].strip()
                        if '**报告类型：**' in line:
                            report_type = line.split('：')[-1].strip()
                        if '**生成时间：**' in line:
                            generate_time = line.split('：')[-1].strip()
                    
                    # 格式化时间
                    if generate_time:
                        try:
                            dt = datetime.strptime(generate_time, '%Y-%m-%d %H:%M:%S')
                            date = dt.strftime('%Y-%m-%d')
                            today = get_china_time_str('%Y-%m-%d')
                            if dt.strftime('%Y-%m-%d') == today:
                                generate_time = f"今日 {dt.strftime('%H:%M')}"
                            else:
                                generate_time = dt.strftime('%m月%d日 %H:%M')
                        except:
                            pass
                    
                    reports.append({
                        'filename': filename,
                        'title': title,
                        'type': report_type,
                        'time': generate_time,
                        'date': date,
                        'word_count': word_count,
                        'status': '已完成'
                    })
                except:
                    pass
    
    # 按时间倒序排序
    reports.sort(key=lambda x: x.get('filename', ''), reverse=True)
    
    return jsonify({'success': True, 'reports': reports})

@app.route('/api/user/report/<email>/<filename>', methods=['GET'])
def get_user_report(email, filename):
    """获取单个报告内容"""
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    user_folder = get_user_folder(email)
    filepath = os.path.join(user_folder, 'report', filename)
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'message': '报告不存在'})
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析标题
        title = filename.replace('.md', '')
        for line in content.split('\n'):
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        # 将Markdown转换为简单HTML
        html_content = markdown_to_html(content)
        
        return jsonify({'success': True, 'title': title, 'content': html_content, 'raw': content})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/user/report/<email>/<filename>', methods=['DELETE'])
def delete_user_report(email, filename):
    """删除报告"""
    if not find_user(email):
        return jsonify({'success': False, 'message': '用户不存在'})
    
    user_folder = get_user_folder(email)
    filepath = os.path.join(user_folder, 'report', filename)
    
    if not os.path.exists(filepath):
        return jsonify({'success': False, 'message': '报告不存在'})
    
    try:
        os.remove(filepath)
        return jsonify({'success': True, 'message': '报告删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def markdown_to_html(md_content):
    """简单的Markdown转HTML"""
    import re
    
    html = md_content
    
    # 表格转换（在标题/列表之前处理）
    def convert_table(m):
        block = m.group(0)
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if len(lines) < 2:
            return block
        def parse_row(line):
            line = line.strip().strip('|')
            return [c.strip() for c in line.split('|')]
        header = parse_row(lines[0])
        # 跳过分隔行（|---|---|）
        body_rows = [parse_row(l) for l in lines[1:] if not re.match(r'^[\s\|\-:]+$', l)]
        out = '<table><thead><tr>' + ''.join(f'<th>{h}</th>' for h in header) + '</tr></thead><tbody>'
        for row in body_rows:
            out += '<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>'
        out += '</tbody></table>'
        return out
    
    html = re.sub(r'(\|[^\n]+\|\n\|[\s\|\-:]+\|\n(\|[^\n]+\|\n?)+)', convert_table, html)
    
    # 标题
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # 粗体
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    
    # 斜体
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    
    # 代码块
    html = re.sub(r'```[\s\S]*?```', lambda m: f'<pre><code>{m.group(0)[3:-3]}</code></pre>', html)
    
    # 行内代码
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
    
    # 列表
    html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
    
    # 分隔线
    html = re.sub(r'^---+$', '<hr>', html, flags=re.MULTILINE)
    
    # 段落
    html = re.sub(r'\n\n', '</p><p>', html)
    html = f'<p>{html}</p>'
    
    # 换行
    html = html.replace('\n', '<br>')
    
    return html

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

@app.route('/api/admin/check-login', methods=['GET'])
def admin_check_login():
    """检查管理员登录状态"""
    return jsonify({'logged_in': session.get('admin_logged_in', False)})

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

@app.route('/api/admin/user-detail/<email>', methods=['GET'])
def admin_get_user_detail(email):
    """获取用户详细信息"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    detail_data = read_detail_data()
    user_detail = next((d for d in detail_data if d['邮箱'] == email), None)
    
    if not user_detail:
        return jsonify({'success': False, 'message': '用户不存在'})
    
    # 更新统计数据
    stats = calculate_user_stats(email)
    user_detail['今日专注时长(分钟)'] = round(stats['today_focus_minutes'], 1)
    for wt in WORK_TYPES:
        user_detail[f'今日{wt}时长(分钟)'] = round(stats['today_type_minutes'][wt], 1)
    user_detail['今日记录条数'] = stats['today_records']
    user_detail['总共记录条数'] = stats['total_records']
    user_detail['今日生成报告数'] = stats['today_reports']
    user_detail['总共生成报告数'] = stats['total_reports']
    
    return jsonify({'success': True, 'user': user_detail})

@app.route('/api/admin/change-user-password', methods=['POST'])
def admin_change_user_password():
    """管理员修改用户密码"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    data = request.json
    email = data.get('email', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not email or not new_password:
        return jsonify({'success': False, 'message': '请填写完整信息'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '密码至少需要6位'})
    
    user = find_user(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'})
    
    # 更新users.csv中的密码
    update_user(email, {'密码': new_password})
    
    # 同步更新detail_person_data.csv中的密码
    detail_data = read_detail_data()
    for d in detail_data:
        if d['邮箱'] == email:
            d['密码'] = new_password
            break
    write_detail_data(detail_data)
    
    return jsonify({'success': True, 'message': '密码修改成功'})

# ============ 安装包管理接口 ============
@app.route('/api/admin/packages', methods=['GET'])
def admin_get_packages():
    """获取安装包列表"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    files_info = load_files_info()
    return jsonify({
        'success': True,
        'packages': files_info.get('files', []),
        'current_version': files_info.get('current_version')
    })

@app.route('/api/admin/packages/upload', methods=['POST'])
def admin_upload_package():
    """上传安装包"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有文件'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': '不支持的文件类型'})
    
    name = request.form.get('name', '').strip()
    version = request.form.get('version', '').strip()
    note = request.form.get('note', '').strip()
    force_update = request.form.get('force_update', '0').strip() == '1'
    
    if not name:
        return jsonify({'success': False, 'message': '请输入文件名'})
    
    if not version:
        return jsonify({'success': False, 'message': '请输入版本号'})
    
    import re
    if not re.match(r'^[0-9.]+$', version):
        return jsonify({'success': False, 'message': '版本号只能是数字和点'})
    
    # 使用用户提供的文件名和版本号构建存储文件名
    safe_name = secure_filename(name) or f"package_{get_china_time_str('%Y%m%d_%H%M%S')}"
    _, ext = os.path.splitext(file.filename)
    filename = f"{safe_name}_v{version}_{get_china_time_str('%Y%m%d_%H%M%S')}{ext}"
    
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    files_info = load_files_info()
    files_info['files'].append({
        'filename': filename,
        'original_name': file.filename,
        'display_name': name,
        'version': version,
        'size': os.path.getsize(filepath),
        'upload_time': get_china_time().isoformat(),
        'path': filepath,
        'note': note,
        'force_update': force_update
    })
    
    if len(files_info['files']) == 1:
        files_info['current_version'] = filename
    
    save_files_info(files_info)
    
    return jsonify({'success': True, 'message': '上传成功', 'filename': filename})

@app.route('/api/admin/packages/set-current', methods=['POST'])
def admin_set_current_package():
    """设置当前安装包版本"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    data = request.json
    filename = data.get('filename')
    
    files_info = load_files_info()
    if not any(f['filename'] == filename for f in files_info['files']):
        return jsonify({'success': False, 'message': '文件不存在'})
    
    files_info['current_version'] = filename
    save_files_info(files_info)
    
    return jsonify({'success': True, 'message': '已设置为当前版本'})

@app.route('/api/admin/packages/<filename>', methods=['DELETE'])
def admin_delete_package(filename):
    """删除安装包"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    
    files_info = load_files_info()
    file_to_delete = next((f for f in files_info['files'] if f['filename'] == filename), None)
    
    if not file_to_delete:
        return jsonify({'success': False, 'message': '文件不存在'})
    
    if os.path.exists(file_to_delete['path']):
        os.remove(file_to_delete['path'])
    
    files_info['files'] = [f for f in files_info['files'] if f['filename'] != filename]
    
    if files_info['current_version'] == filename:
        files_info['current_version'] = files_info['files'][-1]['filename'] if files_info['files'] else None
    
    save_files_info(files_info)
    
    return jsonify({'success': True, 'message': '删除成功'})


# ============ GitHub 自动更新（定时检测 + GLM 提取 + 自动上传） ============
AUTO_UPDATE_DEFAULTS = {
    'enabled': False,
    'github_repo': 'DGLZR/frog-daliy-check',
    'github_mirror': 'https://bdnb.cn',
    'interval_minutes': 60,
    'glm_api_key': 'e0f50530805f4ed0af556c4040d99eb3.DkyxdRgrogMYAWqs',
    'glm_model': 'glm-4.7-flash',
    'last_processed_tag': None,
    'last_check_time': None,
    'last_check_result': None,
}

def load_auto_update_settings():
    """读取自动更新配置（含默认值兜底）"""
    merged = dict(AUTO_UPDATE_DEFAULTS)
    merged.update(config.get('auto_update', {}) or {})
    return merged

def save_auto_update_settings(updates):
    """保存自动更新配置到 config.json"""
    global config
    if 'auto_update' not in config:
        config['auto_update'] = {}
    config['auto_update'].update(updates)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config['auto_update']

def _record_check(ok, message, extra=None):
    """记录最近一次检测结果"""
    updates = {
        'last_check_time': get_china_time_str('%Y-%m-%d %H:%M:%S'),
        'last_check_result': {'ok': bool(ok), 'message': message, 'time': get_china_time_str('%Y-%m-%d %H:%M:%S')},
    }
    if extra:
        updates.update(extra)
    save_auto_update_settings(updates)

def fetch_github_releases(repo):
    """拉取 GitHub 仓库的 releases（优先走国内镜像站，失败回退直连 GitHub）"""
    if not REQUESTS_AVAILABLE:
        raise RuntimeError('服务器未安装 requests 库，无法访问 GitHub')
    owner, _, name = repo.partition('/')
    owner = owner.strip(); name = name.strip()
    if not owner or not name:
        raise RuntimeError(f'仓库名格式错误: {repo}')

    errors = []
    # 1) 国内镜像站
    mirror = (load_auto_update_settings().get('github_mirror') or 'https://bdnb.cn').rstrip('/')
    try:
        url = f'{mirror}/api/repos/{owner}/{name}/releases'
        resp = requests.get(url, params={'page': 1, 'per_page': 100}, headers={
            'Accept': 'application/json',
            'User-Agent': 'FrogDailyCheck-AutoUpdate',
        }, timeout=30)
        if resp.status_code == 200:
            payload = resp.json()
            if isinstance(payload, dict) and 'data' in payload:
                releases = payload.get('data')
            elif isinstance(payload, list):
                releases = payload
            else:
                releases = None
            if isinstance(releases, list):
                return [r for r in releases if not r.get('draft')]
            errors.append('镜像站返回格式异常')
        else:
            errors.append(f'镜像站 HTTP {resp.status_code}')
    except Exception as e:
        errors.append(f'镜像站访问失败: {e}')

    # 2) 回退直连 GitHub API
    try:
        url = f'https://api.github.com/repos/{owner}/{name}/releases'
        resp = requests.get(url, headers={
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'FrogDailyCheck-AutoUpdate',
        }, timeout=30)
        if resp.status_code == 404:
            raise RuntimeError('GitHub 仓库不存在或为私有仓库 (404)')
        if resp.status_code == 403:
            raise RuntimeError('GitHub API 访问受限 (403)，可能被限流')
        resp.raise_for_status()
        releases = resp.json()
        if isinstance(releases, list):
            return [r for r in releases if not r.get('draft')]
        errors.append('GitHub 返回格式异常')
    except RuntimeError:
        raise
    except Exception as e:
        errors.append(f'GitHub 访问失败: {e}')

    raise RuntimeError('；'.join(errors) if errors else '无法获取 releases')

def call_glm_extract(body, api_key, model):
    """调用 GLM 免费模型，提取更新内容并翻译成中文（带限流重试）"""
    if not REQUESTS_AVAILABLE:
        raise RuntimeError('服务器未安装 requests 库，无法调用 GLM')
    if not api_key:
        raise RuntimeError('未配置 GLM API Key')
    prompt = (
        '你是软件更新日志整理助手。请阅读下面这段 GitHub Release 的更新说明（可能中英混合、包含无关内容）。\n'
        '任务：\n'
        '1. 只提取其中描述「本次版本更新内容」的部分，忽略贡献者名单、Full Changelog、自动生成说明、链接、图标，以及「下一版本将…」等未来计划等无关内容。\n'
        '2. 把提取出的每一条内容都翻译成简体中文。\n'
        '3. 将每条内容归类到下面三种标题之一，且只能使用这三种：新增、优化、修复。\n'
        '   - 新增：全新的功能或能力\n'
        '   - 优化：对已有功能的改进、性能提升、体验优化\n'
        '   - 修复：修复的 bug、问题或异常\n'
        '4. 严格按下面的格式输出，每一条独占一行，以 "- " 开头。没有某类内容就省略该类标题。不要输出任何解释、编号或多余空行。\n'
        '\n'
        '格式示例：\n'
        '新增\n'
        '- xxx\n'
        '- xxx\n'
        '优化\n'
        '- xxx\n'
        '修复\n'
        '- xxx\n'
        '\n'
        '更新说明如下：\n'
        '---\n' + (body or '') + '\n---'
    )
    RETRY_KEYWORDS = ('429', '1305', '限流', 'rate limit', 'too many', '繁忙', '人数过多', '请求过多', '稍后')
    last_error = None
    for attempt in range(5):
        try:
            resp = requests.post(
                'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={'model': model, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.2, 'stream': False},
                timeout=90,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data['choices'][0]['message']['content']
            try:
                err_msg = str(resp.json().get('error', {}).get('message', resp.text))
            except Exception:
                err_msg = resp.text or ''
            msg = f'HTTP {resp.status_code} {err_msg}'
            retryable = any(k in (str(resp.status_code) + ' ' + err_msg).lower() for k in RETRY_KEYWORDS)
            if not retryable:
                raise RuntimeError(msg)
            last_error = RuntimeError(msg)
        except RuntimeError as e:
            if not any(k in str(e).lower() for k in RETRY_KEYWORDS):
                raise
            last_error = e
        except Exception as e:
            last_error = e
        if attempt < 4:
            print(f'[自动更新] GLM 繁忙/限流，{int(1.5 * (attempt + 1))}秒后重试 (第{attempt + 1}/5次)')
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'GLM 调用失败（已重试 5 次）: {last_error}')

def _clean_item(line):
    """清洗单条更新内容"""
    line = line.strip()
    line = re.sub(r'^[-*•·]\s*', '', line)
    line = re.sub(r'^\d+[.)、]\s*', '', line)
    return line.strip()

def parse_update_note(text):
    """把 GLM 输出解析为 {新增:[], 优化:[], 修复:[]}"""
    result = {'新增': [], '优化': [], '修复': []}
    if not text:
        return result
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r'^(新增|优化|修复)\s*[：:]\s*(.*)$', line)
        if m:
            current = m.group(1)
            rest = m.group(2).strip()
            if rest:
                result[current].append(_clean_item(rest))
            continue
        if line in ('新增', '优化', '修复'):
            current = line
            continue
        item = _clean_item(line)
        if item and current:
            result[current].append(item)
    return result

def format_update_note(parsed):
    """把结构化更新内容格式化为 Markdown 文本（### 新增/优化/修复 + 列表）"""
    lines = []
    for key in ('新增', '优化', '修复'):
        items = parsed.get(key) or []
        if items:
            lines.append(f'### {key}')
            for it in items:
                lines.append(f'- {it}')
    return '\n'.join(lines)

def parse_version(v):
    """解析版本号，返回可比较的键 (浮点数, 分段元组)。
    同时兼容 0.3 > 0.25 这种十进制风格，以及 1.2.3 这种多段风格。"""
    v = (v or '').strip().lower().lstrip('v')
    m = re.search(r'\d+(\.\d+)*', v)
    if not m:
        return (0.0, (0,))
    s = m.group(0)
    parts = tuple(int(p) for p in s.split('.'))
    try:
        f = float(s)
    except ValueError:
        f = 0.0
    return (f, parts)

def compare_versions(a, b):
    """比较两个版本号：a>b 返回 1，a<b 返回 -1，相等返回 0"""
    pa, pb = parse_version(a), parse_version(b)
    if pa > pb:
        return 1
    if pa < pb:
        return -1
    return 0

def _pick_exe_asset(assets):
    """从 release 资产里挑一个可下载的安装包（没有则返回 None）"""
    if not assets:
        return None
    for ext in ('.exe', '.zip', '.7z', '.rar', '.msi'):
        for a in assets:
            n = (a.get('name') or '').lower()
            if n.endswith(ext):
                return a
    return None

def download_github_asset(asset, save_dir):
    """下载 release 资产到 uploads 目录（优先镜像站下载代理），返回 (文件路径, 大小)"""
    url = asset.get('browser_download_url')
    if not url:
        raise RuntimeError('该 release 没有可下载的文件资产')
    name = secure_filename(asset.get('name') or 'package.exe') or 'package.exe'

    base, ext = os.path.splitext(name)
    if not ext:
        ext = '.exe'
    filename = f'{base}_{get_china_time_str("%Y%m%d_%H%M%S")}{ext}'
    filepath = os.path.join(save_dir, filename)

    errors = []
    mirror = (load_auto_update_settings().get('github_mirror') or 'https://bdnb.cn').rstrip('/')
    # 1) 镜像站下载代理
    try:
        from urllib.parse import quote
        proxy_url = f'{mirror}/api/download/asset?url={quote(url, safe="")}&filename={quote(name, safe="")}&fast=1&mirror=0&proxy=1'
        resp = requests.get(proxy_url, stream=True, headers={'User-Agent': 'FrogDailyCheck-AutoUpdate'}, timeout=600)
        if resp.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            return filepath, os.path.getsize(filepath)
        errors.append(f'镜像下载 HTTP {resp.status_code}')
    except Exception as e:
        errors.append(f'镜像下载失败: {e}')

    # 2) 回退直连 GitHub
    resp = requests.get(url, stream=True, headers={'User-Agent': 'FrogDailyCheck-AutoUpdate'}, timeout=600)
    resp.raise_for_status()
    with open(filepath, 'wb') as f:
        for chunk in resp.iter_content(8192):
            if chunk:
                f.write(chunk)
    return filepath, os.path.getsize(filepath)

def register_auto_package(filepath, display_name, version, note, size):
    """把下载好的安装包登记为安装包并设为当前版本"""
    files_info = load_files_info()
    files_info['files'].append({
        'filename': os.path.basename(filepath),
        'original_name': os.path.basename(filepath),
        'display_name': display_name,
        'version': version,
        'size': size,
        'upload_time': get_china_time().isoformat(),
        'path': filepath,
        'note': note,
        'force_update': False,
        'source': 'github-auto',
    })
    files_info['current_version'] = os.path.basename(filepath)
    save_files_info(files_info)

_update_lock = threading.Lock()

def run_update_check(auto_upload=True):
    """核心检测逻辑：同步 releases -> 判断是否新版本 -> 下载 -> 上传"""
    with _update_lock:
        settings = load_auto_update_settings()
        last_tag = settings.get('last_processed_tag')
        result = {
            'success': False, 'has_update': False, 'uploaded': False,
            'latest_version': '', 'current_version': last_tag or '无',
            'update_note': '', 'message': '',
        }

        # 同步所有 releases（记录版本+时间），返回从新到旧列表
        synced = sync_github_releases()
        if not synced:
            result['message'] = '无法获取 GitHub 版本信息'
            _record_check(False, result['message'])
            return result

        latest = synced[0]
        tag = latest.get('version') or ''
        result['latest_version'] = tag

        # 判断是否有新版本
        is_new = (not last_tag) or (compare_versions(tag, last_tag) > 0)
        if last_tag and compare_versions(tag, last_tag) == 0:
            is_new = False

        if not is_new:
            result['success'] = True
            result['message'] = '已是最新版本（本地 ' + str(last_tag) + '，GitHub ' + str(tag) + '）'
            _record_check(True, result['message'])
            return result

        result['has_update'] = True
        result['current_version'] = last_tag or '无'
        result['update_note'] = latest.get('note') or latest.get('summary') or ''

        if not auto_upload:
            result['success'] = True
            result['message'] = '检测到新版本 ' + str(tag) + '（自动上传未开启，仅检测）'
            _record_check(True, result['message'])
            return result

        # 下载并上传
        asset_info = latest.get('asset') or {}
        github_url = asset_info.get('url') or ''
        asset_name = asset_info.get('name') or 'package.exe'
        if not github_url:
            result['message'] = '检测到新版本 ' + str(tag) + '，但该 Release 没有可下载的安装包'
            _record_check(False, result['message'])
            return result

        asset_obj = {'browser_download_url': github_url, 'name': asset_name}
        try:
            filepath, size = download_github_asset(asset_obj, UPLOAD_FOLDER)
        except Exception as e:
            result['message'] = '下载安装包失败：' + str(e)
            _record_check(False, result['message'])
            return result

        version = tag.lstrip('vV')
        note = result['update_note']
        register_auto_package(filepath, '绿豆蛙日报助手', version, note, size)
        _record_check(True, '已自动上传新版本 ' + str(tag) + ' 并设为当前版本', {'last_processed_tag': tag})

        result['success'] = True
        result['uploaded'] = True
        result['message'] = '已自动上传新版本 ' + str(tag) + ' 并设为当前版本'
        return result


_auto_update_thread = None

def _auto_update_worker():
    """后台线程：定时同步全部版本记录（含发布时间）+ 检测新版本"""
    time.sleep(30)  # 启动后先等待，避免服务器刚启动就立即检测
    while True:
        interval = 60
        try:
            settings = load_auto_update_settings()
            interval = max(int(settings.get('interval_minutes', 60) or 60), 1)
            auto_upload = bool(settings.get('enabled'))
            run_update_check(auto_upload=auto_upload)
        except Exception as e:
            print('[自动更新] 定时任务异常: ' + str(e))
        time.sleep(interval * 60)

def start_auto_update_scheduler():
    """启动后台自动更新检测线程（幂等）"""
    global _auto_update_thread
    if _auto_update_thread and _auto_update_thread.is_alive():
        return
    _auto_update_thread = threading.Thread(target=_auto_update_worker, daemon=True, name='auto-update-scheduler')
    _auto_update_thread.start()
    print('[自动更新] 后台检测线程已启动')


# ============ 自动更新管理接口 ============
@app.route('/api/admin/auto-update/settings', methods=['GET'])
def admin_get_auto_update_settings():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    s = load_auto_update_settings()
    safe = dict(s)
    key = safe.get('glm_api_key', '')
    safe['glm_api_key_configured'] = bool(key)
    safe['glm_api_key'] = '********' if key else ''
    return jsonify({'success': True, 'settings': safe})

@app.route('/api/admin/auto-update/settings', methods=['POST'])
def admin_update_auto_update_settings():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    data = request.json or {}
    updates = {}
    if 'enabled' in data:
        updates['enabled'] = bool(data['enabled'])
    if 'interval_minutes' in data:
        try:
            updates['interval_minutes'] = max(int(data['interval_minutes']), 1)
        except (TypeError, ValueError):
            pass
    if 'github_repo' in data:
        repo = str(data['github_repo']).strip()
        if repo:
            updates['github_repo'] = repo
    save_auto_update_settings(updates)
    return jsonify({'success': True, 'message': '设置已保存'})

@app.route('/api/admin/auto-update/check', methods=['POST'])
def admin_auto_update_check():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    settings = load_auto_update_settings()
    auto_upload = bool(settings.get('enabled'))
    result = run_update_check(auto_upload=auto_upload)
    return jsonify({'success': True, 'result': result})

@app.route('/api/admin/auto-update/status', methods=['GET'])
def admin_auto_update_status():
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401
    s = load_auto_update_settings()
    return jsonify({
        'success': True,
        'enabled': bool(s.get('enabled')),
        'github_repo': s.get('github_repo'),
        'interval_minutes': s.get('interval_minutes'),
        'last_check_time': s.get('last_check_time'),
        'last_check_result': s.get('last_check_result'),
        'last_processed_tag': s.get('last_processed_tag'),
    })



# ============ 版本历史接口 ============
def format_china_datetime(iso):
    """ISO 时间 -> 东八区 'YYYY-MM-DD HH:MM'"""
    if not iso:
        return ''
    try:
        dt = datetime.fromisoformat(str(iso).replace('Z', '+00:00'))
        dt = dt.astimezone(CHINA_TZ)
        return dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return ''

def load_versions_cache():
    """读取版本缓存，返回 (versions, synced_at)"""
    if os.path.exists(VERSIONS_FILE):
        try:
            with open(VERSIONS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('versions', []), data.get('synced_at')
        except Exception:
            pass
    return [], None

def load_versions():
    """读取版本历史数据"""
    versions, _ = load_versions_cache()
    return versions

def save_versions_cache(versions, synced_at):
    """把版本列表写入缓存文件"""
    with open(VERSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'synced_at': synced_at, 'versions': versions}, f, ensure_ascii=False, indent=2)

def _build_changes_and_note(body, api_key, model, cached):
    """用 GLM 提取并翻译更新内容，返回 (summary, changes, note)。带缓存，失败回退原始说明。"""
    if cached and cached.get('changes'):
        return cached.get('summary', ''), cached.get('changes', []), cached.get('note', '')
    try:
        raw = call_glm_extract(body or '', api_key, model)
        parsed = parse_update_note(raw)
        changes = [{'type': k, 'text': t} for k in ('新增', '优化', '修复') for t in (parsed.get(k) or [])]
        note = format_update_note(parsed)
        summary = ('本次更新包含 ' + str(len(changes)) + ' 项改动') if changes else ''
        return summary, changes, note
    except Exception as e:
        print('[自动更新] GLM 提取失败，回退原始说明: ' + str(e))
        fallback = (body or '').strip()
        if len(fallback) > 400:
            fallback = fallback[:400] + '...'
        return fallback, [], fallback

def _is_version_like(s):
    """判断字符串是否像纯版本号（如 v0.3、0.25、1.2.3）"""
    s = (s or '').strip().lower().lstrip('v')
    if not s:
        return False
    return all(ch.isdigit() or ch == '.' for ch in s)

def _extract_title(name, tag, body):
    """从 release 名或正文提取一个可读标题"""
    name = (name or '').strip()
    tag = (tag or '').strip()
    if name and name.lower() != tag.lower() and not _is_version_like(name):
        return name
    if body:
        for line in str(body).splitlines():
            t = line.strip()
            if t.startswith('#'):
                t = t.lstrip('#').strip()
            t = t.replace('*', '').replace('_', '').replace('`', '').strip()
            if t:
                return t[:50]
    return tag or '版本'

def sync_github_releases():
    """同步所有 GitHub releases 到本地缓存（记录版本号 + 发布时间 + GLM 翻译），返回从新到旧的版本列表"""
    settings = load_auto_update_settings()
    repo = settings.get('github_repo', 'DGLZR/frog-daliy-check')
    api_key = settings.get('glm_api_key')
    model = settings.get('glm_model')
    mirror = (settings.get('github_mirror') or 'https://bdnb.cn').rstrip('/')

    old_versions, _ = load_versions_cache()
    old_map = {}
    for ov in old_versions:
        tag = ov.get('version') or ov.get('tag_name') or ''
        # 只复用带 datetime 的真实同步记录（避免旧占位数据污染）
        if tag and ov.get('datetime'):
            old_map[str(tag).lower()] = ov

    try:
        releases = fetch_github_releases(repo)
    except Exception as e:
        print('[自动更新] 同步 releases 失败: ' + str(e))
        return old_versions

    if not releases:
        return old_versions

    from urllib.parse import quote
    synced = []
    for r in releases:
        tag = (r.get('tag_name') or '').strip()
        name = (r.get('name') or '').strip()
        dt = format_china_datetime(r.get('published_at') or r.get('created_at'))
        date = dt.split(' ')[0] if dt else ''

        cached = old_map.get(str(tag).lower())
        summary, changes, note = _build_changes_and_note(r.get('body'), api_key, model, cached)

        asset = _pick_exe_asset(r.get('assets') or [])
        asset_name = (asset.get('name') or '') if asset else ''
        github_url = (asset.get('browser_download_url') or '') if asset else ''
        download_url = None
        if github_url:
            download_url = mirror + '/api/download/asset?url=' + quote(github_url, safe='') + '&filename=' + quote(asset_name, safe='') + '&fast=1&mirror=0&proxy=1'

        title = _extract_title(name, tag, r.get('body'))
        if changes and changes[0].get('text'):
            title = changes[0]['text']
            if len(title) > 24:
                title = title[:24] + '...'

        record = {
            'version': tag,
            'date': date,
            'datetime': dt,
            'title': title,
            'channel': '预发布' if r.get('prerelease') else '稳定版',
            'summary': summary,
            'changes': changes,
            'note': note,
            'html_url': r.get('html_url'),
            'raw_body': (r.get('body') or '').strip(),
            'download_url': download_url,
            'size': (asset.get('size', 0) if asset else 0),
            'asset': {'name': asset_name, 'url': github_url} if asset else None,
        }
        synced.append(record)

    synced.sort(key=lambda x: (x.get('datetime') or '', x.get('version') or ''), reverse=True)

    save_versions_cache(synced, get_china_time_str('%Y-%m-%d %H:%M:%S'))
    return synced

@app.route('/api/versions', methods=['GET'])
def get_versions():
    """获取版本更新历史（覆盖全部版本，按时间从新到旧）"""
    versions, synced_at = load_versions_cache()
    if not versions:
        versions = sync_github_releases()
        _, synced_at = load_versions_cache()

    files_info = load_files_info()
    files = files_info.get('files', [])
    current = files_info.get('current_version')

    result = []
    for v in versions:
        item = dict(v)
        item.setdefault('is_current', False)
        item.setdefault('download_url', None)
        item.setdefault('size', 0)

        tag = str(item.get('version', '')).lstrip('vV')
        asset_name = ((item.get('asset') or {}).get('name')) or ''

        local = None
        for f in files:
            fver = str(f.get('version', '')).lstrip('vV')
            if fver and tag and fver == tag:
                local = f
                break
        if not local and asset_name:
            for f in files:
                if f.get('original_name') == asset_name or f.get('filename') == asset_name:
                    local = f
                    break

        if local and os.path.exists(os.path.join(UPLOAD_FOLDER, local['filename'])):
            item['download_url'] = '/download/' + local['filename']
            item['size'] = local.get('size', item.get('size', 0))
            item['is_current'] = (local['filename'] == current)

        result.append(item)

    return jsonify({'success': True, 'versions': result, 'count': len(result), 'synced_at': synced_at})


# ============ 版本检查接口 ============
@app.route('/api/check-update', methods=['GET'])
def check_update():
    """检查更新 - 只检查当前版本"""
    current_version = request.args.get('current_version', 'v0.0').strip()
    
    # 从 files_info.json 读取当前版本的版本号
    files_info = load_files_info()
    latest_version = None
    update_log = ''
    download_url = ''
    force_update = False
    
    if files_info.get('current_version'):
        # 找到当前版本的文件信息
        for f in files_info.get('files', []):
            if f['filename'] == files_info['current_version']:
                ver = f.get('version', '0')
                latest_version = f'v{ver}' if not ver.startswith('v') else ver
                update_log = f.get('note', '')
                download_url = f"/download/{f['filename']}"
                force_update = bool(f.get('force_update', False))
                break
    
    # 如果没有当前版本，返回无更新
    if not latest_version:
        return jsonify({
            'success': True,
            'has_update': False,
            'current_version': current_version,
            'latest_version': current_version,
            'update_log': '',
            'download_url': '',
            'force_update': False
        })
    
    # 比较版本号
    def parse_version(v):
        try:
            return float(v.replace('v', ''))
        except:
            return 0.0
    
    has_update = parse_version(latest_version) > parse_version(current_version)
    
    return jsonify({
        'success': True,
        'has_update': has_update,
        'current_version': current_version,
        'latest_version': latest_version,
        'update_log': update_log,
        'download_url': download_url if has_update else '',
        'force_update': force_update if has_update else False
    })


# ============ 服务器监测接口 ============
# 缓存上一次的网络 I/O，用于计算速率
_last_net_io = {'sent': 0, 'recv': 0, 'time': 0}

def _format_bytes(num):
    """字节转可读单位"""
    try:
        num = float(num)
    except (TypeError, ValueError):
        return '0 B'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if num < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} EB"

def _format_uptime(seconds):
    """秒转可读时长"""
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return '未知'
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days: parts.append(f"{days}天")
    if hours: parts.append(f"{hours}小时")
    parts.append(f"{minutes}分钟")
    return ' '.join(parts)

@app.route('/api/admin/server-stats', methods=['GET'])
def admin_server_stats():
    """服务器监测 - 返回硬件信息与实时指标"""
    if not session.get('admin_logged_in'):
        return jsonify({'success': False}), 401

    if not PSUTIL_AVAILABLE:
        return jsonify({
            'success': False,
            'message': '服务器未安装 psutil，无法获取监测数据'
        }), 500

    import time
    now = time.time()

    # ---- CPU ----
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)
    try:
        cpu_freq = psutil.cpu_freq()
        cpu_freq_mhz = round(cpu_freq.current, 0) if cpu_freq else 0
    except Exception:
        cpu_freq_mhz = 0
    try:
        per_cpu = psutil.cpu_percent(interval=None, percpu=True)
    except Exception:
        per_cpu = []
    try:
        load_avg = list(psutil.getloadavg())
    except Exception:
        load_avg = []

    # ---- 内存 ----
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # ---- 磁盘 ----
    try:
        disk = psutil.disk_usage('/')
    except Exception:
        disk = psutil.disk_usage('C:\\') if os.name == 'nt' else None

    # ---- 网络 ----
    net = psutil.net_io_counters()
    net_rate = {'sent': 0.0, 'recv': 0.0}
    if _last_net_io['time'] > 0:
        dt = now - _last_net_io['time']
        if dt > 0:
            net_rate['sent'] = max(0, (net.bytes_sent - _last_net_io['sent']) / dt)
            net_rate['recv'] = max(0, (net.bytes_recv - _last_net_io['recv']) / dt)
    _last_net_io['sent'] = net.bytes_sent
    _last_net_io['recv'] = net.bytes_recv
    _last_net_io['time'] = now

    # ---- 系统 / 开机时间 ----
    boot_time = psutil.boot_time()
    uptime_seconds = now - boot_time
    try:
        cpu_model = platform.processor() or '未知'
    except Exception:
        cpu_model = '未知'

    # ---- 进程数 / 线程数 ----
    try:
        process_count = len(psutil.pids())
    except Exception:
        process_count = 0
    try:
        thread_count = psutil.Process().num_threads()
    except Exception:
        thread_count = 0

    return jsonify({
        'success': True,
        'timestamp': now,
        'static': {
            'hostname': socket.gethostname(),
            'os': f"{platform.system()} {platform.release()}",
            'os_detail': platform.platform(),
            'arch': platform.machine(),
            'python_version': platform.python_version(),
            'cpu_model': cpu_model,
            'cpu_logical': cpu_count_logical,
            'cpu_physical': cpu_count_physical,
            'cpu_freq_mhz': cpu_freq_mhz,
            'total_memory': _format_bytes(mem.total),
            'total_memory_raw': mem.total,
            'total_swap': _format_bytes(swap.total),
            'disk_total': _format_bytes(disk.total) if disk else '未知',
            'disk_device': '/' if os.name != 'nt' else 'C:\\',
            'boot_time': datetime.fromtimestamp(boot_time).strftime('%Y-%m-%d %H:%M:%S'),
            'uptime': _format_uptime(uptime_seconds)
        },
        'dynamic': {
            'cpu_percent': cpu_percent,
            'per_cpu': per_cpu,
            'load_avg': load_avg,
            'memory_percent': mem.percent,
            'memory_used': _format_bytes(mem.used),
            'memory_available': _format_bytes(mem.available),
            'swap_percent': swap.percent,
            'swap_used': _format_bytes(swap.used),
            'disk_percent': disk.percent if disk else 0,
            'disk_used': _format_bytes(disk.used) if disk else '未知',
            'disk_free': _format_bytes(disk.free) if disk else '未知',
            'net_sent_total': _format_bytes(net.bytes_sent),
            'net_recv_total': _format_bytes(net.bytes_recv),
            'net_sent_rate': net_rate['sent'],
            'net_recv_rate': net_rate['recv'],
            'net_sent_rate_text': _format_bytes(net_rate['sent']) + '/s',
            'net_recv_rate_text': _format_bytes(net_rate['recv']) + '/s',
            'process_count': process_count,
            'thread_count': thread_count,
            'uptime_seconds': int(uptime_seconds)
        }
    })


if __name__ == '__main__':
    init_csv()
    start_auto_update_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=True)