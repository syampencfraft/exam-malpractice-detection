# Exam Malpractice Detection System

A Django-based web application for conducting online exams with integrated face recognition and malpractice detection.

## Features

- **User Authentication**: Student registration and login.
- **Student Approval**: Admin dashboard to approve registered students.
- **Exam Management**: Admins can create exams and add questions.
- **Face Verification**: Multi-step face verification before starting an exam.
- **Malpractice Detection**: Real-time monitoring for:
  - No face detected
  - Multiple faces detected
  - Looking away from the screen
  - Browser tab switching
- **Admin Analytics**: Detailed logs and reports of violations.
- **Recording**: Full exam session recording and playback.

## Tech Stack

- **Backend**: Django (Python)
- **Frontend**: HTML5, Vanilla CSS, JavaScript, Bootstrap
- **Face Recognition**: `face_recognition`, `dlib`, `opencv-python`
- **Database**: SQLite (default)

## Prerequisites

- Python 3.8+
- CMake (required for `dlib`)
- C++ Build Tools

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/syampencfraft/exam-malpractice-detection.git
   cd exam-malpractice-detection
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create Superuser**:
   ```bash
   python manage.py createsuperuser
   ```

5. **Run Server**:
   ```bash
   python manage.py runserver
   ```

## Usage

1. Register as a student.
2. Login as admin to approve the student profile.
3. Access the exam after undergoing face verification.
4. Admins can view results and malpractice logs in the dashboard.
