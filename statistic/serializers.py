from rest_framework import serializers
from mainApp.models import Group, User

class UserStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    students_count = serializers.IntegerField()
    active_users = serializers.IntegerField(required=False)
    
    
class SubjectStatSerializer(serializers.Serializer):
    subject_id = serializers.UUIDField()
    subject_name = serializers.CharField()
    student_count = serializers.IntegerField()
    avg_score = serializers.FloatField()


class GroupStatInSubjectSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField()
    avg_score = serializers.FloatField()
    total_attempts = serializers.IntegerField()

    class Meta:
        model = Group
        fields = ["id", "name", "kurs", "student_count", "avg_score", "total_attempts"]


class UserStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "group", "total_attempts", "total_correct", "total_wrong", "average_score"]