from django.urls import path
from . import views
from django.views.generic import ListView
from .views import jobgalleryview, addJob, jobgallery, viewJob, deleteJob, JobCategoryView, applyJob, job_detail, edit_application

#GalleryView
urlpatterns = [ 
    path('', views.jobgallery, name='jobgallery'),
    path('job/<str:pk>/', views.viewJob, name='job'),
    path('addJob/', views.addJob, name='addJob'),
    #job list
    path('joblistview/', views.jobgalleryview, name='joblistview'),
    path('applicationview/', views.applicationview, name='applicationview'),
    path('apply/<int:job_id>/', views.applyJob, name='apply_job'),
    path('job/<int:job_id>/', views.job_detail, name='jobview'),
    #end
    path('edit-application/<int:pk>/', views.edit_application, name='edit-application'),
    path('delete-job/<str:pk>', views.deleteJob, name="delete-job"),
    path('category/<str:cats>/', views.JobCategoryView, name='category'),
    #content for jobs and its urls
    path('upload-jobs-excel/', views.upload_jobs_from_excel, name='upload_jobs_excel'),
]
