from django.urls import path
from . import views

urlpatterns = [
    # ===== EXISTING URLS (keep your current ones) =====
    path('', views.gallery, name='applicationgallery'),
    path('application/<str:pk>/', views.viewApplication, name='application'),
    path('addapplication/', views.addApplication, name='addapplication'),
    path('listview/', views.galleryview, name='listview'),
    path('university/', views.UniversityView, name='universitys'),
    path('delete-application/<str:pk>', views.deleteApplication, name="delete-application"),
    path('adduniversity/', views.AddUniversityView, name='adduniversity'),
    
    # ===== DASHBOARD & OVERVIEW =====
    path('dashboard/', views.dashboard, name='dashboard'),
    path('overview/', views.dashboard, name='overview'),  # Alias for dashboard
    
    # ===== APPLICATION MANAGEMENT =====
    path('my-applications/', views.my_applications, name='my_applications'),
    path('all/', views.my_applications, name='all_applications'),  # Alias
    path('edit/<int:pk>/', views.edit_application, name='edit_application'),
    path('view/<int:pk>/', views.edit_application, name='view_application'),  # Alias for viewing
    path('duplicate/<int:pk>/', views.duplicate_application, name='duplicate_application'),
    path('copy/<int:pk>/', views.duplicate_application, name='copy_application'),  # Alias
    
    # ===== AUTOMATION CONTROL =====
    path('automate/<int:pk>/', views.start_automation, name='start_automation'),
    path('auto/<int:pk>/', views.start_automation, name='auto'),  # Short alias
    path('run/<int:pk>/', views.start_automation, name='run_automation'),  # Another alias
    
    path('automation-status/<int:pk>/', views.automation_status, name='automation_status'),
    path('status/<int:pk>/', views.automation_status, name='status'),  # Short alias
    
    path('stop-automation/<int:pk>/', views.stop_automation, name='stop_automation'),
    path('stop/<int:pk>/', views.stop_automation, name='stop'),  # Short alias
    
    path('retry-automation/<int:pk>/', views.retry_automation, name='retry_automation'),
    path('retry/<int:pk>/', views.retry_automation, name='retry'),  # Short alias
    
    path('pause-automation/<int:pk>/', views.stop_automation, name='pause_automation'),  # Same as stop
    
    # ===== AUTOMATION CONSOLE & INTERFACE =====
    path('automation-console/<int:pk>/', views.automation_console, name='automation_console'),
    path('console/<int:pk>/', views.automation_console, name='console'),  # Short alias
    path('ai-assistant/<int:pk>/', views.automation_console, name='ai_assistant'),  # User-friendly name
    
    path('automation-preview/<int:pk>/', views.automation_preview, name='automation_preview'),
    path('preview/<int:pk>/', views.automation_preview, name='preview'),  # Short alias
    
    # ===== AI SERVICES CONFIGURATION =====
    path('ai-services/', views.ai_services, name='ai_services'),
    path('ai/', views.ai_services, name='ai'),  # Short alias
    path('ai-config/', views.ai_services, name='ai_config'),  # Another alias
    
    path('ai-service/add/', views.add_ai_service, name='add_ai_service'),
    path('ai/add/', views.add_ai_service, name='ai_add'),  # Short alias
    
    path('ai-service/edit/<int:pk>/', views.edit_ai_service, name='edit_ai_service'),
    path('ai/edit/<int:pk>/', views.edit_ai_service, name='ai_edit'),  # Short alias
    
    path('ai-service/delete/<int:pk>/', views.delete_ai_service, name='delete_ai_service'),
    path('ai/delete/<int:pk>/', views.delete_ai_service, name='ai_delete'),  # Short alias
    
    path('ai-service/test/<int:pk>/', views.test_ai_service, name='test_ai_service'),
    path('ai/test/<int:pk>/', views.test_ai_service, name='ai_test'),  # Short alias
    
    # ===== UNIVERSITY SELECTION (Integration with college app) =====
    path('select-university/', views.select_university, name='select_university'),
    path('universities/', views.select_university, name='universities'),  # Alias
    path('uni/', views.select_university, name='uni'),  # Short alias
    
    path('university-detail/<int:pk>/', views.university_detail, name='university_detail'),
    path('uni/<int:pk>/', views.university_detail, name='uni_detail'),  # Short alias
    
    # ===== BURSARY SELECTION (Integration with bursary app) =====
    path('select-bursary/', views.select_bursary, name='select_bursary'),
    path('bursaries/', views.select_bursary, name='bursaries'),  # Alias
    path('bursary-list/', views.select_bursary, name='bursary_list'),  # Another alias
    
    # ===== REPORTS & ANALYTICS =====
    path('reports/', views.reports, name='reports'),
    path('analytics/', views.reports, name='analytics'),  # Alias
    path('stats/', views.reports, name='stats'),  # Another alias
    
    path('export-applications/', views.export_applications, name='export_applications'),
    path('export/', views.export_applications, name='export'),  # Short alias
    path('download/', views.export_applications, name='download'),  # Another alias
    
    # ===== API ENDPOINTS (for AJAX calls) =====
    path('api/application-data/<int:pk>/', views.api_application_data, name='api_application_data'),
    path('api/data/<int:pk>/', views.api_application_data, name='api_data'),  # Short alias
    
    path('api/update-field/<int:pk>/', views.api_update_field, name='api_update_field'),
    path('api/update/<int:pk>/', views.api_update_field, name='api_update'),  # Short alias
    
    path('api/log-action/<int:pk>/', views.api_log_action, name='api_log_action'),
    path('api/log/<int:pk>/', views.api_log_action, name='api_log'),  # Short alias
    
    path('api/automation-progress/<int:pk>/', views.api_automation_progress, name='api_automation_progress'),
    path('api/progress/<int:pk>/', views.api_automation_progress, name='api_progress'),  # Short alias
    
    path('api/validate-url/', views.api_validate_url, name='api_validate_url'),
    path('api/validate/', views.api_validate_url, name='api_validate'),  # Short alias
    path('check-url/', views.api_validate_url, name='check_url'),  # User-friendly alias
    
    # ===== UTILITY & TEST PAGES =====
    path('ws-test/', views.ws_test, name='ws_test'),
    path('websocket-test/', views.ws_test, name='websocket_test'),  # Alias
    
    path('health/', views.health_check, name='health_check'),
    path('health-check/', views.health_check, name='health'),  # Alias
    
    # ===== SETTINGS =====
    path('settings/', views.automation_settings, name='automation_settings'),
    path('config/', views.automation_settings, name='config'),  # Short alias
    path('preferences/', views.automation_settings, name='preferences'),  # User-friendly
    
    # ===== QUICK ACTIONS =====
    path('quick-add/', views.addApplication, name='quick_add'),  # Alias for quick access
    path('new/', views.addApplication, name='new'),  # Very short alias
    
    # ===== BULK OPERATIONS =====
    path('bulk-delete/', views.bulk_delete_applications, name='bulk_delete_applications'),
    path('bulk-export/', views.export_applications, name='bulk_export'),  # Alias
    
    # ===== HELP & DOCUMENTATION =====
    
    # ===== SEARCH =====
    
    # AI Testing URLs
    path('test-ai/', views.test_ai, name='test_ai'),
    path('run-ai-test/', views.run_ai_test, name='run_ai_test'),
    path('application/<int:pk>/test-ai/', views.test_application_ai, name='test_application_ai'),
    path('api/quick-ai-test/', views.api_quick_ai_test, name='api_quick_ai_test'),
    path('ai-health-check/', views.ai_health_check, name='ai_health_check'),
    path('clear-ai-cache/', views.clear_ai_cache, name='clear_ai_cache'),

    # uls for automation
    path('automation/<uuid:session_id>/preview/', views.get_automation_preview, name='automation-preview'),
]
