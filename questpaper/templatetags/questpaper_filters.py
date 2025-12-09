# questpaper/templatetags/questpaper_filters.py
from django import template

register = template.Library()

@register.filter
def filter_by_grade(question_papers, grade_id):
    """Filter question papers by grade ID"""
    if not question_papers or not grade_id:
        return []
    
    # Convert grade_id to int if it's a string
    try:
        grade_id = int(grade_id)
    except (ValueError, TypeError):
        return []
    
    # Filter the papers
    return [paper for paper in question_papers if paper.grade and paper.grade.id == grade_id]

@register.filter
def group_by_subject(question_papers):
    """Group question papers by subject"""
    grouped = {}
    for paper in question_papers:
        subject_name = paper.subject.name if paper.subject else 'Unknown'
        if subject_name not in grouped:
            grouped[subject_name] = []
        grouped[subject_name].append(paper)
    return grouped.items()