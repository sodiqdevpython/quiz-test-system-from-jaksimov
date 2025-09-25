import os
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Question, Theme, TestImportFile, TestAttempt, Answer, Test, Option
from django.db import models

_currently_parsing = set()


@receiver(post_save, sender=TestImportFile)
def parse_test_file_on_save(sender, instance, created, **kwargs):
    if not created:
        return

    file_key = f"{instance.id}_{instance.file.name}"
    if file_key in _currently_parsing:
        print(f"Parse jarayonida: {instance.file.name}")
        return

    _currently_parsing.add(file_key)

    try:
        print(f"Signal ishga tushdi (yangi fayl): {instance.file.name}")

        if instance.file:
            try:
                from utils.parsers import parse_word_file_advanced, save_image_to_django

                print(f"Fayl yo'li: {instance.file.path}")
                print(f"Fayl mavjud: {os.path.exists(instance.file.path)}")
                questions_data = parse_word_file_advanced(instance.file.path)
                print(f"Parse qilingan savollar soni: {len(questions_data)}")

                if not questions_data:
                    print("OGOHLANTIRISH: Hech qanday savol topilmadi!")
                    return

                

                test_name = f"Auto test - {os.path.basename(instance.file.name)}"
                test = Test.objects.create(
                    theme=instance.theme,
                    name=test_name,
                    default_duration=30
                )
                print(f"Test yaratildi: {test}")

                created_questions = 0
                for i, q_data in enumerate(questions_data, 1):
                    try:
                        print(f"Savol {i} yaratilmoqda: {q_data.get('text', '')[:50]}...")

                        if not q_data.get('text'):
                            print(f"  Savol {i} bo'sh, o'tkazib yuborildi")
                            continue

                        question = Question.objects.create(
                            test=test,
                            text=q_data.get("text", "")
                        )

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
                                        save=False 
                                    )
                                    question.save(update_fields=['image'])
                                    print(f"    Savol rasmi saqlandi: {image_file.name}")
                            except Exception as e:
                                print(f"    Savol rasmi saqlashda xatolik: {e}")

                        created_options = 0
                        for opt_data in q_data.get("options", []):
                            if not opt_data.get('text'):
                                continue

                            option = Option.objects.create(
                                question=question,
                                text=opt_data.get("text", ""),
                                is_correct=opt_data.get("is_correct", False)
                            )

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
                            print(f" Variant yaratildi: {opt_data.get('text', '')[:30]} ({status}) {img_status}")

                        if created_options > 0:
                            created_questions += 1
                        else:
                            question.delete()
                            print(f"  Savol {i} o'chirildi (variantlar yo'q)")

                    except Exception as e:
                        print(f"  Savol {i} yaratishda xatolik: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue

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
        _currently_parsing.discard(file_key)


@receiver(post_save, sender=Question)
def update_test_question_count(sender, instance, created, **kwargs):
    if any(str(instance.test.theme.id) in key for key in _currently_parsing):
        return

    test = instance.test
    test.question_count = test.questions.count()
    test.save()


@receiver(post_delete, sender=Question)
def update_test_question_count_on_delete(sender, instance, **kwargs):
    test = instance.test
    test.question_count = test.questions.count()
    test.save()


@receiver(post_save, sender=Theme)
def update_subject_theme_count(sender, instance, **kwargs):
    subject = instance.subject
    subject.theme_count = subject.themes.count()
    subject.save()


@receiver(post_delete, sender=Theme)
def update_subject_theme_count_on_delete(sender, instance, **kwargs):
    subject = instance.subject
    subject.theme_count = subject.themes.count()
    subject.save()
    


@receiver(post_save, sender=TestAttempt)
def update_user_stats(sender, instance, created, **kwargs):
    if instance.finished_at:
        user = instance.user
        attempts = user.attempts.filter(finished_at__isnull=False)

        total_attempts = attempts.count()
        total_correct = Answer.objects.filter(attempt__in=attempts, is_correct=True).count()
        total_wrong = Answer.objects.filter(attempt__in=attempts, is_correct=False).count()
        avg_score = attempts.aggregate(avg=models.Avg("score"))["avg"] or 0.0
        user.total_attempts = total_attempts
        user.total_correct = total_correct
        user.total_wrong = total_wrong
        user.average_score = round(avg_score, 2)
        user.save(update_fields=["total_attempts", "total_correct", "total_wrong", "average_score"])