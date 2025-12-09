from django import template

register = template.Library()

@register.filter
def filter_by_grade(papers, grade_id):
    """Filter question papers by grade ID"""
    if not papers or not grade_id:
        return []
    try:
        grade_id = int(grade_id)
        return [paper for paper in papers if paper.grade and paper.grade.id == grade_id]
    except (ValueError, TypeError):
        return []