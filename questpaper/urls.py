from django.urls import path
from . import views
from .views import (
    TopicListView, TopicCreateView, TopicDetailView, TopicUpdateView, TopicDeleteView,
    DepartmentListView, DepartmentCreateView, DepartmentDetailView, 
    DepartmentUpdateView, DepartmentDeleteView,
    QuestionPaperListView
)

urlpatterns = [
    # =========================
    # CORE (USED BY TEMPLATE)
    # =========================
    path('view/<int:pk>/', views.view_question_paper, name='view'),
    path('download/<int:pk>/', views.download_question_paper, name='download'),

    # =========================
    # QUESTION PAPER PAGES
    # =========================
    path('', views.question_paper_list, name='questpaper_list'),
    path('upload/', views.upload_question_paper, name='upload'),
    
    # IMPORTANT: keep this AFTER view/download
    path('<int:pk>/', views.question_paper_detail, name='questpaper_detail'),
    path('<int:pk>/delete/', views.delete_question_paper, name='questpaper_delete'),
    path('<int:pk>/reprocess/', views.reprocess_paper, name='questpaper_reprocess'),

    # =========================
    # FILTERS
    # =========================
    path('questionpaperlist/', views.filter_question_papers, name='filter_question_papers'),
    
    # Alternative class-based list view
    path('class-list/', QuestionPaperListView.as_view(), name='questionpaper_class_list'),

    # =========================
    # TOPIC URLs
    # =========================
    path('topics/', TopicListView.as_view(), name='topic_list'),
    path('topics/create/', TopicCreateView.as_view(), name='topic_create'),
    path('topics/<int:pk>/', TopicDetailView.as_view(), name='topic_detail'),
    path('topics/<int:pk>/update/', TopicUpdateView.as_view(), name='topic_update'),
    path('topics/<int:pk>/delete/', TopicDeleteView.as_view(), name='topic_delete'),

    # =========================
    # DEPARTMENT URLs
    # =========================
    path('departments/', DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<int:pk>/update/', DepartmentUpdateView.as_view(), name='department_update'),
    path('departments/<int:pk>/delete/', DepartmentDeleteView.as_view(), name='department_delete'),
]