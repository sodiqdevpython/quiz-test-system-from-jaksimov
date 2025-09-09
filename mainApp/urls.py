from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    GroupListView, GroupDetailView,
    UserListView, UserDetailView,
    CategoryListView,
    SubjectListView, SubjectDetailView,
    ThemeListView, ThemeDetailView, LogoutView
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
]
