import docx
import base64
from typing import List, Dict, Any, Optional, Tuple

DOCX_AVAILABLE = True

class WordTestReader:
    def __init__(self):
        self.questions = []
        self.document = None

    def read_test_file(self, file_path):
        if not DOCX_AVAILABLE:
            return {'success': False, 'error': 'python-docx kutubxonasi o\'rnatilmagan', 'questions': []}

        try:
            self.document = docx.Document(file_path)
            print(
                f"Document ochildi. Paragraflar: {len(self.document.paragraphs)}, Jadvallar: {len(self.document.tables)}")

            questions = self._parse_document()
            return {'success': True, 'questions': questions, 'total_questions': len(questions), 'file_path': file_path}

        except Exception as e:
            print(f"Word fayl ochishda xatolik: {str(e)}")
            return {'success': False, 'error': str(e), 'questions': []}

    def _parse_document(self):
        questions = []

        if self.document.tables:
            print("Jadvallar topildi...")
            for table_idx, table in enumerate(self.document.tables):
                table_questions = self._parse_table_with_precise_images(table, table_idx)
                questions.extend(table_questions)

        print(f"Jami topilgan savollar: {len(questions)}")
        return questions

    def _parse_table_with_precise_images(self, table, table_idx):
        questions = []

        try:
            print(
                f"Jadval {table_idx} - {len(table.rows)} qator x {len(table.rows[0].cells) if table.rows else 0} ustun")

            for row_idx, row in enumerate(table.rows):
                if row_idx == 0:
                    continue

                print(f"\nQator {row_idx} tahlil qilinmoqda...")
                cells = row.cells

                if len(cells) >= 5:
                    # ID ni olish
                    id_cell = cells[0]
                    id_text = self._extract_cell_text(id_cell).strip()
                    
                    if not id_text:
                        print("  ID bo'sh - qator tashlandi")
                        continue

                    # Har bitta katakdan rasm bilan text ni ajratib oldin
                    question_cell = cells[1]
                    option_a_cell = cells[2]
                    option_b_cell = cells[3]
                    option_c_cell = cells[4]
                    option_d_cell = cells[5] if len(cells) > 5 else None

                    # Savolga matn bilan rasmnni olganim
                    question_text, question_images = self._extract_text_and_images(question_cell, "Savol")
                    
                    # Agar savolda na matn na rasm bo'lsa, tashlab ketamiz
                    if not question_text and not question_images:
                        print("  Savol katagi butunlay bo'sh - qator tashlandi")
                        continue

                    # A variant
                    option_a_text, option_a_images = self._extract_text_and_images(option_a_cell, "A")
                    # B variant
                    option_b_text, option_b_images = self._extract_text_and_images(option_b_cell, "B")
                    # C variant
                    option_c_text, option_c_images = self._extract_text_and_images(option_c_cell, "C")
                    # D variant
                    option_d_text, option_d_images = "", []
                    if option_d_cell:
                        option_d_text, option_d_images = self._extract_text_and_images(option_d_cell, "D")

                    # Variantlardan kamida bittasida kontent bo'lishi kerak
                    has_valid_options = any([
                        option_a_text or option_a_images,
                        option_b_text or option_b_images, 
                        option_c_text or option_c_images,
                        option_d_text or option_d_images
                    ])
                    
                    if not has_valid_options:
                        print("  Barcha variantlar bo'sh - qator tashlandi")
                        continue

                    question = {
                        'id': id_text,
                        'text': question_text or '',
                        'images': question_images,
                        'image_data': question_images[0] if question_images else None,  # backward compatibility
                        'options': [
                            {
                                'text': option_a_text or '', 
                                'is_correct': True, 
                                'images': option_a_images,
                                'image_data': option_a_images[0] if option_a_images else None
                            },
                            {
                                'text': option_b_text or '', 
                                'is_correct': False, 
                                'images': option_b_images,
                                'image_data': option_b_images[0] if option_b_images else None
                            },
                            {
                                'text': option_c_text or '', 
                                'is_correct': False, 
                                'images': option_c_images,
                                'image_data': option_c_images[0] if option_c_images else None
                            },
                            {
                                'text': option_d_text or '', 
                                'is_correct': False, 
                                'images': option_d_images,
                                'image_data': option_d_images[0] if option_d_images else None
                            }
                        ]
                    }
                    questions.append(question)

                    # Debug
                    text_preview = question_text[:50] + "..." if question_text else "FAQT RASM"
                    print(f"Savol yaratildi: '{text_preview}' | Rasmlar: {len(question_images)} ta")

                    for i, opt in enumerate(question['options']):
                        opt_letter = chr(65 + i)  # A, B, C, D
                        text_preview = opt['text'][:30] + "..." if opt['text'] else "FAQT RASM"
                        print(f"    {opt_letter}) '{text_preview}' {'✓' if opt['is_correct'] else '✗'} | Rasmlar: {len(opt['images'])}")

        except Exception as e:
            print(f"Jadval parse qilishda xato: {e}")
            import traceback
            traceback.print_exc()

        return questions

    def _extract_cell_text(self, cell):
        """Katakdan to'liq matnni olish"""
        text_parts = []
        
        # Oddiy paragraphlar
        for paragraph in cell.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())
        
        # Textbox lardan matn olish
        try:
            cell_xml = cell._tc.xml
            import xml.etree.ElementTree as ET
            from io import StringIO
            
            namespaces = {
                'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                'v': 'urn:schemas-microsoft-com:vml',
                'wps': 'http://schemas.microsoft.com/office/word/2010/wordprocessingShape',
            }
            
            root = ET.fromstring(cell_xml)
            
            # VML textbox
            for textbox in root.findall('.//v:textbox//w:t', namespaces):
                if textbox.text and textbox.text.strip():
                    text_parts.append(textbox.text.strip())
            
            # DrawingML textbox  
            for textbox in root.findall('.//wps:txbx//w:txbxContent//w:t', namespaces):
                if textbox.text and textbox.text.strip():
                    text_parts.append(textbox.text.strip())
                    
        except Exception as e:
            print(f"Textbox matn olishda xato: {e}")
        
        return '\n'.join(text_parts) if text_parts else ''

    def _extract_text_and_images(self, cell, cell_name):
        """Katakdan matn va barcha rasmlarni olish"""
        text = self._extract_cell_text(cell)
        images = []

        try:
            print(f"{cell_name} katakchasi: matn='{text[:30]}...'")

            # 1. Run darajasida rasmlarni qidirish
            for para_idx, paragraph in enumerate(cell.paragraphs):
                for run_idx, run in enumerate(paragraph.runs):
                    if hasattr(run, '_element'):
                        # Drawing rasmlari
                        drawings = run._element.xpath('.//w:drawing', namespaces={
                            'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                        })
                        
                        for drawing in drawings:
                            blips = drawing.xpath('.//a:blip', namespaces={
                                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
                            })

                            for blip in blips:
                                rId = blip.get(
                                    '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                                if rId and rId in self.document.part.related_parts:
                                    image_data = self._get_image_data(rId)
                                    if image_data:
                                        images.append(image_data)
                                        print(f"  Drawing Rasm: {image_data['extension']}, {len(image_data['data'])} bayt")

                        # Picture rasmlari
                        pics = run._element.xpath('.//pic:pic', namespaces={
                            'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'
                        })

                        for pic in pics:
                            blips = pic.xpath('.//a:blip', namespaces={
                                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'
                            })

                            for blip in blips:
                                rId = blip.get(
                                    '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                                if rId and rId in self.document.part.related_parts:
                                    image_data = self._get_image_data(rId)
                                    if image_data:
                                        images.append(image_data)
                                        print(f"  Picture Rasm: {image_data['extension']}, {len(image_data['data'])} bayt")

            # 2. Cell darajasida rasmlarni qidirish (VML va boshqalar)
            try:
                cell_xml = cell._tc.xml
                import xml.etree.ElementTree as ET
                
                namespaces = {
                    'v': 'urn:schemas-microsoft-com:vml',
                    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                }
                
                root = ET.fromstring(cell_xml)
                
                # VML rasmlari
                for imagedata in root.findall('.//v:imagedata', namespaces):
                    rId = imagedata.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    if rId and rId in self.document.part.related_parts:
                        image_data = self._get_image_data(rId)
                        if image_data:
                            images.append(image_data)
                            print(f"  VML Rasm: {image_data['extension']}, {len(image_data['data'])} bayt")
                            
            except Exception as e:
                print(f"Cell XML parse xato: {e}")

            print(f"  {cell_name}: {len(images)} ta rasm topildi")
            return text, images

        except Exception as e:
            print(f"{cell_name} katakda xatolik: {e}")
            return text, []

    def _get_image_data(self, rId):
        """rId orqali rasm ma'lumotlarini olish"""
        try:
            if rId in self.document.part.related_parts:
                image_part = self.document.part.related_parts[rId]
                if hasattr(image_part, 'blob') and image_part.blob:
                    image_data = image_part.blob
                    
                    # Formatni aniqlash
                    if image_data.startswith(b'\xff\xd8'):
                        ext = 'jpg'
                    elif image_data.startswith(b'\x89PNG'):
                        ext = 'png'
                    elif image_data.startswith(b'GIF'):
                        ext = 'gif'
                    elif image_data.startswith(b'RIFF') and len(image_data) > 12 and image_data[8:12] == b'WEBP':
                        ext = 'webp'
                    elif image_data.startswith(b'BM'):
                        ext = 'bmp'
                    else:
                        ext = 'jpg'  # default

                    return {
                        'data': image_data,
                        'data_base64': base64.b64encode(image_data).decode('utf-8'),
                        'extension': ext,
                        'content_type': f'image/{ext}',
                        'rId': rId,
                        'size': len(image_data)
                    }
        except Exception as e:
            print(f"Rasm olishda xato {rId}: {e}")
        
        return None

    def debug_all_images(self):
        print("\n=== BARCHA RASMLARGA DEBUG ===")
        for part_id, part in self.document.part.related_parts.items():
            if hasattr(part, 'blob') and part.blob:
                blob = part.blob
                if len(blob) > 100:  # Faqat haqiqiy rasmlarni ko'rsatish
                    format_info = "Noma'lum"
                    if blob.startswith(b'\xff\xd8'):
                        format_info = "JPEG"
                    elif blob.startswith(b'\x89PNG'):
                        format_info = "PNG"
                    elif blob.startswith(b'GIF'):
                        format_info = "GIF"
                    elif blob.startswith(b'RIFF') and len(blob) > 12 and blob[8:12] == b'WEBP':
                        format_info = "WEBP"
                    
                    print(f"Rasm: {part_id} - {len(blob)} bayt - {format_info}")


def save_image_to_django(image_data, extension, prefix="question"):
    """Rasm ma'lumotlarini Django FileField uchun tayyorlash"""
    if not image_data:
        return None

    try:
        from django.core.files.base import ContentFile
        import uuid

        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.{extension}"

        if isinstance(image_data, dict):
            raw_data = image_data.get('data')
        else:
            raw_data = image_data

        django_file = ContentFile(raw_data, name=filename)
        return django_file

    except Exception as e:
        print(f"Rasm saqlashda xato: {e}")
        return None


def parse_word_file_advanced(file_path):
    """Django signals uchun parser funksiya"""
    print(f"=== WORD FAYL PARSE QILISH BOSHLANDI ===")
    print(f"File path: {file_path}")

    try:
        if not DOCX_AVAILABLE:
            print("XATOLIK: python-docx kutubxonasi o'rnatilmagan!")
            return []

        reader = WordTestReader()
        result = reader.read_test_file(file_path)

        if result['success']:
            questions_data = []

            for q in result['questions']:
                question_data = {
                    'id': q.get('id', ''),
                    'text': q['text'],
                    'images': q.get('images', []),
                    'image_data': q.get('image_data'),
                    'options': q['options']
                }
                questions_data.append(question_data)

            print(f"\nMuvaffaqiyatli parse qilindi: {len(questions_data)} ta savol")

            for i, q_data in enumerate(questions_data):
                print(f"\nSavol {i + 1} (ID: {q_data['id']}): {q_data['text'][:70] if q_data['text'] else 'FAQT RASM'}...")
                if q_data.get('images'):
                    print(f"  Savolda {len(q_data['images'])} ta rasm")

                for j, opt in enumerate(q_data['options']):
                    has_text = bool(opt['text'])
                    has_image = bool(opt.get('images'))
                    
                    content_parts = []
                    if has_text:
                        content_parts.append("matn")
                    if has_image:
                        content_parts.append(f"{len(opt['images'])} rasm")
                    
                    content = "+".join(content_parts) if content_parts else "bo'sh"
                    print(f"  {chr(65 + j)}) {content} ({'✓' if opt['is_correct'] else '✗'})")

            return questions_data
        else:
            print(f"Parse qilishda xatolik: {result['error']}")
            return []

    except Exception as e:
        print(f"Parser da umumiy xatolik: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def debug_word_images(file_path):
    try:
        reader = WordTestReader()
        reader.document = docx.Document(file_path)
        reader.debug_all_images()
    except Exception as e:
        print(f"Debug xatolik: {e}")


def debug_word_file(file_path):
    debug_word_images(file_path)

def parse_word_file_simple(file_path):
    return parse_word_file_advanced(file_path)

def test_parsing(file_path):
    return parse_word_file_advanced(file_path)