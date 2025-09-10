from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Group, User, Category, Subject, Theme
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    GroupSerializer, UserSerializer, AttemptStartQuerySerializer, AttemptStartResponseSerializer,AttemptStateSerializer,
    CategorySerializer, SubjectSerializer, ThemeSerializer, ThemeListSerializer, SubmitAnswerWithTagSerializer,
    AttemptFinishResponseSerializer
)
from .models import (
    Question, Test, TestAttempt, Answer, Option
)
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.shortcuts import get_object_or_404
import random, secrets, datetime, hmac, hashlib



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





CACHE_PREFIX = "attempt_meta:"

def _cache_key(attempt_id):
    return f"{CACHE_PREFIX}{attempt_id}"

def _now():
    return timezone.now()

def _expires(started_at, minutes):
    return started_at + datetime.timedelta(minutes=minutes)


class AttemptStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, theme_id):
        q = AttemptStartQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        count = q.validated_data["count"]
        order = q.validated_data["order"]
        mode  = q.validated_data["mode"]
        custom_duration = q.validated_data.get("duration")

        theme = get_object_or_404(Theme, id=theme_id)
        test = Test.objects.filter(theme=theme).order_by("created").first()
        if test is None:
            test = Test.objects.create(theme=theme, name=f"Auto ({theme.name})")

        # Old attempt tekshir
        active_attempt = TestAttempt.objects.filter(
            test=test, user=request.user, finished_at__isnull=True
        ).order_by("-started_at").first()

        if active_attempt:
            meta = cache.get(_cache_key(active_attempt.id))
            if meta:
                expires_at = datetime.datetime.fromisoformat(meta["expires_at"])
                if _now() < expires_at:
                    # Resume old attempt
                    questions = [ans.question for ans in active_attempt.answers.select_related("question")]
                    ctx = {
                        'request': request,
                        'attempt_secret': meta["secret"],
                        'option_salts': meta["salts"],
                    }
                    resp = {
                        "attempt_id": active_attempt.id,
                        "theme_id": str(theme.id),
                        "test_id": str(test.id),
                        "count": len(questions),
                        "order": order,
                        "mode": mode,
                        "duration": custom_duration or test.default_duration,
                        "expires_at": expires_at,
                        "questions": questions,
                    }
                    ser = AttemptStartResponseSerializer(resp, context=ctx)
                    return Response(ser.data, status=200)
            # expired bo‘lsa finish qilamiz
            active_attempt.finished_at = _now()
            active_attempt.save(update_fields=["finished_at"])

        # Yangi attempt
        pool = Question.objects.filter(test__theme=theme).prefetch_related("options").order_by("created")
        total = pool.count()
        if total == 0:
            return Response({"detail": "Bu mavzuda savollar yo‘q"}, status=400)

        n = min(count, total)
        if order == "random":
            ids = list(pool.values_list("id", flat=True))
            chosen_ids = set(random.sample(ids, n))
            questions = [q for q in pool if q.id in chosen_ids]
        else:
            questions = list(pool[:n])

        attempt = TestAttempt.objects.create(test=test, user=request.user, mode=mode)
        Answer.objects.bulk_create([Answer(attempt=attempt, question=qobj) for qobj in questions])

        duration = custom_duration or test.default_duration
        expires_at = _expires(attempt.started_at, duration)

        # Secret + salts
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
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, attempt_id):
        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
        meta = cache.get(_cache_key(attempt_id))
        if not meta:
            return Response({"detail": "Attempt meta topilmadi yoki muddati o‘tgan"}, status=400)

        expires_at = datetime.datetime.fromisoformat(meta["expires_at"])
        if _now() >= expires_at:
            return self._finish_and_response(attempt)

        ser = SubmitAnswerWithTagSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        qid = str(ser.validated_data["question_id"])
        oid = str(ser.validated_data["option_id"])
        tag = ser.validated_data["tag"]

        # HMAC check
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

        # progress
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
            "total": len(meta["order_ids"]),
            "remaining_seconds": max(0, int((expires_at - _now()).total_seconds()))
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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, attempt_id):
        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
        meta = cache.get(_cache_key(attempt_id))

        if meta:
            expires_at = datetime.datetime.fromisoformat(meta["expires_at"])
            if _now() >= expires_at and not attempt.finished_at:
                # ❗ Tugaganini belgilaymiz
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
    permission_classes = [permissions.IsAuthenticated]

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

