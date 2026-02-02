# views.py - Fixed to work with your new models
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.db.models import Count, Q, F
from django.core.paginator import Paginator
from application.tasks import start_automation_task
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
import json
import logging
import re
import uuid
import os
from datetime import datetime, timedelta
import csv

# Import your application models
from .models import *
# Import your existing models
try:
    from college.models import CollegeAndUniversities
    HAS_COLLEGE_APP = True
except ImportError:
    HAS_COLLEGE_APP = False
    CollegeAndUniversities = None

try:
    from bursary.models import Bursary
    HAS_BURSARY_APP = True
except ImportError:
    HAS_BURSARY_APP = False
    Bursary = None

logger = logging.getLogger(__name__)

# ===== FIXED EXISTING VIEWS =====
# Add these imports at the top of your views.py
import openai
import anthropic
from django.core.cache import cache

# ===== AI TESTING VIEWS =====

@login_required
def test_ai(request):
    """Test AI service page"""
    # Get available AI services
    ai_services = AIService.objects.filter(is_active=True)
    
    # Get recent test results from session
    test_results = request.session.get('ai_test_results', [])
    
    context = {
        'ai_services': ai_services,
        'test_results': test_results[:5],  # Last 5 tests
        'page_title': 'Test AI Services'
    }
    return render(request, 'applications/test_ai.html', context)


@login_required
@csrf_exempt
def run_ai_test(request):
    """Run a test on an AI service"""
    if request.method == 'POST':
        try:
            service_id = request.POST.get('service_id')
            test_prompt = request.POST.get('prompt', 'Hello, please respond with "AI is working"')
            
            if not service_id:
                messages.error(request, 'Please select an AI service')
                return redirect('test_ai')
            
            service = AIService.objects.get(id=service_id, is_active=True)
            
            # Check rate limits
            if not service.can_make_request():
                messages.error(request, f'Rate limit exceeded for {service.name}. Please wait a minute.')
                return redirect('test_ai')
            
            # Run the test
            result = test_ai_service(service, test_prompt)
            
            # Store result in session
            test_results = request.session.get('ai_test_results', [])
            test_results.append({
                'timestamp': timezone.now().isoformat(),
                'service': service.name,
                'prompt': test_prompt,
                'response': result.get('response', ''),
                'success': result.get('success', False),
                'error': result.get('error', '')
            })
            request.session['ai_test_results'] = test_results[-10:]  # Keep last 10
            
            if result.get('success'):
                messages.success(request, f'AI test successful! {service.name} is working.')
            else:
                messages.error(request, f'AI test failed: {result.get("error")}')
                
        except AIService.DoesNotExist:
            messages.error(request, 'AI service not found or inactive')
        except Exception as e:
            messages.error(request, f'Error testing AI: {str(e)}')
    
    return redirect('test_ai')


def test_ai_service(service, prompt):
    """Helper function to test an AI service"""
    try:
        if service.provider == 'openai':
            client = openai.OpenAI(
                api_key=service.api_key,
                base_url=service.base_url if service.base_url else None
            )
            
            response = client.chat.completions.create(
                model=service.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1
            )
            
            result = {
                'success': True,
                'response': response.choices[0].message.content.strip(),
                'tokens_used': response.usage.total_tokens if response.usage else 50
            }
            
        elif service.provider == 'anthropic':
            client = anthropic.Anthropic(api_key=service.api_key)
            
            response = client.messages.create(
                model=service.model_name,
                max_tokens=100,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = {
                'success': True,
                'response': response.content[0].text.strip(),
                'tokens_used': 100
            }
            
        else:
            result = {
                'success': False,
                'error': f'Provider {service.provider} not implemented'
            }
        
        # Record usage if successful
        if result.get('success'):
            service.total_requests += 1
            service.total_tokens += result.get('tokens_used', 0)
            service.last_used = timezone.now()
            service.save()
            
            # Update cache for rate limiting
            cache_key = f"ai_service_{service.id}_minute_count"
            current = cache.get(cache_key, 0)
            cache.set(cache_key, current + 1, 60)
        
        return result
        
    except Exception as e:
        logger.error(f"AI test error for {service.name}: {e}")
        return {
            'success': False,
            'error': str(e)
        }


@login_required
def test_application_ai(request, pk):
    """Test AI on a specific application"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    # Check if we have an AI service
    ai_service = application.get_ai_service()
    
    if not ai_service:
        messages.error(request, 'No active AI service available for this application')
        return redirect('viewApplication', pk=pk)
    
    if request.method == 'POST':
        try:
            # Test with application data
            test_prompt = f"""
            Please analyze this university application data:
            
            Student: {application.student}
            University: {application.university_name}
            Course: {application.course_faculty}
            Email: {application.email}
            Phone: {application.phone}
            
            Based on this information, suggest:
            1. Any missing information
            2. Potential improvements
            3. Formatting suggestions for the actual application
            """
            
            result = test_ai_service(ai_service, test_prompt)
            
            if result.get('success'):
                # Save the analysis
                application.notes = f"AI Analysis ({timezone.now().strftime('%Y-%m-%d %H:%M')}):\n{result['response']}\n\n{application.notes}"
                application.save()
                
                messages.success(request, 'AI analysis completed and saved to application notes')
            else:
                messages.error(request, f'AI analysis failed: {result.get("error")}')
                
        except Exception as e:
            messages.error(request, f'Error running AI analysis: {str(e)}')
    
    context = {
        'application': application,
        'ai_service': ai_service,
        'page_title': f'Test AI on {application.student}\'s Application'
    }
    return render(request, 'applications/test_application_ai.html', context)


@login_required
@csrf_exempt
def api_quick_ai_test(request):
    """Quick AI test endpoint (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service_id = data.get('service_id')
            prompt = data.get('prompt', 'Say "AI is working" in a creative way')
            
            if not service_id:
                return JsonResponse({'success': False, 'error': 'Service ID required'})
            
            service = AIService.objects.get(id=service_id, is_active=True)
            
            # Check rate limits
            if not service.can_make_request():
                return JsonResponse({
                    'success': False, 
                    'error': 'Rate limit exceeded. Try again in a minute.'
                })
            
            # Run test
            result = test_ai_service(service, prompt)
            
            return JsonResponse(result)
            
        except AIService.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'AI service not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def ai_health_check(request):
    """Check health of all AI services"""
    if not request.user.is_staff:
        messages.error(request, 'Only staff can view AI health check')
        return redirect('dashboard')
    
    services = AIService.objects.all()
    health_results = []
    
    for service in services:
        # Simple connectivity test
        test_prompt = "Respond with 'OK' only"
        result = test_ai_service(service, test_prompt)
        
        health_results.append({
            'service': service,
            'status': 'active' if result.get('success') else 'inactive',
            'last_test': timezone.now(),
            'error': result.get('error'),
            'response': result.get('response')
        })
    
    context = {
        'health_results': health_results,
        'page_title': 'AI Services Health Check'
    }
    return render(request, 'applications/ai_health_check.html', context)


@login_required
def clear_ai_cache(request):
    """Clear AI rate limiting cache (admin only)"""
    if not request.user.is_staff:
        messages.error(request, 'Only staff can clear AI cache')
        return redirect('dashboard')
    
    # Clear all AI service cache keys
    for service in AIService.objects.all():
        cache_key = f"ai_service_{service.id}_minute_count"
        cache.delete(cache_key)
    
    messages.success(request, 'AI rate limiting cache cleared')
    return redirect('ai_services')


def gallery(request):
    """Your existing gallery view - FIXED for new models"""
    user = request.user
    university_filter = request.GET.get('university')
    
    # Get applications for the current user
    applications = Application.objects.filter(user=user)
    
    # Apply university filter if provided
    if university_filter:
        applications = applications.filter(
            Q(selected_university__title__icontains=university_filter) |
            Q(university_manual__icontains=university_filter)
        )
    
    # Get unique universities for the user (for filter dropdown)
    universities = []
    try:
        # Get universities from applications
        uni_ids = applications.exclude(selected_university__isnull=True).values_list('selected_university', flat=True).distinct()
        if uni_ids:
            universities = CollegeAndUniversities.objects.filter(id__in=uni_ids)
    except:
        pass
    
    context = {
        'universities': universities, 
        'applications': applications,
        'page_title': 'Application Gallery'
    }
    return render(request, 'applications/applicationgallery.html', context)


def viewApplication(request, pk):
    """View application details"""
    try:
        application = Application.objects.get(id=pk)
        # Check if user owns this application or is staff
        if not request.user.is_staff and application.user != request.user:
            messages.error(request, "You don't have permission to view this application.")
            return redirect('gallery')
            
        context = {
            'application': application,
            'page_title': f'Application: {application.student}'
        }
        return render(request, 'applications/application.html', context)
    except Application.DoesNotExist:
        messages.error(request, "Application not found.")
        return redirect('gallery')



@login_required
def addApplication(request):
    """Add new application with multiple university selection and redirect to upload documents"""

    universities = []
    bursaries = []

    if HAS_COLLEGE_APP:
        universities = CollegeAndUniversities.objects.all()[:50]

    if HAS_BURSARY_APP:
        bursaries = Bursary.objects.all()[:50]

    if request.method == 'POST':
        try:
            data = request.POST

            # Debug: Log received data
            logger.info(f"Received application data: {dict(data)}")
            logger.info(f"FILES received: {list(request.FILES.keys())}")

            # Prepare application data with defaults
            application_data = {
                'user': request.user,
                'student': data.get('student', '').strip(),
                'email': data.get('email', '').strip(),
                'id_number': data.get('id_number', '').strip(),
                'gender': data.get('gender', '').strip(),
                'phone': data.get('phone', '').strip(),
                'address': data.get('address', '').strip(),
                'school_name': data.get('school_name', '').strip(),
                'course_faculty': data.get('course_faculty', '').strip(),
                'disability': data.get('disability', '').strip(),
                'details': data.get('details', '').strip(),
                'university_manual': data.get('university_manual', '').strip(),
                'bursary_manual': data.get('bursary_manual', '').strip(),
                'next_of_kin': data.get('next_of_kin', '').strip(),
                'target_form_url': data.get('target_form_url', '').strip(),
                'status': Application.Status.DRAFT,
                'automation_status': Application.Status.DRAFT
            }

            # Handle date fields
            date_of_birth = data.get('date_of_birth', '').strip()
            if date_of_birth:
                try:
                    application_data['date_of_birth'] = date_of_birth
                except ValueError as e:
                    logger.warning(f"Invalid date format for date_of_birth: {date_of_birth} - {e}")

            # Handle matric year
            matric_year = data.get('matric_year', '').strip()
            if matric_year and matric_year.isdigit():
                try:
                    application_data['matric_year'] = int(matric_year)
                except ValueError as e:
                    logger.warning(f"Invalid matric_year: {matric_year} - {e}")

            # 1️⃣ Create application
            application = Application.objects.create(**application_data)
            logger.info(f"Created application ID: {application.id}")

            # 2️⃣ UNIVERSITY SELECTION - NOW SUPPORTS MULTIPLE
            # ====================================================
            
            # Handle multiple university selection from checkboxes
            university_ids = request.POST.getlist('selected_universities[]')
            manual_university = data.get('university_manual', '').strip()
            
            university_selected = False
            
            if university_ids and HAS_COLLEGE_APP:
                try:
                    # Filter out empty strings and 'none'
                    university_ids = [uid for uid in university_ids if uid and uid != 'none']
                    
                    if university_ids:
                        universities_list = CollegeAndUniversities.objects.filter(id__in=university_ids)
                        
                        # Set multiple universities
                        application.universities.set(universities_list)
                        
                        # Also set the primary selected university (first one for backward compatibility)
                        if universities_list.exists():
                            application.selected_university = universities_list.first()
                        
                        application.university_manual = ''  # Clear manual if we selected from list
                        university_selected = True
                        
                        logger.info(f"Selected {universities_list.count()} universities: {[u.title for u in universities_list]}")
                        
                        # Auto-set target URL from first university
                        first_university = universities_list.first()
                        if first_university and first_university.website_url and not application.target_form_url:
                            base_url = first_university.website_url
                            if 'apply' not in base_url and 'application' not in base_url:
                                application.target_form_url = f"{base_url.rstrip('/')}/apply"
                            else:
                                application.target_form_url = base_url
                            logger.info(f"Auto-set target URL: {application.target_form_url}")
                except (ValueError, CollegeAndUniversities.DoesNotExist) as e:
                    logger.warning(f"Error processing university IDs {university_ids}: {e}")
                    # If university not found, check if manual entry exists
                    if manual_university:
                        application.university_manual = manual_university
                        university_selected = True
                        logger.info(f"Using manual university entry: {manual_university}")
            
            # If no selection from list but manual entry exists, use manual
            elif manual_university and not university_selected:
                application.university_manual = manual_university
                university_selected = True
                logger.info(f"Using manual university (no selection from list): {manual_university}")
            
            # If no universities selected at all, set a default message
            if not university_selected:
                logger.warning("No universities selected for application")
                messages.info(request, "No universities selected. You can add universities later when editing the application.")

            # 3️⃣ BURSARIES (ManyToMany - can select multiple)
            bursary_ids = request.POST.getlist('selected_bursaries[]')
            if bursary_ids and HAS_BURSARY_APP:
                try:
                    # Filter out empty strings
                    bursary_ids = [bid for bid in bursary_ids if bid and bid.strip()]
                    if bursary_ids:
                        bursaries_list = Bursary.objects.filter(id__in=bursary_ids)
                        application.selected_bursaries.set(bursaries_list)
                        logger.info(f"Added {bursaries_list.count()} bursaries to application")
                except (ValueError, Bursary.DoesNotExist) as e:
                    logger.warning(f"Error processing bursary IDs {bursary_ids}: {e}")

            # 4️⃣ Profile image
            if 'profile_image' in request.FILES:
                try:
                    profile_image = request.FILES['profile_image']
                    # Validate image
                    if profile_image.size > 5 * 1024 * 1024:  # 5MB limit
                        messages.warning(request, "Profile image is too large. Max size is 5MB.")
                    elif not profile_image.content_type.startswith('image/'):
                        messages.warning(request, "Please upload a valid image file.")
                    else:
                        application.profile_image = profile_image
                        logger.info(f"Profile image uploaded: {profile_image.name}")
                except Exception as e:
                    logger.error(f"Error uploading profile image: {e}")
                    messages.warning(request, "There was an issue with your profile image upload.")

            # 5️⃣ Introduction video (optional)
            if 'introduction_video' in request.FILES:
                try:
                    introduction_video = request.FILES['introduction_video']
                    # Validate video
                    if introduction_video.size > 50 * 1024 * 1024:  # 50MB limit
                        messages.warning(request, "Introduction video is too large. Max size is 50MB.")
                    elif not introduction_video.content_type.startswith('video/'):
                        messages.warning(request, "Please upload a valid video file.")
                    else:
                        application.introduction_video = introduction_video
                        logger.info(f"Introduction video uploaded: {introduction_video.name}")
                except Exception as e:
                    logger.error(f"Error uploading introduction video: {e}")
                    messages.warning(request, "There was an issue with your introduction video upload.")

            # 6️⃣ Parse and save additional details
            try:
                # Trigger the save method which will auto-parse details
                application.save()
                
                # Log parsed data for debugging
                if application.email:
                    logger.info(f"Extracted email: {application.email}")
                if application.phone:
                    logger.info(f"Extracted phone: {application.phone}")
                if application.id_number:
                    logger.info(f"Extracted ID: {application.id_number}")
                    
            except Exception as e:
                logger.error(f"Error saving application details: {e}")

            # 7️⃣ Success message + redirect
            success_message = "Your application was submitted successfully. "
            
            # Add university-specific message
            university_count = application.universities.count()
            if university_count > 0:
                if university_count == 1:
                    university = application.universities.first()
                    success_message += f"You applied to {university.title}. "
                else:
                    university_names = ", ".join([u.title for u in application.universities.all()])
                    success_message += f"You applied to {university_count} universities: {university_names}. "
            elif application.university_manual:
                success_message += f"You applied to {application.university_manual}. "
            
            # Add bursary message
            bursary_count = application.selected_bursaries.count()
            if bursary_count > 0:
                success_message += f"You selected {bursary_count} bursary{'s' if bursary_count > 1 else ''}. "
            
            success_message += "You can now upload your documents."
            
            messages.success(request, success_message)
            
            logger.info(f"Application {application.id} created successfully for user {request.user.username}")
            
            return redirect('uploadfile', application_id=application.pk)

        except Exception as e:
            logger.exception(f"Application creation failed: {e}")
            error_message = "Something went wrong while creating your application. "
            
            # User-friendly error messages
            if "student" in str(e).lower():
                error_message += "Please check the student name field."
            elif "email" in str(e).lower():
                error_message += "Please check the email address."
            elif "address" in str(e).lower():
                error_message += "Please check the address field."
            elif "required" in str(e).lower():
                error_message += "Please fill in all required fields."
            else:
                error_message += "Please try again or contact support if the problem persists."
            
            messages.error(request, error_message)
            
            # Return form with existing data
            return render(
                request,
                'applications/addapplication.html',
                {
                    'universities': universities,
                    'bursaries': bursaries,
                    'page_title': 'Add New Application',
                    'form_data': request.POST,
                    'preserved_files': list(request.FILES.keys()) if request.FILES else []
                }
            )

    # GET request - show empty form
    return render(
        request,
        'applications/addapplication.html',
        {
            'universities': universities,
            'bursaries': bursaries,
            'page_title': 'Add New Application'
        }
    )


def galleryview(request):
    """List all applications (admin/staff view)"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to view all applications.")
        return redirect('gallery')
    
    applications = Application.objects.all().order_by('-created_at')
    
    # Add pagination
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'applications': page_obj,
        'page_obj': page_obj,
        'page_title': 'All Applications'
    }
    return render(request, 'applications/listview.html', context)


@login_required
def deleteApplication(request, pk):
    """Delete application"""
    try:
        application = Application.objects.get(id=pk)
        
        # Check permission
        if not request.user.is_staff and application.user != request.user:
            messages.error(request, "You don't have permission to delete this application.")
            return redirect('gallery')
        
        # Delete associated files
        if application.profile_image:
            try:
                if os.path.exists(application.profile_image.path):
                    os.remove(application.profile_image.path)
            except Exception as e:
                logger.error(f"Error deleting profile image: {e}")
        
        if application.introduction_video:
            try:
                if os.path.exists(application.introduction_video.path):
                    os.remove(application.introduction_video.path)
            except Exception as e:
                logger.error(f"Error deleting video: {e}")
        
        # Delete the application
        student_name = application.student
        application.delete()
        
        messages.success(request, f"Application for {student_name} deleted successfully!")
        
    except Application.DoesNotExist:
        messages.error(request, "Application not found.")
    except Exception as e:
        logger.error(f"Error deleting application: {e}")
        messages.error(request, f"Error deleting application: {str(e)}")
    
    return redirect('gallery')


# ===== NEW AUTOMATION VIEWS =====

@login_required
def dashboard(request):
    """Main dashboard with statistics and overview"""
    
    # Get user's applications
    applications = Application.objects.filter(user=request.user)
    
    # Statistics
    total_applications = applications.count()
    draft_applications = applications.filter(status=Application.Status.DRAFT).count()
    ready_applications = applications.filter(status=Application.Status.READY).count()
    submitted_applications = applications.filter(status=Application.Status.SUBMITTED).count()
    
    # Recent applications
    recent_applications = applications.order_by('-created_at')[:5]
    
    # Automation statistics
    successful_automations = applications.filter(
        automation_status=Application.Status.COMPLETED
    ).count()
    
    failed_automations = applications.filter(
        automation_status=Application.Status.FAILED
    ).count()
    
    # AI services status
    ai_services = AIService.objects.filter(is_active=True)
    
    context = {
        'total_applications': total_applications,
        'draft_applications': draft_applications,
        'ready_applications': ready_applications,
        'submitted_applications': submitted_applications,
        'successful_automations': successful_automations,
        'failed_automations': failed_automations,
        'recent_applications': recent_applications,
        'ai_services': ai_services,
        'page_title': 'Dashboard',
    }
    
    return render(request, 'applications/dashboard.html', context)


@login_required
def my_applications(request):
    """List all user's applications with filtering"""
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    university_filter = request.GET.get('university', '')
    search_query = request.GET.get('q', '')
    
    # Base queryset
    applications = Application.objects.filter(user=request.user)
    
    # Apply filters
    if status_filter != 'all':
        applications = applications.filter(status=status_filter)
    
    if university_filter:
        applications = applications.filter(
            Q(selected_university__title__icontains=university_filter) |
            Q(university_manual__icontains=university_filter)
        )
    
    if search_query:
        applications = applications.filter(
            Q(student__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(course_faculty__icontains=search_query)
        )
    
    # Order and paginate
    applications = applications.order_by('-created_at')
    paginator = Paginator(applications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique universities for filter dropdown
    universities = []
    if HAS_COLLEGE_APP:
        universities = CollegeAndUniversities.objects.all()[:20]
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'university_filter': university_filter,
        'search_query': search_query,
        'universities': universities,
        'status_choices': Application.Status.choices,
        'page_title': 'My Applications',
    }
    
    return render(request, 'applications/my_applications.html', context)


#edit applications
@login_required
def edit_application(request, pk):
    """Edit an existing application with multiple university support"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            # Update basic fields
            application.student = request.POST.get('student', application.student)
            application.address = request.POST.get('address', application.address)
            application.disability = request.POST.get('disability', application.disability)
            application.details = request.POST.get('details', application.details)
            application.next_of_kin = request.POST.get('next_of_kin', application.next_of_kin)
            application.target_form_url = request.POST.get('target_form_url', application.target_form_url)
            
            # Update contact fields
            application.email = request.POST.get('email', application.email)
            application.phone = request.POST.get('phone', application.phone)
            application.id_number = request.POST.get('id_number', application.id_number)
            
            # Update academic fields
            application.course_faculty = request.POST.get('course_faculty', application.course_faculty)
            application.school_name = request.POST.get('school_name', application.school_name)
            application.matric_year = request.POST.get('matric_year', application.matric_year)
            
            # Update personal details
            application.gender = request.POST.get('gender', application.gender)
            application.marital_status = request.POST.get('marital_status', application.marital_status)
            application.home_language = request.POST.get('home_language', application.home_language)
            application.citizenship = request.POST.get('citizenship', application.citizenship)
            application.race = request.POST.get('race', application.race)
            
            # Handle date of birth
            dob = request.POST.get('date_of_birth', '')
            if dob:
                try:
                    application.date_of_birth = dob
                except ValueError:
                    pass
            
            # ===== MULTIPLE UNIVERSITY SELECTION =====
            university_ids = request.POST.getlist('selected_universities[]')
            manual_university = request.POST.get('university_manual', '')
            
            if university_ids and university_ids != ['none'] and HAS_COLLEGE_APP:
                try:
                    # Filter out empty strings and 'none'
                    university_ids = [uid for uid in university_ids if uid and uid != 'none']
                    
                    if university_ids:
                        universities_list = CollegeAndUniversities.objects.filter(id__in=university_ids)
                        
                        # Set multiple universities
                        application.universities.set(universities_list)
                        
                        # Also set the primary selected university (first one for backward compatibility)
                        if universities_list.exists():
                            application.selected_university = universities_list.first()
                        
                        application.university_manual = ''  # Clear manual entry
                    else:
                        # Clear all universities if no selection
                        application.universities.clear()
                        application.selected_university = None
                        application.university_manual = manual_university
                        
                except CollegeAndUniversities.DoesNotExist:
                    application.universities.clear()
                    application.selected_university = None
                    application.university_manual = manual_university
            else:
                # No universities selected from list, use manual entry
                application.universities.clear()
                application.selected_university = None
                application.university_manual = manual_university
            
            # ===== BURSARY SELECTION =====
            bursary_ids = request.POST.getlist('selected_bursaries[]')
            if bursary_ids and HAS_BURSARY_APP:
                try:
                    bursaries_list = Bursary.objects.filter(id__in=bursary_ids)
                    application.selected_bursaries.set(bursaries_list)
                    application.bursary_manual = ''  # Clear manual entry
                except Exception as e:
                    logger.error(f"Error updating bursaries: {e}")
                    application.bursary_manual = request.POST.get('bursary_manual', '')
            else:
                application.selected_bursaries.clear()
                application.bursary_manual = request.POST.get('bursary_manual', '')
            
            # Handle file uploads
            if 'profile_image' in request.FILES:
                # Delete old file if exists
                if application.profile_image:
                    try:
                        if os.path.exists(application.profile_image.path):
                            os.remove(application.profile_image.path)
                    except Exception as e:
                        logger.error(f"Error deleting old profile image: {e}")
                application.profile_image = request.FILES['profile_image']
            
            if 'introduction_video' in request.FILES:
                # Delete old file if exists
                if application.introduction_video:
                    try:
                        if os.path.exists(application.introduction_video.path):
                            os.remove(application.introduction_video.path)
                    except Exception as e:
                        logger.error(f"Error deleting old video: {e}")
                application.introduction_video = request.FILES['introduction_video']
            
            # Update status
            new_status = request.POST.get('status', application.status)
            if new_status in dict(Application.Status.choices):
                application.status = new_status
            
            # Update automation settings
            ai_service_id = request.POST.get('preferred_ai_service')
            if ai_service_id and ai_service_id != 'none':
                try:
                    ai_service = AIService.objects.get(id=ai_service_id)
                    application.preferred_ai_service = ai_service
                except AIService.DoesNotExist:
                    pass
            
            # Save to trigger parsing
            application.save()
            
            messages.success(request, 'Application updated successfully!')
            
            # Redirect based on button clicked
            if 'save_and_automate' in request.POST:
                return redirect('start_automation', pk=application.pk)
            elif 'save_and_view' in request.POST:
                return redirect('viewApplication', pk=application.pk)
            else:
                return redirect('my_applications')
            
        except Exception as e:
            logger.error(f"Error updating application: {e}")
            messages.error(request, f'Error updating application: {str(e)}')
    
    # Get available universities and bursaries
    universities_list = []
    bursaries_list = []
    
    if HAS_COLLEGE_APP:
        universities_list = CollegeAndUniversities.objects.all()
    
    if HAS_BURSARY_APP:
        bursaries_list = Bursary.objects.all()
    
    # Get AI services for selection
    ai_services = AIService.objects.filter(is_active=True)
    
    context = {
        'application': application,
        'universities': universities_list,
        'bursaries': bursaries_list,
        'ai_services': ai_services,
        'status_choices': Application.Status.choices,
        'page_title': 'Edit Application',
    }
    
    return render(request, 'applications/edit_application.html', context)

# In your Application model, add this method:
def get_universities_list(self):
    """Get list of selected university names"""
    universities = []
    
    # Get from ManyToMany field
    if self.universities.exists():
        universities.extend([u.title for u in self.universities.all()])
    
    # Get from single selection (for backward compatibility)
    elif self.selected_university:
        universities.append(self.selected_university.title)
    
    # Get manual entry
    elif self.university_manual:
        universities.append(self.university_manual)
    
    return universities if universities else ["No university selected"]

@property
def university_names(self):
    """Get formatted string of university names"""
    return ", ".join(self.get_universities_list())

# Update the existing university_name property to use the first university
@property
def university_name(self):
    """Get primary university name"""
    universities = self.get_universities_list()
    return universities[0] if universities else "Not specified"


    
@login_required
def UniversityView(request):
    """University management view"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to manage universities.")
        return redirect('dashboard')
    
    universities = []
    if HAS_COLLEGE_APP:
        universities = CollegeAndUniversities.objects.all().order_by('title')
    
    context = {
        'universities': universities,
        'page_title': 'Universities'
    }
    return render(request, 'applications/university.html', context)


@login_required
def AddUniversityView(request):
    """Add new university"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to add universities.")
        return redirect('UniversityView')
    
    if request.method == 'POST':
        try:
            # This would create a new university in your college app
            # For now, we'll just show a message
            messages.info(request, "University addition would be handled by the college app.")
            return redirect('UniversityView')
        except Exception as e:
            messages.error(request, f"Error adding university: {str(e)}")
    
    context = {
        'page_title': 'Add University'
    }
    return render(request, 'applications/adduniversity.html', context)


#automate applications
@require_GET
def get_automation_preview(request, session_id):
    session = AutomationSession.objects.get(id=session_id)
    
    if not session.preview_image:
        return JsonResponse({"error": "No preview available"}, status=404)
    
    # Return the image file
    if os.path.exists(session.preview_image):
        return FileResponse(open(session.preview_image, 'rb'), content_type='image/png')
    
    
@login_required
def start_automation(request, pk):
    application = get_object_or_404(
        Application,
        pk=pk,
        user=request.user
    )

    # 🔒 CHECK 1: Target URL exists
    if not application.target_form_url:
        messages.error(
            request,
            "This application has no target form URL."
        )
        return redirect("application_detail", pk=application.pk)

    # 🔒 CHECK 2: Application status allows automation
    if application.status not in [
        Application.Status.DRAFT,
        Application.Status.READY,
        Application.Status.FAILED,
    ]:
        messages.warning(
            request,
            "This application cannot be automated in its current state."
        )
        return redirect("application_detail", pk=application.pk)

    # 🔒 CHECK 3: Prevent duplicate running sessions
    if AutomationSession.objects.filter(
        application=application,
        status__in=[
            Application.Status.ANALYZING,
            Application.Status.RUNNING,
        ]
    ).exists():
        messages.info(
            request,
            "Automation is already running for this application."
        )
        return redirect("automation_console", pk=application.pk)

    # 🔒 CHECK 4: AI service selection
    ai_service = application.ai_service
    if not ai_service:
        messages.error(
            request,
            "No AI service selected for this application."
        )
        return redirect("application_detail", pk=application.pk)

    # ✅ CREATE SESSION
    session = AutomationSession.objects.create(
        application=application,
        session_id=str(uuid.uuid4())[:8],
        ai_service=ai_service,
        target_url=application.target_form_url,
        status=Application.Status.ANALYZING,
        total_steps=10,
    )

    # 📝 LOG
    application.add_automation_log(
        "Browser automation queued",
        level="info"
    )

    # 🚀 START AUTOMATION (CELERY)
    start_automation_task.delay(session.id)

    messages.success(
        request,
        "Automation started successfully."
    )

    return redirect("automation_console", pk=application.pk)



@login_required
def automation_console(request, pk):
    """Main automation console interface"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    # Get latest automation session
    try:
        session = AutomationSession.objects.filter(application=application).latest('started_at')
    except AutomationSession.DoesNotExist:
        session = None
    
    # Get AI services for selection
    ai_services = AIService.objects.filter(is_active=True)
    
    # Get structured data for the AI
    structured_data = application.get_structured_data()
    
    # Get recent automation logs
    recent_logs = application.automation_log[-10:] if application.automation_log else []
    
    context = {
        'application': application,
        'session': session,
        'ai_services': ai_services,
        'structured_data': json.dumps(structured_data, indent=2),
        'recent_logs': recent_logs,
        'page_title': 'Automation Console',
    }
    
    return render(request, 'applications/automation_console.html', context)


@login_required
def ai_services(request):
    """List and manage AI services"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to manage AI services.")
        return redirect('dashboard')
    
    services = AIService.objects.all().order_by('priority', 'name')
    
    context = {
        'services': services,
        'page_title': 'AI Services Configuration',
    }
    
    return render(request, 'applications/ai_services.html', context)


@login_required
def add_ai_service(request):
    """Add a new AI service"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to add AI services.")
        return redirect('ai_services')
    
    if request.method == 'POST':
        try:
            service = AIService.objects.create(
                name=request.POST.get('name'),
                provider=request.POST.get('provider'),
                api_key=request.POST.get('api_key'),
                base_url=request.POST.get('base_url', ''),
                model_name=request.POST.get('model_name'),
                max_tokens=int(request.POST.get('max_tokens', 4000)),
                temperature=float(request.POST.get('temperature', 0.1)),
                is_active=request.POST.get('is_active') == 'on',
                priority=int(request.POST.get('priority', 1)),
                requests_per_minute=int(request.POST.get('requests_per_minute', 60)),
                requests_per_day=int(request.POST.get('requests_per_day', 1000)),
            )
            
            messages.success(request, f'AI service "{service.name}" added successfully!')
            return redirect('ai_services')
            
        except Exception as e:
            logger.error(f"Error adding AI service: {e}")
            messages.error(request, f'Error adding AI service: {str(e)}')
    
    # Provider choices
    provider_choices = [
        ('openai', 'OpenAI (GPT-4, GPT-3.5)'),
        ('anthropic', 'Anthropic (Claude)'),
        ('google', 'Google (Gemini)'),
        ('huggingface', 'Hugging Face'),
    ]
    
    context = {
        'provider_choices': provider_choices,
        'page_title': 'Add AI Service',
    }
    
    return render(request, 'applications/add_ai_service.html', context)


# ===== API ENDPOINTS =====

@login_required
@csrf_exempt
def api_application_data(request, pk):
    """API endpoint to get application data (for AJAX)"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    data = application.get_structured_data()
    return JsonResponse(data)


@login_required
@csrf_exempt
def api_update_field(request, pk):
    """API endpoint to update a single field (for AJAX)"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            field_name = data.get('field')
            value = data.get('value')
            
            if hasattr(application, field_name):
                setattr(application, field_name, value)
                application.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Field {field_name} updated successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Field {field_name} does not exist'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
@csrf_exempt
def api_validate_url(request):
    """API endpoint to validate a university form URL"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            url = data.get('url', '').strip()
            
            if not url:
                return JsonResponse({
                    'valid': False,
                    'error': 'URL is required'
                })
            
            # Basic URL validation
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(url):
                return JsonResponse({
                    'valid': False,
                    'error': 'Invalid URL format'
                })
            
            # Check for common university application keywords
            university_keywords = ['apply', 'application', 'admission', 'register', 'enroll']
            has_keyword = any(keyword in url.lower() for keyword in university_keywords)
            
            # Check for common university domains (South Africa)
            sa_university_domains = [
                'ac.za', '.edu', 'uct.ac.za', 'wits.ac.za', 'uj.ac.za',
                'up.ac.za', 'ukzn.ac.za', 'sun.ac.za', 'nwu.ac.za'
            ]
            has_university_domain = any(domain in url.lower() for domain in sa_university_domains)
            
            warnings = []
            if not has_keyword:
                warnings.append('URL does not contain common application keywords (apply, application, etc.)')
            
            if not has_university_domain:
                warnings.append('URL does not appear to be a South African university domain')
            
            return JsonResponse({
                'valid': True,
                'warnings': warnings,
                'has_keyword': has_keyword,
                'has_university_domain': has_university_domain
            })
            
        except Exception as e:
            return JsonResponse({
                'valid': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ===== ERROR HANDLERS =====

def handler404(request, exception):
    """Custom 404 handler"""
    return render(request, 'applications/404.html', status=404)


def handler500(request):
    """Custom 500 handler"""
    return render(request, 'applications/500.html', status=500)


# ===== HEALTH CHECK =====

def health_check(request):
    """Health check endpoint for monitoring"""
    try:
        # Check database
        Application.objects.count()
        
        # Check AI services
        active_services = AIService.objects.filter(is_active=True).count()
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'connected',
            'active_ai_services': active_services,
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        }, status=500)

# ===== IMPLEMENTED VIEWS =====

@login_required
def edit_ai_service(request, pk):
    """Edit an existing AI service"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to edit AI services.")
        return redirect('ai_services')
    
    service = get_object_or_404(AIService, pk=pk)
    
    if request.method == 'POST':
        try:
            service.name = request.POST.get('name')
            service.provider = request.POST.get('provider')
            
            # Only update API key if provided (not masked)
            new_api_key = request.POST.get('api_key')
            if new_api_key and new_api_key != '********':
                service.api_key = new_api_key
            
            service.base_url = request.POST.get('base_url', '')
            service.model_name = request.POST.get('model_name')
            service.max_tokens = int(request.POST.get('max_tokens', 4000))
            service.temperature = float(request.POST.get('temperature', 0.1))
            service.is_active = request.POST.get('is_active') == 'on'
            service.priority = int(request.POST.get('priority', 1))
            service.requests_per_minute = int(request.POST.get('requests_per_minute', 60))
            service.requests_per_day = int(request.POST.get('requests_per_day', 1000))
            
            service.save()
            
            messages.success(request, f'AI service "{service.name}" updated successfully!')
            return redirect('ai_services')
            
        except Exception as e:
            logger.error(f"Error updating AI service: {e}")
            messages.error(request, f'Error updating AI service: {str(e)}')
    
    # Provider choices
    provider_choices = [
        ('openai', 'OpenAI (GPT-4, GPT-3.5)'),
        ('anthropic', 'Anthropic (Claude)'),
        ('google', 'Google (Gemini)'),
        ('huggingface', 'Hugging Face'),
    ]
    
    # Mask API key for display
    masked_api_key = '********' if service.api_key else ''
    
    context = {
        'service': service,
        'provider_choices': provider_choices,
        'masked_api_key': masked_api_key,
        'page_title': f'Edit {service.name}',
    }
    
    return render(request, 'applications/edit_ai_service.html', context)


@login_required
def delete_ai_service(request, pk):
    """Delete an AI service"""
    if not request.user.is_staff:
        messages.error(request, "You don't have permission to delete AI services.")
        return redirect('ai_services')
    
    service = get_object_or_404(AIService, pk=pk)
    
    if request.method == 'POST':
        name = service.name
        
        # Check if any applications are using this service
        using_applications = Application.objects.filter(preferred_ai_service=service).count()
        using_sessions = AutomationSession.objects.filter(ai_service=service).count()
        
        if using_applications > 0 or using_sessions > 0:
            messages.error(request, 
                f'Cannot delete "{name}" because it is being used by {using_applications} applications '
                f'and {using_sessions} sessions. Change their AI service first.')
            return redirect('ai_services')
        
        service.delete()
        messages.success(request, f'AI service "{name}" deleted successfully!')
        return redirect('ai_services')
    
    # Get usage statistics
    using_applications = Application.objects.filter(preferred_ai_service=service).count()
    using_sessions = AutomationSession.objects.filter(ai_service=service).count()
    
    context = {
        'service': service,
        'using_applications': using_applications,
        'using_sessions': using_sessions,
        'page_title': 'Delete AI Service',
    }
    
    return render(request, 'applications/delete_ai_service.html', context)


@login_required
def select_university(request):
    """Select university from existing list (integration with college app)"""
    
    search_query = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    
    # Get universities from college app
    if HAS_COLLEGE_APP:
        universities = CollegeAndUniversities.objects.all()
        
        if search_query:
            universities = universities.filter(
                Q(title__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Paginate
        paginator = Paginator(universities, 20)
        try:
            universities_page = paginator.page(page)
        except:
            universities_page = paginator.page(1)
    else:
        universities_page = None
        messages.info(request, "College app not installed. Please install it to access universities.")
    
    context = {
        'universities_page': universities_page,
        'search_query': search_query,
        'has_college_app': HAS_COLLEGE_APP,
        'page_title': 'Select University',
    }
    
    return render(request, 'applications/select_university.html', context)


@login_required
def university_detail(request, pk):
    """View university details"""
    if not HAS_COLLEGE_APP:
        messages.error(request, "College app not installed.")
        return redirect('dashboard')
    
    university = get_object_or_404(CollegeAndUniversities, pk=pk)
    
    # Get applications for this university by current user
    applications = Application.objects.filter(
        user=request.user,
        selected_university=university
    ).order_by('-created_at')
    
    # Statistics
    total_applications = applications.count()
    draft_applications = applications.filter(status=Application.Status.DRAFT).count()
    submitted_applications = applications.filter(status=Application.Status.SUBMITTED).count()
    
    # Get similar universities
    similar_universities = CollegeAndUniversities.objects.filter(
        location=university.location
    ).exclude(id=university.id)[:5]
    
    context = {
        'university': university,
        'applications': applications[:10],  # Show only last 10
        'total_applications': total_applications,
        'draft_applications': draft_applications,
        'submitted_applications': submitted_applications,
        'similar_universities': similar_universities,
        'page_title': university.title,
    }
    
    return render(request, 'applications/university_detail.html', context)


@login_required
def select_bursary(request):
    """Select bursary from existing list (integration with bursary app)"""
    
    search_query = request.GET.get('q', '')
    bursary_type = request.GET.get('type', 'all')
    status_filter = request.GET.get('status', 'active')
    
    # Get bursaries from bursary app
    if HAS_BURSARY_APP:
        bursaries = Bursary.objects.all()
        
        if search_query:
            bursaries = bursaries.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(provider__icontains=search_query)
            )
        
        if bursary_type != 'all':
            bursaries = bursaries.filter(posted_as=bursary_type)
        
        # Filter by status
        today = timezone.now().date()
        if status_filter == 'active':
            bursaries = bursaries.filter(closing_date__gte=today)
        elif status_filter == 'expired':
            bursaries = bursaries.filter(closing_date__lt=today)
        
        bursaries = bursaries.order_by('-closing_date')
    else:
        bursaries = None
        messages.info(request, "Bursary app not installed. Please install it to access bursaries.")
    
    # Get unique types for filter
    bursary_types = []
    if HAS_BURSARY_APP:
        bursary_types = Bursary.objects.values_list('posted_as', flat=True).distinct()
    
    context = {
        'bursaries': bursaries,
        'search_query': search_query,
        'bursary_type': bursary_type,
        'status_filter': status_filter,
        'bursary_types': bursary_types,
        'has_bursary_app': HAS_BURSARY_APP,
        'page_title': 'Select Bursary',
    }
    
    return render(request, 'applications/select_bursary.html', context)


@login_required
def reports(request):
    """Generate reports and analytics"""
    
    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    report_type = request.GET.get('type', 'overview')
    
    # Base queryset
    applications = Application.objects.filter(user=request.user)
    
    # Apply date filter
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            applications = applications.filter(created_at__gte=start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            applications = applications.filter(created_at__lte=end)
        except ValueError:
            pass
    
    # Statistics based on report type
    stats = {}
    chart_data = {}
    
    if report_type == 'overview':
        stats = {
            'total': applications.count(),
            'by_status': dict(applications.values('status').annotate(count=Count('id')).values_list('status', 'count')),
            'by_automation_status': dict(applications.values('automation_status').annotate(count=Count('id')).values_list('automation_status', 'count')),
            'success_rate': 0,
        }
        
        # Calculate success rate
        successful = applications.filter(automation_status=Application.Status.COMPLETED).count()
        attempted = applications.filter(
            automation_status__in=[Application.Status.COMPLETED, Application.Status.FAILED]
        ).count()
        
        if attempted > 0:
            stats['success_rate'] = round((successful / attempted) * 100, 1)
    
    elif report_type == 'university':
        # Group by university
        university_stats = applications.values(
            'selected_university__title',
            'university_manual'
        ).annotate(
            count=Count('id'),
            submitted=Count('id', filter=Q(status=Application.Status.SUBMITTED)),
            automated=Count('id', filter=Q(automation_status=Application.Status.COMPLETED))
        ).order_by('-count')
        
        stats['university_stats'] = list(university_stats)
        
        # Chart data for universities
        chart_data = {
            'labels': [],
            'data': [],
        }
        for stat in university_stats[:10]:  # Top 10
            uni_name = stat['selected_university__title'] or stat['university_manual'] or 'Unknown'
            chart_data['labels'].append(uni_name[:20])  # Limit label length
            chart_data['data'].append(stat['count'])
    
    elif report_type == 'timeline':
        # Monthly trend
        monthly_data = applications.extra(
            select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"}
        ).values('month').annotate(
            count=Count('id'),
            submitted=Count('id', filter=Q(status=Application.Status.SUBMITTED))
        ).order_by('month')[:12]
        
        stats['monthly_data'] = list(monthly_data)
        
        # Chart data for timeline
        chart_data = {
            'labels': [item['month'] for item in monthly_data],
            'data': [item['count'] for item in monthly_data],
            'submitted': [item['submitted'] for item in monthly_data],
        }
    
    elif report_type == 'ai_usage':
        # AI usage statistics
        ai_stats = []
        total_tokens = 0
        total_cost = 0
        
        for service in AIService.objects.filter(is_active=True):
            service_apps = applications.filter(preferred_ai_service=service)
            ai_stats.append({
                'service': service,
                'applications_count': service_apps.count(),
                'requests': service.total_requests,
                'tokens': service.total_tokens,
                'last_used': service.last_used,
            })
            total_tokens += service.total_tokens
        
        # Rough cost estimation (varies by provider)
        # Assuming average cost: $0.01 per 1000 tokens
        if total_tokens > 0:
            total_cost = (total_tokens / 1000) * 0.01
        
        stats['ai_stats'] = ai_stats
        stats['total_tokens'] = total_tokens
        stats['estimated_cost'] = round(total_cost, 2)
    
    # Default today's date for date inputs
    today = datetime.now().strftime('%Y-%m-%d')
    default_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    context = {
        'stats': stats,
        'chart_data': json.dumps(chart_data),
        'start_date': start_date or default_start,
        'end_date': end_date or today,
        'report_type': report_type,
        'report_types': [
            ('overview', 'Overview'),
            ('university', 'By University'),
            ('timeline', 'Timeline'),
            ('ai_usage', 'AI Usage'),
        ],
        'page_title': 'Reports & Analytics',
    }
    
    return render(request, 'applications/reports.html', context)


@login_required
def export_applications(request):
    """Export applications as CSV"""
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    export_format = request.GET.get('format', 'csv')
    
    # Base queryset
    applications = Application.objects.filter(user=request.user)
    
    # Apply filters
    if status_filter != 'all':
        applications = applications.filter(status=status_filter)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            applications = applications.filter(created_at__gte=start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            applications = applications.filter(created_at__lte=end)
        except ValueError:
            pass
    
    if export_format == 'csv':
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="applications_export.csv"'
        
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow([
            'ID', 'Student Name', 'Email', 'Phone', 'University', 
            'Course/Faculty', 'Status', 'Automation Status', 'Created Date',
            'Submission Date', 'Address', 'ID Number', 'Date of Birth',
            'Gender', 'Marital Status', 'Home Language', 'Citizenship',
            'Race', 'School Name', 'Matric Year', 'Target Form URL',
            'Next of Kin', 'Disability', 'Notes'
        ])
        
        # Write data
        for app in applications:
            writer.writerow([
                app.pk,
                app.student,
                app.email or '',
                app.phone or '',
                app.university_name,
                app.course_faculty or '',
                app.get_status_display(),
                app.get_automation_status_display(),
                app.created_at.strftime('%Y-%m-%d %H:%M'),
                app.submission_date.strftime('%Y-%m-%d %H:%M') if app.submission_date else '',
                app.address or '',
                app.id_number or '',
                app.date_of_birth.strftime('%Y-%m-%d') if app.date_of_birth else '',
                app.gender or '',
                app.marital_status or '',
                app.home_language or '',
                app.citizenship or '',
                app.race or '',
                app.school_name or '',
                app.matric_year or '',
                app.target_form_url or '',
                app.next_of_kin or '',
                app.disability or '',
                (app.notes or '')[:100],  # Truncate notes
            ])
        
        return response
    
    elif export_format == 'json':
        # Create JSON response
        data = []
        for app in applications:
            data.append({
                'id': app.pk,
                'student': app.student,
                'email': app.email,
                'phone': app.phone,
                'university': app.university_name,
                'course_faculty': app.course_faculty,
                'status': app.status,
                'automation_status': app.automation_status,
                'created_at': app.created_at.isoformat(),
                'submission_date': app.submission_date.isoformat() if app.submission_date else None,
                'address': app.address,
                'id_number': app.id_number,
                'date_of_birth': app.date_of_birth.isoformat() if app.date_of_birth else None,
                'gender': app.gender,
                'marital_status': app.marital_status,
                'home_language': app.home_language,
                'citizenship': app.citizenship,
                'race': app.race,
                'school_name': app.school_name,
                'matric_year': app.matric_year,
                'target_form_url': app.target_form_url,
                'next_of_kin': app.next_of_kin,
                'disability': app.disability,
                'notes': app.notes,
                'progress_percentage': app.progress_percentage,
                'is_ready_for_automation': app.is_ready_for_automation,
            })
        
        response = JsonResponse(data, safe=False)
        response['Content-Disposition'] = 'attachment; filename="applications_export.json"'
        return response
    
    else:
        # Show export page with options
        today = datetime.now().strftime('%Y-%m-%d')
        default_start = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        context = {
            'status_choices': Application.Status.choices,
            'start_date': start_date or default_start,
            'end_date': end_date or today,
            'status_filter': status_filter,
            'total_applications': applications.count(),
            'page_title': 'Export Applications',
        }
        
        return render(request, 'applications/export_applications.html', context)


@login_required
def duplicate_application(request, pk):
    """Create a duplicate of an existing application"""
    original = get_object_or_404(Application, pk=pk, user=request.user)
    
    try:
        # Create a duplicate
        duplicate = Application.objects.create(
            user=request.user,
            student=original.student,
            address=original.address,
            disability=original.disability,
            details=original.details,
            next_of_kin=original.next_of_kin,
            email=original.email,
            phone=original.phone,
            id_number=original.id_number,
            date_of_birth=original.date_of_birth,
            gender=original.gender,
            marital_status=original.marital_status,
            home_language=original.home_language,
            citizenship=original.citizenship,
            race=original.race,
            course_faculty=original.course_faculty,
            school_name=original.school_name,
            matric_year=original.matric_year,
            target_form_url='',  # Clear URL for new application
            status=Application.Status.DRAFT,
            automation_status=Application.Status.DRAFT,
        )
        
        # Copy relationships
        if original.selected_university:
            duplicate.selected_university = original.selected_university
        duplicate.university_manual = original.university_manual
        
        # Copy bursaries
        duplicate.selected_bursaries.set(original.selected_bursaries.all())
        duplicate.bursary_manual = original.bursary_manual
        
        duplicate.save()
        
        messages.success(request, f'Application duplicated successfully! New application #{duplicate.pk}')
        return redirect('edit_application', pk=duplicate.pk)
        
    except Exception as e:
        logger.error(f"Error duplicating application: {e}")
        messages.error(request, f'Error duplicating application: {str(e)}')
        return redirect('my_applications')


@login_required
def automation_status(request, pk):
    """Check automation status (JSON endpoint for AJAX)"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    try:
        session = AutomationSession.objects.filter(application=application).latest('started_at')
    except AutomationSession.DoesNotExist:
        session = None
    
    response_data = {
        'application_id': application.pk,
        'status': application.automation_status,
        'progress': application.progress_percentage,
        'last_updated': application.last_automation_attempt.isoformat() if application.last_automation_attempt else None,
        'session': {
            'id': session.session_id if session else None,
            'status': session.status if session else None,
            'progress': session.progress_percentage if session else 0,
            'current_step': session.current_step if session else None,
            'started_at': session.started_at.isoformat() if session else None,
            'duration': str(session.duration) if session else None,
        } if session else None,
        'ai_service': {
            'name': application.preferred_ai_service.name if application.preferred_ai_service else None,
            'model': application.preferred_ai_service.model_name if application.preferred_ai_service else None,
        } if application.preferred_ai_service else None,
    }
    
    return JsonResponse(response_data)


@login_required
def stop_automation(request, pk):
    """Stop an ongoing automation"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Update application status
        application.update_automation_status(Application.Status.DRAFT, "Automation stopped by user")
        
        # Update session if exists
        try:
            session = AutomationSession.objects.filter(
                application=application, 
                status__in=[Application.Status.ANALYZING, Application.Status.FILLING]
            ).latest('started_at')
            session.status = Application.Status.FAILED
            session.ended_at = timezone.now()
            session.save()
            
            application.add_automation_log("Automation stopped by user", level='warning')
            
        except AutomationSession.DoesNotExist:
            pass
        
        messages.info(request, 'Automation stopped successfully.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        else:
            return redirect('automation_console', pk=application.pk)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def retry_automation(request, pk):
    """Retry a failed automation"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # Check if we can retry
        if application.automation_status not in [Application.Status.FAILED, Application.Status.DRAFT]:
            messages.error(request, 'Cannot retry automation in current state.')
            return redirect('automation_console', pk=application.pk)
        
        # Start new automation
        return redirect('start_automation', pk=application.pk)
    
    return redirect('automation_console', pk=application.pk)


@login_required
def automation_preview(request, pk):
    """Preview what the AI will do before execution"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    # Get AI service
    ai_service = application.get_ai_service()
    
    # Simulate what the AI would do
    # In a real implementation, this would call the AI to analyze the form
    
    preview_steps = [
        {
            'step': 1,
            'action': 'navigate',
            'description': f'Open {application.target_form_url}',
            'estimated_time': '5s'
        },
        {
            'step': 2,
            'action': 'analyze',
            'description': 'Analyze form structure and identify fields',
            'estimated_time': '10s'
        },
        {
            'step': 3,
            'action': 'map_fields',
            'description': 'Map application data to form fields',
            'estimated_time': '15s'
        },
        {
            'step': 4,
            'action': 'fill_personal',
            'description': f'Fill personal information: {application.student}',
            'estimated_time': '30s'
        },
        {
            'step': 5,
            'action': 'fill_contact',
            'description': f'Fill contact information: {application.email}, {application.phone}',
            'estimated_time': '20s'
        },
        {
            'step': 6,
            'action': 'fill_academic',
            'description': f'Fill academic information: {application.course_faculty}',
            'estimated_time': '25s'
        },
        {
            'step': 7,
            'action': 'handle_next',
            'description': 'Click next/continue buttons if multi-page form',
            'estimated_time': 'Variable'
        },
        {
            'step': 8,
            'action': 'review',
            'description': 'Wait for user review before submission',
            'estimated_time': 'User controlled'
        },
    ]
    
    context = {
        'application': application,
        'ai_service': ai_service,
        'preview_steps': preview_steps,
        'page_title': 'Automation Preview',
    }
    
    return render(request, 'applications/automation_preview.html', context)


@login_required
@csrf_exempt
def api_log_action(request, pk):
    """API endpoint to log automation actions (for AJAX)"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            level = data.get('level', 'info')
            step = data.get('step', '')
            screenshot = data.get('screenshot', '')
            
            if not message:
                return JsonResponse({
                    'success': False,
                    'error': 'Message is required'
                }, status=400)
            
            # Add log entry
            application.add_automation_log(message, level)
            
            # Update current step if provided
            if step:
                try:
                    session = AutomationSession.objects.filter(
                        application=application
                    ).latest('started_at')
                    session.current_step = step
                    session.save()
                except AutomationSession.DoesNotExist:
                    pass
            
            # Store screenshot if provided
            if screenshot and screenshot.startswith('data:image'):
                # Extract base64 image data
                import base64
                try:
                    # Format: data:image/png;base64,XXXXX
                    header, encoded = screenshot.split(',', 1)
                    image_data = base64.b64decode(encoded)
                    
                    # Take screenshot
                    application.take_screenshot(
                        screenshot_data=encoded[:500],  # Store first 500 chars
                        description=f"Step: {step}" if step else "Automation screenshot"
                    )
                except Exception as e:
                    logger.error(f"Error processing screenshot: {e}")
            
            # Get updated log
            recent_logs = application.automation_log[-5:] if application.automation_log else []
            
            return JsonResponse({
                'success': True,
                'message': 'Action logged successfully',
                'log_id': len(application.automation_log) - 1 if application.automation_log else 0,
                'timestamp': timezone.now().isoformat(),
                'recent_logs': recent_logs,
                'application_status': application.automation_status,
                'application_id': application.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error logging action: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    # GET request - return recent logs
    elif request.method == 'GET':
        try:
            limit = int(request.GET.get('limit', 20))
            level_filter = request.GET.get('level', '')
            
            logs = application.automation_log
            if not logs:
                logs = []
            
            # Apply filters
            filtered_logs = logs
            if level_filter:
                filtered_logs = [log for log in logs if log.get('level') == level_filter]
            
            # Limit results
            recent_logs = filtered_logs[-limit:] if filtered_logs else []
            
            return JsonResponse({
                'success': True,
                'logs': recent_logs,
                'total_logs': len(logs),
                'filtered_logs': len(filtered_logs),
                'application_status': application.automation_status,
                'last_updated': application.last_automation_attempt.isoformat() if application.last_automation_attempt else None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
@csrf_exempt
def api_automation_progress(request, pk):
    """API endpoint to update automation progress (for AJAX)"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            progress = data.get('progress', 0)
            step_description = data.get('step', '')
            completed_steps = data.get('completed_steps', 0)
            total_steps = data.get('total_steps', 0)
            status = data.get('status', '')
            field_mapping = data.get('field_mapping', {})
            filled_fields = data.get('filled_fields', [])
            errors = data.get('errors', [])
            
            # Validate progress
            try:
                progress = int(progress)
                if progress < 0 or progress > 100:
                    return JsonResponse({
                        'success': False,
                        'error': 'Progress must be between 0 and 100'
                    }, status=400)
            except (ValueError, TypeError):
                progress = 0
            
            # Update or create automation session
            try:
                session = AutomationSession.objects.filter(application=application).latest('started_at')
            except AutomationSession.DoesNotExist:
                session = AutomationSession.objects.create(
                    application=application,
                    session_id=str(uuid.uuid4())[:8],
                    target_url=application.target_form_url or '',
                    status=application.automation_status,
                    total_steps=total_steps or 10
                )
            
            # Update session
            if completed_steps:
                session.completed_steps = completed_steps
            
            if total_steps:
                session.total_steps = total_steps
            
            if step_description:
                session.current_step = step_description
            
            if status and status in dict(Application.Status.choices):
                session.status = status
                # Also update application automation status if it's a significant status change
                if status in [Application.Status.COMPLETED, Application.Status.FAILED, Application.Status.SUBMITTED]:
                    application.automation_status = status
                    application.save()
            
            if field_mapping:
                session.detected_fields = field_mapping
            
            if filled_fields:
                session.filled_fields = filled_fields
            
            if errors:
                session.errors = errors
            
            session.save()
            
            # Log progress update
            log_message = f"Progress: {progress}%"
            if step_description:
                log_message += f" - {step_description}"
            
            application.add_automation_log(log_message, level='info')
            
            # Update application's last automation attempt
            application.last_automation_attempt = timezone.now()
            application.save()
            
            return JsonResponse({
                'success': True,
                'progress': progress,
                'session_id': session.session_id,
                'current_step': session.current_step,
                'completed_steps': session.completed_steps,
                'total_steps': session.total_steps,
                'session_progress': session.progress_percentage,
                'status': session.status,
                'application_status': application.automation_status,
                'timestamp': timezone.now().isoformat()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    # GET request - return current progress
    elif request.method == 'GET':
        try:
            # Get latest session
            try:
                session = AutomationSession.objects.filter(application=application).latest('started_at')
                session_data = {
                    'id': session.session_id,
                    'status': session.status,
                    'progress': session.progress_percentage,
                    'current_step': session.current_step,
                    'completed_steps': session.completed_steps,
                    'total_steps': session.total_steps,
                    'started_at': session.started_at.isoformat(),
                    'duration': str(session.duration),
                    'detected_fields': session.detected_fields,
                    'filled_fields': session.filled_fields,
                    'errors': session.errors,
                    'target_url': session.target_url
                }
            except AutomationSession.DoesNotExist:
                session_data = None
            
            # Get recent logs
            recent_logs = application.automation_log[-10:] if application.automation_log else []
            
            # Calculate overall progress
            overall_progress = application.progress_percentage
            
            return JsonResponse({
                'success': True,
                'application': {
                    'id': application.id,
                    'student': application.student,
                    'university': application.university_name,
                    'status': application.status,
                    'automation_status': application.automation_status,
                    'progress_percentage': overall_progress,
                    'is_ready_for_automation': application.is_ready_for_automation,
                    'target_form_url': application.target_form_url,
                    'last_automation_attempt': application.last_automation_attempt.isoformat() if application.last_automation_attempt else None
                },
                'session': session_data,
                'recent_logs': recent_logs,
                'ai_service': {
                    'name': application.preferred_ai_service.name if application.preferred_ai_service else None,
                    'model': application.preferred_ai_service.model_name if application.preferred_ai_service else None,
                    'is_active': application.preferred_ai_service.is_active if application.preferred_ai_service else False
                } if application.preferred_ai_service else None,
                'structured_data': application.get_structured_data() if request.GET.get('full_data') == 'true' else None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    # PUT request - update specific fields
    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            
            # Get or create session
            try:
                session = AutomationSession.objects.filter(application=application).latest('started_at')
            except AutomationSession.DoesNotExist:
                session = AutomationSession.objects.create(
                    application=application,
                    session_id=str(uuid.uuid4())[:8],
                    target_url=application.target_form_url or '',
                    status=application.automation_status
                )
            
            # Update specific fields
            update_fields = {}
            
            if 'current_step' in data:
                session.current_step = data['current_step']
                update_fields['current_step'] = data['current_step']
            
            if 'completed_steps' in data:
                session.completed_steps = data['completed_steps']
                update_fields['completed_steps'] = data['completed_steps']
            
            if 'total_steps' in data:
                session.total_steps = data['total_steps']
                update_fields['total_steps'] = data['total_steps']
            
            if 'status' in data and data['status'] in dict(Application.Status.choices):
                session.status = data['status']
                update_fields['status'] = data['status']
                
                # Update application status for significant changes
                if data['status'] in [Application.Status.COMPLETED, Application.Status.FAILED, Application.Status.SUBMITTED]:
                    application.automation_status = data['status']
                    application.save()
            
            if 'detected_fields' in data:
                session.detected_fields = data['detected_fields']
                application.field_mapping = data['detected_fields']
                application.save()
                update_fields['detected_fields'] = data['detected_fields']
            
            if 'filled_fields' in data:
                session.filled_fields = data['filled_fields']
                update_fields['filled_fields'] = data['filled_fields']
            
            if 'errors' in data:
                session.errors = data['errors']
                update_fields['errors'] = data['errors']
            
            session.save()
            
            # Log the update
            if update_fields:
                application.add_automation_log(
                    f"Session updated: {', '.join(update_fields.keys())}",
                    level='info'
                )
            
            return JsonResponse({
                'success': True,
                'updated_fields': list(update_fields.keys()),
                'session_id': session.session_id,
                'session_progress': session.progress_percentage,
                'application_status': application.automation_status
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    # DELETE request - end session
    elif request.method == 'DELETE':
        try:
            session = AutomationSession.objects.filter(application=application).latest('started_at')
            session.status = Application.Status.FAILED
            session.ended_at = timezone.now()
            session.save()
            
            application.automation_status = Application.Status.FAILED
            application.add_automation_log("Automation session ended by API request", level='warning')
            application.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Session ended successfully',
                'session_id': session.session_id,
                'duration': str(session.duration)
            })
            
        except AutomationSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'No active session found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# Helper function to generate sample automation progress
def generate_sample_progress(application):
    """Generate sample progress data for testing"""
    sample_steps = [
        "Initializing browser automation",
        f"Navigating to {application.target_form_url or 'application form'}",
        "Analyzing form structure",
        "Mapping form fields to application data",
        "Filling personal information",
        "Filling contact information",
        "Filling academic information",
        "Uploading documents (if any)",
        "Reviewing filled form",
        "Submitting application",
        "Capturing submission confirmation"
    ]
    
    import random
    current_step = random.choice(sample_steps) if sample_steps else "Processing"
    progress = random.randint(10, 90)
    completed_steps = random.randint(1, len(sample_steps) - 1)
    
    return {
        'progress': progress,
        'step': current_step,
        'completed_steps': completed_steps,
        'total_steps': len(sample_steps),
        'status': random.choice(['analyzing', 'filling', 'waiting_review'])
    }


# WebSocket test endpoint with automation simulation
@login_required
def ws_test(request):
    """WebSocket test page with automation simulation"""
    applications = Application.objects.filter(user=request.user, target_form_url__isnull=False)[:5]
    
    context = {
        'applications': applications,
        'ws_url': f"ws://{request.get_host()}/ws/automation/",
        'page_title': 'WebSocket & Automation Test'
    }
    
    return render(request, 'applications/ws_test.html', context)


# Add this for testing automation without actual AI
@login_required
@csrf_exempt
def api_simulate_automation(request, pk):
    """Simulate automation for testing (no AI required)"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            # Create a simulation session
            session = AutomationSession.objects.create(
                application=application,
                session_id=f"SIM_{str(uuid.uuid4())[:6]}",
                target_url=application.target_form_url or "https://example.com/apply",
                status=Application.Status.ANALYZING,
                total_steps=10,
                browser_type="chromium"
            )
            
            # Update application status
            application.automation_status = Application.Status.ANALYZING
            application.last_automation_attempt = timezone.now()
            application.save()
            
            # Add initial log
            application.add_automation_log(
                "Starting automation simulation",
                level='info'
            )
            
            # Simulate field detection
            sample_fields = {
                'personal': ['name', 'email', 'phone', 'id_number', 'date_of_birth'],
                'academic': ['course', 'faculty', 'school', 'matric_year'],
                'address': ['street', 'city', 'postal_code', 'country']
            }
            
            session.detected_fields = sample_fields
            session.save()
            
            return JsonResponse({
                'success': True,
                'session_id': session.session_id,
                'message': 'Simulation started',
                'detected_fields': sample_fields,
                'next_step': 'analyzing_form'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)


@login_required
@csrf_exempt
def api_simulate_progress(request, pk):
    """Simulate progress updates for testing"""
    application = get_object_or_404(Application, pk=pk, user=request.user)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action', 'next')
            
            # Get session
            try:
                session = AutomationSession.objects.filter(
                    application=application,
                    session_id__startswith='SIM_'
                ).latest('started_at')
            except AutomationSession.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'No simulation session found'
                }, status=404)
            
            import random
            import time
            
            # Simulate different actions
            if action == 'next':
                session.completed_steps = min(session.completed_steps + 1, session.total_steps)
                
                # Simulate step completion
                steps = [
                    "Analyzing form structure",
                    "Detecting input fields",
                    "Mapping data to form fields",
                    "Filling personal information",
                    "Filling academic information",
                    "Filling contact details",
                    "Uploading documents",
                    "Reviewing form data",
                    "Clicking submit button",
                    "Capturing confirmation"
                ]
                
                current_step = steps[session.completed_steps - 1] if session.completed_steps <= len(steps) else "Processing"
                session.current_step = current_step
                
                # Randomly fill some fields
                if session.completed_steps >= 4 and session.completed_steps <= 7:
                    filled = session.filled_fields or []
                    new_fields = ['name', 'email', 'phone', 'course'][:session.completed_steps - 3]
                    filled.extend([f for f in new_fields if f not in filled])
                    session.filled_fields = filled
                
                # Random errors
                if random.random() < 0.1:  # 10% chance of error
                    errors = session.errors or []
                    errors.append(f"Simulated error at step {session.completed_steps}")
                    session.errors = errors
                    application.add_automation_log(
                        f"Simulated error: Issue at step {session.completed_steps}",
                        level='error'
                    )
                else:
                    application.add_automation_log(
                        f"Step completed: {current_step}",
                        level='info'
                    )
                
                # Update status based on progress
                if session.completed_steps >= session.total_steps:
                    session.status = Application.Status.COMPLETED
                    application.automation_status = Application.Status.COMPLETED
                    application.add_automation_log(
                        "Automation simulation completed successfully!",
                        level='success'
                    )
                elif session.completed_steps >= session.total_steps * 0.7:
                    session.status = Application.Status.WAITING_REVIEW
                    application.automation_status = Application.Status.WAITING_REVIEW
                elif session.completed_steps >= session.total_steps * 0.3:
                    session.status = Application.Status.FILLING
                    application.automation_status = Application.Status.FILLING
                
                session.save()
                application.save()
                
                return JsonResponse({
                    'success': True,
                    'progress': session.progress_percentage,
                    'current_step': session.current_step,
                    'completed_steps': session.completed_steps,
                    'total_steps': session.total_steps,
                    'status': session.status,
                    'filled_fields': session.filled_fields,
                    'errors': session.errors,
                    'duration': str(session.duration)
                })
            
            elif action == 'reset':
                session.completed_steps = 0
                session.current_step = "Starting simulation"
                session.filled_fields = []
                session.errors = []
                session.status = Application.Status.ANALYZING
                session.save()
                
                application.automation_status = Application.Status.ANALYZING
                application.save()
                
                application.add_automation_log(
                    "Simulation reset to start",
                    level='info'
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Simulation reset',
                    'progress': 0
                })
            
            elif action == 'fail':
                session.status = Application.Status.FAILED
                session.ended_at = timezone.now()
                session.save()
                
                application.automation_status = Application.Status.FAILED
                application.save()
                
                application.add_automation_log(
                    "Simulation failed (simulated error)",
                    level='error'
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Simulation failed',
                    'status': 'failed',
                    'duration': str(session.duration)
                })
            
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Unknown action: {action}'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)


@login_required
def automation_settings(request):
    """Automation settings and preferences page"""
    
    # Get or create user profile settings
    user_profile = request.user
    
    # Default settings structure
    default_settings = {
        'general': {
            'auto_start': False,
            'show_preview': True,
            'enable_sound': True,
            'notifications': True,
            'default_browser': 'chromium',
            'timeout': 30,
            'retry_attempts': 3,
            'delay_between_steps': 1,
        },
        'ai': {
            'default_service': None,
            'auto_select_service': True,
            'max_tokens_per_request': 4000,
            'temperature': 0.1,
            'enable_fallback': True,
            'cost_warning_threshold': 50,
        },
        'automation': {
            'capture_screenshots': True,
            'screenshot_quality': 'medium',
            'save_logs': True,
            'log_retention_days': 30,
            'auto_submit': False,
            'require_confirmation': True,
            'validate_urls': True,
            'test_connection': True,
        },
        'appearance': {
            'theme': 'light',
            'compact_view': False,
            'show_tutorial': True,
            'language': 'en',
            'time_format': '12h',
            'date_format': 'YYYY-MM-DD',
        },
        'notifications': {
            'email_completion': True,
            'email_errors': True,
            'browser_completion': True,
            'browser_errors': True,
            'sound_completion': True,
            'sound_errors': True,
            'desktop_completion': False,
            'desktop_errors': True,
        },
        'advanced': {
            'debug_mode': False,
            'log_level': 'info',
            'enable_webhook': False,
            'webhook_url': '',
            'api_rate_limit': 60,
            'cache_duration': 300,
            'enable_backup': True,
            'backup_frequency': 'daily',
        }
    }
    
    # Get current settings from user model or profile
    current_settings = {}
    if hasattr(user_profile, 'automation_settings'):
        current_settings = user_profile.automation_settings
    else:
        # Try to get from user profile model if exists
        try:
            profile = user_profile.profile
            if hasattr(profile, 'automation_settings'):
                current_settings = profile.automation_settings
        except AttributeError:
            # User has no profile model
            pass
    
    # Merge with defaults (deep merge)
    def deep_merge(default, current):
        merged = default.copy()
        if isinstance(current, dict):
            for key, value in current.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = value
        return merged
    
    settings_data = deep_merge(default_settings, current_settings)
    
    if request.method == 'POST':
        try:
            # Update settings based on form data
            updated_settings = {
                'general': {
                    'auto_start': request.POST.get('auto_start') == 'on',
                    'show_preview': request.POST.get('show_preview') == 'on',
                    'enable_sound': request.POST.get('enable_sound') == 'on',
                    'notifications': request.POST.get('notifications') == 'on',
                    'default_browser': request.POST.get('default_browser', 'chromium'),
                    'timeout': int(request.POST.get('timeout', 30)),
                    'retry_attempts': int(request.POST.get('retry_attempts', 3)),
                    'delay_between_steps': float(request.POST.get('delay_between_steps', 1)),
                },
                'ai': {
                    'default_service': request.POST.get('default_service') or None,
                    'auto_select_service': request.POST.get('auto_select_service') == 'on',
                    'max_tokens_per_request': int(request.POST.get('max_tokens_per_request', 4000)),
                    'temperature': float(request.POST.get('temperature', 0.1)),
                    'enable_fallback': request.POST.get('enable_fallback') == 'on',
                    'cost_warning_threshold': float(request.POST.get('cost_warning_threshold', 50)),
                },
                'automation': {
                    'capture_screenshots': request.POST.get('capture_screenshots') == 'on',
                    'screenshot_quality': request.POST.get('screenshot_quality', 'medium'),
                    'save_logs': request.POST.get('save_logs') == 'on',
                    'log_retention_days': int(request.POST.get('log_retention_days', 30)),
                    'auto_submit': request.POST.get('auto_submit') == 'on',
                    'require_confirmation': request.POST.get('require_confirmation') == 'on',
                    'validate_urls': request.POST.get('validate_urls') == 'on',
                    'test_connection': request.POST.get('test_connection') == 'on',
                },
                'appearance': {
                    'theme': request.POST.get('theme', 'light'),
                    'compact_view': request.POST.get('compact_view') == 'on',
                    'show_tutorial': request.POST.get('show_tutorial') == 'on',
                    'language': request.POST.get('language', 'en'),
                    'time_format': request.POST.get('time_format', '12h'),
                    'date_format': request.POST.get('date_format', 'YYYY-MM-DD'),
                },
                'notifications': {
                    'email_completion': request.POST.get('email_completion') == 'on',
                    'email_errors': request.POST.get('email_errors') == 'on',
                    'browser_completion': request.POST.get('browser_completion') == 'on',
                    'browser_errors': request.POST.get('browser_errors') == 'on',
                    'sound_completion': request.POST.get('sound_completion') == 'on',
                    'sound_errors': request.POST.get('sound_errors') == 'on',
                    'desktop_completion': request.POST.get('desktop_completion') == 'on',
                    'desktop_errors': request.POST.get('desktop_errors') == 'on',
                },
                'advanced': {
                    'debug_mode': request.POST.get('debug_mode') == 'on',
                    'log_level': request.POST.get('log_level', 'info'),
                    'enable_webhook': request.POST.get('enable_webhook') == 'on',
                    'webhook_url': request.POST.get('webhook_url', ''),
                    'api_rate_limit': int(request.POST.get('api_rate_limit', 60)),
                    'cache_duration': int(request.POST.get('cache_duration', 300)),
                    'enable_backup': request.POST.get('enable_backup') == 'on',
                    'backup_frequency': request.POST.get('backup_frequency', 'daily'),
                }
            }
            
            # Save settings to user model or profile
            if hasattr(user_profile, 'automation_settings'):
                user_profile.automation_settings = updated_settings
                user_profile.save()
            else:
                # Try to save to profile model
                try:
                    profile = user_profile.profile
                    profile.automation_settings = updated_settings
                    profile.save()
                except AttributeError:
                    # Create a simple JSON field in user model if possible
                    user_profile.automation_settings = updated_settings
                    user_profile.save()
            
            messages.success(request, 'Settings saved successfully!')
            
            # Redirect to prevent form resubmission
            return redirect('automation_settings')
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messages.error(request, f'Error saving settings: {str(e)}')
    
    # Get active AI services for dropdown
    ai_services = AIService.objects.filter(is_active=True)
    
    # Get user's recent activity for settings context
    recent_applications = Application.objects.filter(user=request.user).order_by('-created_at')[:5]
    automation_stats = {
        'total': Application.objects.filter(user=request.user).count(),
        'automated': Application.objects.filter(
            user=request.user, 
            automation_status=Application.Status.COMPLETED
        ).count(),
        'failed': Application.objects.filter(
            user=request.user, 
            automation_status=Application.Status.FAILED
        ).count(),
    }
    
    # Options for dropdowns
    browser_options = [
        ('chromium', 'Chromium (Recommended)'),
        ('chrome', 'Google Chrome'),
        ('firefox', 'Mozilla Firefox'),
        ('safari', 'Safari'),
        ('edge', 'Microsoft Edge'),
    ]
    
    theme_options = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('auto', 'Auto (System)'),
    ]
    
    quality_options = [
        ('low', 'Low (Fastest)'),
        ('medium', 'Medium (Balanced)'),
        ('high', 'High (Best Quality)'),
    ]
    
    language_options = [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('zh', 'Chinese'),
    ]
    
    time_format_options = [
        ('12h', '12-hour (AM/PM)'),
        ('24h', '24-hour'),
    ]
    
    date_format_options = [
        ('YYYY-MM-DD', '2024-01-15'),
        ('MM/DD/YYYY', '01/15/2024'),
        ('DD/MM/YYYY', '15/01/2024'),
        ('MMM DD, YYYY', 'Jan 15, 2024'),
    ]
    
    log_level_options = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    backup_frequency_options = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('never', 'Never'),
    ]
    
    context = {
        'settings': settings_data,
        'ai_services': ai_services,
        'recent_applications': recent_applications,
        'automation_stats': automation_stats,
        
        # Options for dropdowns
        'browser_options': browser_options,
        'theme_options': theme_options,
        'quality_options': quality_options,
        'language_options': language_options,
        'time_format_options': time_format_options,
        'date_format_options': date_format_options,
        'log_level_options': log_level_options,
        'backup_frequency_options': backup_frequency_options,
        
        'page_title': 'Automation Settings',
    }
    
    return render(request, 'applications/settings.html', context)


@login_required
@csrf_exempt
def api_save_settings(request):
    """API endpoint to save settings via AJAX"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            setting_key = data.get('key')
            setting_value = data.get('value')
            category = data.get('category', 'general')
            
            if not setting_key:
                return JsonResponse({
                    'success': False,
                    'error': 'Setting key is required'
                })
            
            user_profile = request.user
            
            # Get current settings
            current_settings = {}
            if hasattr(user_profile, 'automation_settings'):
                current_settings = user_profile.automation_settings
            else:
                try:
                    profile = user_profile.profile
                    if hasattr(profile, 'automation_settings'):
                        current_settings = profile.automation_settings
                except AttributeError:
                    pass
            
            # Ensure category exists
            if category not in current_settings:
                current_settings[category] = {}
            
            # Update the specific setting
            current_settings[category][setting_key] = setting_value
            
            # Save back
            if hasattr(user_profile, 'automation_settings'):
                user_profile.automation_settings = current_settings
                user_profile.save()
            else:
                try:
                    profile = user_profile.profile
                    profile.automation_settings = current_settings
                    profile.save()
                except AttributeError:
                    user_profile.automation_settings = current_settings
                    user_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Setting {setting_key} updated',
                'key': setting_key,
                'value': setting_value,
                'category': category
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error saving setting: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
@csrf_exempt
def api_reset_settings(request):
    """API endpoint to reset settings to defaults"""
    if request.method == 'POST':
        try:
            user_profile = request.user
            
            # Default settings
            default_settings = {
                'general': {
                    'auto_start': False,
                    'show_preview': True,
                    'enable_sound': True,
                    'notifications': True,
                    'default_browser': 'chromium',
                    'timeout': 30,
                    'retry_attempts': 3,
                    'delay_between_steps': 1,
                },
                'ai': {
                    'default_service': None,
                    'auto_select_service': True,
                    'max_tokens_per_request': 4000,
                    'temperature': 0.1,
                    'enable_fallback': True,
                    'cost_warning_threshold': 50,
                },
                'automation': {
                    'capture_screenshots': True,
                    'screenshot_quality': 'medium',
                    'save_logs': True,
                    'log_retention_days': 30,
                    'auto_submit': False,
                    'require_confirmation': True,
                    'validate_urls': True,
                    'test_connection': True,
                },
                'appearance': {
                    'theme': 'light',
                    'compact_view': False,
                    'show_tutorial': True,
                    'language': 'en',
                    'time_format': '12h',
                    'date_format': 'YYYY-MM-DD',
                },
                'notifications': {
                    'email_completion': True,
                    'email_errors': True,
                    'browser_completion': True,
                    'browser_errors': True,
                    'sound_completion': True,
                    'sound_errors': True,
                    'desktop_completion': False,
                    'desktop_errors': True,
                },
                'advanced': {
                    'debug_mode': False,
                    'log_level': 'info',
                    'enable_webhook': False,
                    'webhook_url': '',
                    'api_rate_limit': 60,
                    'cache_duration': 300,
                    'enable_backup': True,
                    'backup_frequency': 'daily',
                }
            }
            
            # Save defaults
            if hasattr(user_profile, 'automation_settings'):
                user_profile.automation_settings = default_settings
                user_profile.save()
            else:
                try:
                    profile = user_profile.profile
                    profile.automation_settings = default_settings
                    profile.save()
                except AttributeError:
                    user_profile.automation_settings = default_settings
                    user_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Settings reset to defaults',
                'settings': default_settings
            })
            
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
@csrf_exempt
def api_export_settings(request):
    """API endpoint to export settings as JSON"""
    try:
        user_profile = request.user
        
        # Get current settings
        current_settings = {}
        if hasattr(user_profile, 'automation_settings'):
            current_settings = user_profile.automation_settings
        else:
            try:
                profile = user_profile.profile
                if hasattr(profile, 'automation_settings'):
                    current_settings = profile.automation_settings
            except AttributeError:
                pass
        
        # Create response
        response = JsonResponse({
            'success': True,
            'user': request.user.username,
            'export_date': timezone.now().isoformat(),
            'settings': current_settings
        })
        
        # Make it downloadable
        response['Content-Disposition'] = f'attachment; filename="automation_settings_{request.user.username}_{timezone.now().strftime("%Y%m%d")}.json"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting settings: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
def api_import_settings(request):
    """API endpoint to import settings from JSON"""
    if request.method == 'POST':
        try:
            if 'settings_file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'error': 'No file uploaded'
                })
            
            file = request.FILES['settings_file']
            
            # Check file size (max 1MB)
            if file.size > 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'File too large (max 1MB)'
                })
            
            # Read and parse JSON
            file_content = file.read().decode('utf-8')
            imported_settings = json.loads(file_content)
            
            # Validate structure
            required_categories = ['general', 'ai', 'automation', 'appearance', 'notifications', 'advanced']
            for category in required_categories:
                if category not in imported_settings:
                    return JsonResponse({
                        'success': False,
                        'error': f'Missing category: {category}'
                    })
            
            user_profile = request.user
            
            # Save imported settings
            if hasattr(user_profile, 'automation_settings'):
                user_profile.automation_settings = imported_settings
                user_profile.save()
            else:
                try:
                    profile = user_profile.profile
                    profile.automation_settings = imported_settings
                    profile.save()
                except AttributeError:
                    user_profile.automation_settings = imported_settings
                    user_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Settings imported successfully',
                'categories_imported': list(imported_settings.keys())
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON file'
            }, status=400)
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
def bulk_delete_applications(request):
    """Bulk delete applications"""
    
    if request.method == 'POST':
        try:
            # Get selected application IDs
            selected_ids = request.POST.getlist('selected_applications')
            
            if not selected_ids:
                messages.warning(request, 'No applications selected for deletion.')
                return redirect('my_applications')
            
            # Verify ownership and delete
            deleted_count = 0
            error_count = 0
            
            for app_id in selected_ids:
                try:
                    application = Application.objects.get(id=app_id, user=request.user)
                    
                    # Delete associated files
                    if application.profile_image:
                        try:
                            if os.path.exists(application.profile_image.path):
                                os.remove(application.profile_image.path)
                        except Exception as e:
                            logger.error(f"Error deleting profile image for app {app_id}: {e}")
                    
                    if application.introduction_video:
                        try:
                            if os.path.exists(application.introduction_video.path):
                                os.remove(application.introduction_video.path)
                        except Exception as e:
                            logger.error(f"Error deleting video for app {app_id}: {e}")
                    
                    # Delete automation sessions first
                    AutomationSession.objects.filter(application=application).delete()
                    
                    # Delete the application
                    application.delete()
                    deleted_count += 1
                    
                except Application.DoesNotExist:
                    error_count += 1
                    logger.warning(f"User {request.user.id} tried to delete non-existent or unauthorized app {app_id}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error deleting application {app_id}: {e}")
            
            # Show results
            if deleted_count > 0:
                messages.success(request, f'Successfully deleted {deleted_count} application(s).')
            
            if error_count > 0:
                messages.warning(request, f'Failed to delete {error_count} application(s). You may not have permission or they no longer exist.')
            
            return redirect('my_applications')
            
        except Exception as e:
            logger.error(f"Error in bulk delete: {e}")
            messages.error(request, f'Error during bulk deletion: {str(e)}')
            return redirect('bulk_delete_applications')
    
    # GET request - show selection interface
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    university_filter = request.GET.get('university', '')
    search_query = request.GET.get('q', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    applications = Application.objects.filter(user=request.user)
    
    # Apply filters
    if status_filter != 'all':
        applications = applications.filter(status=status_filter)
    
    if university_filter:
        applications = applications.filter(
            Q(selected_university__title__icontains=university_filter) |
            Q(university_manual__icontains=university_filter)
        )
    
    if search_query:
        applications = applications.filter(
            Q(student__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(course_faculty__icontains=search_query) |
            Q(id_number__icontains=search_query)
        )
    
    # Date range filter
    if date_from:
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            applications = applications.filter(created_at__date__gte=start_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            applications = applications.filter(created_at__date__lte=end_date)
        except ValueError:
            pass
    
    # Apply bulk selection criteria
    bulk_criteria = request.GET.get('bulk_criteria', 'none')
    
    if bulk_criteria == 'draft_old':
        # Draft applications older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        applications = applications.filter(
            status=Application.Status.DRAFT,
            created_at__lt=cutoff_date
        )
    
    elif bulk_criteria == 'failed_automation':
        # Applications with failed automation
        applications = applications.filter(
            automation_status=Application.Status.FAILED
        )
    
    elif bulk_criteria == 'no_university':
        # Applications without university specified
        applications = applications.filter(
            selected_university__isnull=True,
            university_manual=''
        )
    
    elif bulk_criteria == 'incomplete':
        # Incomplete applications (progress < 50%)
        # We need to annotate with progress percentage
        incomplete_apps = []
        for app in applications:
            if app.progress_percentage < 50:
                incomplete_apps.append(app.id)
        applications = applications.filter(id__in=incomplete_apps)
    
    elif bulk_criteria == 'old_submitted':
        # Submitted applications older than 90 days
        cutoff_date = timezone.now() - timedelta(days=90)
        applications = applications.filter(
            status=Application.Status.SUBMITTED,
            created_at__lt=cutoff_date
        )
    
    # Order and paginate
    applications = applications.order_by('-created_at')
    paginator = Paginator(applications, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique universities for filter dropdown
    universities = []
    if HAS_COLLEGE_APP:
        universities = CollegeAndUniversities.objects.all()[:20]
    
    # Get statistics
    total_applications = Application.objects.filter(user=request.user).count()
    draft_applications = Application.objects.filter(
        user=request.user, 
        status=Application.Status.DRAFT
    ).count()
    old_draft_applications = Application.objects.filter(
        user=request.user,
        status=Application.Status.DRAFT,
        created_at__lt=timezone.now() - timedelta(days=30)
    ).count()
    failed_automations = Application.objects.filter(
        user=request.user,
        automation_status=Application.Status.FAILED
    ).count()
    
    context = {
        'page_obj': page_obj,
        'total_applications': total_applications,
        'draft_applications': draft_applications,
        'old_draft_applications': old_draft_applications,
        'failed_automations': failed_automations,
        
        # Filter parameters
        'status_filter': status_filter,
        'university_filter': university_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'bulk_criteria': bulk_criteria,
        
        # Options
        'universities': universities,
        'status_choices': Application.Status.choices,
        'bulk_criteria_options': [
            ('none', 'Select applications manually'),
            ('draft_old', 'Draft applications (older than 30 days)'),
            ('failed_automation', 'Applications with failed automation'),
            ('no_university', 'Applications without university'),
            ('incomplete', 'Incomplete applications (< 50% progress)'),
            ('old_submitted', 'Submitted applications (older than 90 days)'),
        ],
        
        'page_title': 'Bulk Delete Applications',
    }
    
    return render(request, 'applications/bulk_delete.html', context)


@login_required
@csrf_exempt
def api_bulk_delete_preview(request):
    """API endpoint to preview bulk delete results"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bulk_criteria = data.get('criteria', 'none')
            filters = data.get('filters', {})
            
            # Base queryset
            applications = Application.objects.filter(user=request.user)
            
            # Apply filters
            if filters.get('status') and filters.get('status') != 'all':
                applications = applications.filter(status=filters.get('status'))
            
            if filters.get('university'):
                applications = applications.filter(
                    Q(selected_university__title__icontains=filters.get('university')) |
                    Q(university_manual__icontains=filters.get('university'))
                )
            
            if filters.get('search'):
                applications = applications.filter(
                    Q(student__icontains=filters.get('search')) |
                    Q(email__icontains=filters.get('search')) |
                    Q(course_faculty__icontains=filters.get('search'))
                )
            
            # Date filters
            if filters.get('date_from'):
                try:
                    start_date = datetime.strptime(filters.get('date_from'), '%Y-%m-%d').date()
                    applications = applications.filter(created_at__date__gte=start_date)
                except ValueError:
                    pass
            
            if filters.get('date_to'):
                try:
                    end_date = datetime.strptime(filters.get('date_to'), '%Y-%m-%d').date()
                    applications = applications.filter(created_at__date__lte=end_date)
                except ValueError:
                    pass
            
            # Apply bulk criteria
            original_count = applications.count()
            
            if bulk_criteria == 'draft_old':
                cutoff_date = timezone.now() - timedelta(days=30)
                applications = applications.filter(
                    status=Application.Status.DRAFT,
                    created_at__lt=cutoff_date
                )
            
            elif bulk_criteria == 'failed_automation':
                applications = applications.filter(
                    automation_status=Application.Status.FAILED
                )
            
            elif bulk_criteria == 'no_university':
                applications = applications.filter(
                    selected_university__isnull=True,
                    university_manual=''
                )
            
            elif bulk_criteria == 'incomplete':
                # Filter incomplete applications
                incomplete_apps = []
                for app in applications:
                    if app.progress_percentage < 50:
                        incomplete_apps.append(app.id)
                applications = applications.filter(id__in=incomplete_apps)
            
            elif bulk_criteria == 'old_submitted':
                cutoff_date = timezone.now() - timedelta(days=90)
                applications = applications.filter(
                    status=Application.Status.SUBMITTED,
                    created_at__lt=cutoff_date
                )
            
            # Get sample applications for preview
            sample_applications = applications[:5].values(
                'id', 'student', 'university_name', 'status', 
                'created_at', 'automation_status'
            )
            
            # Format dates
            for app in sample_applications:
                app['created_at'] = app['created_at'].strftime('%Y-%m-%d') if app['created_at'] else ''
            
            return JsonResponse({
                'success': True,
                'total_matching': applications.count(),
                'original_count': original_count,
                'sample_applications': list(sample_applications),
                'criteria': bulk_criteria,
                'filters': filters
            })
            
        except Exception as e:
            logger.error(f"Error in bulk delete preview: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@login_required
@csrf_exempt
def api_bulk_delete_execute(request):
    """API endpoint to execute bulk delete"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            application_ids = data.get('application_ids', [])
            
            if not application_ids:
                return JsonResponse({
                    'success': False,
                    'error': 'No application IDs provided'
                })
            
            # Verify all applications belong to user
            user_applications = Application.objects.filter(
                id__in=application_ids,
                user=request.user
            )
            
            if user_applications.count() != len(application_ids):
                return JsonResponse({
                    'success': False,
                    'error': 'Some applications not found or unauthorized'
                })
            
            # Delete in batch
            deleted_count = 0
            errors = []
            
            for application in user_applications:
                try:
                    # Delete associated files
                    if application.profile_image:
                        try:
                            if os.path.exists(application.profile_image.path):
                                os.remove(application.profile_image.path)
                        except Exception as e:
                            logger.error(f"Error deleting profile image: {e}")
                    
                    if application.introduction_video:
                        try:
                            if os.path.exists(application.introduction_video.path):
                                os.remove(application.introduction_video.path)
                        except Exception as e:
                            logger.error(f"Error deleting video: {e}")
                    
                    # Delete automation sessions
                    AutomationSession.objects.filter(application=application).delete()
                    
                    # Delete application
                    application.delete()
                    deleted_count += 1
                    
                except Exception as e:
                    errors.append(f"Application {application.id}: {str(e)}")
                    logger.error(f"Error deleting application {application.id}: {e}")
            
            return JsonResponse({
                'success': True,
                'deleted_count': deleted_count,
                'total_requested': len(application_ids),
                'errors': errors,
                'message': f'Successfully deleted {deleted_count} out of {len(application_ids)} applications'
            })
            
        except Exception as e:
            logger.error(f"Error in bulk delete execute: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)




@require_GET
def automation_preview(request, session_id):
    """Simple preview endpoint"""
    try:
        session = AutomationSession.objects.get(id=session_id)
        
        if not session.preview_image or not os.path.exists(session.preview_image):
            return JsonResponse({
                'status': session.status,
                'message': 'No preview yet'
            })
        
        # Return the image
        return FileResponse(
            open(session.preview_image, 'rb'),
            content_type='image/png'
        )
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@csrf_exempt
def automation_continue(request, session_id):
    """Simple continue endpoint"""
    try:
        data = json.loads(request.body)
        session = AutomationSession.objects.get(id=session_id)
        
        # Change status to continue
        session.status = 'RUNNING'  # Use string directly
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Automation resumed',
            'new_status': session.status
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_GET
def automation_status(request, session_id):
    """Simple status endpoint"""
    try:
        session = AutomationSession.objects.get(id=session_id)
        
        return JsonResponse({
            'id': str(session.id),
            'status': session.status,
            'preview_exists': bool(session.preview_image and os.path.exists(session.preview_image)),
            'updated_at': session.updated_at.isoformat() if session.updated_at else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)