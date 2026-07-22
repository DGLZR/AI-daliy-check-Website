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
DETAIL_CSV = os.path.join(DATA_DIR, 'detail_person_data.csv')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
FILES_INFO_PATH = os.path.join(BASE_DIR, 'files_info.json')

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
                           '今日生成报告数量', '总共生成报告数量'])

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
        '今日生成报告数量': 0,
        '总共生成报告数量': 0
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
        '注册时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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

def calculate_user_stats(email):
    """计算用户统计数据"""
    user_folder = get_user_folder(email)
    records_file = os.path.join(user_folder, 'records.csv')
    summary_file = os.path.join(user_folder, 'daily_summary.csv')
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    stats = {
        'today_focus_minutes': 0,
        'today_type_minutes': {wt: 0 for wt in WORK_TYPES},
        'today_reports': 0,
        'total_reports': 0
    }
    
    # 读取records.csv计算今日数据
    if os.path.exists(records_file):
        with open(records_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['日期'] == today:
                    try:
                        duration = float(row['持续时长(分钟)'])
                        work_type = row['工作类型']
                        stats['today_focus_minutes'] += duration
                        if work_type in stats['today_type_minutes']:
                            stats['today_type_minutes'][work_type] += duration
                    except (ValueError, KeyError):
                        pass
    
    # 读取daily_summary.csv计算报告数量
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    stats['total_reports'] += int(row.get('记录条数', 0))
                    if row['日期'] == today:
                        stats['today_reports'] = int(row.get('记录条数', 0))
                except (ValueError, KeyError):
                    pass
    
    return stats

def update_detail_data_on_login(email):
    """登录时更新用户详细数据"""
    stats = calculate_user_stats(email)
    detail_data = read_detail_data()
    
    for d in detail_data:
        if d['邮箱'] == email:
            d['最近登录时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            d['今日专注时长(分钟)'] = round(stats['today_focus_minutes'], 1)
            for wt in WORK_TYPES:
                d[f'今日{wt}时长(分钟)'] = round(stats['today_type_minutes'][wt], 1)
            d['今日生成报告数量'] = stats['today_reports']
            d['总共生成报告数量'] = stats['total_reports']
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
    # 更新详细数据
    update_detail_data_on_login(email)
    
    return jsonify({'success': True, 'message': '登录成功'})

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
        '日期': data.get('date', datetime.now().strftime('%Y-%m-%d')),
        '时间': data.get('time', datetime.now().strftime('%H:%M:%S')),
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
    
    date = data.get('date', datetime.now().strftime('%Y-%m-%d'))
    
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
    user_detail['今日生成报告数量'] = stats['today_reports']
    user_detail['总共生成报告数量'] = stats['total_reports']
    
    return jsonify({'success': True, 'user': user_detail})

if __name__ == '__main__':
    init_csv()
    app.run(host='0.0.0.0', port=5000, debug=True)