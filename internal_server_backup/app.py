from flask import Flask, render_template, request, redirect, url_for
import yaml
import os
import time

app = Flask(__name__)

DATA_DIR = "data"
STATIC_MATERIAL_DIR = "static/materials"

MATERIAL_FILE = os.path.join(DATA_DIR, "materials.yaml")
QUESTION_FILE = os.path.join(DATA_DIR, "questions.yaml")
SCORE_FILE = os.path.join(DATA_DIR, "scores.yaml")
PROGRESS_FILE = os.path.join(DATA_DIR, "training_progress.yaml")
# MIN_TRAIN_SECONDS = 5 * 60
MIN_TRAIN_SECONDS = 10


def load_yaml(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or default


def save_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)


def is_trained(employee_id, material_id):
    progress = load_yaml(PROGRESS_FILE, {"progress": []})["progress"]
    return any(p for p in progress if p["employee_id"] == employee_id and p["material_id"] == material_id)


@app.route("/")
def index():
    keyword = request.args.get("keyword", "")
    materials = load_yaml(MATERIAL_FILE, {}).get("materials", [])
    employee_id = ""  # 示例，实际来自登录或 URL
    # employee_id = request.form.get('employee_id')

    for m in materials:
        if is_trained(employee_id, m["id"]):
            m["can_exam"] = True
        else:
            m["can_exam"] = False
    for m in materials:
        m["file_path"] = f"static/materials/{m['file']}"

    if keyword:
        materials = [m for m in materials if keyword in m["name"] or keyword in m["station"] or keyword in m["project"]]
    return render_template("index.html", materials=materials, employee_id=employee_id)


@app.route("/training/<material_id>", methods=["GET", "POST"])
def training(material_id):
    materials = load_yaml(MATERIAL_FILE, {}).get("materials", [])
    material = next((m for m in materials if m["id"] == material_id), None)

    if not material:
        return "课程不存在", 404

    material["file_path"] = f"static/materials/{material['file']}"

    progress = load_yaml(PROGRESS_FILE, {"progress": []})
    message = None
    employee_id = None

    if request.method == "POST":
        employee_id = request.form.get("employee_id")
        start_time = float(request.form.get("start_time", 0))
        end_time = time.time()

        if not employee_id:
            message = "请输入员工ID"
        elif not start_time:
            message = "培训计时错误，请重新进入培训页面"
        else:
            duration = int(end_time - start_time)
            effective_seconds = int(request.form.get("effective_seconds", 0))

            # ✅ 双重校验
            if duration < MIN_TRAIN_SECONDS:
                message = f"培训页面停留时间不足（{duration}s），至少需要 {MIN_TRAIN_SECONDS}s"
            elif effective_seconds < MIN_TRAIN_SECONDS:
                message = f"有效学习时间不足（{effective_seconds}s），至少需要 {MIN_TRAIN_SECONDS}s"
            else:
                # ✅ 清除旧记录
                progress["progress"] = [
                    p
                    for p in progress["progress"]
                    if not (p["employee_id"] == employee_id and p["material_id"] == material_id)
                ]

                # ✅ 写入新记录
                progress["progress"].append(
                    {
                        "employee_id": employee_id,
                        "material_id": material_id,
                        "trained": True,
                        "start_time": int(start_time),
                        "end_time": int(end_time),
                        "duration_effective": effective_seconds,
                    }
                )

                save_yaml(PROGRESS_FILE, progress)
                message = "✅ 培训已完成，可进入考试"

    return render_template(
        "training.html", material=material, employee_id=employee_id, message=message, min_seconds=MIN_TRAIN_SECONDS
    )


@app.route("/exam/<material_id>", methods=["GET", "POST"])
def exam(material_id):
    employee_id = request.args.get("employee_id") or request.form.get("employee_id")
    if not employee_id:
        return "缺少 employee_id", 400
    # ❌ 未培训 → 禁止考试
    if not is_trained(employee_id, material_id):
        return "请先完成培训，再参加考试", 403
    materials = load_yaml(MATERIAL_FILE, {}).get("materials", [])
    questions = load_yaml(QUESTION_FILE, {}).get("questions", {})
    scores = load_yaml(SCORE_FILE, {"scores": []})

    material = next(m for m in materials if m["id"] == material_id)
    qs = questions.get(material_id, [])
    print(material_id)
    # print(materials, materials, material_id)
    if request.method == "POST":
        employee_id = request.form["employee_id"]

        score = 0
        for idx, q in enumerate(qs):
            if request.form.get(f"q{idx}") == q["answer"]:
                score += 1

        total = len(qs)

        # ✅ 百分比成绩（整数，便于展示）
        percentage = round(score / total * 100)

        # ✅ 合格线 80%
        passed = percentage >= 80

        # 读取已有成绩
        existing = None
        for s in scores["scores"]:
            if s["employee_id"] == employee_id and s["material_id"] == material_id:
                existing = s
                break

        if existing:
            # ✅ 只保留最高分
            if score > existing["score"]:
                existing["score"] = score
                existing["total"] = total
                existing["percentage"] = percentage
                existing["passed"] = passed
        else:
            scores["scores"].append(
                {
                    "employee_id": employee_id,
                    "material_id": material_id,
                    "material_name": material["name"],
                    "station": material["station"],
                    "project": material["project"],
                    "score": score,
                    "percentage": percentage,
                    "total": total,
                    "passed": passed,
                }
            )

        save_yaml(SCORE_FILE, scores)
        return redirect(url_for("scores"))

    return render_template("exam.html", material=material, questions=qs)


@app.route("/scores")
def scores():
    employee_id = request.args.get("employee_id", "")
    data = load_yaml(SCORE_FILE, {"scores": []})["scores"]

    if employee_id:
        data = [s for s in data if s["employee_id"] == employee_id]

    return render_template("scores.html", results=data)


@app.route("/clear/<employee_id>")
def clear(employee_id):
    data = load_yaml(SCORE_FILE, {"scores": []})
    data["scores"] = [s for s in data["scores"] if s["employee_id"] != employee_id]
    save_yaml(SCORE_FILE, data)
    return redirect(url_for("scores"))


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    # app.run(host='0.0.0.0', port=5000, debug=True)
    app.run(host="10.200.147.42", port=5000, debug=True)
