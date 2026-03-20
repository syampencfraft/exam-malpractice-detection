from django.db import models

# Create your models here.
from django.contrib.auth.models import User
from django.db import models

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='student_images/', null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    student_class = models.CharField(max_length=100, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    class_id = models.CharField(max_length=50, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    face_encoding = models.TextField(null=True, blank=True, help_text="JSON-encoded face embedding for verification")

    def __str__(self):
        return self.user.username

class Exam(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    time = models.TimeField()
    topic = models.CharField(max_length=200)
    duration_minutes = models.IntegerField(help_text="Duration in minutes")
    students = models.ManyToManyField(User, related_name='exams')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    TYPE_CHOICES = [
        ('MCQ', 'Multiple Choice'),
        ('DESCRIPTIVE', 'Descriptive'),
    ]
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    question_text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='MCQ')
    
    # MCQ Options (optional for Descriptive)
    option_1 = models.CharField(max_length=200, null=True, blank=True)
    option_2 = models.CharField(max_length=200, null=True, blank=True)
    option_3 = models.CharField(max_length=200, null=True, blank=True)
    option_4 = models.CharField(max_length=200, null=True, blank=True)
    correct_option = models.IntegerField(choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')], null=True, blank=True)

    def __str__(self):
        return f"{self.exam.title} - {self.question_text[:50]}"

class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    result = models.ForeignKey('ExamResult', on_delete=models.CASCADE, null=True, blank=True, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()
    
    def __str__(self):
        return f"{self.student.username} - {self.question.question_text[:30]}"

class ExamResult(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Evaluation'),
        ('PUBLISHED', 'Published'),
    ]
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    total_questions = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PUBLISHED')
    admin_comments = models.TextField(null=True, blank=True)
    grade = models.CharField(max_length=50, null=True, blank=True, default="Pending")
    video_file = models.FileField(upload_to='exam_recordings/', null=True, blank=True, help_text="Full exam video recording")
    completed_at = models.DateTimeField(auto_now_add=True)

    @property
    def percentage(self):
        if self.total_questions > 0:
            return int((self.score / self.total_questions) * 100)
        return 0

    def __str__(self):
        return f"{self.student.username} - {self.exam.title} ({self.score}/{self.total_questions})"

class MalpracticeLog(models.Model):
    TYPES = [
        ('NO_FACE', 'No Face Detected'),
        ('MULTIPLE_FACES', 'Multiple Faces Detected'),
        ('LOOKING_AWAY', 'Looking Away from Screen'),
        ('EYE_TRACKING', 'Eyes Off Screen'),
        ('HEAD_POSE_LEFT', 'Head Turned Left'),
        ('HEAD_POSE_RIGHT', 'Head Turned Right'),
        ('HEAD_POSE_UP', 'Head Tilted Up'),
        ('HEAD_POSE_DOWN', 'Head Tilted Down'),
        ('PHONE_DETECTED', 'Mobile Phone Detected'),
        ('VOICE_DETECTED', 'Voice/Sound Detected'),
        ('TAB_SWITCH', 'Switched Browser Tab'),
        ('SUSPICIOUS_OBJECT', 'Suspicious Object Detected'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    log_type = models.CharField(max_length=50, choices=TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='MEDIUM')
    details = models.TextField(blank=True, null=True)
    snapshot = models.ImageField(upload_to='malpractice_snapshots/', null=True, blank=True, help_text="Frame capture at time of detection")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['student', 'exam']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f"{self.student.username} - {self.log_type} ({self.severity}) at {self.timestamp}"
    
    def get_severity_color(self):
        """Return Bootstrap color class for severity"""
        colors = {'LOW': 'info', 'MEDIUM': 'warning', 'HIGH': 'danger'}
        return colors.get(self.severity, 'secondary')

class FaceVerification(models.Model):
    """Track face verification attempts for exam access"""
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    verified = models.BooleanField(default=False)
    similarity_score = models.FloatField(null=True, blank=True, help_text="Face matching confidence score")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        unique_together = ['student', 'exam']  # One verification per student per exam
    
    def __str__(self):
        status = "Verified" if self.verified else "Failed"
        return f"{self.student.username} - {self.exam.title} - {status}"
