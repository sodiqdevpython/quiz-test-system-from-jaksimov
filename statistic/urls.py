from .views import UserFullStatsView, TestStatsView, SubjectThemeStatsView, SubjectStatView, GroupStatInSubjectView, GroupUserStatInSubjectView
from django.urls import path

urlpatterns = [
    path("users/", UserFullStatsView.as_view(), name="user-full-stats"),
    path("tests/", TestStatsView.as_view(), name="test-full-stats"),
    path("subjects/<uuid:subject_id>/stats", SubjectThemeStatsView.as_view(), name="subject-stats"),
    path("subjects/<uuid:subject_id>/themes/<uuid:theme_id>/stats", SubjectThemeStatsView.as_view(), name="theme-stats"),
    
    path("stats/subject/<uuid:pk>/", SubjectStatView.as_view(), name="subject-stat"),
    path("stats/subject/<uuid:pk>/groups/", GroupStatInSubjectView.as_view(), name="subject-group-stats"),
    path("stats/subject/<uuid:subject_id>/groups/<uuid:group_id>/users/", GroupUserStatInSubjectView.as_view(), name="subject-group-user-stats"),
]