from rest_framework import serializers
from .models import (
    Group, User, Category, Subject, Theme,
    Test, Question, Option, TestAttempt, Answer
)
import hmac, hashlib, random
from django.db.models import Count
from django.db.models.functions import TruncDate

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        token['role'] = user.role  
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role  
        return data

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id','name']

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

class SubjectBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'name']

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

def _abs_url(request, f):
    if not f:
        return None
    url = f.url
    return request.build_absolute_uri(url) if request else url


class AttemptStartQuerySerializer(serializers.Serializer):
    count = serializers.IntegerField(required=True)
    order = serializers.ChoiceField(choices=('random', 'sequential'), required=True)
    mode  = serializers.ChoiceField(choices=('sequential', 'all_in_one'), required=True)
    duration = serializers.IntegerField(required=False, min_value=1, max_value=240)
    
    a = serializers.IntegerField(required=False)
    b = serializers.IntegerField(required=False)
    
    def validate(self, attrs):
        a = attrs.get("a")
        b = attrs.get("b")
        if (a is None) ^ (b is None):
            raise serializers.ValidationError("a va b birga yuborilishi kerak")
        return attrs


class AttemptOptionOutSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    tag_true = serializers.SerializerMethodField()
    tag_false = serializers.SerializerMethodField()

    class Meta:
        model  = Option
        fields = ('id', 'text', 'image_url', 'tag_true', 'tag_false')

    def get_image_url(self, obj):
        return _abs_url(self.context.get('request'), obj.image)

    def _make_tag(self, obj, correct_flag: int):
        secret = (self.context or {}).get('attempt_secret')
        salts = (self.context or {}).get('option_salts', {})
        salt = salts.get(str(obj.id))
        payload = f"{obj.question_id}:{obj.id}:{correct_flag}:{salt}".encode()
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    def get_tag_true(self, obj):
        return self._make_tag(obj, 1)

    def get_tag_false(self, obj):
        return self._make_tag(obj, 0)


class AttemptQuestionOutSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    options   = serializers.SerializerMethodField()
    correct_token = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ('id', 'text', 'image_url', 'options', 'correct_token')

    def get_image_url(self, obj):
        return _abs_url(self.context.get('request'), obj.image)

    def get_options(self, obj):
        options = list(obj.options.all())
        random.shuffle(options)
        return AttemptOptionOutSerializer(options, many=True, context=self.context).data

    def get_correct_token(self, obj):
        correct_opt = obj.options.filter(is_correct=True).first()
        if not correct_opt:
            return None
        secret = (self.context or {}).get('attempt_secret')
        salts = (self.context or {}).get('option_salts', {})
        salt = salts.get(str(correct_opt.id))
        payload = f"{obj.id}:{correct_opt.id}:1:{salt}".encode()
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


class AttemptStartResponseSerializer(serializers.Serializer):
    attempt_id = serializers.UUIDField()
    theme_id = serializers.UUIDField()
    test_id = serializers.UUIDField()
    count = serializers.IntegerField()
    order = serializers.CharField()
    mode = serializers.CharField()
    duration = serializers.IntegerField()
    expires_at = serializers.DateTimeField()
    questions = AttemptQuestionOutSerializer(many=True)


class SubmitAnswerWithTagSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    option_id   = serializers.UUIDField()
    verdict     = serializers.BooleanField()
    tag         = serializers.CharField()


class AttemptStateSerializer(serializers.Serializer):
    attempt_id   = serializers.UUIDField()
    started_at   = serializers.DateTimeField()
    expires_at   = serializers.DateTimeField()
    finished_at  = serializers.DateTimeField(allow_null=True)
    current_idx  = serializers.IntegerField()
    total        = serializers.IntegerField()
    answered     = serializers.IntegerField()
    correct      = serializers.IntegerField()
    score        = serializers.FloatField(allow_null=True)


class AttemptFinishResponseSerializer(serializers.Serializer):
    attempt_id = serializers.UUIDField()
    correct    = serializers.IntegerField()
    total      = serializers.IntegerField()
    score      = serializers.FloatField()


class AttemptResultSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.first_name")
    correct = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = TestAttempt
        fields = (
            "id",
            "user",
            "started_at",
            "finished_at",
            "duration",
            "score",
            "mode",
            "order",
            "count",
            "correct",
            "total",
        )

    def get_correct(self, obj):
        return obj.answers.filter(is_correct=True).count()

    def get_total(self, obj):
        return obj.answers.count()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "name", "kurs")


class UserProfileSerializer(serializers.ModelSerializer):
    group = GroupSerializer()
    profile_photo_url = serializers.SerializerMethodField()
    attempts_count = serializers.SerializerMethodField()
    last_active = serializers.SerializerMethodField()
    activity = serializers.SerializerMethodField()
    
    rank_overall = serializers.SerializerMethodField()
    rank_in_group = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "email",
            "group",
            "profile_photo_url",
            "attempts_count",
            "last_active",
            "activity",
            "total_attempts",
            "total_correct",
            "total_wrong",
            "average_score",
            "rank_overall",
            "rank_in_group",
        )

    def get_profile_photo_url(self, obj):
        if obj.profile_photo:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.profile_photo.url) if request else obj.profile_photo.url
        return None

    def get_attempts_count(self, obj):
        return obj.attempts.count()

    def get_last_active(self, obj):
        attempt = obj.attempts.order_by("-started_at").first()
        return attempt.started_at if attempt else None
    
    def get_activity(self, obj):
        stats = (
            obj.attempts
            .annotate(day=TruncDate("started_at"))
            .values("day")
            .annotate(attempts=Count("id"))
            .order_by("day")
        )
        return [{"date": row["day"], "attempts": row["attempts"]} for row in stats]
    
    def get_rank_overall(self, obj):
        better_users = User.objects.filter(average_score__gt=obj.average_score).count()
        return better_users + 1
    
    def get_rank_in_group(self, obj):
        if not obj.group:
            return None
        better_users = User.objects.filter(
            group=obj.group,
            average_score__gt=obj.average_score
        ).count()
        return better_users + 1


class UserActivityStatSerializer(serializers.Serializer):
    date = serializers.DateField()
    attempts = serializers.IntegerField()


class UserRatingSerializer(serializers.ModelSerializer):
    group = GroupSerializer()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "role",
            "group",
            "total_attempts",
            "total_correct",
            "total_wrong",
            "average_score",
            "profile_photo"
        )


class UserStatSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(source="user__id")
    username = serializers.CharField(source="user__username")
    attempts = serializers.IntegerField()
    avg_score = serializers.FloatField()

class UserStatSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(source="user__id")
    username = serializers.CharField(source="user__username")
    first_name = serializers.CharField(source="user__first_name", allow_null=True)
    last_name = serializers.CharField(source="user__last_name", allow_null=True)
    email = serializers.EmailField(source="user__email", allow_null=True)

    attempts = serializers.IntegerField()
    avg_score = serializers.FloatField()
    avg_duration = serializers.FloatField()
    total_correct = serializers.IntegerField()
    total_wrong = serializers.IntegerField()

class ProfilePhotoUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("profile_photo",)


class AttemptResultSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id")
    username = serializers.CharField(source="user.username")
    correct = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()

    class Meta:
        model = TestAttempt
        fields = (
            "id",
            "user_id",
            "username",
            "started_at",
            "finished_at",
            "duration",
            "score",
            "mode",
            "count",
            "correct",
            "total",
        )

    def get_correct(self, obj):
        return obj.answers.filter(is_correct=True).count()

    def get_total(self, obj):
        return obj.answers.count()

    def get_count(self, obj):
        return obj.answers.count()



class TopAttemptSerializer(serializers.ModelSerializer):
    attempt_id = serializers.UUIDField(source="id")
    user_id = serializers.UUIDField(source="user.id")
    username = serializers.CharField(source="user.username")
    first_name = serializers.CharField(source="user.first_name", allow_null=True)
    last_name = serializers.CharField(source="user.last_name", allow_null=True)

    correct = serializers.IntegerField(source="correct_count")
    wrong = serializers.IntegerField(source="wrong_count")
    total_questions = serializers.IntegerField()

    duration = serializers.SerializerMethodField()
    accuracy = serializers.SerializerMethodField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()

    class Meta:
        model = TestAttempt
        fields = [
            "attempt_id",
            "user_id", "username", "first_name", "last_name",
            "score", "duration","mode",
            "correct", "wrong", "total_questions", "accuracy",
            "started_at", "finished_at",
        ]

    def get_duration(self, obj):
        if not obj.finished_at or not obj.started_at:
            return None
        delta = obj.finished_at - obj.started_at
        total_seconds = int(delta.total_seconds())
        minutes, sec = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours} soat {minutes} minut {sec} sekund"
        elif minutes:
            return f"{minutes} minut {sec} sekund"
        else:
            return f"{sec} sekund"

    def get_accuracy(self, obj):
        tq = getattr(obj, "total_questions", 0) or 0
        return round((obj.correct_count / tq) * 100, 2) if tq else 0.0


class CreateSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class ThemeBasicInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = ['id', 'name']
        
class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ["text", "image", "is_correct"]

class QuestionCreateSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, required=True)

    class Meta:
        model = Question
        fields = ["test", "text", "image", "options"]

    def create(self, validated_data):
        options_data = validated_data.pop("options")
        question = Question.objects.create(**validated_data)
        for opt in options_data:
            Option.objects.create(question=question, **opt)
        return question
