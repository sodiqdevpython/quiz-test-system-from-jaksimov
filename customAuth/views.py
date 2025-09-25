import uuid
from rest_framework import generics
from rest_framework.response import Response
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import generics, permissions, status
from django.contrib.auth import get_user_model
from .serializers import (
    RegisterSerializer, ChangePasswordSerializer, UpdateEmailSerializer
)
from .serializers import ForgotPasswordSerializer, ResetPasswordSerializer
from .tasks import send_reset_email

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Parol muvaffaqiyatli o'zgartirildi."}, status=status.HTTP_200_OK)
    

class UpdateEmailView(generics.UpdateAPIView):
    serializer_class = UpdateEmailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Bunday email topilmadi."}, status=status.HTTP_400_BAD_REQUEST)

        token = str(uuid.uuid4())
        cache.set(token, user.id, timeout=600)

        print("Email yuborishni Celery worker bajaradi")
        send_reset_email.delay(email, token)

        return Response({"detail": "Parolni tiklash uchun email yuborildi."}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        user_id = cache.get(token)
        if not user_id:
            return Response({"detail": "Token noto'g'ri yoki muddati o'tgan."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(id=user_id)
        user.set_password(new_password)
        user.save()

        cache.delete(token)

        return Response({"detail": "Parol muvaffaqiyatli tiklandi."}, status=status.HTTP_200_OK)
