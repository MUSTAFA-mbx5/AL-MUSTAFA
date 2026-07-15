# -*- coding: utf-8 -*-
"""
برنامج إدارة وقراءة البطاقة التموينية الإلكترونية العراقية
تطوير: مكتبة المصطفى
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import google.generativeai as genai
from PIL import Image, ImageTk, ImageDraw
import json
import threading
import os
import webbrowser
import requests

# --- إعدادات الألوان والمظهر ---
PRIMARY_COLOR = "#0f5132"  # أخضر غامق مثل البطاقة الأصلية
SECONDARY_COLOR = "#198754" # أخضر متوسط
BG_COLOR = "#f4f7f6"        # خلفية رمادية فاتحة جداً مائلة للزرقة
CARD_BG = "#ffffff"         # خلفية بيضاء ناصعة للكروت
TEXT_COLOR = "#212529"      # لون النص الأساسي

class RationCardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("نظام قراءة وطباعة البطاقة التموينية الإلكترونية")
        self.root.geometry("900x780")
        self.root.configure(bg=BG_COLOR)
        
        # دعم اتجاه الكتابة من اليمين إلى اليسار
        self.root.option_add('*font', ('Segoe UI', 10))
        
        # إنشاء الصور التجريبية للـ Logos إذا لم تكن موجودة
        self.create_placeholder_logos()
        
        # تهيئة قائمة أفراد العائلة
        self.member_rows = []
        
        # بناء الواجهة
        self.create_header()
        self.create_api_and_upload_section()
        self.create_main_layout()
        
        # إضافة فرد افتراضي واحد عند التشغيل
        self.add_member_row()

    def create_placeholder_logos(self):
        """إنشاء شعارات تجريبية في حال لم تكن متوفرة لكي لا ينهار البرنامج"""
        if not os.path.exists("logo1.png"):
            img1 = Image.new('RGBA', (150, 150), color='#198754')
            draw = ImageDraw.Draw(img1)
            draw.text((30, 65), "Logo 1", fill="white")
            img1.save("logo1.png")
            
        if not os.path.exists("logo2.png"):
            img2 = Image.new('RGBA', (150, 150), color='#0f5132')
            draw = ImageDraw.Draw(img2)
            draw.text((30, 65), "Logo 2", fill="white")
            img2.save("logo2.png")

    def create_header(self):
        """إنشاء الهيدر العلوي مع الشعارات يميناً ويساراً"""
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=20, pady=10)
        
        # الشعار الأيمن (logo1)
        self.logo1_img = self.load_and_resize_image("logo1.png", (65, 65))
        if self.logo1_img:
            logo1_lbl = tk.Label(header_frame, image=self.logo1_img, bg=BG_COLOR)
            logo1_lbl.pack(side="right", padx=10)
            
        # العنوان في المنتصف
        title_lbl = tk.Label(
            header_frame, 
            text="معلومات البطاقة التموينية الإلكترونية", 
            font=("Segoe UI", 18, "bold"), 
            fg=PRIMARY_COLOR, 
            bg=BG_COLOR
        )
        title_lbl.pack(side="right", expand=True)
        
        # الشعار الأيسر (logo2)
        self.logo2_img = self.load_and_resize_image("logo2.png", (65, 65))
        if self.logo2_img:
            logo2_lbl = tk.Label(header_frame, image=self.logo2_img, bg=BG_COLOR)
            logo2_lbl.pack(side="left", padx=10)

    def load_and_resize_image(self, path, size):
        try:
            img = Image.open(path)
            img = img.resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return None

    def create_api_and_upload_section(self):
        """قسم إعدادات التلغرام والـ API ورفع الصورة"""
        top_control_frame = tk.LabelFrame(self.root, text=" لوحة التحكم والربط ", font=("Segoe UI", 10, "bold"), bg=BG_COLOR, fg=PRIMARY_COLOR, padx=10, pady=10)
        top_control_frame.pack(fill="x", padx=20, pady=5)
        
        # نجعل الشبكة مرنة
        top_control_frame.columnconfigure((0,1,2,3), weight=1)
        
        # توكن التلغرام (مخفي بنجوم)
        tk.Label(top_control_frame, text="توكن بوت التلغرام:", bg=BG_COLOR).grid(row=0, column=3, sticky="e", padx=5, pady=2)
        self.tg_token_entry = tk.Entry(top_control_frame, show="*", justify="right")
        self.tg_token_entry.grid(row=0, column=2, sticky="ew", padx=5, pady=2)
        
        # معرف التلغرام (مخفي بنجوم)
        tk.Label(top_control_frame, text="معرف القناة/المستلم (ID):", bg=BG_COLOR).grid(row=0, column=1, sticky="e", padx=5, pady=2)
        self.tg_id_entry = tk.Entry(top_control_frame, show="*", justify="right")
        self.tg_id_entry.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        
        # مفتاح Gemini API
        tk.Label(top_control_frame, text="مفتاح Gemini API:", bg=BG_COLOR).grid(row=1, column=3, sticky="e", padx=5, pady=5)
        self.gemini_key_entry = tk.Entry(top_control_frame, show="*", justify="right")
        self.gemini_key_entry.grid(row=1, column=2, sticky="ew", padx=5, pady=5)
        
        # أزرار إظهار/إخفاء البيانات الحساسة
        self.show_secrets = False
        self.toggle_btn = tk.Button(top_control_frame, text="إظهار الرموز 👁️", command=self.toggle_secrets_visibility, bg="#e2e8f0")
        self.toggle_btn.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # زر رفع الصورة الذكي
        self.upload_btn = tk.Button(
            top_control_frame, 
            text="قراءة استمارة تلقائياً (OCR) 📸", 
            command=self.start_ocr_thread, 
            bg=PRIMARY_COLOR, 
            fg="white", 
            font=("Segoe UI", 11, "bold"),
            cursor="hand2"
        )
        self.upload_btn.grid(row=0, column=4, rowspan=2, columnspan=1, sticky="nsew", padx=10, pady=2)

    def toggle_secrets_visibility(self):
        """التبديل بين إظهار وإخفاء كلمات المرور والرموز"""
        if self.show_secrets:
            self.tg_token_entry.config(show="*")
            self.tg_id_entry.config(show="*")
            self.gemini_key_entry.config(show="*")
            self.toggle_btn.config(text="إظهار الرموز 👁️")
            self.show_secrets = False
        else:
            self.tg_token_entry.config(show="")
            self.tg_id_entry.config(show="")
            self.gemini_key_entry.config(show="")
            self.toggle_btn.config(text="إخفاء الرموز 🔒")
            self.show_secrets = True

    def create_main_layout(self):
        """إنشاء التقسيم الرئيسي: الحقول الأساسية يميناً، وأفراد العائلة يساراً"""
        main_paned = tk.Frame(self.root, bg=BG_COLOR)
        main_paned.pack(fill="both", expand=True, padx=20, pady=5)
        
        # القسم الأيمن: البيانات الأساسية
        right_frame = tk.LabelFrame(main_paned, text=" بيانات البطاقة الأساسية (قابلة للتعديل) ", font=("Segoe UI", 10, "bold"), bg=BG_COLOR, fg=PRIMARY_COLOR, padx=10, pady=10)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.fields = {}
        fields_config = [
            ("card_number", "رقم البطاقة التموينية:"),
            ("family_head", "اسم رب الأسرة:"),
            ("food_agent_name", "اسم وكيل الغذائية:"),
            ("food_agent_id", "رقم وكيل الغذائية:"),
            ("flour_agent_name", "اسم وكيل الطحين:"),
            ("flour_agent_id", "رقم وكيل الطحين:"),
            ("governorate", "المحافظة:"),
            ("branch", "الفرع:"),
            ("center_name_id", "اسم ورقم المركز:")
        ]
        
        for idx, (key, label_text) in enumerate(fields_config):
            lbl = tk.Label(right_frame, text=label_text, bg=BG_COLOR, anchor="w")
            lbl.pack(fill="x", pady=(2, 0))
            
            entry = tk.Entry(right_frame, justify="right", font=("Segoe UI", 10))
            entry.pack(fill="x", pady=(0, 6))
            self.fields[key] = entry
            
        # القسم الأيسر: جدول أفراد الأسرة الديناميكي
        left_frame = tk.LabelFrame(main_paned, text=" الأفراد المسجلين بالبطاقة ", font=("Segoe UI", 10, "bold"), bg=BG_COLOR, fg=PRIMARY_COLOR, padx=10, pady=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # حاوية سكرولر لأفراد العائلة
        canvas_container = tk.Frame(left_frame, bg=BG_COLOR)
        canvas_container.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(canvas_container, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_COLOR)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="right", fill="both", expand=True)
        scrollbar.pack(side="left", fill="y")
        
        # أزرار الإجراءات الخاصة بجدول العائلة
        family_buttons_frame = tk.Frame(left_frame, bg=BG_COLOR)
        family_buttons_frame.pack(fill="x", pady=5)
        
        add_btn = tk.Button(family_buttons_frame, text="إضافة فرد جديد ➕", command=self.add_member_row, bg=SECONDARY_COLOR, fg="white", font=("Segoe UI", 9, "bold"))
        add_btn.pack(side="right", padx=5)
        
        # أزرار الإجراءات النهائية في الأسفل
        bottom_buttons_frame = tk.Frame(self.root, bg=BG_COLOR)
        bottom_buttons_frame.pack(fill="x", padx=20, pady=15)
        
        # زر التصدير والطباعة
        print_btn = tk.Button(
            bottom_buttons_frame, 
            text="تصدير وتجهيز الكرت للطباعة 🖨️", 
            command=self.export_to_html, 
            bg="#0d6efd", 
            fg="white", 
            font=("Segoe UI", 12, "bold"), 
            pady=6
        )
        print_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))
        
        # زر الإرسال إلى التلغرام
        self.send_btn = tk.Button(
            bottom_buttons_frame, 
            text="إرسال البيانات إلى تلغرام ✈️", 
            command=self.send_to_telegram, 
            bg="#229ED9", 
            fg="white", 
            font=("Segoe UI", 12, "bold"), 
            pady=6
        )
        self.send_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

    def add_member_row(self, name="", relationship=""):
        """إضافة سطر ديناميكي جديد لجدول أفراد الأسرة"""
        row_frame = tk.Frame(self.scrollable_frame, bg=BG_COLOR)
        row_frame.pack(fill="x", pady=4, padx=2)
        
        # حقل الاسم
        name_entry = tk.Entry(row_frame, width=22, justify="right")
        name_entry.insert(0, name)
        name_entry.pack(side="right", padx=3)
        
        # حقل الصلة
        relation_entry = tk.Entry(row_frame, width=15, justify="right")
        relation_entry.insert(0, relationship)
        relation_entry.pack(side="right", padx=3)
        
        # زر الحذف الخاص بالسطر
        del_btn = tk.Button(
            row_frame, 
            text="❌", 
            bg="#dc3545", 
            fg="white", 
            font=("Segoe UI", 8),
            command=lambda: self.remove_member_row(row_frame)
        )
        del_btn.pack(side="right", padx=3)
        
        self.member_rows.append({
            "frame": row_frame,
            "name": name_entry,
            "relationship": relation_entry
        })
        
        self.canvas.yview_moveto(1.0)

    def remove_member_row(self, frame_to_remove):
        """حذف سطر عضو من القائمة"""
        for row in self.member_rows:
            if row["frame"] == frame_to_remove:
                row["frame"].destroy()
                self.member_rows.remove(row)
                break

    def start_ocr_thread(self):
        """تشغيل الذكاء الاصطناعي في الخلفية"""
        api_key = self.gemini_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("تنبيه", "يرجى إدخال مفتاح Gemini API أولاً لإتمام عملية القراءة التلقائية.")
            return
            
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if not file_path:
            return
            
        self.upload_btn.config(text="جاري المعالجة... ⏳", state="disabled")
        threading.Thread(target=self.process_image_ocr, args=(file_path, api_key), daemon=True).start()

    def process_image_ocr(self, file_path, api_key):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            img = Image.open(file_path)
            
            prompt = """
            قم بقراءة صورة "معلومات البطاقة التموينية" واستخرج البيانات بدقة متناهية.
            أرجع النتيجة بصيغة JSON فقط بهذا الهيكل تماماً دون أي مقدمات أو نصوص إضافية أو علامات ماركداون:
            {
              "card_number": "رقم البطاقة التموينية المكون من أرقام فقط",
              "family_head": "اسم رب الاسرة",
              "food_agent_name": "اسم وكيل الغذائية",
              "food_agent_id": "رقم وكيل الغذائية",
              "flour_agent_name": "اسم وكيل الطحين",
              "flour_agent_id": "رقم وكيل الطحين",
              "center_name_id": "اسم ورقم المركز مثل: الرميثة 733",
              "branch": "الفرع",
              "governorate": "المحافظة",
              "family_members": [
                {"name": "الاسم المسجل الأول", "relationship": "الصلة"},
                {"name": "الاسم المسجل الثاني", "relationship": "الصلة"}
              ]
            }
            """
            
            response = model.generate_content([prompt, img])
            response_text = response.text.strip()
            
            # تنظيف ردود الماركداون
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            data = json.loads(response_text)
            self.root.after(0, self.fill_fields_from_json, data)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("خطأ في القراءة", f"فشلت قراءة الصورة تلقائياً. تأكد من جودتها ومفتاح الـ API.\n\nالتفاصيل: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.upload_btn.config(text="قراءة استمارة تلقائياً (OCR) 📸", state="normal"))

    def fill_fields_from_json(self, data):
        """تعبئة الحقول بالبيانات وتحديث جدول أفراد العائلة"""
        for key, entry in self.fields.items():
            entry.delete(0, tk.END)
            if key in data:
                entry.insert(0, data[key])
                
        for row in self.member_rows[:]:
            self.remove_member_row(row["frame"])
            
        members = data.get("family_members", [])
        if members:
            for member in members:
                self.add_member_row(member.get("name", ""), member.get("relationship", ""))
        else:
            self.add_member_row()
            
        messagebox.showinfo("نجاح القراءة", "تم استخراج كافة البيانات بنجاح! يرجى مراجعتها وتعديلها يدوياً إذا دعت الحاجة.")

    def send_to_telegram(self):
        """إرسال البيانات المستخرجة كرسالة منسقة إلى قناة أو محادثة تلغرام"""
        token = self.tg_token_entry.get().strip()
        chat_id = self.tg_id_entry.get().strip()
        
        if not token or not chat_id:
            messagebox.showwarning("تنبيه", "يرجى ملء حقول توكن البوت ومعرف المستلم (ID) في قسم التحكم أولاً.")
            return
            
        # جمع البيانات من الواجهة
        card_number = self.fields["card_number"].get()
        family_head = self.fields["family_head"].get()
        food_agent_name = self.fields["food_agent_name"].get()
        food_agent_id = self.fields["food_agent_id"].get()
        flour_agent_name = self.fields["flour_agent_name"].get()
        flour_agent_id = self.fields["flour_agent_id"].get()
        governorate = self.fields["governorate"].get()
        branch = self.fields["branch"].get()
        center_name_id = self.fields["center_name_id"].get()
        
        # صياغة أسماء العائلة
        members_text = ""
        for idx, row in enumerate(self.member_rows):
            name = row["name"].get().strip()
            relation = row["relationship"].get().strip()
            if name:
                members_text += f" {idx+1}. {name} - ({relation})\n"
                
        if not members_text:
            members_text = "لا يوجد أفراد مسجلين."
            
        # صياغة نص رسالة التلغرام المنسقة بدقة
        message_text = f"""
🔔 *تم إرسال بطاقة تموينية جديدة* 🔔

*• رقم البطاقة التموينية:* `{card_number}`
*• اسم رب الأسرة:* {family_head}

*• وكيل المواد الغذائية:* {food_agent_name} ({food_agent_id})
*• وكيل الطحين:* {flour_agent_name} ({flour_agent_id})

*• المحافظة:* {governorate}
*• الفرع:* {branch}
*• اسم ورقم المركز التمويني:* {center_name_id}

*👥 الأفراد المسجلين:*
{members_text}
"""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "Markdown"
        }
        
        self.send_btn.config(text="جاري الإرسال... ⏳", state="disabled")
        threading.Thread(target=self._tg_send_thread, args=(url, payload), daemon=True).start()

    def _tg_send_thread(self, url, payload):
        try:
            response = requests.post(url, json=payload, timeout=10)
            res_data = response.json()
            if response.status_code == 200 and res_data.get("ok"):
                self.root.after(0, lambda: messagebox.showinfo("نجاح الإرسال", "تم إرسال كافة البيانات إلى التلغرام بنجاح!"))
            else:
                error_desc = res_data.get("description", "خطأ غير معروف")
                self.root.after(0, lambda: messagebox.showerror("فشل الإرسال", f"فشل إرسال الرسالة عبر التلغرام.\n\nالسبب: {error_desc}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("خطأ في الاتصال", f"حدث خطأ أثناء الاتصال بالتلغرام:\n\n{str(e)}"))
        finally:
            self.root.after(0, lambda: self.send_btn.config(text="إرسال البيانات إلى تلغرام ✈️", state="normal"))

    def export_to_html(self):
        """إنشاء كرت البطاقة التموينية بتصميم ويب ديناميكي جاهز للطباعة"""
        card_number = self.fields["card_number"].get()
        family_head = self.fields["family_head"].get()
        food_agent_name = self.fields["food_agent_name"].get()
        food_agent_id = self.fields["food_agent_id"].get()
        flour_agent_name = self.fields["flour_agent_name"].get()
        flour_agent_id = self.fields["flour_agent_id"].get()
        governorate = self.fields["governorate"].get()
        branch = self.fields["branch"].get()
        center_name_id = self.fields["center_name_id"].get()
        
        members_html = ""
        for idx, row in enumerate(self.member_rows):
            name = row["name"].get().strip()
            relation = row["relationship"].get().strip()
            if name:
                bg_class = "even" if idx % 2 == 0 else "odd"
                members_html += f'''
                <tr class="{bg_class}">
                    <td>{name}</td>
                    <td>{relation}</td>
                </tr>
                '''
                
        html_content = f'''<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>معلومات البطاقة التموينية الإلكترونية</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;800&display=swap');
        
        body {{
            font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif;
            background-color: #f1f5f9;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: flex-start;
        }}
        
        .ration-card {{
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 20px;
            width: 100%;
            max-width: 800px;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);
            padding: 30px;
            box-sizing: border-box;
        }}
        
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3px solid #15803d;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        
        .header img {{
            height: 75px;
            width: auto;
            object-fit: contain;
        }}
        
        .header .title-area {{
            text-align: center;
            flex-grow: 1;
        }}
        
        .header .title-area h1 {{
            color: #166534;
            font-size: 24px;
            margin: 0;
            font-weight: 800;
        }}
        
        .header .title-area p {{
            color: #15803d;
            font-size: 14px;
            margin: 5px 0 0 0;
            font-weight: 700;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 25px;
        }}
        
        .triple-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 15px;
            margin-bottom: 25px;
        }}
        
        .info-box {{
            background: #f8fafc;
            border: 1.5px solid #e2e8f0;
            border-radius: 12px;
            padding: 12px 15px;
            text-align: center;
        }}
        
        .info-box .label {{
            color: #166534;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 6px;
            display: block;
        }}
        
        .info-box .value {{
            color: #334155;
            font-size: 16px;
            font-weight: 700;
        }}
        
        .family-table-container {{
            border: 1.5px solid #e2e8f0;
            border-radius: 12px;
            overflow: hidden;
            background: #ffffff;
            margin-top: 20px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: right;
        }}
        
        th {{
            background-color: #f0fdf4;
            color: #166534;
            font-weight: 700;
            font-size: 15px;
            padding: 12px 15px;
            border-bottom: 2px solid #bbf7d0;
        }}
        
        td {{
            padding: 12px 15px;
            font-size: 15px;
            color: #334155;
            border-bottom: 1px solid #f1f5f9;
            font-weight: 600;
        }}
        
        tr.even {{ background-color: #ffffff; }}
        tr.odd {{ background-color: #fafbfb; }}
        
        @media print {{
            body {{ background-color: #ffffff; padding: 0; }}
            .ration-card {{ box-shadow: none; border: none; padding: 10px; width: 100%; }}
            .info-box {{
                background: #ffffff !important;
                border: 1.5px solid #94a3b8 !important;
                print-color-adjust: exact;
            }}
            th {{
                background-color: #f0fdf4 !important;
                border-bottom: 2px solid #86efac !important;
                print-color-adjust: exact;
            }}
            .family-table-container {{ page-break-inside: auto; }}
            tr {{ page-break-inside: avoid; page-break-after: auto; }}
        }}
    </style>
</head>
<body>

    <div class="ration-card">
        <div class="header">
            <img src="logo1.png" alt="الشعار الأيمن" onerror="this.style.display='none'">
            <div class="title-area">
                <h1>البطاقة التموينية</h1>
                <p>وزارة التجارة العراقية</p>
            </div>
            <img src="logo2.png" alt="الشعار الأيسر" onerror="this.style.display='none'">
        </div>
        
        <div class="info-grid">
            <div class="info-box">
                <span class="label">رقم البطاقة التموينية</span>
                <div class="value">{card_number or '---'}</div>
            </div>
            <div class="info-box">
                <span class="label">اسم رب الاسرة</span>
                <div class="value">{family_head or '---'}</div>
            </div>
        </div>
        
        <div class="info-grid">
            <div class="info-box">
                <span class="label">اسم ورقم وكيل الطحين</span>
                <div class="value">{flour_agent_name or '---'} {f'({flour_agent_id})' if flour_agent_id else ''}</div>
            </div>
            <div class="info-box">
                <span class="label">اسم ورقم وكيل الغذائية</span>
                <div class="value">{food_agent_name or '---'} {f'({food_agent_id})' if food_agent_id else ''}</div>
            </div>
        </div>
        
        <div class="triple-grid">
            <div class="info-box">
                <span class="label">اسم ورقم المركز</span>
                <div class="value">{center_name_id or '---'}</div>
            </div>
            <div class="info-box">
                <span class="label">الفرع</span>
                <div class="value">{branch or '---'}</div>
            </div>
            <div class="info-box">
                <span class="label">المحافظة</span>
                <div class="value">{governorate or '---'}</div>
            </div>
        </div>
        
        <div class="family-table-container">
            <table>
                <thead>
                    <tr>
                        <th style="width: 60%;">الافراد المسجلين</th>
                        <th style="width: 40%;">الصلة</th>
                    </tr>
                </thead>
                <tbody>
                    {members_html if members_html else '<tr><td colspan="2" style="text-align:center; color:#94a3b8;">لا يوجد أفراد مسجلين مضافين حالياً</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

</body>
</html>
'''
        output_filename = "ration_card_output.html"
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(html_content)
            webbrowser.open(os.path.abspath(output_filename))
            messagebox.showinfo("تم التصدير", f"تم توليد الكرت بنجاح وحفظه باسم '{output_filename}'.\n\nاضغط Ctrl + P لطباعته.")
        except Exception as e:
            messagebox.showerror("خطأ في التصدير", f"تعذر حفظ وتصدير الملف.\n\nالتفاصيل: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = RationCardApp(root)
    root.mainloop()

