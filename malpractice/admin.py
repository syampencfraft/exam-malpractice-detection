from django.contrib import admin
from .models import StudentProfile, Exam, Question, ExamResult, MalpracticeLog, FaceVerification

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 3

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'time', 'duration_minutes')
    inlines = [QuestionInline]

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'email_display', 'student_class', 'department', 'is_approved')
    list_filter = ('is_approved', 'department', 'student_class')
    search_fields = ('user__username', 'user__email', 'class_id')
    actions = ['approve_students']

    def email_display(self, obj):
        return obj.user.email
    email_display.short_description = 'Email'

    def approve_students(self, request, queryset):
        queryset.update(is_approved=True)
    approve_students.short_description = "Approve selected students"

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'score', 'total_questions', 'percentage', 'completed_at')
    list_filter = ('exam', 'completed_at')
    search_fields = ('student__username', 'exam__title')
    
    def percentage(self, obj):
        return f"{(obj.score / obj.total_questions * 100):.1f}%"
    percentage.short_description = 'Score %'

@admin.register(MalpracticeLog)
class MalpracticeLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'log_type', 'timestamp')
    list_filter = ('log_type', 'exam', 'timestamp')
    search_fields = ('student__username', 'exam__title')
    readonly_fields = ('timestamp',)

@admin.register(FaceVerification)
class FaceVerificationAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam', 'verified', 'similarity_score', 'timestamp')
    list_filter = ('verified', 'exam', 'timestamp')
    search_fields = ('student__username', 'exam__title')
    readonly_fields = ('timestamp',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return self.readonly_fields + ('student', 'exam')
        return self.readonly_fields

