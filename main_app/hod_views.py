import json
import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponse, HttpResponseRedirect,
                              get_object_or_404, redirect, render)
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import UpdateView
from django.db.models import Count
import pandas as pd
import numpy as np
from .forms import *
from .models import *

def admin_home(request):
    # Aggregate counts for primary entities
    total_staff = Staff.objects.count()
    total_students = Student.objects.count()
    total_schools = School.objects.count()
    total_parents = Parent.objects.count()
    total_subject = Subject.objects.count()
    items = NewsAndEvents.objects.all().order_by("-updated_date")
    total_course = Course.objects.count()
    total_grade = Grade.objects.count()
    total_educators = Educator.objects.count()
    total_principals = Principal.objects.count()
    total_members = Member.objects.count()
    
    # Attendance by subject
    subjects = Subject.objects.all()
    attendance_list = []
    subject_list = []
    for subject in subjects:
        attendance_count = Attendance.objects.filter(subject=subject).count()
        subject_list.append(subject.name[:7])  # First 7 characters of subject name
        attendance_list.append(attendance_count)
    
    # Total subjects, students, and educators in each course
    course_all = Course.objects.all()
    course_name_list = []
    subject_count_list = []
    student_count_list_in_course = []
    educator_count_list_in_course = []
    
    for course in course_all:
        student_count = Student.objects.filter(course_id=course.id).count()
        educator_count = Educator.objects.filter(course_id=course.id).count()
        course_name_list.append(course.name)
        student_count_list_in_course.append(student_count)
        educator_count_list_in_course.append(educator_count)
    
    # Total grades and subjects in each school
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
    
    # School statistics for subjects, courses,
    #  grades, educators, etc.
    school_count_list_in_course = []
    school_count_list_in_grade = []
    school_count_list_in_educator = []
    school_count_list_in_student = []
    school_count_list_in_parent = []
    school_count_list_in_principal = []
    
    for school in school_all:
        course_count = Course.objects.filter(id=school.id).count()
        educator_count = Educator.objects.filter(id=school.id).count()
        student_count = Student.objects.filter(id=school.id).count()
        parent_count = Parent.objects.filter(id=school.id).count()
        principal_count = Principal.objects.filter(id=school.id).count()
        
        school_count_list_in_course.append(course_count)
        school_count_list_in_grade.append(grade_count)
        school_count_list_in_educator.append(educator_count)
        school_count_list_in_student.append(student_count)
        school_count_list_in_parent.append(parent_count)
        school_count_list_in_principal.append(principal_count)
    
    # Student attendance and leave records
    student_attendance_present_list = []
    student_attendance_leave_list = []
    student_name_list = []
    
    students = Student.objects.all()
    for student in students:
        attendance = AttendanceReport.objects.filter(student_id=student.id, status=True).count()
        absent = AttendanceReport.objects.filter(student_id=student.id, status=False).count()
        leave = LeaveReportStudent.objects.filter(student_id=student.id, status=1).count()
        student_attendance_present_list.append(attendance)
        student_attendance_leave_list.append(leave + absent)
        student_name_list.append(student.admin.first_name)
    
    # Context dictionary with corrected keys
    context = {
        'page_title': "Administrative Dashboard",
        "title": "News & Events",
        "items": items,
        'total_schools': total_schools,
        'total_grade': total_grade,
        'total_students': total_students,
        'total_educators': total_educators,
        'total_parents': total_parents,
        'total_principals': total_principals,
        'total_members': total_members,
        'total_staff': total_staff,
        'total_course': total_course,
        'total_subject': total_subject,
        'subject_list': subject_list,
        'attendance_list': attendance_list,
        'student_attendance_present_list': student_attendance_present_list,
        'student_attendance_leave_list': student_attendance_leave_list,
        "student_name_list": student_name_list,
        "student_count_list_in_subject": student_count_list_in_course,
        "course_name_list": course_name_list,
        "subject_count_list": subject_count_list,
        "educator_count_list_in_course": educator_count_list_in_course,
        "school_list": school_list,
        "grade_count_list_in_school": grade_count_list_in_school,
        "subject_count_list_in_school": subject_count_list_in_school,
        "school_count_list_in_course": school_count_list_in_course,
        "school_count_list_in_grade": school_count_list_in_grade,
        "school_count_list_in_educator": school_count_list_in_educator,
        "school_count_list_in_student": school_count_list_in_student,
        "school_count_list_in_parent": school_count_list_in_parent,
        "school_count_list_in_principal": school_count_list_in_principal,
    }
    
    return render(request, 'hod_template/home_content.html', context)



def post_add(request):
    if request.method == 'POST':
        data = request.POST
        image = request.FILES.get('image')

        post = NewsAndEvents.objects.create(
            title=data.get('title'),
            summary=data.get('summary'),
            posted_as=data.get('posted_as'),
            image=image,
        )

        # Email logic here...

        messages.success(request, "News post added!")
        return redirect('admin_home')

    return render(request, 'hod_template/post_add.html')




def edit_post(request, pk):
    instance = get_object_or_404(NewsAndEvents, pk=pk)
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST, instance=instance)
        title = request.POST.get("title")
        if form.is_valid():
            form.save()

            messages.success(request, (title + " has been updated."))
            return redirect("admin_home")
        else:
            messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm(instance=instance)
    return render(
        request,
        "hod_template/post_add.html",
        {
            "title": "Edit Post",
            "form": form,
        },
    )



def delete_post(request, pk):
    post = get_object_or_404(NewsAndEvents, pk=pk)
    title = post.title
    post.delete()
    messages.success(request, (title + " has been deleted."))
    return redirect("staff_home")


def add_staff(request):
    form = StaffForm(request.POST or None, request.FILES or None)
    context = {'form': form, 'page_title': 'Add Staff'}
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            school = form.cleaned_data.get('school')
            circuit = school.circuit  # Get circuit related to the school

            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password')
            passport = request.FILES.get('profile_pic')
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=2, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.staff.course = course
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('login_page'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Please fulfil all requirements")

    return render(request, 'hod_template/add_staff_template.html', context)

#add student
def add_student(request):
    student_form = StudentForm(request.POST or None, request.FILES or None)
    context = {'form': student_form, 'page_title': 'Add Student'}

    if request.method == 'POST':
        if student_form.is_valid():
            # Extract form fields
            first_name = student_form.cleaned_data.get('first_name')
            last_name = student_form.cleaned_data.get('last_name')
            address = student_form.cleaned_data.get('address')
            email = student_form.cleaned_data.get('email')
            gender = student_form.cleaned_data.get('gender')
            password = student_form.cleaned_data.get('password')

            course = student_form.cleaned_data.get('course')
            grade = student_form.cleaned_data.get('grade')
            school = student_form.cleaned_data.get('school')

            # Automatically get circuit from selected school
            circuit = school.circuit  

            # Handle image upload
            passport = request.FILES.get('profile_pic')
            fs = FileSystemStorage()
            passport_url = None
            if passport:
                filename = fs.save(passport.name, passport)
                passport_url = fs.url(filename)

            try:
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    user_type=3,
                    first_name=first_name,
                    last_name=last_name,
                    profile_pic=passport_url
                )
                user.gender = gender
                user.address = address
                user.save()

                Student.objects.create(
                    admin=user,
                    course=course,
                    circuit=circuit,
                    school=school,
                    grade=grade
                )

                messages.success(request, "Successfully Added Student")
                return redirect(reverse('login_page'))

            except Exception as e:
                messages.error(request, f"Could Not Add Student: {e}")
        else:
            messages.error(request, "Form is not valid")

    return render(request, 'hod_template/add_student_template.html', context)


def add_principal(request):
    principal_form = PrincipalForm(request.POST or None, request.FILES or None)
    context = {'form': principal_form, 'page_title': 'Add Principal'}
    if request.method == 'POST':
        if principal_form.is_valid():
            first_name = principal_form.cleaned_data.get('first_name')
            last_name = principal_form.cleaned_data.get('last_name')
            address = principal_form.cleaned_data.get('address')
            email = principal_form.cleaned_data.get('email')
            gender = principal_form.cleaned_data.get('gender')
            password = principal_form.cleaned_data.get('password')
            school = principal_form.cleaned_data.get('school')
            circuit = principal_form.cleaned_data.get('circuit')
            #added content
            grade = principal_form.cleaned_data.get('grade')
            subject = principal_form.cleaned_data.get('subject')
            term = principal_form.cleaned_data.get('term')
            course = principal_form.cleaned_data.get('course')
            passport = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=4, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.principal.grade = grade
                user.principal.subject = subject
                user.principal.term = term
                user.principal.course = course
                user.principal.school = school
                user.principal.circuit = circuit
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('login_page'))
            except Exception as e:
                messages.error(request, "Could Not Add: " + str(e))
        else:
            messages.error(request, "Could Not Add: ")
    return render(request, 'hod_template/add_principal_template.html', context)


def add_educator(request):
    educator_form = EducatorForm(request.POST or None, request.FILES or None)
    context = {'form': educator_form, 'page_title': 'Add Educator'}

    if request.method == 'POST':
        if educator_form.is_valid():
            try:
                # Extract CustomUser fields
                first_name = educator_form.cleaned_data.get('first_name')
                last_name = educator_form.cleaned_data.get('last_name')
                email = educator_form.cleaned_data.get('email')
                gender = educator_form.cleaned_data.get('gender')
                password = educator_form.cleaned_data.get('password')
                address = educator_form.cleaned_data.get('address')

                # ✅ Extract Educator model fields (only what's in your form)
                school = educator_form.cleaned_data.get('school')
                grades = educator_form.cleaned_data.get('grades')  # ✅ Fixed: 'grades' not 'grade'
                subjects = educator_form.cleaned_data.get('subjects')
                profile_pic = request.FILES.get('profile_pic')

                # Upload image
                profile_pic_url = None
                if profile_pic:
                    fs = FileSystemStorage()
                    filename = fs.save(profile_pic.name, profile_pic)
                    profile_pic_url = fs.url(filename)

                # Create CustomUser
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    user_type=5,  # Educator
                    first_name=first_name,
                    last_name=last_name,
                    profile_pic=profile_pic_url
                )
                user.gender = gender
                user.address = address
                user.save()

                # Create Educator instance
                educator = Educator.objects.create(
                    admin=user,
                    school=school,
                    # ✅ Removed fields that aren't in your form: grade, circuit, term, session, course
                )
                
                # ✅ Set the many-to-many fields
                educator.grades.set(grades)    # ✅ This should work now with checkboxes
                educator.subjects.set(subjects) # ✅ This should work now with checkboxes
                educator.save()

                messages.success(request, "Successfully Added Educator")
                return redirect('login_page')

            except Exception as e:
                messages.error(request, f"Could Not Add Educator: {e}")
        else:
            messages.error(request, "Form is not valid")

    return render(request, 'hod_template/add_educator_template.html', context)


def add_circuit_manager(request):
    circuit_manager_form = Circuit_ManagerForm(request.POST or None, request.FILES or None)
    context = {'form': circuit_manager_form, 'page_title': 'Add Circuit_Manager'}
    if request.method == 'POST':
        if circuit_manager_form.is_valid():
            first_name = circuit_manager_form.cleaned_data.get('first_name')
            last_name = circuit_manager_form.cleaned_data.get('last_name')
            address = circuit_manager_form.cleaned_data.get('address')
            email = circuit_manager_form.cleaned_data.get('email')
            gender = circuit_manager_form.cleaned_data.get('gender')
            password = circuit_manager_form.cleaned_data.get('password')
            circuit = circuit_manager_form.cleaned_data.get('circuit')
            passport = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=5, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.circuit_manager.circuit = circuit
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('login_page'))
            except Exception as e:
                messages.error(request, "Could Not Add: " + str(e))
        else:
            messages.error(request, "Could Not Add: ")
    return render(request, 'hod_template/add_circuit_manager_template.html', context)



def add_member(request):
    member_form = MemberForm(request.POST or None, request.FILES or None)
    context = {'form': member_form, 'page_title': 'Add Member'}
    
    if request.method == 'POST':
        if member_form.is_valid():
            try:
                # ✅ Extract only fields that exist in the form
                first_name = member_form.cleaned_data.get('first_name')
                last_name = member_form.cleaned_data.get('last_name')
                address = member_form.cleaned_data.get('address')
                email = member_form.cleaned_data.get('email')
                gender = member_form.cleaned_data.get('gender')
                password = member_form.cleaned_data.get('password')
                position = member_form.cleaned_data.get('position')  # ✅ Only extra field in form
                passport = request.FILES.get('profile_pic')  # ✅ Use get() to avoid KeyError
                
                # Upload image
                passport_url = None
                if passport:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)

                # Create CustomUser
                user = CustomUser.objects.create_user(
                    email=email, 
                    password=password, 
                    user_type=8, 
                    first_name=first_name, 
                    last_name=last_name, 
                    profile_pic=passport_url
                )
                user.gender = gender
                user.address = address
                user.save()

                # ✅ Create Member instance with only the position field
                member = Member.objects.create(
                    admin=user,
                    position=position
                )
                # ✅ Remove these lines - they don't exist in your form:
                # user.school = school  # ❌ Not in form
                # user.position = position  # ❌ Already set in Member
                # user.member.session = session  # ❌ Not in form  
                # user.member.term = term  # ❌ Not in form

                messages.success(request, "Successfully Added Member")
               
                # ✅ If you need circuit redirect, you'll need to add school field to form
                # For now, redirect to a default page
                return redirect('admin_dashboard')  # or wherever you want

            except Exception as e:
                messages.error(request, f"Could Not Add Member: {str(e)}")
        else:
            messages.error(request, "Form is not valid")
    
    return render(request, 'hod_template/add_member_template.html', context)



def add_cwa_admin(request):
    cwa_admin_form = CWA_AdminForm(request.POST or None, request.FILES or None)
    context = {'form': cwa_admin_form, 'page_title': 'Add Member'}
    if request.method == 'POST':
        if cwa_admin_form.is_valid():
            first_name = cwa_admin_form.cleaned_data.get('first_name')
            last_name = cwa_admin_form.cleaned_data.get('last_name')
            address = cwa_admin_form.cleaned_data.get('address')
            email = cwa_admin_form.cleaned_data.get('email')
            gender = cwa_admin_form.cleaned_data.get('gender')
            password = cwa_admin_form.cleaned_data.get('password')
            school = cwa_admin_form.cleaned_data.get('school')
            collegeanduniversity = cwa_admin_form.cleaned_data.get('collegeanduniversity')
            bursary = cwa_admin_form.cleaned_data.get('bursary')
            position = cwa_admin_form.cleaned_data.get('position')
            term = cwa_admin_form.cleaned_data.get('term')
            session = cwa_admin_form.cleaned_data.get('session')
            passport = request.FILES['profile_pic']
            fs = FileSystemStorage()
            filename = fs.save(passport.name, passport)
            passport_url = fs.url(filename)
            try:
                user = CustomUser.objects.create_user(
                    email=email, password=password, user_type=8, first_name=first_name, last_name=last_name, profile_pic=passport_url)
                user.gender = gender
                user.address = address
                user.school = school
                user.position = position
                user.member.session = session
                user.member.term = term
                user.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('login_page'))
            except Exception as e:
                messages.error(request, "Could Not Add: " + str(e))
        else:
            messages.error(request, "Could Not Add: ")
    return render(request, 'hod_template/add_cwa_admin_template.html', context)



def search_students(request):
    query = request.GET.get('q', '')
    if query:
        # Search students by first name or last name
        students = Student.objects.filter(
            admin__first_name__icontains=query
        ) | Student.objects.filter(
            admin__last_name__icontains=query
        )
        
        results = [
            {
                'id': student.id,
                'name': f"{student.admin.first_name} {student.admin.last_name}",
                'school': student.school.name if student.school else "No School",  # Check if school is None
            }
            for student in students
        ]
    else:
        results = []

    return JsonResponse(results, safe=False)



def add_parent(request):
    if request.method == 'POST':
        # Fetch the parent data from the form
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        gender = request.POST.get('gender')
        password = request.POST.get('password')
        address = request.POST.get('address')
        profile_pic = request.FILES.get('profile_pic')

        # Fetch the selected student IDs from the form (from the hidden field)
        student_ids = request.POST.get('students', '').split(',')
        selected_students = Student.objects.filter(id__in=student_ids)

        try:
            # Create the CustomUser (parent)
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                user_type=8,  # Assuming '8' is the user type for Parent
                first_name=first_name,
                last_name=last_name,
                profile_pic=profile_pic
            )
            # Set additional user data
            user.gender = gender
            user.address = address
            user.save()

            # Create Parent instance and link the user
            parent = Parent.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                email=email,
                gender=gender,
                address=address,
                profile_pic=profile_pic
            )

            # Associate the selected students with the parent
            parent.students.set(selected_students)  # Many-to-many relationship
            parent.save()

            # Show success message
            messages.success(request, "Parent and students added successfully.")
            return redirect('some_success_page')  # Redirect to a success page or another relevant page

        except Exception as e:
            messages.error(request, f"Could not add parent: {str(e)}")
            return redirect('add_parent')  # Stay on the 'add_parent' page in case of error

    else:
        return render(request, 'hod_template/add_parent_template.html', {'page_title': 'Add Parent'})



def add_course(request):
    form = CourseForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Course'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                course = Course()
                course.name = name
                course.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_course'))
            except:
                messages.error(request, "Could Not Add")
        else:
            messages.error(request, "Could Not Add")
    return render(request, 'hod_template/add_course_template.html', context)

#add grade
def add_grade(request):
    form = GradeForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Grade'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            school = form.cleaned_data.get('school')
            try:
                grade = Grade()
                grade.name = name
                grade.school = school
                grade.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_grade'))
            except:
                messages.error(request, "Could Not Add")
        else:
            messages.error(request, "Could Not Add")
    return render(request, 'hod_template/add_grade_template.html', context)

#add school
def add_school(request):
    form = SchoolForm(request.POST or None, request.FILES or None)  # Handle files for the logo field
    context = {
        'form': form,
        'page_title': 'Add School'
    }

    if request.method == 'POST':
        if form.is_valid():
            school = form.save(commit=False)  # Temporarily save without committing
            
            # Check if the user is authenticated and not a superuser before assigning them
            if request.user.is_authenticated and not request.user.is_superuser:
                school.user = request.user  # Assign authenticated user
            
            try:
                school.save()
                messages.success(request, "School Successfully Added")
                return redirect(reverse('add_school'))  # Redirect back to add school page
            except Exception as e:
                messages.error(request, f"Could Not Add School: {str(e)}")
        else:
            messages.error(request, "Please fill the form correctly.")
    
    return render(request, 'hod_template/add_school_template.html', context)

#add subjects
def add_subject(request):
    form = SubjectForm(request.POST or None)
    context = {
        'form': form,
        'page_title': 'Add Subject'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            school = form.cleaned_data.get('school')
            grade = form.cleaned_data.get('grade')
            course = form.cleaned_data.get('course')
            
            staff = form.cleaned_data.get('staff')
            try:
                subject = Subject()
                subject.name = name
                subject.school = school
                subject.grade = grade
                subject.staff = staff
                subject.course = course
                subject.save()
                messages.success(request, "Successfully Added")
                return redirect(reverse('add_subject'))

            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")

    return render(request, 'hod_template/add_subject_template.html', context)


def manage_staff(request):
    allStaff = CustomUser.objects.filter(user_type=2)
    context = {
        'allStaff': allStaff,
        'page_title': 'Manage Staff'
    }
    return render(request, "hod_template/manage_staff.html", context)



def manage_student(request):
    students = CustomUser.objects.filter(user_type=3)
    context = {
        'students': students,
        'page_title': 'Manage Students'
    }
    return render(request, "hod_template/manage_student.html", context)



def manage_circuit_manager(request):
    circuit_managers = CustomUser.objects.filter(user_type=2)
    context = {
        'circuit_managers': circuit_managers,
        'page_title': 'Manage Circuit_Manager'
    }
    return render(request, "hod_template/manage_circuit_manager.html", context)



def manage_educator(request):
    educators = CustomUser.objects.filter(user_type=2)
    context = {
        'educators': educators,
        'page_title': 'Manage Educator'
    }
    return render(request, "hod_template/manage_educator.html", context)



def manage_principal(request):
    principals = CustomUser.objects.filter(user_type=2)
    context = {
        'principals': principals,
        'page_title': 'Manage Principal'
    }
    return render(request, "hod_template/manage_principal.html", context)



def manage_member(request):
    members = CustomUser.objects.filter(user_type=2)
    context = {
        'members': members,
        'page_title': 'Manage Member'
    }
    return render(request, "hod_template/manage_member.html", context)



def manage_parent(request):
    parents = CustomUser.objects.filter(user_type=2)
    context = {
        'parents': parents,
        'page_title': 'Manage Parent'
    }
    return render(request, "hod_template/manage_parent.html", context)



def manage_course(request):
    courses = Course.objects.all()
    context = {
        'courses': courses,
        'page_title': 'Manage Courses'
    }
    return render(request, "hod_template/manage_course.html", context)


def manage_grade(request):
    grades = Grade.objects.all()
    context = {
        'grades': grades,
        'page_title': 'Manage Grades'
    }
    return render(request, "hod_template/manage_grade.html", context)


def manage_subject(request):
    subjects = Subject.objects.all()
    context = {
        'subjects': subjects,
        'page_title': 'Manage Subjects'
    }
    return render(request, "hod_template/manage_subject.html", context)


def manage_school(request):
    schools = School.objects.all()
    context = {
        'schools': schools,
        'page_title': 'Manage Schools'
    }
    return render(request, "hod_template/manage_school.html", context)


def manage_grade(request):
    grades = Grade.objects.all()
    context = {
        'grades': grades,
        'page_title': 'Manage Grades'
    }
    return render(request, "hod_template/manage_grade.html", context)



def edit_staff(request, staff_id):
    staff = get_object_or_404(Staff, id=staff_id)
    form = StaffForm(request.POST or None, instance=staff)
    context = {
        'form': form,
        'staff_id': staff_id,
        'page_title': 'Edit Staff'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            course = form.cleaned_data.get('course')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=staff.admin.id)
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address = address
                staff.course = course
                user.save()
                staff.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_staff', args=[staff_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please fil form properly")
    else:
        user = CustomUser.objects.get(id=staff_id)
        staff = Staff.objects.get(id=user.id)
        return render(request, "hod_template/edit_staff_template.html", context)


def edit_cwa_admin(request, cwa_admin_id):
    cwa_admin = get_object_or_404(CWA_Admin, id=cwa_admin_id)
    form = CWA_AdminForm(request.POST or None, instance=cwa_admin)
    context = {
        'form': form,
        'cwa_admin_id': cwa_admin_id,
        'page_title': 'Edit cwa_admin'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            course = form.cleaned_data.get('course')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=cwa_admin.admin.id)
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.first_name = first_name
                user.last_name = last_name
                user.gender = gender
                user.address = address
                cwa_admin.course = course
                user.save()
                cwa_admin.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_cwa_admin', args=[cwa_admin_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please fil form properly")
    else:
        user = CustomUser.objects.get(id=cwa_admin_id)
        cwa_admin = CWA_Admin.objects.get(id=user.id)
        return render(request, "hod_template/edit_cwa_admin_template.html", context)



def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    form = StudentForm(request.POST or None, instance=student)
    context = {
        'form': form,
        'student_id': student_id,
        'page_title': 'Edit Student'
    }
    if request.method == 'POST':
        if form.is_valid():
            first_name = form.cleaned_data.get('first_name')
            last_name = form.cleaned_data.get('last_name')
            address = form.cleaned_data.get('address')
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            gender = form.cleaned_data.get('gender')
            password = form.cleaned_data.get('password') or None
            course = form.cleaned_data.get('course')
            session = form.cleaned_data.get('session')
            passport = request.FILES.get('profile_pic') or None
            try:
                user = CustomUser.objects.get(id=student.admin.id)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    user.profile_pic = passport_url
                user.username = username
                user.email = email
                if password != None:
                    user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                student.session = session
                user.gender = gender
                user.address = address
                student.course = course
                user.save()
                student.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_student', args=[student_id]))
            except Exception as e:
                messages.error(request, "Could Not Update " + str(e))
        else:
            messages.error(request, "Please Fill Form Properly!")
    else:
        return render(request, "hod_template/edit_student_template.html", context)


#add principal 
def add_principal(request):
    principal_form = PrincipalForm(request.POST or None, request.FILES or None)
    context = {'form': principal_form, 'page_title': 'Add Principal'}
    
    if request.method == 'POST':
        if principal_form.is_valid():
            try:
                # Extract only fields that exist in the form
                first_name = principal_form.cleaned_data.get('first_name')
                last_name = principal_form.cleaned_data.get('last_name')
                address = principal_form.cleaned_data.get('address')
                email = principal_form.cleaned_data.get('email')
                gender = principal_form.cleaned_data.get('gender')
                password = principal_form.cleaned_data.get('password')
                school = principal_form.cleaned_data.get('school')
                grades = principal_form.cleaned_data.get('grades')  # ✅ Now multiple grades
                subjects = principal_form.cleaned_data.get('subjects')  # ✅ Now multiple subjects
                passport = request.FILES.get('profile_pic')
                
                # Upload image
                passport_url = None
                if passport:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)

                # Create CustomUser
                user = CustomUser.objects.create_user(
                    email=email, 
                    password=password, 
                    user_type=4, 
                    first_name=first_name, 
                    last_name=last_name, 
                    profile_pic=passport_url
                )
                user.gender = gender
                user.address = address
                user.save()

                # Create Principal instance
                principal = Principal.objects.create(
                    admin=user,
                    school=school
                )
                # ✅ Set the many-to-many fields
                principal.grades.set(grades)
                principal.subjects.set(subjects)

                messages.success(request, "Successfully Added Principal")
                return redirect(reverse('login_page'))
                
            except Exception as e:
                messages.error(request, f"Could Not Add Principal: {str(e)}")
        else:
            messages.error(request, "Form is not valid")
    
    return render(request, 'hod_template/add_principal_template.html', context)

    

def edit_course(request, course_id):
    instance = get_object_or_404(Course, id=course_id)
    form = CourseForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'course_id': course_id,
        'page_title': 'Edit Course'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                course = Course.objects.get(id=course_id)
                course.name = name
                course.save()
                messages.success(request, "Successfully Updated")
            except:
                messages.error(request, "Could Not Update")
        else:
            messages.error(request, "Could Not Update")

    return render(request, 'hod_template/edit_course_template.html', context)



def edit_grade(request, course_id):
    instance = get_object_or_404(Grade, id=grade_id)
    form = GradeForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'grade_id': grade_id,
        'page_title': 'Edit Grade'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            try:
                grade = Grade.objects.get(id=grade_id)
                grade.name = name
                grade.save()
                messages.success(request, "Successfully Updated")
            except:
                messages.error(request, "Could Not Update")
        else:
            messages.error(request, "Could Not Update")

    return render(request, 'hod_template/edit_grade_template.html', context)




def edit_subject(request, subject_id):
    instance = get_object_or_404(Subject, id=subject_id)
    form = SubjectForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'subject_id': subject_id,
        'page_title': 'Edit Subject'
    }
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data.get('name')
            course = form.cleaned_data.get('course')
            staff = form.cleaned_data.get('staff')
            try:
                subject = Subject.objects.get(id=subject_id)
                subject.name = name
                subject.staff = staff
                subject.course = course
                subject.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_subject', args=[subject_id]))
            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")
    return render(request, 'hod_template/edit_subject_template.html', context)





#edit school function
def edit_school(request, school_id):  # Use school_id instead of subject_id
    instance = get_object_or_404(School, id=school_id)
    form = SchoolForm(request.POST or None, instance=instance)
    context = {
        'form': form,
        'school_id': school_id,
        'page_title': 'Edit School'
    }

    if request.method == 'POST':
        if form.is_valid():
            # Get cleaned data from the form
            emis = form.cleaned_data.get('emis')
            name = form.cleaned_data.get('name')
            phase = form.cleaned_data.get('phase')
            sector = form.cleaned_data.get('sector')
            educators_on_db = form.cleaned_data.get('educators_on_db')
            school_term = form.cleaned_data.get('school_term')
            website_url = form.cleaned_data.get('website_url')
            email = form.cleaned_data.get('email')
            whatsapp_number = form.cleaned_data.get('whatsapp_number')
            address = form.cleaned_data.get('address')
            year = form.cleaned_data.get('year')
            count = form.cleaned_data.get('count')
            
            try:
                school = School.objects.get(id=school_id)
                school.emis = emis
                school.name = name
                school.phase = phase
                school.sector = sector
                school.educators_on_db = educators_on_db
                school.school_term = school_term  # Fixed typo: 'term' -> 'school_term'
                school.website_url = website_url
                school.email = email
                school.whatsapp_number = whatsapp_number
                school.address = address
                school.year = year
                school.count = count
                school.save()
                messages.success(request, "Successfully Updated")
                return redirect(reverse('edit_school', args=[school_id]))
            except Exception as e:
                messages.error(request, "Could Not Add " + str(e))
        else:
            messages.error(request, "Fill Form Properly")
    
    return render(request, 'hod_template/edit_school.html', context)


def add_term(request):
    form = TermForm(request.POST or None)
    context = {'form': form, 'page_title': 'Add Term'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "School Term Created")
                return redirect(reverse('add_term'))
            except Exception as e:
                messages.error(request, 'Could Not Add ' + str(e))
        else:
            messages.error(request, 'Fill Form Properly ')
    return render(request, "hod_template/add_term_template.html", context)

    
def add_session(request):
    form = SessionForm(request.POST or None)
    context = {'form': form, 'page_title': 'Add Session'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Session Created")
                return redirect(reverse('add_session'))
            except Exception as e:
                messages.error(request, 'Could Not Add ' + str(e))
        else:
            messages.error(request, 'Fill Form Properly ')
    return render(request, "hod_template/add_session_template.html", context)


def manage_educator(request):
    educators = (CustomUser.objects
                 .filter(user_type=2)
                 .values('school', 'grade')
                 .annotate(count=Count('id'))
                 .order_by('school', 'grade'))
    
    context = {
        'educators': educators,
        'page_title': 'Manage Educator'
    }
    return render(request, "hod_template/manage_educator.html", context)


def manage_principal(request):
    principals = (CustomUser.objects
                  .filter(user_type=4)  # Adjust user_type for principal
                  .select_related('principal', 'principal__school', 'principal__grade', 'principal__course', 'principal__term')
                  .all())
    
    context = {
        'principals': principals,
        'page_title': 'Manage Principal'
    }
    return render(request, "hod_template/manage_principal.html", context)

def manage_member(request):
    members = (CustomUser.objects
               .filter(user_type=4)  # Adjust user_type for member
               .values('school', 'grade')
               .annotate(count=Count('id'))
               .order_by('school', 'grade'))
    
    context = {
        'members': members,
        'page_title': 'Manage Member'
    }
    return render(request, "hod_template/manage_member.html", context)


def manage_parent(request):
    parents = (CustomUser.objects
               .filter(user_type=5)  # Adjust user_type for parent
               .values('school', 'grade')
               .annotate(count=Count('id'))
               .order_by('school', 'grade'))
    
    context = {
        'parents': parents,
        'page_title': 'Manage Parent'
    }
    return render(request, "hod_template/manage_parent.html", context)


def manage_course(request):
    courses = (
        Course.objects
        .values('id', 'school', 'name')  # ✅ Include 'id' so we can use it in the template
        .annotate(count=Count('id'))
        .order_by('school', 'name')
    )

    context = {
        'courses': courses,
        'page_title': 'Manage Courses',
    }
    return render(request, "hod_template/manage_course.html", context)

    
def manage_session(request):
    sessions = Session.objects.all()
    context = {'sessions': sessions, 'page_title': 'Manage Session'}
    return render(request, "hod_template/manage_session.html", context)



def manage_term(request):
    terms = Term.objects.all()
    context = {'terms': terms, 'page_title': 'Manage School Terms'}
    return render(request, "hod_template/manage_term.html", context)


def edit_session(request, session_id):
    instance = get_object_or_404(Session, id=session_id)
    form = SessionForm(request.POST or None, instance=instance)
    context = {'form': form, 'session_id': session_id,
               'page_title': 'Edit Session'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Session Updated")
                return redirect(reverse('edit_session', args=[session_id]))
            except Exception as e:
                messages.error(
                    request, "Session Could Not Be Updated " + str(e))
                return render(request, "hod_template/edit_session_template.html", context)
        else:
            messages.error(request, "Invalid Form Submitted ")
            return render(request, "hod_template/edit_session_template.html", context)

    else:
        return render(request, "hod_template/edit_session_template.html", context)



def edit_term(request, session_id):
    instance = get_object_or_404(Term, id=term_id)
    form = TermForm(request.POST or None, instance=instance)
    context = {'form': form, 'term_id': term_id,
               'page_title': 'Edit School Term'}
    if request.method == 'POST':
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Term Updated")
                return redirect(reverse('edit_term', args=[term_id]))
            except Exception as e:
                messages.error(
                    request, "Term Could Not Be Updated " + str(e))
                return render(request, "hod_template/edit_term_template.html", context)
        else:
            messages.error(request, "Invalid Form Submitted ")
            return render(request, "hod_template/edit_term_template.html", context)

    else:
        return render(request, "hod_template/edit_term_template.html", context)



@csrf_exempt
def check_email_availability(request):
    email = request.POST.get("email")
    try:
        user = CustomUser.objects.filter(email=email).exists()
        if user:
            return HttpResponse(True)
        return HttpResponse(False)
    except Exception as e:
        return HttpResponse(False)


@csrf_exempt
def student_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackStudent.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Student Feedback Messages'
        }
        return render(request, 'hod_template/student_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackStudent, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def staff_feedback_message(request):
    if request.method != 'POST':
        feedbacks = FeedbackStaff.objects.all()
        context = {
            'feedbacks': feedbacks,
            'page_title': 'Staff Feedback Messages'
        }
        return render(request, 'hod_template/staff_feedback_template.html', context)
    else:
        feedback_id = request.POST.get('id')
        try:
            feedback = get_object_or_404(FeedbackStaff, id=feedback_id)
            reply = request.POST.get('reply')
            feedback.reply = reply
            feedback.save()
            return HttpResponse(True)
        except Exception as e:
            return HttpResponse(False)


@csrf_exempt
def view_staff_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportStaff.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Staff'
        }
        return render(request, "hod_template/staff_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportStaff, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


@csrf_exempt
def view_student_leave(request):
    if request.method != 'POST':
        allLeave = LeaveReportStudent.objects.all()
        context = {
            'allLeave': allLeave,
            'page_title': 'Leave Applications From Students'
        }
        return render(request, "hod_template/student_leave_view.html", context)
    else:
        id = request.POST.get('id')
        status = request.POST.get('status')
        if (status == '1'):
            status = 1
        else:
            status = -1
        try:
            leave = get_object_or_404(LeaveReportStudent, id=id)
            leave.status = status
            leave.save()
            return HttpResponse(True)
        except Exception as e:
            return False


def admin_view_attendance(request):
    subjects = Subject.objects.all()
    sessions = Session.objects.all()
    context = {
        'subjects': subjects,
        'sessions': sessions,
        'page_title': 'View Attendance'
    }

    return render(request, "hod_template/admin_view_attendance.html", context)


@csrf_exempt
def get_admin_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    attendance_date_id = request.POST.get('attendance_date_id')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = get_object_or_404(
            Attendance, id=attendance_date_id, session=session)
        attendance_reports = AttendanceReport.objects.filter(
            attendance=attendance)
        json_data = []
        for report in attendance_reports:
            data = {
                "status":  str(report.status),
                "name": str(report.student)
            }
            json_data.append(data)
        return JsonResponse(json.dumps(json_data), safe=False)
    except Exception as e:
        return None


def admin_view_profile(request):
    admin = get_object_or_404(Admin, admin=request.user)
    form = AdminForm(request.POST or None, request.FILES or None,
                     instance=admin)
    context = {'form': form,
               'page_title': 'View/Edit Profile'
               }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                passport = request.FILES.get('profile_pic') or None
                custom_user = admin.admin
                if password != None:
                    custom_user.set_password(password)
                if passport != None:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    custom_user.profile_pic = passport_url
                custom_user.first_name = first_name
                custom_user.last_name = last_name
                custom_user.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('admin_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(
                request, "Error Occured While Updating Profile " + str(e))
    return render(request, "hod_template/admin_view_profile.html", context)


def admin_notify_staff(request):
    staff = CustomUser.objects.filter(user_type=2)
    context = {
        'page_title': "Send Notifications To Staff",
        'allStaff': staff
    }
    return render(request, "hod_template/staff_notification.html", context)


def admin_notify_student(request):
    student = CustomUser.objects.filter(user_type=3)
    context = {
        'page_title': "Send Notifications To Students",
        'students': student
    }
    return render(request, "hod_template/student_notification.html", context)


@csrf_exempt
def send_student_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    student = get_object_or_404(Student, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Student Management System",
                'body': message,
                'click_action': reverse('student_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': student.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationStudent(student=student, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


@csrf_exempt
def send_staff_notification(request):
    id = request.POST.get('id')
    message = request.POST.get('message')
    staff = get_object_or_404(Staff, admin_id=id)
    try:
        url = "https://fcm.googleapis.com/fcm/send"
        body = {
            'notification': {
                'title': "Student Management System",
                'body': message,
                'click_action': reverse('staff_view_notification'),
                'icon': static('dist/img/AdminLTELogo.png')
            },
            'to': staff.admin.fcm_token
        }
        headers = {'Authorization':
                   'key=AAAA3Bm8j_M:APA91bElZlOLetwV696SoEtgzpJr2qbxBfxVBfDWFiopBWzfCfzQp2nRyC7_A2mlukZEHV4g1AmyC6P_HonvSkY2YyliKt5tT3fe_1lrKod2Daigzhb2xnYQMxUWjCAIQcUexAMPZePB',
                   'Content-Type': 'application/json'}
        data = requests.post(url, data=json.dumps(body), headers=headers)
        notification = NotificationStaff(staff=staff, message=message)
        notification.save()
        return HttpResponse("True")
    except Exception as e:
        return HttpResponse("False")


def delete_staff(request, staff_id):
    staff = get_object_or_404(CustomUser, staff__id=staff_id)
    staff.delete()
    messages.success(request, "Staff deleted successfully!")
    return redirect(reverse('manage_staff'))

def delete_term(request, term_id):
    staff = get_object_or_404(CustomUser, term__id=term_id)
    staff.delete()
    messages.success(request, "Term deleted successfully!")
    return redirect(reverse('manage_term'))


def delete_student(request, student_id):
    student = get_object_or_404(CustomUser, student__id=student_id)
    student.delete()
    messages.success(request, "Student deleted successfully!")
    return redirect(reverse('manage_student'))

def delete_cwa_admin(request, student_id):
    cwa_admin = get_object_or_404(CustomUser, cwa_admin__id=cwa_admin_id)
    cwa_admin.delete()
    messages.success(request, "CWA_admin deleted successfully!")
    return redirect(reverse('manage_cwa_admin'))


def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    try:
        course.delete()
        messages.success(request, "Course deleted successfully!")
    except Exception:
        messages.error(
            request, "Sorry, some students are assigned to this course already. Kindly change the affected student course and try again")
    return redirect(reverse('manage_course'))



def delete_grade(request, course_id):
    grade = get_object_or_404(Course, id=course_id)
    try:
        grade.delete()
        messages.success(request, "Grade deleted successfully!")
    except Exception:
        messages.error(
            request, "Sorry, some grades are assigned to this grade already. Kindly change the affected grade and try again")
    return redirect(reverse('manage_grade'))



def delete_subject(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    subject.delete()
    messages.success(request, "Subject deleted successfully!")
    return redirect(reverse('manage_subject'))

def delete_school(request, school_id):
    school = get_object_or_404(School, id=school_id)
    school.delete()
    messages.success(request, "School deleted successfully!")
    return redirect(reverse('manage_school'))


def delete_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    try:
        session.delete()
        messages.success(request, "Session deleted successfully!")
    except Exception:
        messages.error(
            request, "There are students assigned to this session. Please move them to another session.")
    return redirect(reverse('manage_session'))

def register_selection(request):
    context = {
        'page_title': 'Select Registration Type',
        'registration_links': [
            {'name': 'Staff', 'url': 'add_staff'},
            {'name': 'Student', 'url': 'add_student'},
            {'name': 'Principal', 'url': 'add_principal'},
            {'name': 'Educator', 'url': 'add_educator'},
            {'name': 'Parent', 'url': 'add_parent'},
            {'name': 'Member', 'url': 'add_member'},
            {'name': 'CWA_Admin', 'url': 'add_cwa_admin'},
        ]
    }
    return render(request, 'registration/register_selection.html', context)

#school perfomance
#To view and calculate the school grade perfomance
def school_performance_view(request):
    # Handle form submission
    if request.method == 'POST':
        form = SchoolPerformanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('school_performance_view')  # Redirect to the same view after saving
    else:
        form = SchoolPerformanceForm()

    # Fetch all performance records and calculate average performance score for graph
    performances = SchoolPerformance.objects.all()
    performance_data = (
        performances
        .values('grade')
        .annotate(avg_performance=Avg('performance_score'))
        .order_by('grade')
    )

    # Data for the bar graph
    grades = [item['grade'] for item in performance_data]
    avg_scores = [float(item['avg_performance']) for item in performance_data]

    context = {
        'form': form,
        'performances': performances,
        'grades': grades,
        'avg_scores': avg_scores,
    }
    return render(request, 'school_performance.html', context)


def upload_courses_from_excel(request):
    if request.method == 'POST':
        form = CourseExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['excel_file']
            try:
                df = pd.read_excel(excel_file)
                df = df.replace({np.nan: ""})
                
                df.columns = [col.strip().lower() for col in df.columns]
                print("Available columns:", df.columns.tolist())
                
                created_count = 0
                updated_count = 0
                errors = []
                skipped = []

                for index, row in df.iterrows():
                    try:
                        # Get course name
                        course_name = None
                        for col in ['name', 'course_name', 'course']:
                            if col in df.columns and row[col]:
                                course_name = str(row[col]).strip()
                                break
                        
                        if not course_name:
                            errors.append(f"Row {index + 2}: Course name is required")
                            continue

                        # Get school EMIS
                        school_emis = None
                        for col in ['school_emis', 'emis', 'school_code']:
                            if col in df.columns and row[col]:
                                school_emis = str(row[col]).strip()
                                break
                        
                        school = None
                        if school_emis and school_emis not in ["", "—"]:
                            school = School.objects.filter(emis=school_emis).first()
                            if not school:
                                errors.append(f"Row {index + 2}: School with EMIS '{school_emis}' not found")

                        # Check if course already exists
                        existing_course = Course.objects.filter(
                            name=course_name, 
                            school=school
                        ).first()
                        
                        if existing_course:
                            skipped.append(f"Row {index + 2}: Course '{course_name}' already exists")
                            continue

                        # Create course
                        Course.objects.create(
                            name=course_name,
                            school=school
                        )
                        
                        created_count += 1
                        school_info = f" for school {school_emis}" if school_emis else ""
                        print(f"✅ Created: {course_name}{school_info}")
                        
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")

                # Show results
                result_msg = f"✅ {created_count} courses created"
                if skipped:
                    result_msg += f", ⏭️ {len(skipped)} duplicates skipped"
                if errors:
                    result_msg += f", ⚠️ {len(errors)} errors"
                    for error in errors[:3]:
                        messages.warning(request, error)
                
                messages.success(request, result_msg)
                return redirect('course_list')

            except Exception as e:
                messages.error(request, f"Error reading Excel file: {e}")
    
    else:
        form = CourseExcelUploadForm()
    
    return render(request, 'courses/upload_excel.html', {'form': form})