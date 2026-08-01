from flask import Blueprint, render_template, jsonify
import os
import csv
from datetime import datetime, timedelta, timezone

superadmin_bp = Blueprint('superadmin', __name__, template_folder='templates')

# 工作类型列表
WORK_TYPES = ['开发', '沟通', '生活', '学习', '设计', '管理', '文档', '娱乐', '产品', '会议', '运维', '测试', '数据分析', '其他']

# 东八区
CST = timezone(timedelta(hours=8))

def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_users():
    users_csv = os.path.join(get_base_dir(), 'data', 'users.csv')
    users = []
    if os.path.exists(users_csv):
        with open(users_csv, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                users.append(row)
    return users

def read_detail_data():
    detail_csv = os.path.join(get_base_dir(), 'data', 'detail_person_data.csv')
    data = []
    if os.path.exists(detail_csv):
        with open(detail_csv, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                data.append(row)
    return data

def get_user_folder(email):
    folder_name = email.replace('@', '_at_').replace('.', '_')
    return os.path.join(get_base_dir(), 'data', 'users', folder_name)

def calculate_user_stats(email):
    """实时计算用户统计数据"""
    user_folder = get_user_folder(email)
    records_file = os.path.join(user_folder, 'records.csv')
    report_folder = os.path.join(user_folder, 'report')
    today = datetime.now(CST).strftime('%Y-%m-%d')

    stats = {
        'today_focus_minutes': 0,
        'today_type_minutes': {wt: 0 for wt in WORK_TYPES},
        'today_records': 0,
        'total_records': 0,
        'today_reports': 0,
        'total_reports': 0
    }

    if os.path.exists(records_file):
        with open(records_file, 'r', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                stats['total_records'] += 1
                if row.get('日期') == today:
                    stats['today_records'] += 1
                    try:
                        duration = float(row.get('持续时长(分钟)', 0))
                        work_type = row.get('工作类型', '其他')
                        stats['today_focus_minutes'] += duration
                        if work_type in stats['today_type_minutes']:
                            stats['today_type_minutes'][work_type] += duration
                    except (ValueError, KeyError):
                        pass

    if os.path.exists(report_folder):
        for filename in os.listdir(report_folder):
            if filename.endswith('.md'):
                stats['total_reports'] += 1
                try:
                    parts = filename.split('_')
                    if len(parts) >= 2:
                        date_str = parts[-2]
                        if len(date_str) == 8:
                            file_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                            if file_date == today:
                                stats['today_reports'] += 1
                except Exception:
                    pass

    return stats

@superadmin_bp.route('/superadmin')
def superadmin_page():
    return render_template('index.html')

@superadmin_bp.route('/superadmin/user/<email>')
def user_detail_page(email):
    """用户详情页面"""
    users = read_users()
    user = next((u for u in users if u['邮箱'] == email), None)
    
    if not user:
        return '用户不存在', 404
    
    detail_data = read_detail_data()
    detail = next((d for d in detail_data if d['邮箱'] == email), {})
    
    # 实时计算统计数据，保证首次渲染准确
    stats = calculate_user_stats(email)
    detail['今日专注时长(分钟)'] = round(stats['today_focus_minutes'], 1)
    for wt in WORK_TYPES:
        detail[f'今日{wt}时长(分钟)'] = round(stats['today_type_minutes'][wt], 1)
    detail['今日记录条数'] = stats['today_records']
    detail['总共记录条数'] = stats['total_records']
    detail['今日生成报告数'] = stats['today_reports']
    detail['总共生成报告数'] = stats['total_reports']
    
    return render_template('user_detail.html', user=user, detail=detail, work_types=WORK_TYPES)