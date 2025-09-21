from rest_framework import generics, permissions
from .models import DeviceToken
from .serializers import DeviceTokenSerializer

class SaveTokenView(generics.CreateAPIView):
    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        token = serializer.validated_data["token"]
        DeviceToken.objects.update_or_create(
            user=self.request.user,
            token=token,
            defaults={"user": self.request.user}
        )
