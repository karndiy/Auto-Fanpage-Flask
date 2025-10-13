# Auto Fanpage Flask (Facebook Graph API)

Flask starter สำหรับ "ระบบจัดการโพสต์อัตโนมัติ" ไปยัง Facebook Page
- เก็บค่า settings ใน `settings.json`
- โพสต์ข้อความ: `/{PAGE_ID}/feed`
- โพสต์วิดีโอ: `/{PAGE_ID}/videos`
- ดึงรายการเพจจาก User token: `/me/accounts`
- มีตัวอย่าง Scheduler (APScheduler) สำหรับตั้งเวลาโพสต์

## สิทธิ์ (Permissions) ที่ต้องใช้
- `pages_show_list` (ดึงรายการเพจจาก user token)
- `pages_read_engagement`
- `pages_manage_posts`

> หมายเหตุ: ในโหมด Live ผู้ใช้นอกทีมแอปจำเป็นต้องผ่าน App Review สำหรับ permission บางตัว

## เริ่มต้น
1) ติดตั้งไลบรารี
```
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
2) ตั้งค่าไฟล์ `settings.json`
3) รัน: `flask --app app.py run -p 5000`
4) เปิด http://localhost:5000
