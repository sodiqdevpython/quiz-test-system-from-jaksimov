from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    GroupListView, GroupDetailView,
    UserListView, UserDetailView,
    CategoryListView,ThemeAttemptsListView,
    SubjectListView, SubjectDetailView,
    ThemeListView, ThemeDetailView, LogoutView,
    AttemptStartView, AttemptFinishView,SubmitAnswerView,
    AttemptStateView, TestAttemptResultsView, MyProfileView,
    UserProfileView, UserActivityStatsView, UserRatingListView,
    ThemeStatsView, SubjectStatsView, ProfilePhotoUpdateView
)


urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="token_logout"),
    # Group
    path("groups/", GroupListView.as_view(), name="group-list"),
    path("groups/<uuid:pk>/", GroupDetailView.as_view(), name="group-detail"),

    # User
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),

    # Category
    path("categories/", CategoryListView.as_view(), name="category-list"),

    # Subject
    path("subjects/", SubjectListView.as_view(), name="subject-list"),
    path("subjects/<uuid:pk>/", SubjectDetailView.as_view(), name="subject-detail"),

    # Theme
    path("themes/", ThemeListView.as_view(), name="theme-list"),
    path("themes/<uuid:pk>/", ThemeDetailView.as_view(), name="theme-detail"),

    path("themes/<uuid:theme_id>/attempts/start", AttemptStartView.as_view(), name="attempt-start"),
    path("attempts/<uuid:attempt_id>/answer", SubmitAnswerView.as_view(), name="attempt-answer"),
    path("attempts/<uuid:attempt_id>/state", AttemptStateView.as_view(), name="attempt-state"),
    path("attempts/<uuid:attempt_id>/finish", AttemptFinishView.as_view(), name="attempt-finish"),

    path("tests/<uuid:test_id>/attempts/results", TestAttemptResultsView.as_view(), name="test-attempt-results"),
    
    path("me/profile", MyProfileView.as_view(), name="my-profile"),
    path("users/<uuid:user_id>/profile", UserProfileView.as_view(), name="user-profile"),
    path("users/<uuid:user_id>/activity", UserActivityStatsView.as_view(), name="user-activity"),
    
    path("ratings", UserRatingListView.as_view(), name="user-ratings"),
    
    path("subjects/<uuid:subject_id>/stats", SubjectStatsView.as_view(), name="subject-stats"),
    path("themes/<uuid:theme_id>/stats", ThemeStatsView.as_view(), name="theme-stats"),
    
    path("me/profile/photo", ProfilePhotoUpdateView.as_view(), name="profile-photo-update"), #! profil rasmni o'zgartirish uchun
    path("themes/<uuid:theme_id>/attempts", ThemeAttemptsListView.as_view(), name="theme-attempts"),
]
