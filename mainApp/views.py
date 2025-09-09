from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Group, User, Category, Subject, Theme
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    GroupSerializer, UserSerializer,
    CategorySerializer, SubjectSerializer, ThemeSerializer, ThemeListSerializer
)
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({"detail": "Login successful"})
        return Response({"detail": "Invalid credentials"}, status=400)

class GroupListView(generics.ListAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    search_fields = ["name", "kurs"]


class GroupDetailView(generics.RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


# 🔹 User
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    search_fields = ["username", "first_name", "last_name", "role"]


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


# 🔹 Category (faqat list)
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]


# 🔹 Subject
class SubjectListView(generics.ListAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    search_fields = ["name"]


class SubjectDetailView(generics.RetrieveAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


# 🔹 Theme
class ThemeListView(generics.ListAPIView):
    queryset = Theme.objects.all()
    serializer_class = ThemeListSerializer
    search_fields = ["name"]
    filterset_fields = ["subject__name"]


class ThemeDetailView(generics.RetrieveAPIView):
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()  # tokenni blacklist qiladi
            return Response({"detail": "Logout qilindi"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Refresh token kerak"}, status=status.HTTP_400_BAD_REQUEST)



