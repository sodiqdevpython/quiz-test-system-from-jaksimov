from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Question, Theme, TestImportFile, TestAttempt, Answer
import os
from django.db import models

# Global flag ikki marta parse qilishni oldini olish uchun
_currently_parsing = set()


@receiver(post_save, sender=TestImportFile)
def parse_test_file_on_save(sender, instance, created, **kwargs):
    """TestImportFile saqlanganda avtomatik parse qilish"""

    # Faqat yangi fayl create qilinganda ishlaydi
    if not created:
        return

    # Ikki marta parse qilishni oldini olish
    file_key = f"{instance.id}_{instance.file.name}"
    if file_key in _currently_parsing:
        print(f"Parse jarayonida: {instance.file.name}")
        return

    _currently_parsing.add(file_key)

    try:
        print(f"Signal ishga tushdi (yangi fayl): {instance.file.name}")

        if instance.file:
            try:
                # Faylni parse qilish
                from utils.parsers import parse_word_file_advanced, save_image_to_django

                print(f"Fayl yo'li: {instance.file.path}")
                print(f"Fayl mavjud: {os.path.exists(instance.file.path)}")

                # Parse qilish
                questions_data = parse_word_file_advanced(instance.file.path)
                print(f"Parse qilingan savollar soni: {len(questions_data)}")

                if not questions_data:
                    print("OGOHLANTIRISH: Hech qanday savol topilmadi!")
                    return

                # Test yaratish
                from .models import Test, Question, Option

                test_name = f"Auto test - {os.path.basename(instance.file.name)}"
                test = Test.objects.create(
                    theme=instance.theme,
                    name=test_name,
                    default_duration=30
                )
                print(f"Test yaratildi: {test}")

                # Savollar va variantlarni yaratish
                created_questions = 0
                for i, q_data in enumerate(questions_data, 1):
                    try:
                        print(f"Savol {i} yaratilmoqda: {q_data.get('text', '')[:50]}...")

                        if not q_data.get('text'):
                            print(f"  Savol {i} bo'sh, o'tkazib yuborildi")
                            continue

                        # Savolni yaratish
                        question = Question.objects.create(
                            test=test,
                            text=q_data.get("text", "")
                        )

                        # Savol rasmini saqlash
                        if q_data.get('image_data'):
                            try:
                                image_file = save_image_to_django(
                                    q_data['image_data'],
                                    q_data['image_data']['extension'],
                                    prefix=f"question_{str(question.id)[:8]}"
                                )
                                if image_file:
                                    question.image.save(
                                        image_file.name,
                                        image_file,
                                        save=False  # Signal chaqirilmasligi uchun
                                    )
                                    question.save(update_fields=['image'])  # Faqat image fieldini yangilash
                                    print(f"    Savol rasmi saqlandi: {image_file.name}")
                            except Exception as e:
                                print(f"    Savol rasmi saqlashda xatolik: {e}")

                        # Variantlarni yaratish
                        created_options = 0
                        for opt_data in q_data.get("options", []):
                            if not opt_data.get('text'):
                                continue

                            option = Option.objects.create(
                                question=question,
                                text=opt_data.get("text", ""),
                                is_correct=opt_data.get("is_correct", False)
                            )

                            # Variant rasmini saqlash
                            if opt_data.get('image_data'):
                                try:
                                    image_file = save_image_to_django(
                                        opt_data['image_data'],
                                        opt_data['image_data']['extension'],
                                        prefix=f"option_{str(option.id)[:8]}"
                                    )
                                    if image_file:
                                        option.image.save(
                                            image_file.name,
                                            image_file,
                                            save=True
                                        )
                                        print(f"      Variant rasmi saqlandi: {image_file.name}")
                                except Exception as e:
                                    print(f"      Variant rasmi saqlashda xatolik: {e}")

                            created_options += 1
                            status = "✓" if opt_data.get('is_correct') else "✗"
                            img_status = "📷" if opt_data.get('image_data') else ""
                            print(f"    Variant yaratildi: {opt_data.get('text', '')[:30]} ({status}) {img_status}")

                        if created_options > 0:
                            created_questions += 1
                        else:
                            # Agar variantlar yaratilmagan bo'lsa, savolni ham o'chirish
                            question.delete()
                            print(f"  Savol {i} o'chirildi (variantlar yo'q)")

                    except Exception as e:
                        print(f"  Savol {i} yaratishda xatolik: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue

                # Test savollar sonini yangilash (signalsiz)
                Test.objects.filter(id=test.id).update(question_count=test.questions.count())

                print(f"\n=== YAKUNIY NATIJA ===")
                print(f"Test nomi: {test.name}")
                print(f"Yaratilgan savollar: {created_questions}")
                print(f"Jami savollar: {test.questions.count()}")

                if test.questions.count() == 0:
                    test.delete()
                    print("Test o'chirildi (savollar yo'q)")

            except ImportError as e:
                print(f"KUTUBXONA XATOLIGI: {str(e)}")
                print("python-docx kutubxonasini o'rnating: pip install python-docx")

            except Exception as e:
                print(f"UMUMIY XATOLIK: {str(e)}")
                import traceback
                traceback.print_exc()

    finally:
        # Parse tugagach flagni olib tashlash
        _currently_parsing.discard(file_key)


@receiver(post_save, sender=Question)
def update_test_question_count(sender, instance, created, **kwargs):
    """Test da savollar soni yangilanganda - faqat manual yaratilganda"""
    # Agar parse jarayonida bo'lsa, signal ishlamasin
    if any(str(instance.test.theme.id) in key for key in _currently_parsing):
        return

    test = instance.test
    test.question_count = test.questions.count()
    test.save()


@receiver(post_delete, sender=Question)
def update_test_question_count_on_delete(sender, instance, **kwargs):
    """Savol o'chirilganda test dagi sonni yangilash"""
    test = instance.test
    test.question_count = test.questions.count()
    test.save()


@receiver(post_save, sender=Theme)
def update_subject_theme_count(sender, instance, **kwargs):
    """Subject da mavzular soni yangilash"""
    subject = instance.subject
    subject.theme_count = subject.themes.count()
    subject.save()


@receiver(post_delete, sender=Theme)
def update_subject_theme_count_on_delete(sender, instance, **kwargs):
    """Mavzu o'chirilganda fan dagi sonni yangilash"""
    subject = instance.subject
    subject.theme_count = subject.themes.count()
    subject.save()
    


@receiver(post_save, sender=TestAttempt)
def update_user_stats(sender, instance, created, **kwargs):
    """
    Har safar TestAttempt tugasa (finished_at != None),
    foydalanuvchi umumiy statistikasi qayta hisoblanadi.
    """
    if instance.finished_at:  # faqat tugallanganda
        user = instance.user

        # Barcha attemptlarini olib qayta hisoblash
        attempts = user.attempts.filter(finished_at__isnull=False)

        total_attempts = attempts.count()
        total_correct = Answer.objects.filter(attempt__in=attempts, is_correct=True).count()
        total_wrong = Answer.objects.filter(attempt__in=attempts, is_correct=False).count()

        # O‘rtacha ball = barcha attemptlarning score o‘rtachasi
        avg_score = attempts.aggregate(avg=models.Avg("score"))["avg"] or 0.0

        # Foydalanuvchini yangilash
        user.total_attempts = total_attempts
        user.total_correct = total_correct
        user.total_wrong = total_wrong
        user.average_score = round(avg_score, 2)
        user.save(update_fields=["total_attempts", "total_correct", "total_wrong", "average_score"])
    
