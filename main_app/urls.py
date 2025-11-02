"""college_management_system URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from main_app.EditResultView import EditResultView
from django.contrib.auth import views as auth_views
from . import hod_views, staff_views, parent_views, member_views, educator_views, circuit_manager_views, student_views, principal_views, cwa_admin_views, views
from .views import *

urlpatterns = [
    path('', views.index_view, name='index'),
    path("login", views.login_page, name='login_page'),
    path("news/", hod_views.post_add, name="news"),
    path("item/<int:pk>/edit/", hod_views.edit_post, name="edit_post"),
    path("item/<int:pk>/delete/", hod_views.delete_post, name="delete_post"),
    path("get_attendance", views.get_attendance, name='get_attendance'),
    path("firebase-messaging-sw.js", views.showFirebaseJS, name='showFirebaseJS'),
    path("doLogin/", views.doLogin, name='user_login'),
    path("logout_user/", views.logout_user, name='user_logout'),
    path("admin/home/", hod_views.admin_home, name='admin_home'),
    path("staff/add", hod_views.add_staff, name='add_staff'),
    path("term/add", hod_views.add_term, name='add_term'),
    path("course/add", hod_views.add_course, name='add_course'),
    path("grade/add", hod_views.add_grade, name='add_grade'),
    path("send_student_notification/", hod_views.send_student_notification,
         name='send_student_notification'),
    path("send_staff_notification/", hod_views.send_staff_notification,
         name='send_staff_notification'),
    path("add_session/", hod_views.add_session, name='add_session'),
    path("admin_notify_student", hod_views.admin_notify_student,
         name='admin_notify_student'),
    path("admin_notify_staff", hod_views.admin_notify_staff,
         name='admin_notify_staff'), 
    path("admin_view_profile", hod_views.admin_view_profile,
         name='admin_view_profile'),
    path("check_email_availability", hod_views.check_email_availability,
         name="check_email_availability"),
    path("session/manage/", hod_views.manage_session, name='manage_session'),
    path("session/edit/<int:session_id>",
         hod_views.edit_session, name='edit_session'),
    path('school/edit/<int:school_id>/', 
         hod_views.edit_school, name='edit_school'),
    path("grade/edit/<int:grade_id>",
         hod_views.edit_grade, name='edit_grade'),
    path("term/edit/<int:term_id>",
         hod_views.edit_term, name='edit_term'),
    path("student/view/feedback/", hod_views.student_feedback_message,
         name="student_feedback_message",),
    path("staff/view/feedback/", hod_views.staff_feedback_message,
         name="staff_feedback_message",),
    path("student/view/leave/", hod_views.view_student_leave,
         name="view_student_leave",),
    path("staff/view/leave/", hod_views.view_staff_leave, name="view_staff_leave",),
    path("attendance/view/", hod_views.admin_view_attendance,
         name="admin_view_attendance",),
    path("attendance/fetch/", hod_views.get_admin_attendance,
         name='get_admin_attendance'),
    #add other users
    
    path("student/add/", hod_views.add_student, name='add_student'),
    path("principal/add/", hod_views.add_principal, name='add_principal'),
    path("educator/add/", hod_views.add_educator, name='add_educator'),
    path("circuit_manager/add/", hod_views.add_circuit_manager, name='add_circuit_manager'),
    path("parent/add/", hod_views.add_parent, name='add_parent'),
    path("member/add/", hod_views.add_member, name='add_member'),
    path("add_cwa_admin/add/", hod_views.add_cwa_admin, name='add_cwa_admin'),

    
    #manager
    path("subject/add/", hod_views.add_subject, name='add_subject'),
    path("school/add/", hod_views.add_school, name='add_school'),
    path("add_item/", hod_views.post_add, name="add_item"),
    path("item/<int:pk>/edit/", hod_views.edit_post, name="edit_post"),
    path("item/<int:pk>/delete/", hod_views.delete_post, name="delete_post"),
    path("term/manage/", hod_views.manage_term, name='manage_term'),
    path("staff/manage/", hod_views.manage_staff, name='manage_staff'),
    path("principal/manage/", hod_views.manage_principal, name='manage_principal'),
    path("educator/manage/", hod_views.manage_educator, name='manage_educator'),
    path("circuit_manager/manage/", hod_views.manage_circuit_manager, name='manage_circuit_manager'),
    path("parent/manage/", hod_views.manage_parent, name='manage_parent'),
    path("member/manage/", hod_views.manage_member, name='manage_member'),
    path("student/manage/", hod_views.manage_student, name='manage_student'),
    path("course/manage/", hod_views.manage_course, name='manage_course'),
    path("grade/manage/", hod_views.manage_grade, name='manage_grade'),
    path("school/manage/", hod_views.manage_school, name='manage_school'),
    path("subject/manage/", hod_views.manage_subject, name='manage_subject'),
    path("staff/edit/<int:staff_id>", hod_views.edit_staff, name='edit_staff'),
    path("staff/delete/<int:staff_id>",
         hod_views.delete_staff, name='delete_staff'),

    path("course/delete/<int:course_id>",
         hod_views.delete_course, name='delete_course'),

    path("grade/delete/<int:grade_id>",
         hod_views.delete_grade, name='delete_grade'),
    
    path("term/delete/<int:grade_id>",
         hod_views.delete_term, name='delete_term'),

    path("subject/delete/<int:subject_id>",
         hod_views.delete_subject, name='delete_subject'),

    path("school/delete/<int:school_id>",
         hod_views.delete_school, name='delete_school'),

    path("session/delete/<int:session_id>",
         hod_views.delete_session, name='delete_session'),

    path("student/delete/<int:student_id>",
         hod_views.delete_student, name='delete_student'),
    path("student/edit/<int:student_id>",
         hod_views.edit_student, name='edit_student'),
    #edit the cwa_admin portal
    path("cwa_admin/edit/<int:cwa_admin_id>",
         hod_views.edit_cwa_admin, name='edit_cwa_admin'),
   
    path('cwa-admin/home/', cwa_admin_views.cwa_admin_home, name='cwa_admin'),
   
    #cwa----end
    path("course/edit/<int:course_id>",
         hod_views.edit_course, name='edit_course'),
    path("subject/edit/<int:subject_id>",
         hod_views.edit_subject, name='edit_subject'),


    # Staff
    
    path("staff/home/", staff_views.staff_home, name='staff_home'),
    path("staff/apply/leave/", staff_views.staff_apply_leave,
         name='staff_apply_leave'),
    path("news/", staff_views.post_add, name="news"),
    path("item/<int:pk>/edit/", staff_views.edit_post, name="edit_post"),
    path("item/<int:pk>/delete/", staff_views.delete_post, name="delete_post"),
    path("staff/feedback/", staff_views.staff_feedback, name='staff_feedback'),
    path("staff/view/profile/", staff_views.staff_view_profile,
         name='staff_view_profile'),
    path("staff/attendance/take/", staff_views.staff_take_attendance,
         name='staff_take_attendance'),
    path("staff/attendance/update/", staff_views.staff_update_attendance,
         name='staff_update_attendance'),
    path("staff/get_students/", staff_views.get_students, name='get_students'),
    path("staff/attendance/fetch/", staff_views.get_student_attendance,
         name='get_student_attendance'),
    path("staff/attendance/save/",
         staff_views.save_attendance, name='save_attendance'),
    path("staff/attendance/update/",
         staff_views.update_attendance, name='update_attendance'),
    path("staff/fcmtoken/", staff_views.staff_fcmtoken, name='staff_fcmtoken'),
    path("staff/view/notification/", staff_views.staff_view_notification,
         name="staff_view_notification"),
    path("staff/result/add/", staff_views.staff_add_result, name='staff_add_result'),
    path("staff/result/edit/", EditResultView.as_view(),
         name='edit_student_result'),
    path('staff/result/fetch/', staff_views.fetch_student_result,
         name='fetch_student_result'),

    #circuits
    path('circuit_gallery/', views.circuitGallery, name='circuit_gallery'),
    path('circuit/<int:pk>/', views.viewCircuit, name='view_circuit'),
    path('add/', views.addCircuit, name='add_circuit'),
    path('edit/<int:pk>/', views.editCircuit, name='edit_circuit'),
    path('delete/<int:pk>/', views.deleteCircuit, name='delete_circuit'),
  
    # Student
    path("student/home/", student_views.student_home, name='student_home'),
    path("student/view/attendance/", student_views.student_view_attendance,
         name='student_view_attendance'),
    path("student/take/attendance/", student_views.student_take_attendance,
         name='student_take_attendance'),
    path('student/submit_attendance/', student_views.submit_attendance, 
         name='submit_attendance'),  # URL for form submission
    path("student/apply/leave/", student_views.student_apply_leave,
         name='student_apply_leave'),
    path("student/feedback/", student_views.student_feedback,
         name='student_feedback'),
    path("student/view/profile/", student_views.student_view_profile,
         name='student_view_profile'),
    path("student/fcmtoken/", student_views.student_fcmtoken,
         name='student_fcmtoken'),
    path("student/add/result/", student_views.student_add_result,
          name='student_add_result'),
    path("student/view/notification/", student_views.student_view_notification,
         name="student_view_notification"),
    path('student/view/result/', student_views.student_view_result,
         name='student_view_result'),
    path('student/question-papers/', student_views.question_paper_list, 
         name='question_paper_list'),
    path('question-papers/<int:pk>/', student_views.question_paper_detail, 
         name='question_paper_detail'),

    #principal
    path('principal/home/', principal_views.principal_home, name='principal_home'),
    path('principal/view_attendance/', principal_views.principal_view_attendance, name='principal_view_attendance'),
    path('principal/view_results/', principal_views.principal_view_results, name='principal_view_results'),
    path('principal/manage_parents/', principal_views.principal_manage_parents, name='principal_manage_parents'),
    path('principal/manage_members/', principal_views.principal_manage_members, name='principal_manage_members'),
    path('principal/view_profile/', principal_views.principal_view_profile, name='principal_view_profile'),
    path("news/", principal_views.post_add, name="news"),
    path("item/<int:pk>/edit/", principal_views.edit_post, name="edit_post"),
    path("item/<int:pk>/delete/", principal_views.delete_post, name="delete_post"),
    # path('principal/add_result/', principal_views.principal_add_result, name='principal_add_result'),
    # path('principal/fetch_student_result/', principal_views.fetch_student_result, name='fetch_student_result'),
    # path('principal/edit_result/<int:result_id>/', principal_views.EditResultView.as_view(), name='edit_result'),
    
    #Circuit Manager
    # Course URLs
    path("news/", circuit_manager_views.post_add, name="news"),
    path("item/<int:pk>/edit/", circuit_manager_views.edit_post, name="edit_post"),
    path("item/<int:pk>/delete/", circuit_manager_views.delete_post, name="delete_post"),
    path('circuit_manager/home/', circuit_manager_views.circuit_manager_home, name='circuit_manager_home'),
    path('courses/', circuit_manager_views.circuit_manager_view_courses, name='circuit_manager_view_courses'),
    path('courses/add/', circuit_manager_views.circuit_manager_add_course, name='circuit_manager_add_course'),
    path('courses/edit/<int:course_id>/', circuit_manager_views.circuit_manager_edit_course, name='circuit_manager_edit_course'),
    path('courses/delete/<int:course_id>/', circuit_manager_views.circuit_manager_delete_course, name='circuit_manager_delete_course'),

    # Session URLs
    path('sessions/', circuit_manager_views.circuit_manager_view_sessions, name='circuit_manager_view_sessions'),
    path('sessions/add/', circuit_manager_views.circuit_manager_add_session, name='circuit_manager_add_session'),
    path('sessions/edit/<int:session_id>/', circuit_manager_views.circuit_manager_edit_session, name='circuit_manager_edit_session'),
    path('sessions/delete/<int:session_id>/', circuit_manager_views.circuit_manager_delete_session, name='circuit_manager_delete_session'),

    # Term URLs
    path('terms/', circuit_manager_views.circuit_manager_view_terms, name='circuit_manager_view_terms'),
    path('terms/add/', circuit_manager_views.circuit_manager_add_term, name='circuit_manager_add_term'),
    path('terms/edit/<int:term_id>/', circuit_manager_views.circuit_manager_edit_term, name='circuit_manager_edit_term'),
    path('terms/delete/<int:term_id>/', circuit_manager_views.circuit_manager_delete_term, name='circuit_manager_delete_term'),

    # Student URLs
    path('students/', circuit_manager_views.circuit_manager_view_students, name='circuit_manager_view_students'),
    
    # Result URLs
    path('results/', circuit_manager_views.circuit_manager_view_results, name='circuit_manager_view_results'),

    # Parent URLs
    path('parents/', circuit_manager_views.circuit_manager_manage_parents, name='circuit_manager_manage_parents'),
    path('parents/add/', circuit_manager_views.circuit_manager_add_parent, name='circuit_manager_add_parent'),
    path('parents/edit/<int:parent_id>/', circuit_manager_views.circuit_manager_edit_parent, name='circuit_manager_edit_parent'),
    path('parents/delete/<int:parent_id>/', circuit_manager_views.circuit_manager_delete_parent, name='circuit_manager_delete_parent'),

    # Member URLs
    path('members/', circuit_manager_views.circuit_manager_manage_members, name='circuit_manager_manage_members'),
    path('members/add/', circuit_manager_views.circuit_manager_add_member, name='circuit_manager_add_member'),
    path('members/edit/<int:member_id>/', circuit_manager_views.circuit_manager_edit_member, name='circuit_manager_edit_member'),
    path('members/delete/<int:member_id>/', circuit_manager_views.circuit_manager_delete_member, name='circuit_manager_delete_member'),
    
    # Educator Urls
    path('educator/upload_question_paper/', educator_views.upload_question_paper, name='upload_question_paper'),
    path('educator/home/', educator_views.educator_home, name='educator_home'),
    path('educator/attendance/take/', educator_views.educator_take_attendance, name='educator_take_attendance'),
    path('educator/attendance/view/', educator_views.educator_view_attendance, name='educator_view_attendance'),
    path('educator/students/', educator_views.educator_view_students, name='educator_view_students'),
    path('educator/attendance/', educator_views.educator_view_attendance, name='educator_view_attendance'),
    path('educator/results/', educator_views.educator_view_results, name='educator_view_results'),
    # path('educator/profile/', educator_views.educator_view_profile, name='educator_view_profile'),
    path('educator/fetch_student_attendance/', educator_views.fetch_student_attendance, name='fetch_student_attendance'),
    path('educator/fetch_student_results/', educator_views.fetch_student_results, name='fetch_student_results'),
    path('educator/manage_subjects/', educator_views.educator_manage_subjects, name='educator_manage_subjects'),
    path('educator/add_subject/', educator_views.educator_add_subject, name='educator_add_subject'),
    path('educator/edit_subject/<int:subject_id>/', educator_views.educator_edit_subject, name='educator_edit_subject'),
    path('educator/delete_subject/<int:subject_id>/', educator_views.educator_delete_subject, name='educator_delete_subject'),
    #member Urls
    path('dashboard/', member_views.member_home, name='member_home'),
    path('attendance/', member_views.member_view_attendance, name='member_view_attendance'),
    path('profile/', member_views.member_view_profile, name='member_view_profile'),
    path('attendance/manage/', member_views.member_manage_attendance_reports, name='member_manage_attendance_reports'),
    path('attendance/add/', member_views.member_add_attendance_report, name='member_add_attendance_report'),
    path('attendance/edit/<int:report_id>/', member_views.member_edit_attendance_report, name='member_edit_attendance_report'),
    path('attendance/delete/<int:report_id>/', member_views.member_delete_attendance_report, name='member_delete_attendance_report'),
    #adversiment url
     #add ad
    path('add/', member_views.add_ad, name='add_ad'),
    path('view/', member_views.view_ads, name='view_ads'),
    path('remove/<int:ad_id>/', member_views.remove_ad, name='remove_ad'),
    path('shared/<uuid:share_id>/', member_views.shared_ad, name='shared_ad'),
    #add card
    path('add/', member_views.add_card, name='add_card'),
    path('view/', member_views.view_cards, name='view_cards'),
    path('remove/<int:ad_id>/', member_views.remove_card, name='remove_card'),
    path('shared/<uuid:share_id>/', member_views.shared_card, name='shared_card'),
    #add payments
    path('add/', member_views.add_payment, name='add_payment'),
    path('view/', member_views.view_payments, name='view_payments'),
    path('remove/<int:payment_id>/', member_views.remove_payment, name='remove_payment'),
    path('shared/<uuid:share_id>/', member_views.shared_payment, name='shared_payment'),
    #terms of use
    path('terms-of-use/', member_views.terms_of_use, name='terms_of_use'),
    path('privacy-policy/', member_views.privacy_policy, name='privacy_policy'),

    
    #parent Urls
    path('parent/', parent_views.parent_home, name='parent_home'),
    path('parent/view-attendance/', parent_views.parent_view_attendance, name='parent_view_attendance'),
    path('parent/view-profile/', parent_views.parent_view_profile, name='parent_view_profile'),
    path('parent/manage-attendance/', parent_views.parent_manage_attendance_reports, name='parent_manage_attendance_reports'),
    path('parent/add-attendance/', parent_views.parent_add_attendance_report, name='parent_add_attendance_report'),
    path('parent/edit-attendance/<int:report_id>/', parent_views.parent_edit_attendance_report, name='parent_edit_attendance_report'),
    path('parent/delete-attendance/<int:report_id>/', parent_views.parent_delete_attendance_report, name='parent_delete_attendance_report'),
    
    #dashboard
    path('subscribe/', views.subscribe_view, name='subscribe'),
    path('view-appointment/', views.view_appointments, name='view_appointments'),
    path('send-feedback/<int:appointment_id>/', views.send_feedback, name='send_feedback'),
    path('feedback-status/', views.feedback_status, name='feedback_status'),
    path('school/submit-documents/', views.submit_documents, name='submit_documents'),
    path('school/view-textbooks/', views.view_textbooks, name='view_textbooks'),
    path("register/", hod_views.register_selection, name='register_selection'),
    
    #documents upload
    path('form/', views.uploadForm, name='form'),
    path('uploadfile/', views.uploadFile, name='uploadfile'),
    path('files/', views.FileView.as_view(), name='files'),
    path('myupload/', views.myUpload, name='myupload'),
    #schools file upload
    path('schoolform/', views.uploadSchoolForm, name='schoolform'),
    path('schoolupload/', views.uploadSchoolFile, name='schoolupload'),
    path('schoolfiles/', views.SchoolFileView.as_view(), name='schoolfiles'),
    path('myschoolupload/', views.mySchoolUpload, name='myschoolupload'),
    #school daschboard
    path('school/dashboard/', views.school_dashboard, name='school_dashboard'),
    
    #manage school
    path('help/', views.Help.as_view(), name="help"),
    path('about/', views.About.as_view(), name="about"),
    path('services/', views.Services.as_view(), name="services"),
    path('cases/', views.OurCases.as_view(), name="cases"),
    path('consulting/', views.Consulting.as_view(), name="consulting"),
    path('other/', views.Other.as_view(), name="other"),
    path('testimonials/', views.Testimonials.as_view(), name="testimonials"),
    path('faq/', views.Faq.as_view(), name="faq"),
    path('message/', views.MessageExchangeView.as_view(), name='message'),
    path('contacts/', views.contact_list_view, name='contact_list'),
    path('contacts/<int:pk>/', views.contact_detail_view, name='contact_detail'), 
    path('contact/', views.contact_create_view, name='contact_form'),
    #Header Learn More
    path('engagewithus/', views.Engage.as_view(), name="engagewithus"),
    path('stayconnected/', views.Connected.as_view(), name="stayconnected"),
    path('officehours/', views.Office.as_view(), name="officehours"),
    

    #sos
    path('sos/<str:pk>/', views.viewSos, name='sos'),
    path('addsos/', views.addSos, name='addsos'),
    path('soslistview/', views.sosview, name='soslistview'),
    path('delete_sos/<str:pk>', views.deleteSos, name="delete_sos"),

    #Circuit Manager
    path('circuitmanager/', CircuitManager.as_view(), name='circuitmanager'),
    path('search/', views.general_search_view, name='general_search_view'),
    #prospector details
    path('prospectors/', ProspectorsListView.as_view(), name='prospectors_list'),
    path('prospectors/upload/', ProspectorsCreateView.as_view(), name='upload_prospector'),
    path('search-students/', hod_views.search_students, name='search_students'),
    path('prospectors/search/', ProspectorsSearchView.as_view(), name='prospectors_search'),
    path('prospectors/edit/<int:prospector_id>/', views.prospector_edit, name='prospector_edit'),
    
    # Add or edit timetable view
    path('timetable/add/', views.timetable_add_edit, name='timetable_add'),  # For creating a new timetable
    path('timetable/edit/<int:timetable_id>/', views.timetable_add_edit, name='timetable_edit'),  # For editing an existing timetable
    path('timetable/', views.timetable_list, name='timetable_list'),
    
    #Terms and Conditions
    path('terms-conditions/', views.terms_conditions, name='terms_conditions'),
    #password reset
    path("password_reset/", views.custom_password_reset_request, name="password_reset_request"),
    path("password_reset/done/", custom_password_reset_done, name="custom_password_reset_done"),
    path("reset/<uidb64>/<token>/", views.custom_password_reset_confirm, name="password_reset_confirm"),
    #UPLOADING AND VIEWING SCHOOLS FROM EXCEL
    path('upload-schools/', views.upload_schools_from_excel, name='upload_schools'),
    #videos
    path('videos/', views.videos_view, name='videos'),
    path('videos/add/', views.video_add_view, name='video_add'),
    path('videos/<int:video_id>/', views.show_video, name='show_video'),
    
    # AJAX endpoints for likes and comments
    path('videos/<int:video_id>/like/', views.like_video, name='like_video'),
    path('videos/<int:video_id>/comment/', views.add_comment, name='add_comment'),
    path('videos/<int:video_id>/comments/', views.get_comments, name='get_comments'),
]
