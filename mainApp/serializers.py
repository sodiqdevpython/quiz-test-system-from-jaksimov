from rest_framework import serializers
from .models import (
    Group, User, Category, Subject, Theme,
    Test, Question, Option, TestAttempt, Answer
)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name']

class AuthorInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'profile_photo')

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"

class SubjectSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    authors = AuthorInfoSerializer(many=True, read_only=True)
    class Meta:
        model = Subject
        fields = ['id', 'name', 'category', 'theme_count', 'authors', 'description']

class ThemeListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = ['id','name', 'duration']


class ThemeSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer()
    class Meta:
        model = Theme
        fields = "__all__"


class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = "__all__"


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = "__all__"


class TestAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAttempt
        fields = "__all__"


class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = "__all__"