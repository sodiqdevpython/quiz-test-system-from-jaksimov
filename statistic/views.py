from rest_framework.views import APIView
from django.shortcuts import render
from rest_framework.response import Response
from mainApp.models import User, TestAttempt, Group, Test, Answer, Question, Subject, Theme
from django.db.models import Avg, Sum, Count, Max, Min
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.generics import ListAPIView
from django.db.models import Q
from rest_framework import generics
from .serializers import (
    SubjectStatSerializer, GroupStatInSubjectSerializer,
    UserStatSerializer
)


@method_decorator(cache_page(60 * 1), name="dispatch")
class UserFullStatsView(APIView):

    def get(self, request):
        qs = User.objects.all()

        total_users = qs.count()
        students_count = qs.filter(role="student").count()
        teachers_count = qs.filter(role="teacher").count()
        admins_count = qs.filter(role="admin").count()

        groups_count = qs.exclude(group=None).values("group").distinct().count()

        total_attempts_sum = qs.aggregate(total=Sum("total_attempts"))["total"] or 0
        avg_attempts_per_user = round(total_attempts_sum / total_users, 2) if total_users > 0 else 0

        global_avg_score = qs.aggregate(avg=Avg("average_score"))["avg"] or 0.0

        global_avg_attempt_score = TestAttempt.objects.aggregate(avg=Avg("score"))["avg"] or 0.0
        
        groups_stats = (
            Group.objects.annotate(user_count=Count("user"))
            .values("id", "name", "kurs", "user_count")
        )

        data = {
            "total_users": total_users,
            "students_count": students_count,
            "teachers_count": teachers_count,
            "admins_count": admins_count,
            "groups_count": groups_count,
            "total_attempts_sum": total_attempts_sum,
            "avg_attempts_per_user": avg_attempts_per_user,
            "global_avg_score": round(global_avg_score, 2),
            "global_avg_attempt_score": round(global_avg_attempt_score, 2),
            "groups_stats": list(groups_stats),
        }

        return Response(data)
    
# @method_decorator(cache_page(60 * 1), name="dispatch")
class TestStatsView(APIView):

    def get(self, request):
        attempts = TestAttempt.objects.all()
        answers = Answer.objects.all()

        total_tests = Question.objects.count()

        total_attempts = attempts.count()
        avg_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0.0

        # Javoblar statistikasi
        total_answers = answers.count()
        correct_answers = answers.filter(is_correct=True).count()
        wrong_answers = total_answers - correct_answers

        data = {
            "total_tests": total_tests,
            "total_attempts": total_attempts,
            "avg_score": round(avg_score, 2),
            "total_answers": total_answers,
            "correct_answers": correct_answers,
            "wrong_answers": wrong_answers,
        }

        return Response(data)
    


class SubjectThemeStatsView(ListAPIView):
    """
    GET /subjects/<subject_id>/stats
    GET /subjects/<subject_id>/themes/<theme_id>/stats
    """

    def get_queryset(self):
        subject_id = self.kwargs.get("subject_id")
        theme_id = self.kwargs.get("theme_id")

        subject_attempts = TestAttempt.objects.filter(test__theme__subject_id=subject_id)

        qs = User.objects.filter(role="student")

        if theme_id:
            qs = qs.filter(attempts__test__theme_id=theme_id)
        else:
            qs = qs.filter(attempts__test__theme__subject_id=subject_id)

        qs = qs.annotate(
            total_attempts=Count("total_attempts", filter=Q(attempts__in=subject_attempts)),
            avg_score=Avg("attempts__score", filter=Q(attempts__in=subject_attempts)),
        ).order_by("-avg_score")

        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        subject_id = kwargs.get("subject_id")
        theme_id = kwargs.get("theme_id")

        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            return Response({"detail": "Fan topilmadi"}, status=404)

        subject_attempts = TestAttempt.objects.filter(test__theme__subject=subject)

        subject_stats = {
            "subject_id": str(subject.id),
            "subject_name": subject.name,
            "total_themes": subject.themes.count(),
            "total_tests": subject.themes.aggregate(cnt=Count("tests"))["cnt"] or 0,
            "total_attempts": subject_attempts.count(),
            "avg_score": round(subject_attempts.aggregate(avg=Avg("score"))["avg"] or 0, 2),
        }

        data = {"subject_stats": subject_stats}

        if theme_id:
            try:
                theme = Theme.objects.get(id=theme_id, subject=subject)
            except Theme.DoesNotExist:
                return Response({"detail": "Mavzu topilmadi"}, status=404)

            theme_attempts = subject_attempts.filter(test__theme=theme)
            data["theme_stats"] = {
                "theme_id": str(theme.id),
                "theme_name": theme.name,
                "total_tests": theme.tests.count(),
                "total_attempts": theme_attempts.count(),
                "avg_score": round(theme_attempts.aggregate(avg=Avg("score"))["avg"] or 0, 2),
            }

        data["leaderboard"] = response.data
        return Response(data)


class SubjectStatView(generics.RetrieveAPIView):
    serializer_class = SubjectStatSerializer

    def get_object(self):
        subject_id = self.kwargs["pk"]
        subject = Subject.objects.get(id=subject_id)
        user = self.request.user

        qs = User.objects.filter(
            role="student",
            attempts__test__theme__subject=subject,
        )

        # student uchun cheklov
        if user.role == "student" and user.group:
            qs = qs.filter(group__kurs=user.group.kurs)

        stats = qs.aggregate(
            student_count=Count("id", distinct=True),
            avg_score=Avg("average_score"),
        )

        return {
            "subject_id": subject.id,
            "subject_name": subject.name,
            **stats,
        }


# --------------------------
# Subject bo‘yicha guruhlar statistikasi
# --------------------------
class GroupStatInSubjectView(generics.ListAPIView):
    serializer_class = GroupStatInSubjectSerializer

    def get_queryset(self):
        subject_id = self.kwargs["pk"]
        user = self.request.user

        qs = Group.objects.filter(
            user__role="student",
            user__attempts__test__theme__subject_id=subject_id,
        )

        if user.role == "student" and user.group:
            qs = qs.filter(
                id=user.group_id,
                kurs=user.group.kurs,
            )

        return qs.distinct().annotate(
            student_count=Count("user", filter=Q(user__role="student"), distinct=True),
            avg_score=Avg("user__average_score"),
            total_attempts=Sum("user__total_attempts"),
        )


# --------------------------
# Subject + Guruh bo‘yicha foydalanuvchilar statistikasi
# --------------------------
class GroupUserStatInSubjectView(generics.ListAPIView):
    serializer_class = UserStatSerializer

    def get_queryset(self):
        subject_id = self.kwargs["subject_id"]
        group_id = self.kwargs["group_id"]
        user = self.request.user

        qs = User.objects.filter(
            role="student",
            group_id=group_id,
            attempts__test__theme__subject_id=subject_id,
        )

        if user.role == "student" and user.group:
            qs = qs.filter(
                group_id=user.group.id,
                group__kurs=user.group.kurs,
            )

        return qs.distinct().order_by("-average_score")