import json
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from questpaper.models import *
from questpaper.forms import *
# Import your form for editing the educator
from .forms import *
from .models import *

def educator_home(request):
    educator = get_object_or_404(Educator, admin=request.user)
    
    # Statistics
    total_students = Student.objects.filter(course=educator.course).count()
    total_grades = Grade.objects.filter(educator=educator).count()
    total_course = Course.objects.count()
    total_subjects = Subject.objects.count()
    total_attendance = AttendanceReport.objects.filter(student__course=educator.course).count()
    total_parents = Parent.objects.count()
    items = NewsAndEvents.objects.all().order_by("-updated_date")

    # Retrieve subjects taught by the educator
    subjects = Subject.objects.filter(educator=educator)
    subject_list = [subject.name for subject in subjects]

    # Retrieve question papers for the educator's subjects
    question_papers = QuestionPaper.objects.filter(subject__in=subjects)

    # Filter question papers by grade and term if requested
    grade_filter = request.GET.get('grade')
    term_filter = request.GET.get('term')

    if grade_filter:
        question_papers = question_papers.filter(grade__id=grade_filter)
    if term_filter:
        question_papers = question_papers.filter(term__id=term_filter)

    # School-related statistics
    school_all = School.objects.all()
    school_list = []
    grade_count_list_in_school = []
    subject_count_list_in_school = []

    for school in school_all:
        grade_count = Grade.objects.filter(school=school).count() if hasattr(Grade, 'school') else 0
        subject_count = Subject.objects.filter(school=school).count() if hasattr(Subject, 'school') else 0
        school_list.append(school.name)
        grade_count_list_in_school.append(grade_count)
        subject_count_list_in_school.append(subject_count)

    # Prepare the context
    context = {
        # Course and school-related stats
        "school_list": school_list,
        "grade_count_list_in_school": grade_count_list_in_school,
        "subject_count_list_in_school": subject_count_list_in_school,

        # Dashboard content
        'page_title': 'Educator Dashboard',
        "title": "News & Events",
        "items": items,
        'total_course': total_course,
        'total_parents': total_parents,
        'total_students': total_students,
        'total_grades': total_grades,
        'total_subjects': total_subjects,
        'total_attendance': total_attendance,
        'subject_list': subject_list,

        # Question papers
        'question_papers': question_papers,
        'subjects': subjects,  # For filtering
        'grades': Grade.objects.all(),
        'terms': Term.objects.all(),
    }

    return render(request, 'educator_template/home_content.html', context)


def upload_question_paper(request):
    if request.method == 'POST':
        # Check if it's a single file upload or bulk upload
        if 'files' in request.FILES:
            return handle_bulk_upload(request)
        else:
            return handle_single_upload(request)
    else:
        form = QuestionPaperUploadForm()
        bulk_form = BulkQuestionPaperUploadForm()

    context = {
        'form': form,
        'bulk_form': bulk_form,
        'page_title': 'Upload Question Paper',
    }
    return render(request, 'upload_question_paper.html', context)

def handle_single_upload(request):
    """Handle single question paper upload"""
    form = QuestionPaperUploadForm(request.POST, request.FILES)
    if form.is_valid():
        question_paper = form.save(commit=False)
        question_paper.uploaded_by = request.user
        question_paper.save()
        form.save_m2m()
        
        # Start auto-processing
        question_paper.schedule_auto_processing()
        
        messages.success(request, "Question paper uploaded successfully and is being processed.")
        return redirect('upload_question_paper')
    else:
        messages.error(request, "Failed to upload the question paper. Please check the form.")
        return render(request, 'upload_question_paper.html', {'form': form, 'bulk_form': BulkQuestionPaperUploadForm()})

def handle_bulk_upload(request):
    """Handle multiple question paper upload"""
    bulk_form = BulkQuestionPaperUploadForm(request.POST, request.FILES)
    if bulk_form.is_valid():
        files = request.FILES.getlist('files')
        successful_uploads = 0
        failed_uploads = 0
        
        for file in files:
            try:
                # Create question paper instance for each file
                question_paper = QuestionPaper(
                    file=file,
                    uploaded_by=request.user,
                    grade=bulk_form.cleaned_data.get('grade'),
                    term=bulk_form.cleaned_data.get('term'),
                    school=bulk_form.cleaned_data.get('school'),
                    department=bulk_form.cleaned_data.get('department'),
                    subject=bulk_form.cleaned_data.get('subject'),
                    complexity_rating=bulk_form.cleaned_data.get('complexity_rating', 3)
                )
                question_paper.save()
                
                # Add topics if any
                if bulk_form.cleaned_data.get('topics'):
                    question_paper.topics.set(bulk_form.cleaned_data['topics'])
                
                # Start auto-processing
                question_paper.schedule_auto_processing()
                
                successful_uploads += 1
                
            except Exception as e:
                print(f"Error uploading {file.name}: {e}")
                failed_uploads += 1
                continue
        
        if successful_uploads > 0:
            messages.success(
                request, 
                f"Successfully uploaded {successful_uploads} question paper(s). They are being processed in the background."
            )
        if failed_uploads > 0:
            messages.warning(
                request,
                f"Failed to upload {failed_uploads} file(s). Please check if they are valid PDF files."
            )
        
        return redirect('upload_question_paper')
    else:
        messages.error(request, "Failed to upload files. Please check the form.")
        return render(request, 'upload_question_paper.html', {
            'form': QuestionPaperUploadForm(),
            'bulk_form': bulk_form
        })

def bulk_upload_progress(request):
    """API endpoint to check bulk upload progress"""
    if request.method == 'GET':
        # You can implement progress tracking here
        # For now, return basic stats
        user_papers = QuestionPaper.objects.filter(uploaded_by=request.user)
        total = user_papers.count()
        processed = user_papers.filter(is_processed=True).count()
        
        return JsonResponse({
            'total': total,
            'processed': processed,
            'pending': total - processed
        })

@csrf_exempt
def delete_question_paper(request, pk):
    """Delete a question paper"""
    if request.method == 'POST':
        question_paper = get_object_or_404(QuestionPaper, pk=pk, uploaded_by=request.user)
        paper_name = question_paper.file.name
        question_paper.delete()
        messages.success(request, f"Question paper '{paper_name}' deleted successfully.")
        return redirect('questionpaperlist')

def reprocess_question_paper(request, pk):
    """Reprocess a question paper"""
    if request.method == 'POST':
        question_paper = get_object_or_404(QuestionPaper, pk=pk, uploaded_by=request.user)
        success = question_paper.reprocess()
        if success:
            messages.success(request, "Question paper is being reprocessed.")
        else:
            messages.error(request, "Failed to reprocess question paper.")
        return redirect('question_paper_detail', pk=pk)

def question_paper_list(request):
    """List all question papers with filtering"""
    question_papers = QuestionPaper.objects.all().order_by('-id')
    departments = Department.objects.all()
    grades = Grade.objects.all()
    terms = Term.objects.all()
    subjects = Subject.objects.all()
    
    # Filtering
    department_filter = request.GET.get('department')
    grade_filter = request.GET.get('grade')
    term_filter = request.GET.get('term')
    subject_filter = request.GET.get('subject')
    status_filter = request.GET.get('status')
    
    if department_filter:
        question_papers = question_papers.filter(department__id=department_filter)
    if grade_filter:
        question_papers = question_papers.filter(grade__id=grade_filter)
    if term_filter:
        question_papers = question_papers.filter(term__id=term_filter)
    if subject_filter:
        question_papers = question_papers.filter(subject__id=subject_filter)
    if status_filter:
        if status_filter == 'processed':
            question_papers = question_papers.filter(is_processed=True)
        elif status_filter == 'pending':
            question_papers = question_papers.filter(is_processed=False)
        elif status_filter == 'error':
            question_papers = question_papers.filter(processing_error__isnull=False)
    
    context = {
        'question_papers': question_papers,
        'departments': departments,
        'grades': grades,
        'terms': terms,
        'subjects': subjects,
    }
    return render(request, 'question_paper_list.html', context)

def question_paper_detail(request, pk):
    question_paper = get_object_or_404(QuestionPaper, pk=pk)
    context = {
        'question_paper': question_paper,
    }
    return render(request, 'question_paper_detail.html', context)


def educator_view_students(request):
    educator = get_object_or_404(Educator, admin=request.user)
    students = Student.objects.filter(course=educator.course)
    
    context = {
        'page_title': 'View Students',
        'students': students
    }
    return render(request, 'educator_template/view_students.html', context)



def educator_take_attendance(request):
    try:
        educator = get_object_or_404(Educator, admin=request.user)
        # Get subjects taught by the educator
        subjects = Subject.objects.filter(educator=educator)
        
        # Get available sessions
        sessions = Session.objects.all()
        
        context = {
            'subjects': subjects,
            'sessions': sessions,
            'page_title': 'Take Attendance'
        }
        
        return render(request, 'educator_template/educator_take_attendance.html', context)
    except Exception as e:
        return HttpResponse(f"Error retrieving sessions: {e}")
    

def submit_educator_attendance(request):
    if request.method == 'POST':
        educator = get_object_or_404(Educator, admin=request.user)
        subject_id = request.POST.get('subject')
        session_id = request.POST.get('session')
        status = request.POST.get('status') == 'present'  # True if 'present', False if 'absent'
        student_ids = request.POST.getlist('students')  # List of student IDs marked as present
        
        # Get the subject and session
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)

        # Record attendance for each student
        for student_id in student_ids:
            student = get_object_or_404(Student, id=student_id)
            
            # Get or create Attendance object
            attendance, created = Attendance.objects.get_or_create(
                session=session,
                subject=subject,
                grade=student.grade,
                date=timezone.now().date()
            )

            # Create AttendanceReport for each student
            AttendanceReport.objects.create(
                student=student,
                attendance=attendance,
                status=status
            )

        messages.success(request, "Attendance recorded successfully!")
        return redirect('educator_take_attendance')
    
    return redirect('educator_take_attendance')

def educator_view_attendance(request):
    educator = get_object_or_404(Educator, admin=request.user)
    if request.method != 'POST':
        subjects = Subject.objects.filter(educator=educator)
        context = {
            'subjects': subjects,
            'page_title': 'View Attendance'
        }
        return render(request, 'educator_template/educator_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student__subject=subject)
            json_data = []
            for report in attendance_reports:
                data = {
                    "student_name": report.student.name,
                    "date":  str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return None

def educator_view_results(request):
    educator = get_object_or_404(Educator, admin=request.user)
    results = StudentResult.objects.filter(student__course=educator.course)
    
    context = {
        'page_title': 'View Results',
        'results': results
    }
    return render(request, 'educator_template/view_results.html', context)


@csrf_exempt
def fetch_student_attendance(request):
    try:
        # Get the educator who is logged in
        educator = get_object_or_404(Educator, admin=request.user)

        # Fetch student ID from POST request
        student_id = request.POST.get('student_id')

        # Get the student object, only if the student is enrolled in a subject taught by the educator
        student = get_object_or_404(Student, id=student_id)

        # Check if the student is enrolled in any subject taught by the educator
        if not student.grade.subjects.filter(educator=educator).exists():
            return HttpResponse('Error: This student is not under your supervision.', status=403)

        # Fetch attendance data for the student
        attendance_data = AttendanceReport.objects.filter(student_id=student_id)

        # Format attendance data for response
        attendance_list = [
            {
                'date': attendance.attendance.date,
                'status': attendance.status
            } for attendance in attendance_data
        ]

        # Return the attendance data as JSON
        return JsonResponse(attendance_list, safe=False)

    except Exception as e:
        return HttpResponse('Error: ' + str(e), status=500)
    

@csrf_exempt
def fetch_student_results(request):
    try:
        educator = get_object_or_404(Educator, admin=request.user)  # Ensure the user is an educator
        subject_id = request.POST.get('subject_id')  # Subject ID from the request

        # Verify that the subject belongs to the educator
        subject = get_object_or_404(Subject, id=subject_id, educator=educator)

        # Fetch results for the subject
        results_data = StudentResult.objects.filter(subject=subject)
        results_list = [
            {
                'student_name': result.student.name,  # Assuming the Student model has a 'name' field
                'assignment': result.assignment,
                'test': result.test,
                'exam': result.exam
            } for result in results_data
        ]
        return JsonResponse(results_list, safe=False)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)
    
    

def educator_add_subject(request):
    try:
        # Ensure the user is an educator
        educator = get_object_or_404(Educator, admin=request.user)

        if request.method == 'POST':
            form = SubjectForm(request.POST)
            if form.is_valid():
                # Save the new subject
                subject = form.save(commit=False)
                subject.save()

                # Optionally, associate the educator with the subject (if necessary)
                # subject.educator = educator
                # subject.save()

                messages.success(request, "Subject added successfully!")
                return redirect('educator_home')  # Redirect to the educator's home page or another page
            else:
                messages.error(request, "Failed to add subject. Please check the form.")
        else:
            form = SubjectForm()

        context = {
            'form': form,
            'page_title': 'Add Subject',
        }
        return render(request, 'educator_template/educator_add_subject.html', context)

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('educator_home')


def educator_manage_subjects(request):
    try:
        educator = get_object_or_404(Educator, admin=request.user)
        subjects = Subject.objects.filter(educator=educator)  # Fetch only subjects the educator manages

        context = {
            'subjects': subjects,
            'page_title': 'Manage Subjects',
        }
        return render(request, 'educator_template/educator_manage_subjects.html', context)

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('educator_home')

def educator_edit_subject(request, subject_id):
    try:
        educator = get_object_or_404(Educator, admin=request.user)
        subject = get_object_or_404(Subject, id=subject_id, educator=educator)  # Only allow editing subjects assigned to the educator

        if request.method == 'POST':
            form = SubjectForm(request.POST, instance=subject)
            if form.is_valid():
                form.save()
                messages.success(request, "Subject updated successfully!")
                return redirect('educator_manage_subjects')
            else:
                messages.error(request, "Failed to update subject. Please check the form.")
        else:
            form = SubjectForm(instance=subject)

        context = {
            'form': form,
            'page_title': 'Edit Subject',
        }
        return render(request, 'educator_template/educator_edit_subject.html', context)

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('educator_manage_subjects')


def educator_delete_subject(request, subject_id):
    try:
        educator = get_object_or_404(Educator, admin=request.user)
        subject = get_object_or_404(Subject, id=subject_id, educator=educator)  # Only allow deletion of subjects assigned to the educator

        subject.delete()
        messages.success(request, "Subject deleted successfully!")
        return redirect('educator_manage_subjects')

    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('educator_manage_subjects')