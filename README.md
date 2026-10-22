# AgroDoktor

O'simlik kasalliklarini sun'iy intellekt (AI) orqali aniqlash xizmati.

AgroDoktor – fermerlar va tomorqa egalari uchun qulay yordamchi bo'lib, o'simlik bargi, mevasi yoki poyasi suratini tahlil qiladi, o'simlikning sog'lom yoki kasallanganligini aniqlaydi hamda amaliy parvarish va davolash tavsiyalarini taqdim etadi.

---

## Asosiy imkoniyatlar

1. **Rasm orqali tahlil**: Telefon kamerasi yoki galereyadan olingan fotosuratni sun'iy intellekt orqali tekshirish.
2. **3 xil aniq xulosa**:
   - **Sog'lom** (yashil belgi)
   - **Kuzatuv talab etadi** (sariq belgi)
   - **Kasallik aniqlandi** (qizil belgi)
3. **Amaliy tavsiyalar**: Har bir holat bo'yicha parvarish, davolash choralari va profilaktika qadamlari.
4. **Natijalar tarixi**: Dala va ekinlar kesimida barcha tekshiruvlar arxivi va dinamikasi.
5. **Keng qamrovli statistika**: Ekin turlari, eng ko'p uchragan kasalliklar va oylik faollik ko'rsatkichlari.

---

## O'rnatish va ishga tushirish

### 1. Virtual muhitni yaratish va faollashtirish

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 3. Sozlamalarni kiritish (.env)

`.env.example` faylidan nusxa olib, `.env` faylini shakllantiring va AI xizmati kalitini kiriting:

```bash
cp .env.example .env
```

### 4. Ma'lumotlar bazasini yangilash

```bash
python manage.py migrate
```

### 5. Demo foydalanuvchini yaratish

Demoga kirish login va paroli `.env` faylidagi `DEMO_USERNAME` va `DEMO_PASSWORD` qiymatlaridan olinadi.
Demo foydalanuvchini yaratish yoki parolini yangilash uchun:

```bash
python manage.py seed_demo
```

### 6. Serverni ishga tushirish

```bash
python manage.py runserver
```

Brauzerda oching: `http://127.0.0.1:8000/`

---

## Telefonda sinash bo'yicha qo'llanma

### Variant A: Mahalliy Wi-Fi tarmog'i orqali

1. Kompyuter va telefoningizni bitta Wi-Fi tarmog'iga ulang.
2. Kompyuterning mahalliy IP manzilini aniqlang:
   ```bash
   hostname -I
   ```
   *(Masalan: `192.168.1.105`)*
3. Serverni barcha tarmoq interfeyslari uchun ishga tushiring:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
4. Telefonda brauzerni ochib, quyidagi manzilga kiring:
   ```
   http://192.168.1.105:8000/
   ```
5. "Demo bilan kirish" tugmasini bosing, `.env`dagi login va parolni kiriting va "Kamera orqali olish" yoki "Galereyadan yuklash" vositasidan foydalaning.

### Variant B: Jonli kamera uchun xavfsiz HTTPS ulanishi

Brauzerlarda jonli kamera tasviri xavfsiz ulanish (HTTPS) talab qiladi. Buning uchun bepul tunnel vositasidan foydalanishingiz mumkin:

```bash
# Masalan, Cloudflare Tunnel yoki ngrok orqali:
ngrok http 8000
```

Yaratilgan `https://...` havolasini telefon brauzerida oching. Shunda to'g'ridan-to'g'ri ekranda ramkali jonli kamera ochiladi va suratga olish imkoniyati ishlaydi.

---

## Sinovlarni tekshirish

Barcha birlik va integratsiya testlarini ishga tushirish:

```bash
python manage.py test tests
```