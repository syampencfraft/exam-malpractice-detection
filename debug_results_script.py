import os
import django
import sys
import json

# Set up Django environment
sys.path.append(r'c:\Users\91953\Desktop\2026 projects\exam\exam\exam')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exam.settings')
django.setup()

from malpractice.models import ExamResult, StudentAnswer, Question
from django.contrib.auth.models import User

def analyze_to_json():
    data = {"results": [], "collisions": []}
    
    results = ExamResult.objects.all().order_by('-completed_at')
    for r in results:
        res_info = {
            "id": r.id,
            "username": r.student.username,
            "student_id": r.student.id,
            "exam_title": r.exam.title,
            "exam_id": r.exam.id,
            "score": r.score,
            "total": r.total_questions,
            "answers_count": StudentAnswer.objects.filter(student=r.student, exam=r.exam).count()
        }
        data["results"].append(res_info)

    # Check for same answers across different students
    descriptive_questions = Question.objects.filter(question_type='DESCRIPTIVE')
    for q in descriptive_questions:
        answers = StudentAnswer.objects.filter(question=q)
        texts = {}
        for a in answers:
            if a.answer_text not in texts:
                texts[a.answer_text] = []
            texts[a.answer_text].append(a.student.username)
        
        for text, students in texts.items():
            if len(students) > 1:
                data["collisions"].append({
                    "question": q.question_text[:50],
                    "text": text[:50],
                    "students": students
                })

    with open(r'c:\Users\91953\Desktop\2026 projects\exam\exam\exam\debug_results.json', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    analyze_to_json()
