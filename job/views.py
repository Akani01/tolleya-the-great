from django.shortcuts import get_object_or_404, render, redirect
from job.models import *
from django.contrib.auth.decorators import login_required
# Create your views here.
from main_app.forms import *
import pandas as pd
import numpy as np
from django.contrib import messages
import os


#gallery

def jobgallery(request):
    user = request.user
    category = request.GET.get('category')
    if category == None:
        jobs = Job.objects.filter(category__user=user)
    else:
        jobs = Job.objects.filter(
            category__name=category, category__user=user)

    categories = Category.objects.filter(user=user)
    context = {'categories': categories, 'jobs': jobs}
    return render(request, 'jobs/jobgallery.html', context)

#view job

def viewJob(request, pk):
    job = Job.objects.get(id=pk)
    return render(request, 'jobs/job.html', {'job': job})

#add job
def addJob(request):
    user = request.user
    categories = user.category_set.all()

    if request.method == 'POST':
        data = request.POST
        image = request.FILES.get('image')  # Get the main image

        if data['category'] != 'none':
            category = Category.objects.get(id=data['category'])
        elif data['category_new'] != '':
            category, created = Category.objects.get_or_create(
                user=user,
                name=data['category_new'])
        else:
            category = None
       
        # Check if the main image is provided before creating the job instance
        if image:
            job = Job.objects.create(
                author=user,  # Set the author to the logged-in user
                category=category,
                description=data['description'],
                image=image,  # Use the main image
                website_url=data.get('website_url', ''),
                whatsapp_number=data.get('whatsapp_number', ''),
                facebook_url=data.get('facebook_url', ''),
                location=data.get('location', ''),
                twitter_url=data.get('twitter_url', ''),
                playstore_url=data.get('playstore_url', ''),
                linkedin_url=data.get('linkedin_url', ''),
                instagram_url=data.get('instagram_url', ''),
                pinterest_url=data.get('pinterest_url', ''),
                youtube_url=data.get('youtube_url', ''),
            )
            
            return redirect('joblistview')  # Make sure the URL name is correct
        else:
            error_message = "Please upload the main image."
            context = {'categories': categories, 'error_message': error_message}
            return render(request, 'jobs/addJob.html', context)

    context = {'categories': categories}
    return render(request, 'jobs/addJob.html', context)


#apply job 
def applyJob(request, job_id):
    # Redirect user if not logged in
    if not request.user.is_authenticated:
        messages.warning(request, "You need to register or log in before applying for a job.")
        return redirect('register_selection')  # 👈 redirect to your actual register route name

    # ✅ Only runs if the user is logged in
    user = request.user
    job = get_object_or_404(Job, id=job_id)
    categories = user.category_set.all()  # safe to call now

    if request.method == 'POST':
        data = request.POST
        image = request.FILES.get('image')
        cv = request.FILES.get('cv')

        # Determine category (either existing or new)
        if data.get('category') and data['category'] != 'none':
            category = Category.objects.get(id=data['category'])
        elif data.get('category_new'):
            category, created = Category.objects.get_or_create(
                user=user,
                name=data['category_new']
            )
        else:
            category = job.category  # fallback to the job's category

        # Validate uploads
        if image and cv:
            ApplyJob.objects.create(
                category=category,
                full_names=data.get('full_names', ''),
                age=data.get('age', ''),
                address=data.get('address', ''),
                qualifications=data.get('qualifications', ''),
                motivation=data.get('motivation', ''),
                recent_jobs=data.get('recent_jobs', ''),
                position=data.get('position', ''),
                marital_status=data.get('marital_status', ''),
                experience=data.get('experience', ''),
                contacts=data.get('contacts', ''),
                whatsapp_no=data.get('whatsapp_no', ''),
                image=image,
                cv=cv,
            )
            messages.success(request, f"You have successfully applied for '{job.description}'!")

            # ✅ redirect to your applicationview page
            return redirect('applicationview')

        else:
            error_message = "Please upload both an image and your CV."
            context = {'categories': categories, 'job': job, 'error_message': error_message}
            return render(request, 'jobs/apply.html', context)

    context = {'categories': categories, 'job': job}
    return render(request, 'jobs/apply.html', context)

#applicationview
def applicationview(request):
    user = request.user

    # Redirect to register if user is not logged in
    if not user.is_authenticated:
        return redirect('login_page')  # change 'register' to your registration URL name

    # Superuser or specific roles see all applications
    if user.is_superuser or user.user_type in ['1','2','4','6','9']:
        applyjobs = ApplyJob.objects.all().order_by('-created_at')
    else:
        applyjobs = ApplyJob.objects.filter(user=user).order_by('-created_at')

    context = {'applyjobs': applyjobs, 'user': user}
    return render(request, 'jobs/applicationview.html', context)

#delete application image
def deleteApplicationJob(request, pk):
    applyjobs = ApplyJob.objects.get(id=pk)
    if len(applyjobs.image) > 0:
        os.remove(applyjobs.image.path)
    applyjobs.delete()
    messages.success(request,"Product Deleted Successfuly")
    return redirect('joblistview')

#edit job application
def edit_application(request, pk):
    application = get_object_or_404(ApplyJob, pk=pk)

    # Only owner or superuser/admin roles can edit
    if request.user != application.user and not request.user.is_superuser:
        return redirect('applicationview')

    if request.method == 'POST':
        # Update all fields manually
        application.full_names = request.POST.get('full_names', application.full_names)
        application.age = request.POST.get('age', application.age)
        application.address = request.POST.get('address', application.address)
        application.qualifications = request.POST.get('qualifications', application.qualifications)
        application.motivation = request.POST.get('motivation', application.motivation)
        application.recent_jobs = request.POST.get('recent_jobs', application.recent_jobs)
        application.position = request.POST.get('position', application.position)
        application.marital_status = request.POST.get('marital_status', application.marital_status)
        application.experience = request.POST.get('experience', application.experience)
        application.contacts = request.POST.get('contacts', application.contacts)
        application.whatsapp_no = request.POST.get('whatsapp_no', application.whatsapp_no)
        category_id = request.POST.get('category')
        if category_id:
            application.category_id = category_id

        # Handle image upload
        if 'image' in request.FILES:
            application.image = request.FILES['image']

        # Handle CV upload
        if 'cv' in request.FILES:
            application.cv = request.FILES['cv']

        application.save()
        return redirect('applicationview')

    categories = Category.objects.all()
    return render(request, 'jobs/edit_application.html', {'application': application, 'categories': categories})

#gallery
def jobgallery(request):
    user = request.user
    category = request.GET.get('category')
    if category == None:
        applyjobs = ApplyJob.objects.filter(category__user=user)
    else:
        applyjobs = ApplyJob.objects.filter(
            category__name=category, category__user=user)

    categories = Category.objects.filter(user=user)
    context = {'categories': categories, 'applyjobs': applyjobs}
    return render(request, 'jobs/jobgallery.html', context)

#view job

def viewJob(request, pk):
    applyjob = ApplyJob.objects.get(id=pk)
    return render(request, 'jobs/applyjob.html', {'applyjob': applyjob})


#job application ends.................

#galleryview
def jobgalleryview(request):
	jobs = Job.objects.all()
	context = {'jobs': jobs}
	template = 'jobs/joblistview.html'	
	return render(request, template, context)

#delete gallery image
def deleteJob(request, pk):
    jobs = Job.objects.get(id=pk)
    if len(jobs.image) > 0:
        os.remove(jobs.image.path)
    jobs.delete()
    messages.success(request,"Product Deleted Successfuly")
    return redirect('joblistview')

#jobcategory view
def JobCategoryView(request, category):
    user = request.user
    category_posts = Post.objects.filter(user=user)
    return render(request, 'job/category.html', { category_posts : category_posts})


# views.py
def job_detail(request, job_id):
    job = Job.objects.get(id=job_id)
    return render(request, 'jobs/job_detail.html', {'job': job})


# upload jobs with ecvell
def upload_jobs_from_excel(request):
    if request.method == 'POST':
        form = UploadExcelForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            try:
                df = pd.read_excel(excel_file)

                # Replace NaN with empty string
                df = df.replace({np.nan: ""})

                required_fields = ["description", "author"]
                for field in required_fields:
                    if field not in df.columns:
                        messages.error(request, f"❌ Missing required column '{field}' in Excel.")
                        return redirect("upload_jobs_excel")

                count = 0
                for _, row in df.iterrows():
                    
                    # ✅ Handle author (must exist)
                    author_email = row.get("author")
                    author = CustomUser.objects.filter(email=author_email).first()
                    if not author:
                        continue  # skip row if no valid author

                    # ✅ Handle category (auto-create if not found)
                    category_name = row.get("category")
                    category = None
                    if isinstance(category_name, str) and category_name.strip():
                        category, _ = Category.objects.get_or_create(name=category_name.strip())

                    # ✅ Create job
                    Job.objects.create(
                        category=category,
                        author=author,
                        image=row.get("image"),  # image must be manually uploaded into media folder
                        video=row.get("video"),
                        website_url=row.get("website_url"),
                        whatsapp_number=row.get("whatsapp_number"),
                        facebook_url=row.get("facebook_url"),
                        zoom_url=row.get("zoom_url"),
                        microsoftTeam_url=row.get("microsoftTeam_url"),
                        location=row.get("location"),
                        twitter_url=row.get("twitter_url"),
                        playstore_url=row.get("playstore_url"),
                        linkedin_url=row.get("linkedin_url"),
                        instagram_url=row.get("instagram_url"),
                        pinterest_url=row.get("pinterest_url"),
                        youtube_url=row.get("youtube_url"),
                        description=row.get("description"),
                    )

                    count += 1

                messages.success(request, f"✅ {count} jobs uploaded successfully!")
                return redirect("jobs_list")

            except Exception as e:
                messages.error(request, f"❌ Error importing file: {e}")
    
    else:
        form = UploadExcelForm()

    return render(request, 'jobs/upload_excel.html', {'form': form})
