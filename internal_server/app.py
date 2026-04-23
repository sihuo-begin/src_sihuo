from flask import Flask, render_template, request, redirect, url_for
import yaml
import os

app = Flask(__name__)

DATA_DIR = 'data'
STATIC_MATERIAL_DIR = 'static/materials'

MATERIAL_FILE = os.path.join(DATA_DIR, 'materials.yaml')
QUESTION_FILE = os.path.join(DATA_DIR, 'questions.yaml')
SCORE_FILE = os.path.join(DATA_DIR, 'scores.yaml')
PROGRESS_FILE = os.path.join(DATA_DIR, 'training_progress.yaml')



def load_yaml(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f) or default


def save_yaml(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(data, f, allow_unicode=True)


def is_trained(employee_id, material_id):
    progress = load_yaml(PROGRESS_FILE, {'progress': []})['progress']
    return any(
        p for p in progress
        if p['employee_id'] == employee_id and p['material_id'] == material_id
    )


@app.route('/')
def index():
    keyword = request.args.get('keyword', '')
    materials = load_yaml(MATERIAL_FILE, {}).get('materials', [])
    employee_id = "10001"  # 示例，实际来自登录或 URL

    for m in materials:
        if is_trained(employee_id, m['id']):
            m['can_exam'] = True
        else:
            m['can_exam'] = False
    for m in materials:
        m['file_path'] = f"static/materials/{m['file']}"

    if keyword:
        materials = [
            m for m in materials
            if keyword in m['name']
            or keyword in m['station']
            or keyword in m['project']
        ]
    # print(materials)
    return render_template('index.html', materials=materials, employee_id=employee_id)


@app.route('/training/<material_id>')
# def training(material_id):
#     materials = load_yaml(MATERIAL_FILE, {}).get('materials', [])
#     material = next(m for m in materials if m['id'] == material_id)
#
#     material['file_path'] = f"{STATIC_MATERIAL_DIR}/{material['file']}"
#     return render_template('training.html', material=material)

def training(material_id):
    employee_id = request.args.get('employee_id')
    if not employee_id:
        return "缺少 employee_id", 400

    progress = load_yaml(PROGRESS_FILE, {'progress': []})

    exists = any(
        p for p in progress['progress']
        if p['employee_id'] == employee_id and p['material_id'] == material_id
    )

    if not exists:
        progress['progress'].append({
            'employee_id': employee_id,
            'material_id': material_id,
            'trained': True
        })
        save_yaml(PROGRESS_FILE, progress)

    # 正常渲染培训页面
    materials = load_yaml(MATERIAL_FILE, {})['materials']
    material = next(m for m in materials if m['id'] == material_id)
    material['file_path'] = f"static/materials/{material['file']}"

    return render_template('training.html', material=material)


@app.route('/exam/<material_id>', methods=['GET', 'POST'])
def exam(material_id):
    employee_id = request.args.get('employee_id') or request.form.get('employee_id')

    if not employee_id:
        return "缺少 employee_id", 400
    # ❌ 未培训 → 禁止考试
    if not is_trained(employee_id, material_id):
        return "请先完成培训，再参加考试", 403
    materials = load_yaml(MATERIAL_FILE, {}).get('materials', [])
    questions = load_yaml(QUESTION_FILE, {}).get('questions', {})
    scores = load_yaml(SCORE_FILE, {'scores': []})

    material = next(m for m in materials if m['id'] == material_id)
    qs = questions.get(material_id, [])

    if request.method == 'POST':
        employee_id = request.form['employee_id']

        # for idx, q in enumerate(qs):
        #     if request.form.get(f'q{idx}') == q['answer']:
        #         score += 1
        #
        # scores['scores'].append({
        #     'employee_id': employee_id,
        #     'material_id': material_id,
        #     'material_name': material['name'],
        #     'station': material['station'],
        #     'project': material['project'],
        #     'score': score,
        #     'total': len(qs)
        # })
        #
        # save_yaml(SCORE_FILE, scores)
        score = 0
        for idx, q in enumerate(qs):
            if request.form.get(f'q{idx}') == q['answer']:
                score += 1

        total = len(qs)
        pass_line = 0.8
        passed = (score / total) >= pass_line

        # 读取已有成绩
        existing = None
        for s in scores['scores']:
            if s['employee_id'] == employee_id and s['material_id'] == material_id:
                existing = s
                break

        if existing:
            # ✅ 只保留最高分
            if score > existing['score']:
                existing['score'] = score
                existing['total'] = total
                existing['passed'] = passed
        else:
            scores['scores'].append({
                'employee_id': employee_id,
                'material_id': material_id,
                'material_name': material['name'],
                'station': material['station'],
                'project': material['project'],
                'score': score,
                'total': total,
                'passed': passed
            })

        save_yaml(SCORE_FILE, scores)
        return redirect(url_for('scores'))

    return render_template('exam.html', material=material, questions=qs)


@app.route('/scores')
def scores():
    employee_id = request.args.get('employee_id', '')
    data = load_yaml(SCORE_FILE, {'scores': []})['scores']

    if employee_id:
        data = [s for s in data if s['employee_id'] == employee_id]

    return render_template('scores.html', results=data)


@app.route('/clear/<employee_id>')
def clear(employee_id):
    data = load_yaml(SCORE_FILE, {'scores': []})
    data['scores'] = [s for s in data['scores'] if s['employee_id'] != employee_id]
    save_yaml(SCORE_FILE, data)
    return redirect(url_for('scores'))


if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    # app.run(host='0.0.0.0', port=5000, debug=True)
    app.run(host='10.200.148.19', port=5000, debug=True)