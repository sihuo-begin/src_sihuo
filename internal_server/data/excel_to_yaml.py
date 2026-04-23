import pandas as pd
import yaml
import os

DATA_DIR = 'data'

materials_df = pd.read_excel('training.xlsx', sheet_name='materials')
questions_df = pd.read_excel('training.xlsx', sheet_name='questions')

# 生成 materials.yaml
materials = {'materials': materials_df.to_dict(orient='records')}

# 生成 questions.yaml
questions = {'questions': {}}
for _, row in questions_df.iterrows():
    mid = row['material_id']
    questions['questions'].setdefault(mid, []).append({
        'question': row['question'],
        'options': {
            'A': row['A'],
            'B': row['B'],
            'C': row['C'],
            'D': row['D'],
        },
        'answer': row['answer']
    })

os.makedirs(DATA_DIR, exist_ok=True)

with open(os.path.join(DATA_DIR, 'materials.yaml'), 'w', encoding='utf-8') as f:
    yaml.safe_dump(materials, f, allow_unicode=True)

with open(os.path.join(DATA_DIR, 'questions.yaml'), 'w', encoding='utf-8') as f:
    yaml.safe_dump(questions, f, allow_unicode=True)

print("✅ Excel 已成功转换为 YAML")