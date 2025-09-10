from rest_framework import serializers
from .models import (
    Group, User, Category, Subject, Theme,
    Test, Question, Option, TestAttempt, Answer
)
import hmac, hashlib, random
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


ALLOWED_COUNTS = (5, 10, 20, 25, 30)

def _abs_url(request, f):
    if not f:
        return None
    url = f.url
    return request.build_absolute_uri(url) if request else url


# --------- Start: query params
class AttemptStartQuerySerializer(serializers.Serializer):
    count = serializers.IntegerField(required=True)
    order = serializers.ChoiceField(choices=('random', 'sequential'), required=True)
    mode  = serializers.ChoiceField(choices=('sequential', 'all_in_one'), required=True)
    duration = serializers.IntegerField(required=False, min_value=1, max_value=240)

    def validate_count(self, v):
        if v not in ALLOWED_COUNTS:
            raise serializers.ValidationError(f"count {ALLOWED_COUNTS} dan biri bo‘lishi kerak")
        return v


# --------- Start: outward packet
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
        """To‘g‘ri variant uchun tag_true qiymatini hisoblaymiz."""
        # 1) to‘g‘ri optionni topamiz
        correct_opt = obj.options.filter(is_correct=True).first()
        if not correct_opt:
            return None
        # 2) serverdagi secret+salt bilan xuddi tag_true formulasi
        secret = (self.context or {}).get('attempt_secret')
        salts = (self.context or {}).get('option_salts', {})
        salt = salts.get(str(correct_opt.id))
        payload = f"{obj.id}:{correct_opt.id}:1:{salt}".encode()
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


class AttemptStartResponseSerializer(serializers.Serializer):
    attempt_id = serializers.UUIDField()
    theme_id   = serializers.UUIDField()
    test_id    = serializers.UUIDField()
    count      = serializers.IntegerField()
    order      = serializers.CharField()
    mode       = serializers.CharField()
    duration   = serializers.IntegerField()
    expires_at = serializers.DateTimeField()
    questions  = AttemptQuestionOutSerializer(many=True)


# --------- Answer
class SubmitAnswerWithTagSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    option_id   = serializers.UUIDField()
    verdict     = serializers.BooleanField()
    tag         = serializers.CharField()


# --------- State
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


# --------- Finish
class AttemptFinishResponseSerializer(serializers.Serializer):
    attempt_id = serializers.UUIDField()
    correct    = serializers.IntegerField()
    total      = serializers.IntegerField()
    score      = serializers.FloatField()

