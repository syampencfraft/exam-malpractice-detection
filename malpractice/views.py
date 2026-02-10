from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import StudentProfile, Exam, Question, ExamResult, MalpracticeLog, FaceVerification, StudentAnswer
from .forms import StudentProfileForm
from django.http import JsonResponse, HttpResponse
import json
from django.views.decorators.csrf import csrf_exempt
import os
import base64
from django.core.files.base import ContentFile
from django.db.models import Count, Q
import csv
from datetime import datetime

from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

from .face_utils import encode_face_from_image, verify_face, is_valid_face_image


# Create your views here.
def first(request):
    return render(request, 'first.html')

def index(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            exams = Exam.objects.all().order_by('-date')
        else:
            taken_exam_ids = ExamResult.objects.filter(student=request.user).values_list('exam_id', flat=True)
            exams = request.user.exams.exclude(id__in=taken_exam_ids).order_by('-date')
    else:
        exams = None
    return render(request,'index.html', {'exams': exams})



def signup_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        age = request.POST.get('age')
        student_class = request.POST.get('class')
        department = request.POST.get('department')
        phone = request.POST.get('phone')
        class_id = request.POST.get('class_id')
        image = request.FILES.get('image')

        if User.objects.filter(username=username).exists():
            return render(request, "signup.html", {"error": "Username already exists."})
        
        if not image:
            return render(request, "signup.html", {"error": "Please upload your face image."})

        # Create user first
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Create profile with image
        profile = StudentProfile.objects.create(
            user=user,
            age=age,
            student_class=student_class,
            department=department,
            phone=phone,
            class_id=class_id,
            image=image
        )
        
        # Encode face from the uploaded image
        image_path = profile.image.path
        face_encoding_json, error = encode_face_from_image(image_path)
        
        if error:
            # Delete the user and profile if face encoding fails
            profile.delete()
            user.delete()
            return render(request, "signup.html", {"error": error})
        
        # Save face encoding
        profile.face_encoding = face_encoding_json
        profile.save()

        return render(request, "signup.html", {
            "msg": "Registered successfully with face verification enabled. Wait for admin approval."
        })

    return render(request, "signup.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user:
            try:
                profile = user.studentprofile
                if not profile.is_approved:
                    messages.error(request, "Admin approval required.")
                    return redirect('login')
            except:
                pass  # admin user

            login(request, user)
            if user.is_staff or user.is_superuser:
                return redirect('approve')
            return redirect('index')

        messages.error(request, "Invalid credentials")

    return render(request, "login.html")


@staff_member_required
def approve_students(request):
    students = StudentProfile.objects.all()

    if request.method == "POST":
        student_id = request.POST['student_id']
        student = StudentProfile.objects.get(id=student_id)
        student.is_approved = True
        student.save()
        messages.success(request, f"Student {student.user.username} approved.")
        return redirect('approve')

    return render(request, "admin_dashboard.html", {"students": students})

@login_required
def profile_view(request, pk=None):
    if pk and (request.user.is_staff or request.user.is_superuser):
        try:
            profile = StudentProfile.objects.get(user_id=pk)
        except StudentProfile.DoesNotExist:
            return redirect('approve')
    else:
        try:
            profile = request.user.studentprofile
        except:
            return redirect('index')
    
    return render(request, "profile.html", {"profile": profile})

@login_required
def edit_profile(request):
    try:
        profile = request.user.studentprofile
    except StudentProfile.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('index')

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'edit_profile.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@staff_member_required
def add_exam(request):
    if request.method == "POST":
        title = request.POST.get('title')
        date = request.POST.get('date')
        time = request.POST.get('time')
        topic = request.POST.get('topic')
        duration = request.POST.get('duration')
        student_ids = request.POST.getlist('students')
        
        exam = Exam.objects.create(
            title=title,
            date=date,
            time=time,
            topic=topic,
            duration_minutes=duration
        )
        if student_ids:
            exam.students.set(student_ids)
            
        if student_ids:
            exam.students.set(student_ids)
            
        messages.success(request, f"Exam '{title}' created. Now add questions.")
        return redirect('add_questions', exam_id=exam.id)
    
    # Only show approved students for selection
    students = StudentProfile.objects.filter(is_approved=True)
    return render(request, "add_exam.html", {"students": students})

@staff_member_required
def add_questions(request, exam_id):
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        messages.error(request, "Exam not found.")
        return redirect('approve')
        
    if request.method == "POST":
        q_type = request.POST.get('question_type')
        text = request.POST.get('question_text')
        
        if q_type == 'MCQ':
            opt1 = request.POST.get('option_1')
            opt2 = request.POST.get('option_2')
            opt3 = request.POST.get('option_3')
            opt4 = request.POST.get('option_4')
            correct = request.POST.get('correct_option')
            
            Question.objects.create(
                exam=exam,
                question_text=text,
                question_type='MCQ',
                option_1=opt1, option_2=opt2, option_3=opt3, option_4=opt4,
                correct_option=correct
            )
        else:
            Question.objects.create(
                exam=exam,
                question_text=text,
                question_type='DESCRIPTIVE'
            )
            
        messages.success(request, "Question added successfully!")
        return redirect('add_questions', exam_id=exam.id)
        
    questions = exam.questions.all().order_by('-id')
    return render(request, "add_questions.html", {"exam": exam, "questions": questions})

@login_required
def take_exam(request, pk):
    try:
        exam = Exam.objects.get(id=pk)
    except Exam.DoesNotExist:
        return redirect('index')
        
    if not request.user.is_staff and not exam.students.filter(id=request.user.id).exists():
        messages.error(request, "You are not assigned to this exam.")
        return redirect('index')
    
    # Check if student has verified their face for this exam
    if not request.user.is_staff:
        try:
            verification = FaceVerification.objects.get(student=request.user, exam=exam)
            if not verification.verified:
                messages.warning(request, "Face verification failed. Please try again.")
                return redirect('verify_face', exam_id=exam.id)
        except FaceVerification.DoesNotExist:
            messages.info(request, "Please verify your identity before starting the exam.")
            return redirect('verify_face', exam_id=exam.id)
    
    questions = exam.questions.all()

    if request.method == "POST":
        score = 0
        has_descriptive = False
        total = questions.count()
        
        for q in questions:
            user_answer = request.POST.get(f'q{q.id}')
            
            if q.question_type == 'DESCRIPTIVE':
                has_descriptive = True
                if user_answer:
                    StudentAnswer.objects.create(
                        student=request.user,
                        exam=exam,
                        question=q,
                        answer_text=user_answer
                    )
            elif q.question_type == 'MCQ':
                if user_answer and int(user_answer) == q.correct_option:
                    score += 1
        
        # Determine status
        status = 'PENDING' if has_descriptive else 'PUBLISHED'
        
        video_file = request.FILES.get('video_file')
        
        ExamResult.objects.create(
            student=request.user,
            exam=exam,
            score=score,
            total_questions=total,
            status=status,
            video_file=video_file
        )
        
        msg = f"Exam '{exam.title}' submitted!"
        if status == 'PENDING':
            msg += " Result pending evaluation."
        else:
            msg += f" Score: {score}/{total}"
            
        messages.success(request, msg)
        return redirect('index')

    return render(request, "take_exam.html", {"exam": exam, "questions": questions})

@login_required
def view_results(request):
    from django.db.models import Count
    results = ExamResult.objects.filter(student=request.user).order_by('-completed_at')
    
    # Calculate malpractice counts per result
    log_counts = MalpracticeLog.objects.filter(student=request.user).values('exam_id').annotate(count=Count('id'))
    count_map = {x['exam_id']: x['count'] for x in log_counts}
    
    results = list(results)
    for res in results:
        res.malpractice_count = count_map.get(res.exam_id, 0)
        
    return render(request, "results.html", {"results": results})

@staff_member_required
def admin_results(request):
    # Get filter parameters
    exam_filter = request.GET.get('exam')
    severity_filter = request.GET.get('severity')
    student_filter = request.GET.get('student')
    
    # Convert exam_filter to int if present
    selected_exam_id = None
    if exam_filter:
        try:
            selected_exam_id = int(exam_filter)
        except (ValueError, TypeError):
            selected_exam_id = None
    
    results = ExamResult.objects.all().order_by('-completed_at')
    malpractice_logs = MalpracticeLog.objects.all().order_by('-timestamp')
    
    # Apply filters
    if selected_exam_id:
        results = results.filter(exam_id=selected_exam_id)
        malpractice_logs = malpractice_logs.filter(exam_id=selected_exam_id)
    
    if severity_filter:
        malpractice_logs = malpractice_logs.filter(severity=severity_filter)
    
    if student_filter:
        results = results.filter(student__username__icontains=student_filter)
        malpractice_logs = malpractice_logs.filter(student__username__icontains=student_filter)
    

    
    # Calculate malpractice counts per result
    # Group logs by student and exam to get counts
    log_counts = MalpracticeLog.objects.values('student_id', 'exam_id').annotate(count=Count('id'))
    count_map = {(x['student_id'], x['exam_id']): x['count'] for x in log_counts}
    
    # Attach counts to results
    # We convert queryset to list to attach attributes effectively
    results = list(results)
    for res in results:
        res.malpractice_count = count_map.get((res.student_id, res.exam_id), 0)
    
    # Calculate statistics
    total_logs = MalpracticeLog.objects.count()
    severity_stats = MalpracticeLog.objects.values('severity').annotate(count=Count('id'))
    type_stats = MalpracticeLog.objects.values('log_type').annotate(count=Count('id')).order_by('-count')[:5]
    
    # Get all exams for filter dropdown
    exams = Exam.objects.all()
    
    context = {
        "results": results,
        "malpractice_logs": malpractice_logs,
        "total_logs": total_logs,
        "severity_stats": severity_stats,
        "type_stats": type_stats,
        "exams": exams,
        "selected_exam": selected_exam_id,
        "selected_severity": severity_filter,
        "selected_student": student_filter,
    }
    return render(request, "admin_results.html", context)

@csrf_exempt
@login_required
def log_malpractice(request):
    if request.method == "POST":
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        log_type = data.get('log_type')
        details = data.get('details')
        severity = data.get('severity', 'MEDIUM')
        snapshot_data = data.get('snapshot')  # Base64 image
        
        try:
            exam = Exam.objects.get(id=exam_id)
            
            # Create log entry
            log = MalpracticeLog(
                student=request.user,
                exam=exam,
                log_type=log_type,
                severity=severity,
                details=details
            )
            
            # Save snapshot if provided
            if snapshot_data:
                # Remove data URI prefix if present
                if ',' in snapshot_data:
                    snapshot_data = snapshot_data.split(',')[1]
                
                # Decode and save image
                image_data = base64.b64decode(snapshot_data)
                filename = f"{request.user.username}_{exam_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                log.snapshot.save(filename, ContentFile(image_data), save=False)
            
            log.save()
            
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse({"status": "ignored"}, status=405)

@staff_member_required
def view_malpractice_logs(request, student_id, exam_id):
    logs = MalpracticeLog.objects.filter(student_id=student_id, exam_id=exam_id).order_by('-timestamp')
    student = User.objects.get(id=student_id)
    exam = Exam.objects.get(id=exam_id)
    
    # Calculate statistics
    total_logs = logs.count()
    severity_breakdown = logs.values('severity').annotate(count=Count('id'))
    type_breakdown = logs.values('log_type').annotate(count=Count('id'))
    
    return render(request, "malpractice_report.html", {
        "logs": logs,
        "student": student,
        "exam": exam,
        "total_logs": total_logs,
        "severity_breakdown": severity_breakdown,
        "type_breakdown": type_breakdown,
    })

@staff_member_required
def evaluate_exam(request, result_id):
    try:
        result = ExamResult.objects.get(id=result_id)
    except ExamResult.DoesNotExist:
        messages.error(request, "Result not found.")
        return redirect('admin_results')
        
    student = result.student
    exam = result.exam
    
    # Get answers
    student_answers = StudentAnswer.objects.filter(student=student, exam=exam)
    answers_map = {a.question_id: a.answer_text for a in student_answers}
    
    # Get malpractice logs
    logs = MalpracticeLog.objects.filter(student=student, exam=exam).order_by('-timestamp')
    log_count = logs.count()
    
    if request.method == "POST":
        score = request.POST.get('score')
        comments = request.POST.get('admin_comments')
        grade = request.POST.get('grade')
        
        result.score = score
        result.admin_comments = comments
        result.grade = grade
        result.status = 'PUBLISHED'
        result.save()
        
        messages.success(request, f"Result for {student.username} published successfully!")
        return redirect('admin_results')
        
    questions = list(exam.questions.all())
    for q in questions:
        q.student_answer = answers_map.get(q.id, "No answer provided.")
    
    return render(request, "evaluate_exam.html", {
        "result": result,
        "questions": questions,
        "logs": logs,
        "log_count": log_count
    })

@staff_member_required
def download_malpractice_report(request, student_id, exam_id):
    """Download malpractice report as CSV"""
    logs = MalpracticeLog.objects.filter(student_id=student_id, exam_id=exam_id).order_by('-timestamp')
    student = User.objects.get(id=student_id)
    exam = Exam.objects.get(id=exam_id)
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="malpractice_report_{student.username}_{exam.title}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'Type', 'Severity', 'Details'])
    
    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.get_log_type_display(),
            log.severity,
            log.details or ''
        ])
    
    return response

@login_required
def verify_face_view(request, exam_id):
    """Display face verification page for exam access"""
    try:
        exam = Exam.objects.get(id=exam_id)
    except Exam.DoesNotExist:
        messages.error(request, "Exam not found.")
        return redirect('index')
    
    # Check if student is assigned to this exam
    if not request.user.is_staff and not exam.students.filter(id=request.user.id).exists():
        messages.error(request, "You are not assigned to this exam.")
        return redirect('index')
    
    # Check if already verified
    try:
        verification = FaceVerification.objects.get(student=request.user, exam=exam)
        if verification.verified:
            messages.success(request, "Face already verified. Proceeding to exam.")
            return redirect('take_exam', pk=exam.id)
    except FaceVerification.DoesNotExist:
        pass
    
    return render(request, "verify_face.html", {"exam": exam})

@csrf_exempt
@login_required
def verify_face_api(request):
    """API endpoint to verify face from webcam image"""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)
    
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        image_data = data.get('image')
        
        if not exam_id or not image_data:
            return JsonResponse({"success": False, "error": "Missing exam_id or image data"}, status=400)
        
        # Get exam
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return JsonResponse({"success": False, "error": "Exam not found"}, status=404)
        
        # Get student profile with face encoding
        try:
            profile = request.user.studentprofile
            if not profile.face_encoding:
                return JsonResponse({
                    "success": False, 
                    "error": "No face encoding found. Please contact admin."
                }, status=400)
        except StudentProfile.DoesNotExist:
            return JsonResponse({"success": False, "error": "Student profile not found"}, status=404)
        
        # Verify face
        is_match, similarity_score, error = verify_face(profile.face_encoding, image_data)
        
        if error:
            return JsonResponse({"success": False, "error": error}, status=400)
        
        # Update or create verification record
        verification, created = FaceVerification.objects.update_or_create(
            student=request.user,
            exam=exam,
            defaults={
                'verified': is_match,
                'similarity_score': similarity_score
            }
        )
        
        if is_match:
            return JsonResponse({
                "success": True,
                "verified": True,
                "similarity_score": similarity_score,
                "message": "Face verified successfully! Redirecting to exam..."
            })
        else:
            return JsonResponse({
                "success": True,
                "verified": False,
                "similarity_score": similarity_score,
                "message": f"Face verification failed. Similarity: {similarity_score:.2%}. Please try again."
            })
            
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@staff_member_required
def admin_view_recording(request, result_id):
    try:
        result = ExamResult.objects.get(id=result_id)
    except ExamResult.DoesNotExist:
        messages.error(request, "Result not found.")
        return redirect('admin_results')
    
    return render(request, "admin_view_recording.html", {"result": result})
