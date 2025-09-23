# models.py
from django.db import models
from utils.models import BaseModel
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from ckeditor.fields import RichTextField


# -----------------------
# 1) User va Guruh
# -----------------------
class Group(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Guruh nomi")
    kurs = models.PositiveIntegerField(verbose_name="Kurs")
    
    def __str__(self):
        return f"{self.name} (Kurs {self.kurs})"
    
    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"


class User(BaseModel, AbstractUser):
    email = models.EmailField(null=True, blank=True, verbose_name="Email")
    profile_photo = models.ImageField(upload_to="profile_photo", null=True, blank=True)
    role = models.CharField(max_length=50, choices=[
        ("student", "Talaba"),
        ("teacher", "O'qituvchi"),
        ("admin", "Admin")
    ], default="student", verbose_name="Rol")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Guruh")
    
    total_attempts = models.PositiveIntegerField(default=0)
    total_correct = models.PositiveIntegerField(default=0)
    total_wrong = models.PositiveIntegerField(default=0)
    average_score = models.FloatField(default=0.0) 

    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["group"]),
            models.Index(fields=["average_score"]),
            models.Index(fields=["total_attempts"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                name="unique_email_not_null",
                condition=~models.Q(email=None) & ~models.Q(email="") # NULL ham, "" ham chiqarib tashlanadi
            )
        ]


# -----------------------
# 2) Fanlar
# -----------------------
class Category(BaseModel):
    name = models.CharField(max_length=255, verbose_name="Kategoriya nomi")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        indexes = [
            models.Index(fields=["name"]),
        ]


class Subject(BaseModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subjects", verbose_name="Kategoriya")
    name = models.CharField(max_length=255, verbose_name="Fan nomi")
    description = models.TextField(verbose_name="Umumiy ma'lumot", null=True, blank=True)
    authors = models.ManyToManyField('User', blank=True, verbose_name="Mualliflar")
    theme_count = models.PositiveIntegerField(default=0, verbose_name="Mavzular soni")
    groups = models.ManyToManyField('Group', blank=True, related_name="subjects", verbose_name="Guruhlar")

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["name"]),
        ]

# -----------------------
# 3) Mavzular
# -----------------------
class Theme(BaseModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="themes", verbose_name="Fan")
    name = models.CharField(max_length=255, verbose_name="Mavzu nomi")
    duration = models.PositiveIntegerField(default=0, verbose_name="Davomiyligi (minut)")
    full_html_file = RichTextField(verbose_name="To'liq matn (HTML)", null=True, blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Mavzu"
        verbose_name_plural = "Mavzular"
        indexes = [
            models.Index(fields=["subject"]),
            models.Index(fields=["name"]),
        ]


class TestImportFile(BaseModel):
    """Theme ga bog'langan test import fayl (Word)"""
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="import_files", verbose_name="Mavzu")
    file = models.FileField(
        upload_to="test_imports/",
        validators=[FileExtensionValidator(allowed_extensions=['doc', 'docx'])],
        verbose_name="Test fayli",
        help_text="Doc yoki docx formatdagi faylni yuklang"
    )

    def __str__(self):
        return f"{self.theme.name} -> {self.file.name}"
    
    class Meta:
        verbose_name = "Test Import Fayli"
        verbose_name_plural = "Test Import Fayllari"
        

# -----------------------
# 4) Testlar
# -----------------------
class Test(BaseModel):
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="tests", verbose_name="Mavzu")
    name = models.CharField(max_length=255, verbose_name="Test nomi")
    default_duration = models.PositiveIntegerField(default=30, verbose_name="Standart davomiyligi (minut)")
    question_count = models.PositiveIntegerField(default=0, verbose_name="Savollar soni")

    def __str__(self):
        return f"{self.name} ({self.theme.name})"
    
    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"
        indexes = [
            models.Index(fields=["theme"]),
            models.Index(fields=["name"]),
        ]


class Question(BaseModel):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="questions", verbose_name="Test")
    text = models.TextField(blank=True, null=True, verbose_name="Savol matni")
    image = models.ImageField(upload_to="questions/", blank=True, null=True, verbose_name="Savol rasmi")

    def __str__(self):
        preview = self.text[:50] if self.text else "Rasm"
        return f"Q{self.id} - {preview}"
    
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
        indexes = [
            models.Index(fields=["test"]),
        ]


class Option(BaseModel):
    question = models.ForeignKey(Question, related_name="options", on_delete=models.CASCADE, verbose_name="Savol")
    text = models.TextField(blank=True, null=True, verbose_name="Variant matni")
    image = models.ImageField(upload_to="options/", blank=True, null=True, verbose_name="Variant rasmi")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri javob")

    def __str__(self):
        preview = self.text[:30] if self.text else "Rasm"
        status = "To'g'ri" if self.is_correct else "Noto'g'ri"
        return f"{preview} ({status})"
    
    class Meta:
        verbose_name = "Variant"
        verbose_name_plural = "Variantlar"
        indexes = [
            models.Index(fields=["question"]),
            models.Index(fields=["is_correct"]),
        ]


class TestAttempt(BaseModel):
    MODE_CHOICES = [
        ("sequential", "Ketma-ket rejim"),
        ("all_in_one", "Ko'p qismli rejim"),
    ]
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts", verbose_name="Test")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attempts", verbose_name="Foydalanuvchi")
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="sequential", verbose_name="Rejim")
    started_at = models.DateTimeField(auto_now_add=True, verbose_name="Boshlangan vaqt")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Tugallangan vaqt")
    score = models.FloatField(null=True, blank=True, verbose_name="Ball")
    duration = models.PositiveIntegerField(null=True, blank=True, verbose_name="Sarflangan vaqt (minut)")

    def __str__(self):
        return f"{self.user.username} - {self.test.name} ({self.mode})"
    
    class Meta:
        verbose_name = "Test Urinishi"
        verbose_name_plural = "Test Urinishlari"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["test"]),
            models.Index(fields=["started_at"]),
            models.Index(fields=["finished_at"]),
            models.Index(fields=["score"]),
        ]


class Answer(BaseModel):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="answers", verbose_name="Urinish")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Savol")
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Tanlangan variant")
    is_correct = models.BooleanField(default=False, verbose_name="To'g'ri javob")

    def __str__(self):
        return f"Javob: {self.attempt.user.username} - Q{self.question.id}"
    
    class Meta:
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"
        indexes = [
            models.Index(fields=["attempt"]),
            models.Index(fields=["question"]),
            models.Index(fields=["selected_option"]),
            models.Index(fields=["is_correct"]),
        ]