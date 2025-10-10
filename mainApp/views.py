from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, filters
from .models import Group, User, Category, Subject, Theme, Question, Test, TestAttempt, Answer, Option
from django.db.models import Count, Avg, Q, Count, F
from .pagination import StandardResultsSetPagination
from django.db.models.expressions import Window, OrderBy
from django.core.cache import cache
from django.db.models.functions import RowNumber
from rest_framework.generics import ListAPIView, CreateAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    CustomTokenObtainPairSerializer, GroupSerializer, UserSerializer, AttemptStartQuerySerializer, AttemptStartResponseSerializer,AttemptStateSerializer,
    CategorySerializer, SubjectSerializer, ThemeSerializer, ThemeListSerializer, SubmitAnswerWithTagSerializer,SubjectBasicSerializer,
    AttemptFinishResponseSerializer, AttemptResultSerializer, UserProfileSerializer, UserRatingSerializer, UserStatSerializer,
    ProfilePhotoUpdateSerializer, TopAttemptSerializer, CreateSubjectSerializer, ThemeBasicInfoSerializer, QuestionCreateSerializer
)
from django.db.models.functions import TruncDate
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.shortcuts import get_object_or_404
import random, secrets, datetime, hmac, hashlib
from rest_framework import generics
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class GroupListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    search_fields = ["name", "kurs"]

class GroupDetailView(generics.RetrieveAPIView):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    search_fields = ["username", "first_name", "last_name", "role"]

class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["name"]

class SubjectListView(generics.ListAPIView):
    serializer_class = SubjectSerializer
    search_fields = ["name"]
    def get_queryset(self):
        user = self.request.user

        if user.role == "admin":
            return Subject.objects.all()

        elif user.role == "teacher":
            return Subject.objects.filter(authors=user)

        elif user.role == "student":
            if user.group:
                return Subject.objects.filter(groups__name=user.group.name)
            return Subject.objects.none()

        return Subject.objects.none()


class SubjectDetailView(generics.RetrieveAPIView):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer


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
            token.blacklist()
            return Response({"detail": "Logout qilindi"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Refresh token kerak"}, status=status.HTTP_400_BAD_REQUEST)


CACHE_PREFIX = "attempt_meta:"

def _cache_key(attempt_id):
    return f"{CACHE_PREFIX}{attempt_id}"

def _now():
    return timezone.now()

def _expires(started_at, minutes):
    return started_at + datetime.timedelta(minutes=minutes)

class AttemptStartView(APIView):
    def get(self, request, theme_id):
        q = AttemptStartQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        count = q.validated_data["count"]
        order = q.validated_data["order"]
        mode  = q.validated_data["mode"]
        custom_duration = q.validated_data.get("duration")

        scope = request.query_params.get("scope", "theme")  

        theme = get_object_or_404(Theme, id=theme_id)
        test = Test.objects.filter(theme=theme).order_by("created").first()
        if test is None:
            return Response(
                {'status': 404, 'message': "Bu mavzuda test yo'q"},
                status=404
            )

        #! Oldingi active attempt yopiladi
        active_attempt = TestAttempt.objects.filter(
            test=test, user=request.user, finished_at__isnull=True
        ).order_by("-started_at").first()

        if active_attempt:
            active_attempt.finished_at = _now()
            total = active_attempt.answers.count()
            correct = active_attempt.answers.filter(is_correct=True).count()
            active_attempt.score = round((correct / total) * 100, 2) if total else 0.0
            active_attempt.duration = int(
                (active_attempt.finished_at - active_attempt.started_at).total_seconds() // 60
            )
            active_attempt.save(update_fields=["finished_at", "score", "duration"])

        if scope == "subject":
            pool = Question.objects.filter(test__theme__subject=theme.subject).prefetch_related("options")
        else:
            pool = Question.objects.filter(test__theme=theme).prefetch_related("options")

        total = pool.count()
        if total == 0:
            return Response({"detail": "Savollar topilmadi"}, status=400)

        if count == 0:
            n = total
        else:
            n = min(count, total)

        if order == "random":
            ids = list(pool.values_list("id", flat=True))
            chosen_ids = set(random.sample(ids, n))
            questions = [q for q in pool if q.id in chosen_ids]
        else:
            questions = list(pool[:n])

        attempt = TestAttempt.objects.create(test=test, user=request.user, mode=mode)
        Answer.objects.bulk_create([Answer(attempt=attempt, question=qobj) for qobj in questions])

        if custom_duration:
            duration = custom_duration
        else:
            duration = len(questions) * 2

        expires_at = _expires(attempt.started_at, duration)

        secret = secrets.token_hex(16)
        option_salts = {str(o.id): secrets.token_hex(8) for q in questions for o in q.options.all()}
        meta = {
            "secret": secret,
            "salts": option_salts,
            "current_idx": 0,
            "order_ids": [str(q.id) for q in questions],
            "expires_at": expires_at.isoformat(),
        }
        cache.set(_cache_key(attempt.id), meta, timeout=duration * 60 + 3600)

        ctx = {'request': request, 'attempt_secret': secret, 'option_salts': option_salts}
        resp = {
            "attempt_id": attempt.id,
            "theme_id": str(theme.id),
            "test_id": str(test.id),
            "scope": scope,
            "count": len(questions),
            "order": order,
            "mode": mode,
            "duration": duration,
            "expires_at": expires_at,
            "questions": questions,
        }
        ser = AttemptStartResponseSerializer(resp, context=ctx)
        return Response(ser.data, status=201)


class SubmitAnswerView(APIView):

    def post(self, request, attempt_id):
        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
        meta = cache.get(_cache_key(attempt_id))
        if not meta:
            return Response({"detail": "Attempt meta topilmadi yoki muddati o'tgan"}, status=400)

        expires_at = datetime.datetime.fromisoformat(meta["expires_at"])
        if _now() >= expires_at:
            return self._finish_and_response(attempt)

        ser = SubmitAnswerWithTagSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qid = str(ser.validated_data["question_id"])
        oid = str(ser.validated_data["option_id"])
        tag = ser.validated_data["tag"]

        secret = meta["secret"]
        salt = meta["salts"].get(oid)
        payload_true = f"{qid}:{oid}:1:{salt}".encode()
        payload_false = f"{qid}:{oid}:0:{salt}".encode()
        expected_true = hmac.new(secret.encode(), payload_true, hashlib.sha256).hexdigest()
        expected_false = hmac.new(secret.encode(), payload_false, hashlib.sha256).hexdigest()

        if tag == expected_true:
            is_correct = True
        elif tag == expected_false:
            is_correct = False
        else:
            return Response({"detail": "Noto‘g‘ri tag"}, status=400)

        ans = get_object_or_404(Answer, attempt=attempt, question_id=qid)
        selected = get_object_or_404(Option, id=oid, question_id=qid)
        ans.selected_option = selected
        ans.is_correct = is_correct
        ans.save(update_fields=["selected_option", "is_correct"])

        try:
            idx = meta["order_ids"].index(qid)
            if idx + 1 > meta["current_idx"]:
                meta["current_idx"] = idx + 1
        except ValueError:
            pass
        cache.set(_cache_key(attempt_id), meta, timeout=60 * 60)

        return Response({
            "attempt_id": str(attempt.id),
            "question_id": qid,
            "option_id": oid,
            "is_correct": is_correct,
            "current_idx": meta["current_idx"],
            "total": len(meta["order_ids"])
        }, status=200)

    def _finish_and_response(self, attempt):
        if not attempt.finished_at:
            total = attempt.answers.count()
            correct = attempt.answers.filter(is_correct=True).count()
            score = round((correct / total) * 100, 2) if total else 0.0
            attempt.finished_at = _now()
            attempt.duration = int((attempt.finished_at - attempt.started_at).total_seconds() // 60)
            attempt.score = score
            attempt.save(update_fields=["finished_at", "duration", "score"])

        return Response({
            "attempt_id": str(attempt.id),
            "finished": True,
            "correct": attempt.answers.filter(is_correct=True).count(),
            "total": attempt.answers.count(),
            "score": attempt.score
        }, status=200)


class AttemptStateView(APIView):

    def get(self, request, attempt_id):
        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
        meta = cache.get(_cache_key(attempt_id))

        if meta:
            expires_at = datetime.datetime.fromisoformat(meta["expires_at"])
            if _now() >= expires_at and not attempt.finished_at:
                attempt.finished_at = _now()
                total = attempt.answers.count()
                correct = attempt.answers.filter(is_correct=True).count()
                attempt.score = round((correct / total) * 100, 2) if total else 0.0
                attempt.save(update_fields=["finished_at", "score"])
            current_idx = meta.get("current_idx", 0)
            total = len(meta.get("order_ids", []))
        else:
            expires_at = _expires(attempt.started_at, attempt.test.default_duration)
            current_idx = attempt.answers.exclude(selected_option__isnull=True).count()
            total = attempt.answers.count()

        answered = attempt.answers.exclude(selected_option__isnull=True).count()
        correct  = attempt.answers.filter(is_correct=True).count()
        out = {
            "attempt_id": attempt.id,
            "started_at": attempt.started_at,
            "expires_at": expires_at,
            "finished_at": attempt.finished_at,
            "current_idx": current_idx,
            "total": total,
            "answered": answered,
            "correct": correct,
            "score": attempt.score,
        }
        return Response(AttemptStateSerializer(out).data, status=200)


class AttemptFinishView(APIView):

    def post(self, request, attempt_id):
        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)

        total = attempt.answers.count()
        correct = attempt.answers.filter(is_correct=True).count()
        score = round((correct / total) * 100, 2) if total else 0.0

        if not attempt.finished_at:
            attempt.finished_at = _now()
            attempt.duration = int((attempt.finished_at - attempt.started_at).total_seconds() // 60)
            attempt.score = score
            attempt.save(update_fields=["finished_at", "duration", "score"])

        out = {
            "attempt_id": attempt.id,
            "correct": correct,
            "total": total,
            "score": score,
        }
        return Response(AttemptFinishResponseSerializer(out).data, status=200)

class TestAttemptResultsView(APIView):

    def get(self, request, test_id):
        test = get_object_or_404(Test, id=test_id)

        attempts = TestAttempt.objects.filter(test=test).select_related("user")

        mode = request.query_params.get("mode")
        order = request.query_params.get("order")

        if mode in ("sequential", "all_in_one"):
            attempts = attempts.filter(mode=mode)
        if order in ("random", "sequential"):
            attempts = attempts.filter(order=order)

        attempts = attempts.order_by("-score", "-correct", "duration")

        ser = AttemptResultSerializer(attempts, many=True)
        return Response(ser.data, status=200)


class MyProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ser = UserProfileSerializer(request.user, context={"request": request})
        return Response(ser.data, status=200)


class UserProfileView(APIView):

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        ser = UserProfileSerializer(user, context={"request": request})
        return Response(ser.data, status=200)


class UserActivityStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        stats = (
            TestAttempt.objects
            .filter(user=user)
            .annotate(day=TruncDate("started_at"))
            .values("day")
            .annotate(attempts=Count("id"))
            .order_by("day")
        )

        data = [
            {"date": row["day"], "attempts": row["attempts"]}
            for row in stats
        ]
        return Response(data, status=200)

class UserRatingListView(ListAPIView):
    serializer_class = UserRatingSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["username", "first_name", "last_name", "email"]
    filter_backends = [filters.SearchFilter]

    def get_queryset(self):
        filter_type = self.request.query_params.get("filter", "best_avg")
        group_id = self.request.query_params.get("group_id")
        subject_id = self.request.query_params.get("subject_id")
        theme_id = self.request.query_params.get("theme_id")

        qs = User.objects.all()

        if group_id:
            qs = qs.filter(group_id=group_id)

        if subject_id:
            qs = qs.filter(attempts__test__theme__subject_id=subject_id)

        if theme_id:
            qs = qs.filter(attempts__test__theme_id=theme_id)

        if filter_type == "most_attempts":
            qs = qs.order_by("-total_attempts")
        elif filter_type == "least_attempts":
            qs = qs.order_by("total_attempts")
        elif filter_type == "worst_avg":
            qs = qs.order_by("average_score")
        else:
            qs = qs.order_by("-average_score")

        return qs.distinct()


class SubjectStatsView(APIView):

    def get(self, request, subject_id):
        subject = get_object_or_404(Subject, id=subject_id)

        attempts = TestAttempt.objects.filter(
            test__theme__subject=subject,
            finished_at__isnull=False
        )

        activity = (
            attempts.annotate(day=TruncDate("started_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        total_attempts = attempts.count()
        avg_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0.0
        avg_duration = attempts.aggregate(avg=Avg("duration"))["avg"] or 0.0
        total_questions = Answer.objects.filter(attempt__in=attempts).count()
        total_correct = Answer.objects.filter(attempt__in=attempts, is_correct=True).count()
        total_wrong = Answer.objects.filter(attempt__in=attempts, is_correct=False).count()

        top_users_qs = (
            attempts.values("user__id", "user__username")
            .annotate(avg_score=Avg("score"), attempts=Count("id"))
            .order_by("-avg_score")
        )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(top_users_qs, request)
        serializer = UserStatSerializer(page, many=True)

        return paginator.get_paginated_response({
            "subject": subject.name,
            "total_attempts": total_attempts,
            "avg_score": round(avg_score, 2),
            "avg_duration": round(avg_duration, 2),
            "total_questions": total_questions,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "activity": list(activity),
            "top_users": serializer.data,
        })


class ThemeStatsView(APIView):

    def get(self, request, theme_id):
        theme = get_object_or_404(Theme, id=theme_id)

        attempts = TestAttempt.objects.filter(
            test__theme=theme,
            finished_at__isnull=False
        )

        activity = (
            attempts.annotate(day=TruncDate("started_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        total_attempts = attempts.count()
        avg_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0.0
        avg_duration = attempts.aggregate(avg=Avg("duration"))["avg"] or 0.0
        total_questions = Answer.objects.filter(attempt__in=attempts).count()
        total_correct = Answer.objects.filter(attempt__in=attempts, is_correct=True).count()
        total_wrong = Answer.objects.filter(attempt__in=attempts, is_correct=False).count()

        top_users_qs = (
            attempts.values("user__id", "user__username")
            .annotate(avg_score=Avg("score"), attempts=Count("id"))
            .order_by("-avg_score")
        )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(top_users_qs, request)
        serializer = UserStatSerializer(page, many=True)

        return paginator.get_paginated_response({
            "theme": theme.name,
            "subject": theme.subject.name,
            "total_attempts": total_attempts,
            "avg_score": round(avg_score, 2),
            "avg_duration": round(avg_duration, 2),
            "total_questions": total_questions,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "activity": list(activity),
            "top_users": serializer.data,
        })


class ProfilePhotoUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ProfilePhotoUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "Profile rasmi yangilandi",
                "profile_photo_url": request.build_absolute_uri(request.user.profile_photo.url),
            },
            status=201,
        )

    def delete(self, request):
        user = request.user
        if user.profile_photo:
            user.profile_photo.delete(save=False)
            user.profile_photo = None
            user.save(update_fields=["profile_photo"])
            return Response({"detail": "Profile rasmi o'chirildi"}, status=200)
        return Response({"detail": "Profil rasmi mavjud emas"}, status=400)


class ThemeStatsView(APIView):

    def get(self, request, theme_id):
        theme = get_object_or_404(Theme, id=theme_id)

        attempts = TestAttempt.objects.filter(
            test__theme=theme,
            finished_at__isnull=False
        )

        activity = (
            attempts.annotate(day=TruncDate("started_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        total_attempts = attempts.count()
        avg_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0.0
        avg_duration = attempts.aggregate(avg=Avg("duration"))["avg"] or 0.0
        total_questions = Answer.objects.filter(attempt__in=attempts).count()
        total_correct = Answer.objects.filter(attempt__in=attempts, is_correct=True).count()
        total_wrong = Answer.objects.filter(attempt__in=attempts, is_correct=False).count()

        return Response({
            "theme": theme.name,
            "subject": theme.subject.name,
            "total_attempts": total_attempts,
            "avg_score": round(avg_score, 2),
            "avg_duration": round(avg_duration, 2),
            "total_questions": total_questions,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "activity": list(activity),
        })


class ThemeTopUsersView(ListAPIView):
    serializer_class = TopAttemptSerializer

    def get_queryset(self):
        theme = get_object_or_404(Theme, id=self.kwargs["theme_id"])

        base = (
            TestAttempt.objects
            .filter(test__theme=theme, finished_at__isnull=False)
            .select_related("user", "test")
            .annotate(
                correct_count=Count("answers", filter=Q(answers__is_correct=True)),
                wrong_count=Count("answers", filter=Q(answers__is_correct=False)),
                total_questions=Count("answers"),
            )
        )

        ranked = base.annotate(
            rn=Window(
                expression=RowNumber(),
                partition_by=[F("user_id")],
                order_by=[
                    OrderBy(F("correct_count"), descending=True),
                    OrderBy(F("duration"), descending=False),
                    OrderBy(F("score"), descending=True),
                    OrderBy(F("finished_at"), descending=False),
                ],
            )
        )

        return (
            ranked.filter(rn=1)
            .order_by("-correct_count", "duration", "-score", "finished_at")
        )
        
class CreateTheme(CreateAPIView):
    queryset = Theme.objects.all()
    serializer_class = ThemeSerializer
    
class CreateSubject(CreateAPIView):
    queryset = Subject.objects.all()
    serializer_class = CreateSubjectSerializer
    

class GroupThemesView(ListAPIView):
    serializer_class = ThemeBasicInfoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs["group_id"]
        return Theme.objects.filter(subject__groups__id=group_id)

class GroupSubjectsView(ListAPIView):
    serializer_class = SubjectBasicSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        group_id = self.kwargs["group_id"]
        return Subject.objects.filter(groups__id=group_id)

class QuestionCreateView(APIView):
    def post(self, request):
        serializer = QuestionCreateSerializer(data=request.data)
        if serializer.is_valid():
            question = serializer.save()
            return Response(
                {
                    "status": 201,
                    "message": "Savol muvaffaqiyatli yaratildi",
                    "data": QuestionCreateSerializer(question).data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)