import json
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template 
from .EmailBackend import EmailBackend
from django.views.generic import ListView
from college.models import CollegeAndUniversities
from django.core.mail import send_mail
from django.contrib import messages
from django.http import HttpResponseRedirect
from bursary.models import Bursary
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.auth.tokens import default_token_generator
from college.forms import CollegeAndUniversitiesForm
from questpaper.models import QuestionPaper, Topic, Department
from main_app.models import School, Grade, Term, Subject, Educator
from django.views import generic
from django.views.generic import DetailView
from django.views import View
from photo.models import Photo
from job.models import Job, Category
from bursary.forms import BursaryForm
from django.core.mail import send_mail
from django.views.generic import TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import *
from django.utils.decorators import method_decorator
from django.core.mail import EmailMessage
from django.db.models import Q
from questpaper.models import *
from django.contrib.auth import get_user_model


def index_view(request):
    # Fetch data from the theblog app models
    news_items = NewsAndEvents.objects.all().order_by("-updated_date")
    bursaries = Bursary.objects.all().order_by("-upload_time")
    school_dashboard = School.objects.all().order_by("name")
    colleges = CollegeAndUniversities.objects.all().order_by("-upload_time")
    schools = School.objects.all()

    # Question paper model
    question_papers = QuestionPaper.objects.all()
    departments = Department.objects.all()
    grades = Grade.objects.all()
    terms = Term.objects.all()
    photos = Photo.objects.filter(approval_status='approved')
    
    # Jobs (added here)
    jobs = Job.objects.all().order_by("-id")
    categories = Category.objects.all()
    
    # Videos - ADD THESE LINES
    video_categories = VideoCategory.objects.all()
    videos = Video.objects.select_related('category', 'author').order_by('-date_posted')[:6]  # Limit to 6 latest videos

    # Appointment form submission
    if request.method == 'POST' and 'appointment_submit' in request.POST:
        appointment_form = AppointmentForm(request.POST)
        if appointment_form.is_valid():
            appointment_form.save()
            messages.success(request, "Thank you for your submission. An appointment has been booked!")
            return redirect('index')
    else:
        appointment_form = AppointmentForm()

    # Subscription form submission
    if request.method == 'POST' and 'subscribe_submit' in request.POST:
        subscription_form = SubscriptionForm(request.POST)
        if subscription_form.is_valid():
            email = subscription_form.cleaned_data['email']
            if not Subscription.objects.filter(email=email).exists():
                subscription_form.save()
                messages.success(request, "You have successfully subscribed!")
            else:
                messages.warning(request, "This email is already subscribed.")
            return redirect('index')
    else:
        subscription_form = SubscriptionForm()

    # Fetch subscription data
    subscriptions = Subscription.objects.all()

    # Context data - ADD VIDEOS TO CONTEXT
    context = {
        "schools": schools,
        "title": "News & Events",
        "news_items": news_items,
        "school_dashboard": school_dashboard,
        "bursaries": bursaries,
        "colleges": colleges,
        'question_papers': question_papers,
        'departments': departments,
        'grades': grades,
        'terms': terms,
        "appointment_form": appointment_form,
        "subscription_form": subscription_form,
        "subscriptions": subscriptions,
        "photos": photos,
        "jobs": jobs,
        "categories": categories,
        # Add videos to context
        "videos": videos,
        "video_categories": video_categories,
        # Add counts for each shortcut
        "question_papers_count": question_papers.count(),
        "schools_count": schools.count(),
        "prospectors_count": Prospectors.objects.count(),
        "colleges_count": colleges.count(),
        "bursaries_count": bursaries.count(),
        "jobs_count": jobs.count(),
        "videos_count": videos.count(),  # Optional: videos count
    }

    return render(request, 'landing/home.html', context)

#general search view
def general_search_view(request):
    """
    Handles both AJAX-based live search and regular search form submissions.
    """
    search_results = {
        "news_items": [],
        "bursary_items": [],
        "school_dashboard": [],
        "college_items": [],
        "question_papers": [],
    }
    search_query = request.GET.get('q', '')  # For regular search
    action = request.POST.get('action', '')  # For AJAX search

    if action == 'post':
        # Handle AJAX search
        search_string = request.POST.get('ss', '').strip()
        if search_string:
            # Collect results from all models for AJAX
            news_items = NewsAndEvents.objects.filter(
                Q(title__icontains=search_string) | Q(summary__icontains=search_string)
            )[:5]
            bursary_items = Bursary.objects.filter(
                Q(title__icontains=search_string) | Q(summary__icontains=search_string)
            )[:5]
            school_dashboard = School.objects.filter(
                Q(name__icontains=search_string) | Q(emis__icontains=search_string)
            )[:5]
            college_items = CollegeAndUniversities.objects.filter(
                Q(title__icontains=search_string) | Q(summary__icontains=search_string)
            )[:5]
            question_papers = QuestionPaper.objects.filter(
                Q(topics__name__icontains=search_string) |
                Q(subject__name__icontains=search_string) |
                Q(grade__name__icontains=search_string)
            ).distinct()[:5]

            # Serialize all results
            serialized_results = {
                "news_items": serializers.serialize('json', news_items, fields=('id', 'title', 'slug')),
                "bursary_items": serializers.serialize('json', bursary_items, fields=('id', 'title', 'slug')),
                "school_dashboard": serializers.serialize('json', school_dashboard, fields=('id', 'name', 'emis')),
                "college_items": serializers.serialize('json', college_items, fields=('id', 'title', 'slug')),
                "question_papers": serializers.serialize('json', question_papers, fields=('id', 'topics', 'subject', 'grade')),
            }
            return JsonResponse(serialized_results)

    # Handle regular search
    if search_query:
        # Search across all models
        search_results["news_items"] = NewsAndEvents.objects.filter(
            Q(title__icontains=search_query) | Q(summary__icontains=search_query)
        )
        search_results["bursary_items"] = Bursary.objects.filter(
            Q(title__icontains=search_query) | Q(summary__icontains=search_query)
        )
        search_results["school_dashboard"] = School.objects.filter(
            Q(name__icontains=search_query) | Q(emis__icontains=search_query)
        )
        search_results["college_items"] = CollegeAndUniversities.objects.filter(
            Q(title__icontains=search_query) | Q(summary__icontains=search_query)
        )
        search_results["question_papers"] = QuestionPaper.objects.filter(
            Q(topics__name__icontains=search_query) |
            Q(subject__name__icontains=search_query) |
            Q(grade__name__icontains=search_query)
        ).distinct()

    return render(request, 'landing/search.html', {
        "q": search_query,
        "results": search_results,
        "form": None,  # Placeholder for the form, if needed
    })

#password
#login_page
#password
#login_page
def login_page(request):
    if request.user.is_authenticated:
        if request.user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif request.user.user_type == '2':
            return redirect(reverse("staff_home"))
                #add user login
        elif request.user.user_type == '3':
            return redirect(reverse("student_home"))
        elif request.user.user_type == '4':
            return redirect(reverse("principal_home"))
        elif request.user.user_type == '5':
            return redirect(reverse("educator_home"))
        elif request.user.user_type == '6':
            return redirect(reverse("circuit_manager_home"))
        elif request.user.user_type == '7':
            return redirect(reverse("parent_home"))
        
        else:
            return redirect(reverse("cwa_admin"))
        
    return render(request, 'main_app/login.html')


#school dashboard
def no_school_page(request):
    return render(request, 'main_app/some_other_page.html')

def school_dashboard(request):
    # Redirect to login if the user is not authenticated
    if not request.user.is_authenticated:
        return redirect('login_page')

    # Check if the user is a superuser
    if request.user.is_superuser:
        schools = School.objects.all()  # Get all schools for the superuser
        context = {
            'schools': schools,
        }
        return render(request, 'main_app/school_dashboard.html', context)

    try:
        # Retrieve the school associated with the logged-in user
        school = School.objects.get(user=request.user)
    except School.DoesNotExist:
        # Redirect to the "No School Associated" page
        return redirect('no_school_page')

    if request.method == 'POST':
        form = SchoolEditForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "School details updated successfully!")
            return redirect('school_dashboard')  # Redirect to avoid resubmission
        else:
            messages.error(request, "There was an error updating the details.")
    else:
        form = SchoolEditForm(instance=school)

    context = {
        'school': school,
        'form': form,
    }
    return render(request, 'main_app/school_dashboard.html', context)

#submit documents
def submit_documents(request):
    school = School.objects.filter(admin=request.user).first()

    # Circuit Manager bypasses school filtering
    if request.user.user_type == "6":  # Circuit Manager
        school = None

    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            document = form.save(commit=False)
            document.school = school if school else None
            document.uploaded_by = request.user
            document.save()
            messages.success(request, "Document uploaded successfully!")
            return redirect('submit_documents')
    else:
        form = DocumentUploadForm(user=request.user)

    # Display all documents relevant to the user
    if request.user.user_type == "6":  # Circuit Manager
        documents = Document.objects.all()
    else:
        documents = Document.objects.filter(school=school)

    context = {
        'form': form,
        'documents': documents,
    }
    return render(request, 'main_app/submit_documents.html', context)

def doLogin(request, **kwargs):
    #Authenticate
    user = EmailBackend.authenticate(request, username=request.POST.get('email'), password=request.POST.get('password'))
    if user != None:
        login(request, user)
        if user.user_type == '1':
            return redirect(reverse("admin_home"))
        elif user.user_type == '2':
            return redirect(reverse("staff_home"))
        #add user login
        elif user.user_type == '3':
            return redirect(reverse("student_home"))
        elif user.user_type == '4':
            return redirect(reverse("principal_home"))
        elif user.user_type == '5':
            return redirect(reverse("educator_home"))
        elif user.user_type == '6':
            return redirect(reverse("circuit_manager_home"))
        elif user.user_type == '7':
            return redirect(reverse("parent_home"))
        elif user.user_type == '8':
            return redirect(reverse("member_home"))
        else:
            return redirect(reverse("CWA_Admin"))
    else:
        messages.error(request, "Invalid details")
        return redirect("/")

#register selection
def terms_conditions(request):
    return render(request, 'registration/terms_conditions.html', {'page_title': 'Terms and Conditions'})

def logout_user(request):
    if request.user != None:
        logout(request)
    return redirect("/")


#attendance
@csrf_exempt
def get_attendance(request):
    subject_id = request.POST.get('subject')
    session_id = request.POST.get('session')
    try:
        subject = get_object_or_404(Subject, id=subject_id)
        session = get_object_or_404(Session, id=session_id)
        attendance = Attendance.objects.filter(subject=subject, session=session)
        attendance_list = []
        for attd in attendance:
            data = {
                    "id": attd.id,
                    "attendance_date": str(attd.date),
                    "session": attd.session.id
                    }
            attendance_list.append(data)
        return JsonResponse(json.dumps(attendance_list), safe=False)
    except Exception as e:
        return None


# List circuits
def circuitGallery(request):
    user = request.user
    search_query = request.GET.get('search')

    if search_query:
        circuits = Circuit.objects.filter(name__icontains=search_query)
    else:
        circuits = Circuit.objects.all()

    context = {'circuits': circuits}
    return render(request, 'circuits/circuit_gallery.html', context)


# List circuits
def circuitGallery(request):
    user = request.user

    # Superuser sees all circuits
    if user.is_superuser:
        circuits = Circuit.objects.all()
        is_admin = True
    else:
        # Normal user: show only their assigned circuit(s)
        try:
            # Assuming user has a foreign key or M2M to Circuit
            circuits = user.circuits.all()  # or user.circuit_set.all()
            if not circuits.exists():
                return redirect('no_access')
            is_admin = False
        except AttributeError:
            # No circuit assigned
            return redirect('no_access')

    context = {'circuits': circuits, 'is_admin': is_admin}
    return render(request, 'circuit/circuit_gallery.html', context)

# View a single circuit
def viewCircuit(request, pk):
    circuit = get_object_or_404(Circuit, pk=pk)
    user = request.user

    # Superuser sees everything
    if user.is_superuser:
        can_view = True
    else:
        # Normal user or circuit manager: check assignment
        try:
            if user.circuit_manager.circuit == circuit:
                can_view = True
            else:
                can_view = False
        except Circuit_Manager.DoesNotExist:
            can_view = False

    if not can_view:
        return redirect('no_access')

    return render(request, 'circuit/circuit_detail.html', {'circuit': circuit, 'is_admin': user.is_superuser})

    
# Add a new circuit with preview
def addCircuit(request):
    if request.method == 'POST':
        data = request.POST

        # Create the Circuit
        circuit = Circuit.objects.create(
            name=data['name'],
            contact=data['contact'],
            email=data['email'],
            whatsapp_number=data['whatsapp_number'],
            address=data.get('address', ''),
        )

        # If user is not superuser, link the circuit to their manager account
        if not request.user.is_superuser:
            manager, created = Circuit_Manager.objects.get_or_create(admin=request.user)
            manager.circuit = circuit
            manager.save()
        else:
            # Optionally show a message for admin
            messages.success(request, f"Circuit '{circuit.name}' added successfully by Admin.")

        return redirect('circuit_gallery')

    return render(request, 'circuit/add_circuit.html')

#edit circuit
def editCircuit(request, pk):
    circuit = get_object_or_404(Circuit, pk=pk)

    # Allow access if user is superuser or manages this circuit
    if not request.user.is_superuser:
        try:
            if request.user.circuit_manager.circuit != circuit:
                return redirect('no_access')
        except Circuit_Manager.DoesNotExist:
            return redirect('no_access')

    if request.method == 'POST':
        data = request.POST
        circuit.name = data['name']
        circuit.contact = data['contact']
        circuit.email = data['email']
        circuit.whatsapp_number = data['whatsapp_number']
        circuit.address = data.get('address', '')
        circuit.save()

        messages.success(request, f"Circuit '{circuit.name}' updated successfully.")
        return redirect('view_circuit', pk=pk)

    context = {'circuit': circuit}
    return render(request, 'circuit/edit_circuit.html', context)


#delete circuit
def deleteCircuit(request, pk):
    circuit = get_object_or_404(Circuit, pk=pk)

    # Allow access if user is superuser or manages this circuit
    if not request.user.is_superuser:
        try:
            if request.user.circuit_manager.circuit != circuit:
                return redirect('no_access')
        except Circuit_Manager.DoesNotExist:
            return redirect('no_access')

    circuit.delete()
    messages.success(request, f"Circuit '{circuit.name}' deleted successfully.")
    return redirect('circuit_gallery')


# ########################################################
# News & Events
# ########################################################

def news_view(request):
    items = NewsAndEvents.objects.all().order_by("-updated_date")
    context = {
        "title": "News & Events",
        "items": items,
    }
    return render(request, "core/news.html", context)

# Use the active user model (CustomUser)
User = get_user_model()

#add news events posts
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
        return redirect('home')

    return render(request, 'core/post_add.html')


#view appointment
def view_appointments(request):
    appointments = Appointment.objects.all().order_by('-submitted_at')  # Correctly use 'objects'
    return render(request, 'view_appointments.html', {'appointments': appointments})

#send feedback
def send_feedback(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    if request.method == 'POST':
        feedback = request.POST.get('feedback')
        appointment.feedback = feedback
        appointment.save()

        #send feedback email to the user
        send_mail(
            subject="Your Appoitment feedback",
            message=f"Dear {appointment.name},\n\n{feedback}\n\nThank you, \nCircuit Management",
            from_email="circuit@example.com",
            recipient_list=[appointment.email],
        )
        return redirect('view_appointments')

    return render(request, 'send_feedback.html', {'appointment': appointment})

#appointment
def appointments_view(request):
    appointments = Appointment.objects.all()  # Fetch all appointments
    return render(request, 'appointments.html', {'appointments': appointments})


def feedback_status(request):
    appointments = Appointment.objects.filter(email=request.GET.get('email'))
    return render(request, 'feedback_status.html', {'appointments': appointments})


def edit_post(request, pk):
    instance = get_object_or_404(NewsAndEvents, pk=pk)
    if request.method == "POST":
        form = NewsAndEventsForm(request.POST, instance=instance)
        title = request.POST.get("title")
        if form.is_valid():
            form.save()

            messages.success(request, (title + " has been updated."))
            return redirect("home")
        else:
            messages.error(request, "Please correct the error(s) below.")
    else:
        form = NewsAndEventsForm(instance=instance)
    return render(
        request,
        "core/post_add.html",
        {
            "title": "Edit Post",
            "form": form,
        },
    )

def subscribe_view(request):
    if request.method == 'POST':
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            if not Subscription.objects.filter(email=email).exists():
               form.save()
               message.success(request, 'You have successfully subscribed!')
            else:
               message.warning(request, "This eamil is already subscribed.")
        else:
            messages.error(request,"Invalid email. Please try again.")
        return redirect('subscribe')
    else:
        form = SubscriptionForm()
    
    subscriptions = Subscription.objects.all()

    return render(request, 'subscribe.html', {'form': form, 'subscriptions': subscriptions})


def delete_post(request, pk):
    post = get_object_or_404(NewsAndEvents, pk=pk)
    title = post.title
    post.delete()
    messages.success(request, (title + " has been deleted."))
    return redirect("home")


def view_textbooks(request):
    textbooks = Textbook.objects.all()

    context = {
        'textbooks': textbooks,
    }
    return render(request, 'view_textbooks.html', context)

def view_textbooks(request):
    if request.user.user_type == "5":  # Educator
        textbooks = Textbook.objects.filter(grade__educators=request.user)
    elif request.user.user_type == "3":  # Student
        textbooks = Textbook.objects.filter(grade__students=request.user)
    else:  # Circuit Manager or others
        textbooks = Textbook.objects.all()

    context = {
        'textbooks': textbooks,
    }
    return render(request, 'view_textbooks.html', context)


#file upload for relevant documents.
class FileView(generic.ListView):
    model = Files
    template_name = 'social/file.html'
    context_object_name = 'files'
    paginate_by = 6

    def get_queryset(self):
        if self.request.user.is_superuser:
            # If the user is a superuser, show all files
            return Files.objects.order_by('-id')
        else:
            # If the user is not a superuser, show only their own files
            return Files.objects.filter(owner=self.request.user).order_by('-id')


def download_file(request, pk):
    file_instance = get_object_or_404(Files, pk=pk)

    # Check if the user is a superuser or the owner of the file
    if request.user.is_superuser or file_instance.owner == request.user:
        file_path = file_instance.pdf.path
        response = FileResponse(open(file_path, 'rb'))
        return response
    else:
        raise Http404("You don't have permission to access this file.")


def uploadForm(request):
    return render(request, 'social/upload.html')

def uploadFile(request):
    if request.method == 'POST':
        filename = request.POST['filename']
        pdf = request.FILES['pdf']
        cover = request.FILES['cover']

        # Use the currently logged-in user as the owner
        owner = request.user

        a = Files(filename=filename, owner=owner, pdf=pdf, cover=cover)
        a.save()

        # URLs for the listview and brokerview pages
        listview_url = request.build_absolute_uri(reverse('listview'))
        brokerview_url = request.build_absolute_uri(reverse('brokerview'))

        # Send email to the user after successful file upload
        email_address = owner.email
        subject = 'Files Uploaded Successfully'
        message = (
            'Thank you for uploading your files. Your submission was successful.'
            'Submit payments to the following account'
            'Click the links below to visit the pages:\n\n'
            'Bursary: {}\n'
            'University: {}'
        ).format('https://www.macrosecond.com/photos/listview/', 'https://www.macrosecond.com/broker/brokerview/')

        context = {'name': owner.first_name, 'message': message}
        email_template = get_template('emailapp/email.html').render(context)

        # Use from_email and to parameters for sender and recipient
        email = EmailMessage(subject, email_template, from_email="macrosecond1@gmail.com", to=[email_address])
        email.content_subtype = "html"
        email.send()

        messages.success(request, 'Files submitted successfully!')
        return redirect('https://pay.yoco.com/macrosecond')
    else:
        messages.error(request, 'Files are not submitted yet!')
        return redirect('form')
    
def myUpload(request):
	return render(request, 'social/myUpload.html')


#SCHOOL FILES UPLOAD
class SchoolFileView(generic.ListView):
    model = Files
    template_name = 'school/schoolfile.html'
    context_object_name = 'schoolfiles'
    paginate_by = 6

    def get_queryset(self):
        if self.request.user.is_superuser:
            # If the user is a superuser, show all files
            return Files.objects.order_by('-id')
        else:
            # If the user is not a superuser, show only their own files
            return Files.objects.filter(owner=self.request.user).order_by('-id')


def download_schoolfile(request, pk):
    file_instance = get_object_or_404(Files, pk=pk)

    # Check if the user is a superuser or the owner of the file
    if request.user.is_superuser or file_instance.owner == request.user:
        file_path = file_instance.pdf.path
        response = FileResponse(open(file_path, 'rb'))
        return response
    else:
        raise Http404("You don't have permission to access this file.")


def uploadSchoolForm(request):
    return render(request, 'school/schoolupload.html')

def uploadSchoolFile(request):
    if request.method == 'POST':
        filename = request.POST['filename']
        pdf = request.FILES['pdf']
        cover = request.FILES['cover']

        # Use the currently logged-in user as the owner
        owner = request.user

        a = Files(filename=filename, owner=owner, pdf=pdf, cover=cover)
        a.save()

        # Send email to the user after successful file upload
        email_address = owner.email
        subject = 'Files Uploaded Successfully'
        message = (
            'Thank you for uploading your files. Your submission was successful.'
            'Submitted for review to the circuit'
            'Click the links below to visit the pages:\n\n'
            'Vhembe West: {}\n'
            'Circuit Management Office: {}'
        ).format('#', '#')

        context = {'name': owner.first_name, 'message': message}
        email_template = get_template('emailapp/email.html').render(context)

        # Use from_email and to parameters for sender and recipient
        email = EmailMessage(subject, email_template, from_email="macrosecond1@gmail.com", to=[email_address])
        email.content_subtype = "html"
        email.send()

        messages.success(request, 'Files submitted successfully!')
        return redirect('mySchoolUpload')
    else:
        messages.error(request, 'Files are not submitted yet!')
        return redirect('schoolform')
    
def mySchoolUpload(request):
	return render(request, 'school/mySchoolUpload.html')


#timetable
def timetable_list(request):
    user = request.user
    timetables = None
    student_subjects = None  # Initialize to handle non-student users

    if user.user_type == "3":  # Student
        try:
            # Fetch the student's grade, course, and subjects
            student = Student.objects.get(admin=user)
            student_subjects = student.course.subject_set.all()  # Get all subjects linked to the course

            # Filter timetables for matching grade and course
            timetables = Timetable.objects.filter(
                grade=student.grade,  # Ensure this is a Grade instance
                course=student.course,  # Ensure this is a Course instance
            ).distinct()
        except Student.DoesNotExist:
            timetables = []

    elif user.user_type == "5":  # Educator
        try:
            educator = Educator.objects.get(admin=user)
            timetables = Timetable.objects.filter(
                grade=educator.grade,  # Ensure this is a Grade instance
                course=educator.course,  # Ensure this is a Course instance
            )
        except Educator.DoesNotExist:
            timetables = []

    elif user.user_type in ["1", "4", "6"]:  # HOD, Principal, Circuit Manager
        timetables = Timetable.objects.all()

    return render(request, 'timetable/timetable_list.html', {
        'timetables': timetables,
        'user_subjects': student_subjects if user.user_type == "3" else None
    })


#timetable add
def timetable_add_edit(request, timetable_id=None):
    # Retrieve the timetable if editing, or None if creating a new one
    timetable = get_object_or_404(Timetable, id=timetable_id) if timetable_id else None

    if request.method == "POST":
        form = TimetableForm(request.POST, instance=timetable)
        if form.is_valid():
            new_timetable = form.save(commit=False)
            if not timetable:  # Only set 'created_by' when creating a new timetable
                new_timetable.created_by = request.user
            new_timetable.save()
            form.save_m2m()  # Save many-to-many relationships (subjects and educators)
            return redirect('timetable_list')  # Redirect to timetable list after save
    else:
        form = TimetableForm(instance=timetable)

    return render(request, 'timetable/add_edit.html', {'form': form})

def showFirebaseJS(request):
    data = """
    // Give the service worker access to Firebase Messaging.
    // Note that you can only use Firebase Messaging here, other Firebase libraries
    // are not available in the service worker.
    importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-app.js');
    importScripts('https://www.gstatic.com/firebasejs/7.22.1/firebase-messaging.js');

    // Initialize the Firebase app in the service worker by passing in
    // your app's Firebase config object.
    // https://firebase.google.com/docs/web/setup#config-object
    firebase.initializeApp({
        apiKey: "AIzaSyBarDWWHTfTMSrtc5Lj3Cdw5dEvjAkFwtM",
        authDomain: "sms-with-django.firebaseapp.com",
        databaseURL: "https://sms-with-django.firebaseio.com",
        projectId: "sms-with-django",
        storageBucket: "sms-with-django.appspot.com",
        messagingSenderId: "945324593139",
        appId: "1:945324593139:web:03fa99a8854bbd38420c86",
        measurementId: "G-2F2RXTL9GT"
    });

    // Retrieve an instance of Firebase Messaging so that it can handle background
    // messages.
    const messaging = firebase.messaging();
    messaging.setBackgroundMessageHandler(function (payload) {
        const notification = JSON.parse(payload);
        const notificationOption = {
            body: notification.body,
            icon: notification.icon
        }
        return self.registration.showNotification(payload.notification.title, notificationOption);
    });
        """
    return HttpResponse(data, content_type='application/javascript')

#header Learn more
class Engage(TemplateView):
    template_name = 'landing/engagewithus.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context
    
#connected
class Connected(TemplateView):
    template_name = 'landing/stayconnected.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

#office
class Office(TemplateView):
    template_name = 'landing/officehours.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context
#footer

#Help Center
class Help(TemplateView):
    template_name = 'landing/help.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

class About(TemplateView):
    template_name = 'landing/about.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

class Services(TemplateView):
    template_name = 'landing/services.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

class OurCases(TemplateView):
    template_name = 'landing/cases.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

class Other(TemplateView):
    template_name = 'landing/other.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

class Testimonials(TemplateView):
    template_name = 'landing/testimonials.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

class Faq(TemplateView):
    template_name = 'landing/faq.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

class Consulting(TemplateView):
    template_name = 'landing/consulting.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context

#messaging
class MessageExchangeView(View):
    template_name = 'message.html'  # Reference to message.html

    def is_ajax_request(self, request):
        """Check if the request is an AJAX request by inspecting the headers."""
        return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

    def get(self, request, *args, **kwargs):
        # Render the message.html page with the form
        form = MessageForm()
        return render(request, self.template_name, {'form': form})

    @method_decorator(csrf_exempt)
    def post(self, request, *args, **kwargs):
        # Handle AJAX form submission
        if self.is_ajax_request(request) and request.method == "POST":
            form = MessageForm(request.POST, request.FILES)
            if form.is_valid():
                # Save the message
                message = form.save(commit=False)

                # Retrieve the CustomUser instance
                user_identifier = request.POST.get('user_email')  # Assume user_email is passed in the request
                user = get_object_or_404(CustomUser, email=user_identifier)
                message.author = user
                message.save()

                # Send email to the user after successful message addition
                email_address = user.email
                subject = 'Message Sent Successfully'
                context = {'name': user.first_name, 'message': 'Your message has been sent successfully.'}
                email_template = get_template('emailapp/email.html').render(context)

                email = EmailMessage(
                    subject, email_template,
                    from_email="Vhembe West Apply <your@email.com>",
                    to=[email_address]
                )
                email.content_subtype = "html"
                email.send()

                # Save each uploaded file to MessageMedia
                files = request.FILES.getlist('media_files')
                for file in files:
                    MessageMedia.objects.create(message=message, media=file)

                # Prepare the response
                media_urls = [media.media.url for media in message.media.all()]
                return JsonResponse({
                    'author': message.author.username,
                    'text': message.text,
                    'media_urls': media_urls,
                    'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                })

        return JsonResponse({'error': 'Invalid request'}, status=400)
    
def external_redirect(request, url):
    return redirect(url)

#add source
def addSos(request):
    user = request.user
    soscategories = user.soscategory_set.all()

    if request.method == 'POST':
        data = request.POST
        image = request.FILES.get('image')  # Get the main image

        if data['soscategory'] != 'none':
            soscategory = SosCategory.objects.get(id=data['soscategory'])
        elif data['soscategory_new'] != '':
            soscategory, created = SosCategory.objects.get_or_create(
                user=user,
                name=data['soscategory_new'])
        else:
            soscategory = None
       
        # Check if the main image is provided before creating the job instance
        if image:
            sos = Sos.objects.create(
                author=user,  # Set the author to the logged-in user
                soscategory=soscategory,
                description=data['description'],
                image=image,  # Use the main image
                date=date,
                assessment=assessment,
                subject=subject,
                grade=grade,

            )
            
            return redirect('soslistview')  # Make sure the URL name is correct
        else:
            error_message = "Please upload the main image."
            context = {'soscategories': soscategories, 'error_message': error_message}
            return render(request, 'sos/addsos.html', context)

    context = {'soscategories': soscategories}
    return render(request, 'sos/addsos.html', context)

#sosview
#galleryview
def sosview(request):
	soss = Sos.objects.all()
	context = {'soss': soss}
	template = 'sos/soslistview.html'	
	return render(request, template, context)

#delete gallery image
def deleteSos(request, pk):
    soss = Sos.objects.get(id=pk)
    if len(soss.image) > 0:
        os.remove(soss.image.path)
    soss.delete()
    messages.success(request,"Sos Deleted Successfuly")
    return redirect('soslistview')

#view job
def viewSos(request, pk):
    sos = Sos.objects.get(id=pk)
    return render(request, 'sos/sos.html', {'sos': sos})


#C.Manager
class CircuitManager(TemplateView):
    template_name = 'landing/circuitmanager.html'

    # If you want to pass any context data to the template, you can override the get_context_data method
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any context data here if needed
        context['some_data'] = 'This is some data to display on the earnings page.'
        return context
    
#contact section
def contact_list_view(request):
    contacts = Contact.objects.all().order_by('-submitted_at')
    return render(request, 'contacts/contact_list.html', {'contacts': contacts})

def contact_detail_view(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    form = ReplyContactForm()
    if request.method == 'POST':
        form = ReplyContactForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            send_mail(
                subject=subject,
                message=message,
                from_email='your_email@example.com',  # Replace with your email
                recipient_list=[contact.gmail],
            )
            messages.success(request, 'Reply sent successfully!')
            return HttpResponseRedirect(request.path_info)
    return render(request, 'contacts/contact_detail.html', {'contact': contact, 'form': form})

#submit contact link
def contact_create_view(request):
    if request.method == 'POST':
        full_names = request.POST.get('full_names')
        gmail = request.POST.get('gmail')
        phone_number = request.POST.get('phone_number')
        message_box = request.POST.get('message_box')

        # Save the contact details to the database
        Contact.objects.create(
            full_names=full_names,
            gmail=gmail,
            phone_number=phone_number,
            message_box=message_box,
        )
        messages.success(request, 'Your message has been submitted successfully!')
        return HttpResponseRedirect(request.path_info)

    return render(request, 'contacts/contact_form.html')

#prospectors update 

# List View - Show Uploaded Prospectors
class ProspectorsListView(ListView):
    model = Prospectors
    template_name = 'prospectors/prospectors_list.html'  # Your template file
    context_object_name = 'prospectors'  # This makes 'prospectors' available in the template

    def get_queryset(self):
        queryset = Prospectors.objects.all()
        query = self.request.GET.get('q', '')  # Get the search query from the GET request
        if query:
            queryset = queryset.filter(institution__icontains=query) | queryset.filter(address__icontains=query)
        return queryset


#prospector search
class ProspectorsSearchView(ListView):
    model = Prospectors
    template_name = 'prospectors/prospectors_search.html'
    context_object_name = 'prospectors'

    def get_queryset(self):
        query = self.request.GET.get('q', '')  # Get the search query from the GET request
        if query:
            # Filter by institution or address containing the search term
            return Prospectors.objects.filter(institution__icontains=query) | Prospectors.objects.filter(address__icontains=query)
        return Prospectors.objects.none()  # If no query, return empty querysetd

# Create View - Upload Prospectors
class ProspectorsCreateView(CreateView):
    model = Prospectors
    fields = ['institution', 'address', 'copy', 'logo']
    template_name = 'prospectors/upload_prospector.html'
    success_url = reverse_lazy('prospectors_list')  # Redirect after successful upload

#edit prospectors

# Create View - Upload Prospectors
class ProspectorsCreateView(CreateView):
    model = Prospectors
    fields = ['institution', 'address', 'copy', 'logo']
    template_name = 'prospectors/upload_prospector.html'
    success_url = reverse_lazy('prospectors_list')  # Redirect after successful upload


#edit prospectors
def prospector_edit(request, prospector_id):
    prospector = get_object_or_404(Prospectors, id=prospector_id)  # Fetch the Prospector

    if request.method == 'POST':
        prospector.institution = request.POST.get('institution')
        prospector.address = request.POST.get('address')

        if 'copy' in request.FILES:
            prospector.copy = request.FILES['copy']  # Handle file upload

        if 'logo' in request.FILES:
            prospector.logo = request.FILES['logo']  # Handle image upload

        prospector.save()  # Save changes to the database
        return redirect('prospectors_list')  # Redirect after editing

    return render(request, 'prospectors/prospectors_edit.html', {'prospector': prospector})

#Reset Password
# View to Handle Password Reset Request
def custom_password_reset_request(request):
    if request.method == "POST":
        form = CustomPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = CustomUser.objects.get(email=email)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = request.build_absolute_uri(f"/reset/{uid}/{token}/")

            # Send reset email
            send_mail(
                "Password Reset Request",
                f"Click the link below to reset your password:\n{reset_link}",
                "noreply@elimcircuit.com",
                [email],
                fail_silently=False,
            )

            messages.success(request, "Password reset link sent to your email.")
            return redirect("custom_password_reset_done") 

    else:
        form = CustomPasswordResetForm()

    return render(request, "custom_auth/password_reset_form.html", {"form": form})

# Reset done
def custom_password_reset_done(request):
    return render(request, "custom_auth/password_reset_done.html")


# View to Handle Password Reset Confirmation
def custom_password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            new_password = request.POST.get("password")
            user.set_password(new_password)
            user.save()
            messages.success(request, "Your password has been reset successfully.")
            return redirect("login_page")

        return render(request, "custom_auth/password_reset_confirm.html")

    messages.error(request, "The password reset link is invalid or has expired.")
    return redirect("password_reset_request")

# Video add functions
def video_add_view(request):
    # Check if user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "Please login to upload videos")
        return redirect('login_page')  # Adjust to your login URL
    
    categories = VideoCategory.objects.all()

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        category_new = request.POST.get("category_new")
        video_file = request.FILES.get("video_file")
        thumbnail = request.FILES.get("thumbnail")

        # Create or get category
        if category_new:
            category_obj, created = VideoCategory.objects.get_or_create(name=category_new)
        elif category_id and category_id != 'none':
            category_obj = VideoCategory.objects.get(id=category_id)
        else:
            category_obj = None

        # Save the video
        video = Video.objects.create(
            author=request.user,
            title=title,
            description=description,
            category=category_obj,
            video_file=video_file,
            thumbnail=thumbnail,
            website_url=request.POST.get("website_url"),
            gmail_url=request.POST.get("gmail_url"),
            whatsapp_number=request.POST.get("whatsapp_number"),
            facebook_url=request.POST.get("facebook_url"),
            tiktok_url=request.POST.get("tiktok_url"),
            zoom_url=request.POST.get("zoom_url"),
            microsoftTeam_url=request.POST.get("microsoftTeam_url"),
            location=request.POST.get("location"),
            twitter_url=request.POST.get("twitter_url"),
            playstore_url=request.POST.get("playstore_url"),
            linkedin_url=request.POST.get("linkedin_url"),
            instagram_url=request.POST.get("instagram_url"),
            pinterest_url=request.POST.get("pinterest_url"),
            youtube_url=request.POST.get("youtube_url"),
        )

        messages.success(request, "Video uploaded successfully!")
        return redirect("show_video", video_id=video.id)

    return render(request, "videos/add_video.html", {"categories": categories})

# View videos
def videos_view(request):
    categories = VideoCategory.objects.all()
    videos = Video.objects.select_related('category', 'author').order_by('-date_posted')
    return render(request, 'videos/videos.html', {'videos': videos, 'categories': categories})

# Show video
def show_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    return render(request, 'videos/show_video.html', {'video': video})

@require_POST
def like_video(request, video_id):
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required',
            'login_url': 'login_page'  # Adjust to your login URL
        }, status=401)
    
    video = get_object_or_404(Video, id=video_id)
    like, created = VideoLike.objects.get_or_create(video=video, user=request.user)
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'likes_count': video.likes.count()
    })

@require_POST
def add_comment(request, video_id):
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required',
            'login_url': 'login_page'  # Adjust to your login URL
        }, status=401)
    
    video = get_object_or_404(Video, id=video_id)
    data = json.loads(request.body)
    
    comment = VideoComment.objects.create(
        video=video,
        user=request.user,
        text=data.get('text')
    )
    
    return JsonResponse({
        'success': True,
        'comment': {
            'user_name': comment.user.username,
            'text': comment.text,
            'created_at': comment.created_at.strftime('%b %d, %Y')
        }
    })

def get_comments(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    comments = video.comments.all().order_by('created_at')
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'user_name': comment.user.username if comment.user else 'Unknown User',
            'text': comment.text,
            'created_at': comment.created_at.strftime('%b %d, %Y')
        })
    
    return JsonResponse(comments_data, safe=False)