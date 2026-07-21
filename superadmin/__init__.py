from flask import Blueprint, render_template, jsonify
import os
import csv

superadmin_bp = Blueprint('superadmin', __name__, template_folder='templates')

# 工作类型列表
WORK_TYPES = ['开发', '沟通', '生活', '学习', '设计', '管理', '文档', '娱乐', '产品', '会议', '运维', '测试', '数据分析', '其他']

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
    
    return render_template('user_detail.html', user=user, detail=detail, work_types=WORK_TYPES)