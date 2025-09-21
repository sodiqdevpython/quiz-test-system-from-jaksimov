from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Group, User, Category, Subject, Theme, 
    TestImportFile, Test, Question, Option, 
    TestAttempt, Answer
)
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm


# -----------------------
# 1) Basic modellar
# -----------------------
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'kurs', 'created']
    list_filter = ['kurs', 'created']
    search_fields = ['name']


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "role", "group", "first_name", "last_name", "profile_photo")

class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = ("username","first_name","last_name","role", "group", "is_active", "profile_photo")

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = ("username", "first_name", "last_name", "role")
    list_filter = ("role", "group", "date_joined")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("date_joined",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email", "profile_photo")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("Extra info", {"fields": ("role", "group")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username",'first_name','last_name','email',"role", "group", "password1", "password2", "profile_photo"),
        }),
    )

    class Media:
        js = ("user_admin.js",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'subjects_count', 'created']
    search_fields = ['name']
    
    def subjects_count(self, obj):
        return obj.subjects.count()
    subjects_count.short_description = 'Fanlar soni'


# -----------------------
# 2) Subject va Theme
# -----------------------
class ThemeInline(admin.TabularInline):
    model = Theme
    extra = 0
    fields = ['name', 'duration', 'created']
    readonly_fields = ['created']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'theme_count', 'authors_list', 'created']
    list_filter = ['category', 'created']
    search_fields = ['name', 'category__name']
    filter_horizontal = ['authors', 'groups']
    inlines = [ThemeInline]
    
    def authors_list(self, obj):
        return ", ".join([author.username for author in obj.authors.all()[:3]])
    authors_list.short_description = 'Mualliflar'


# -----------------------
# 3) Theme va TestImportFile
# -----------------------
class TestImportFileInline(admin.TabularInline):
    model = TestImportFile
    extra = 1
    fields = ['file', 'created']
    readonly_fields = ['created']


class TestInline(admin.TabularInline):
    model = Test
    extra = 0
    fields = ['name', 'question_count', 'default_duration', 'created']
    readonly_fields = ['question_count', 'created']


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'duration', 'tests_count', 'created']
    list_filter = ['subject', 'duration', 'created']
    search_fields = ['name', 'subject__name']
    inlines = [TestImportFileInline, TestInline]
    
    def tests_count(self, obj):
        return obj.tests.count()
    tests_count.short_description = 'Testlar soni'


@admin.register(TestImportFile)
class TestImportFileAdmin(admin.ModelAdmin):
    list_display = ['theme', 'file', 'created']
    list_filter = ['created', 'theme__subject']
    search_fields = ['theme__name', 'file']


# -----------------------
# 4) Test, Question, Option
# -----------------------
class OptionInline(admin.TabularInline):
    model = Option
    extra = 4
    max_num = 4
    fields = ['text', 'image', 'is_correct']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['text', 'image']
    readonly_fields = ['text', 'image']


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['name', 'theme', 'question_count', 'default_duration', 'attempts_count', 'created']
    list_filter = ['theme__subject', 'default_duration', 'created']
    search_fields = ['name', 'theme__name']
    inlines = [QuestionInline]
    
    def attempts_count(self, obj):
        return obj.attempts.count()
    attempts_count.short_description = 'Urinishlar soni'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'test', 'text_preview', 'has_image', 'options_count', 'created']
    list_filter = ['test', 'created']
    search_fields = ['text', 'test__name']
    inlines = [OptionInline]
    
    def text_preview(self, obj):
        if obj.text:
            return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
        return "Rasm"
    text_preview.short_description = 'Savol'
    
    def has_image(self, obj):
        return format_html(
            '<span style="color: green;">✓</span>' if obj.image else 
            '<span style="color: red;">✗</span>'
        )
    has_image.short_description = 'Rasm'
    
    def options_count(self, obj):
        return obj.options.count()
    options_count.short_description = 'Variantlar'


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'text_preview', 'has_image', 'is_correct']
    list_filter = ['is_correct', 'question__test', 'created']
    search_fields = ['text', 'question__text']
    
    def text_preview(self, obj):
        if obj.text:
            return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
        return "Rasm"
    text_preview.short_description = 'Variant'
    
    def has_image(self, obj):
        return format_html(
            '<span style="color: green;">✓</span>' if obj.image else 
            '<span style="color: red;">✗</span>'
        )
    has_image.short_description = 'Rasm'


# -----------------------
# 5) TestAttempt va Answer
# -----------------------
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    fields = ['question', 'selected_option', 'is_correct']
    readonly_fields = ['question', 'selected_option', 'is_correct']


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'mode', 'score', 'duration', 'started_at', 'finished_at']
    list_filter = ['mode', 'started_at', 'finished_at', 'test__theme__subject']
    search_fields = ['user__username', 'test__name']
    inlines = [AnswerInline]
    readonly_fields = ['started_at', 'finished_at', 'score', 'duration']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt_info', 'question_preview', 'selected_option_preview', 'is_correct']
    list_filter = ['is_correct', 'attempt__test', 'attempt__started_at']
    search_fields = ['attempt__user__username', 'question__text']
    
    def attempt_info(self, obj):
        return f"{obj.attempt.user.username} - {obj.attempt.test.name}"
    attempt_info.short_description = 'Urinish'
    
    def question_preview(self, obj):
        return obj.question.text[:30] + '...' if obj.question.text and len(obj.question.text) > 30 else obj.question.text or "Rasm"
    question_preview.short_description = 'Savol'
    
    def selected_option_preview(self, obj):
        if obj.selected_option:
            text = obj.selected_option.text
            return text[:30] + '...' if text and len(text) > 30 else text or "Rasm"
        return "Tanlanmagan"
    selected_option_preview.short_description = 'Tanlangan variant'