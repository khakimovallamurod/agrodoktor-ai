"""
Management command to seed the demo user and ~14 realistic past scans.
Idempotent: updates existing demo user and ensures complete historical dataset.
"""

from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from scans.models import Scan
from scans.services.image_utils import (
    create_placeholder_leaf_image,
    generate_thumbnail,
)


class Command(BaseCommand):
    help = "Seed demo user and ~14 realistic plant disease scans across 6 months."

    def handle(self, *args, **options):
        username = getattr(settings, "DEMO_USERNAME", "demo")
        first_name = getattr(settings, "DEMO_FIRST_NAME", "O'rolboy")
        last_name = getattr(settings, "DEMO_LAST_NAME", "Xakimov")

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": "demo@agrodoktor.uz",
                "is_active": True,
            },
        )
        if not user.first_name:
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=["first_name", "last_name"])

        # Check existing scans count
        existing_count = Scan.objects.filter(user=user).count()
        if existing_count >= 14:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Demo foydalanuvchida ({user.username}) allaqachon {existing_count} ta tekshiruv mavjud."
                )
            )
            return

        self.stdout.write("Demo tekshiruvlar yaratilmoqda...")

        now = timezone.now()

        # 14 realistic sample records
        sample_dataset = [
            {
                "crop": "Pomidor",
                "field": "Issiqxona #1",
                "class": Scan.CLASS_DISEASED,
                "disease": "Fitoftoroz (Fitoflora)",
                "dtype": "fungal",
                "severity": "high",
                "conf": 0.94,
                "days_ago": 2,
                "summary": "Pomidor barglarida fitoftoroz zamburug'li kasalligi belgilari kuzatilmoqda.",
                "obs": [
                    "Barg chetlarida qo'ng'ir qoramtir dog'lar",
                    "Pastki qismida oqish zamburug' g'ubori",
                    "Barg to'qimalarining qurishi",
                ],
                "causes": [
                    "Issiqxonadagi yuqori namlik (85%+)",
                    "Haroratning keskin o'zgarishi",
                ],
                "treat": [
                    "Kasallangan barglarni ehtiyotkorlik bilan kesib, yoqib yuboring",
                    "Issiqxona shamollatilishini kuchaytiring",
                    "Biologik vositalar yoki ruxsat etilgan fungitsidlar bilan ishlov bering (yorliqdagi ko'rsatmaga amal qiling)",
                ],
                "prev": [
                    "Tomchilatib sug'orish tizimiga o'tish",
                    "O'simliklar oralig'ini kengroq saqlash",
                ],
                "call": "Agar dog'lar poyaga yoki mevalarga o'tsa, agronomga murojaat qiling.",
            },
            {
                "crop": "Pomidor",
                "field": "Issiqxona #2",
                "class": Scan.CLASS_HEALTHY,
                "disease": "",
                "dtype": "none",
                "severity": "none",
                "conf": 0.98,
                "days_ago": 5,
                "summary": "Pomidor bargi toza, sog'lom va rivojlanish yaxshi holatda.",
                "obs": [
                    "Teng yashil rang, to'liq to'qima",
                    "Dog'lar yoki mog'or alomatlari ko'rinmaydi",
                ],
                "causes": [],
                "treat": [
                    "Rejali sug'orish va parvarishni davom ettiring",
                ],
                "prev": [
                    "Muntazam profilaktik ko'rik",
                    "Mikroelementlar bilan oziqlantirish",
                ],
                "call": "Hozirda agronom ko'rigiga zarurat yo'q.",
            },
            {
                "crop": "Kartoshka",
                "field": "1-dala (shimol)",
                "class": Scan.CLASS_DISEASED,
                "disease": "Kolorado qo'ng'izi zarari",
                "dtype": "pest",
                "severity": "medium",
                "conf": 0.91,
                "days_ago": 12,
                "summary": "Kartoshka yaprog'ida zararkunanda qurtlarining kemirish alomatlari kuzatilmoqda.",
                "obs": [
                    "Barg chetlari va o'rtasi kemirilgan",
                    "Qo'ng'ir lichinkalar mavjudligi ehtimoli",
                ],
                "causes": [
                    "Mavsumiy zararkunandalar faollashuvi",
                ],
                "treat": [
                    "Zararkunandalarni qo'lda terib olish yoki biologik insektitsid qo'llash",
                    "Kimyoviy himoya vositasini yorliqdagi ko'rsatmaga binoan seping",
                ],
                "prev": [
                    "Ekinni erta bahorda himoya to'rlari bilan to'sish",
                    "Almashlab ekish",
                ],
                "call": "Maydonning 20% dan ortig'i zararlansa, zudlik bilan agronom bilan bog'laning.",
            },
            {
                "crop": "Bug'doy",
                "field": "Sharqiy paykal",
                "class": Scan.CLASS_DISEASED,
                "disease": "Sariq zang (Puccinia striiformis)",
                "dtype": "fungal",
                "severity": "high",
                "conf": 0.95,
                "days_ago": 24,
                "summary": "Bug'doy bargida sariq zang kasalligi chiziqlari ko'zga tashlanmoqda.",
                "obs": [
                    "Barg bo'ylab sariq-to'q sariq chiziqli pustulalar",
                    "Barg to'qimalarining xlorotik o'zgarishi",
                ],
                "causes": [
                    "Bahorgi nam va salqin ob-havo",
                ],
                "treat": [
                    "Tizimli fungitsidlar bilan ekinzorga ishlov berish (yorliqqa qat'iy rioya qiling)",
                ],
                "prev": [
                    "Chidamli navlarni ekish",
                    "Fosfor-kaliy o'g'itlarini me'yorida berish",
                ],
                "call": "Keng maydonga tarqalish xavfi bo'lsa, mutaxassis ko'rigi zarur.",
            },
            {
                "crop": "Olma",
                "field": "Meva bog'i",
                "class": Scan.CLASS_SUSPICIOUS,
                "disease": "Kalmaraz (Parch) alomatlari",
                "dtype": "fungal",
                "severity": "low",
                "conf": 0.83,
                "days_ago": 35,
                "summary": "Olma barglarida kichik qora dog'lar va engil qavariqlar kuzatilmoqda.",
                "obs": [
                    "Barg yuzasida zaytun rangli mayda dog'lar",
                    "Qisqarish va engil deformatsiya",
                ],
                "causes": [
                    "Bahorgi yog'ingarchilikdan so'ng namlik saqlanib qolishi",
                ],
                "treat": [
                    "Barglarni ortiqcha namlanishdan saqlash",
                    "Biologik preparat bilan purkash",
                ],
                "prev": [
                    "Daraxt shoxlarini o'z vaqtida butash va quyosh tushishini ta'minlash",
                ],
                "call": "Dog'lar mevalarga o'tishni boshlasa agronom ko'rigi tavsiya etiladi.",
            },
            {
                "crop": "Paxta",
                "field": "G'o'za maydoni #4",
                "class": Scan.CLASS_DISEASED,
                "disease": "Vilt (Vertitsillyoz so'lish)",
                "dtype": "fungal",
                "severity": "high",
                "conf": 0.89,
                "days_ago": 48,
                "summary": "G'o'za barglarida vilt kasalligiga xos mozaikasimon sarg'ayish va qurish alomatlari bor.",
                "obs": [
                    "Barg tomirlari oralig'ida sarg'ayish va to'qimalarning o'lishi",
                    "Tushki paytda o'simlikning so'lishi",
                ],
                "causes": [
                    "Tuproqdagi vilt zamburug'i",
                    "Haddan ortiq zovur suvi bilan sug'orish",
                ],
                "treat": [
                    "Zararlangan tuplarni daladan chiqarib tashlash",
                    "Kaliy o'g'itlari bilan oziqlantirishni ko'paytirish",
                ],
                "prev": [
                    "Tuproqni chuqur haydash",
                    "Viltga chidamli seleksiya navlarini ekish",
                ],
                "call": "Ushbu kasallik xavfli bo'lgani sababli agronom bilan maslahatlashing.",
            },
            {
                "crop": "Uzum",
                "field": "Tokzor maydoni",
                "class": Scan.CLASS_DISEASED,
                "disease": "Oidium (Un-shudring)",
                "dtype": "fungal",
                "severity": "medium",
                "conf": 0.93,
                "days_ago": 62,
                "summary": "Tok barglari ustida kulrang-oq unsimon g'ubor belgilari kuzatilmoqda.",
                "obs": [
                    "Bargning ustki qismida oq changsimon qatlam",
                    "Barg qirralarining yuqoriga qayrilishi",
                ],
                "causes": [
                    "Issiq va quruq havo sharoiti, havoning yetarli aylanmasligi",
                ],
                "treat": [
                    "Oltingugurt asosidagi preparatlar bilan ishlov berish (yorliq bo'yicha)",
                    "Ortiqcha novdalarni butash",
                ],
                "prev": [
                    "Tok qatorlarida yaxshi havo aylanishini ta'minlash",
                ],
                "call": "G'o'ralar yorila boshlasa agronomga murojaat qiling.",
            },
            {
                "crop": "Bodring",
                "field": "Issiqxona #1",
                "class": Scan.CLASS_HEALTHY,
                "disease": "",
                "dtype": "none",
                "severity": "none",
                "conf": 0.97,
                "days_ago": 75,
                "summary": "Bodring yaprog'i sog'lom, normal turgor holatida va faol o'smoqda.",
                "obs": [
                    "To'q yashil yagona rang",
                    "Zararlanish yoki teshiklar yo'q",
                ],
                "causes": [],
                "treat": [
                    "Muntazam suv va mikroiqlim nazorati",
                ],
                "prev": [
                    "Haroratni 22-26 daraja oralig'ida ushlab turish",
                ],
                "call": "Hozircha zarurat yo'q.",
            },
            {
                "crop": "Bug'doy",
                "field": "Markaziy paykal",
                "class": Scan.CLASS_HEALTHY,
                "disease": "",
                "dtype": "none",
                "severity": "none",
                "conf": 0.96,
                "days_ago": 90,
                "summary": "Bug'doy poyasi va barglari baquvvat, begona dog'lar kuzatilmadi.",
                "obs": [
                    "Toza poya va barg plastinkasi",
                ],
                "causes": [],
                "treat": ["Agrotexnik parvarish"],
                "prev": ["O'z vaqtida oziqlantirish"],
                "call": "Zarurat yo'q.",
            },
            {
                "crop": "Paxta",
                "field": "Daryo bo'yi paykali",
                "class": Scan.CLASS_SUSPICIOUS,
                "disease": "Shira (Tsvid) va oziqa yetishmovchiligi",
                "dtype": "pest",
                "severity": "low",
                "conf": 0.81,
                "days_ago": 105,
                "summary": "G'o'za barglarida yengil yopishqoqlik va chetlarining sarg'ayishi kuzatilmoqda.",
                "obs": [
                    "Barg pastki yuzasida mayda hasharotlar to'planishi",
                    "Barg qirralarining burishishi",
                ],
                "causes": [
                    "Issiq kunlarda shira hasharotlarining ko'payishi",
                ],
                "treat": [
                    "Biologik oltinko'z yoki xonqizi hasharotlarini jalb qilish",
                    "Zarur bo'lsa biologik preparat purkash",
                ],
                "prev": [
                    "Begona o'tlarni yo'qotish",
                ],
                "call": "Shira ko'payib ketsa, agronomga xabar bering.",
            },
            {
                "crop": "Kartoshka",
                "field": "2-dala",
                "class": Scan.CLASS_DISEASED,
                "disease": "Erta qora dog'lanish (Alternarioz)",
                "dtype": "fungal",
                "severity": "medium",
                "conf": 0.88,
                "days_ago": 120,
                "summary": "Barglarda konsentrik doirasimon qora-qo'ng'ir dog'lar aniqlangan.",
                "obs": [
                    "Nishon shaklidagi qatlamli to'q dog'lar",
                    "Pastki barglarning sarg'ayib qurishi",
                ],
                "causes": [
                    "Quruq va nam kunlarning almashinishi",
                ],
                "treat": [
                    "Kasallangan pastki barglarni olib tashlash",
                    "Fungitsid bilan profilaktik purkash (yorliqqa asosan)",
                ],
                "prev": [
                    "O'simlikni kaliy va azot bilan to'g'ri mutanosiblikda oziqlantirish",
                ],
                "call": "Yuqori barglarga o'tsa agronom ko'rigi zarur.",
            },
            {
                "crop": "Pomidor",
                "field": "1-dala",
                "class": Scan.CLASS_SUSPICIOUS,
                "disease": "Barg buralishi va azot tanqisligi",
                "dtype": "nutrient",
                "severity": "low",
                "conf": 0.84,
                "days_ago": 135,
                "summary": "Pomidor barglarida qayiqsimon yuqoriga buralish va och yashil rang kuzatildi.",
                "obs": [
                    "Barglarning quyi qismidan buralishi",
                    "Qalinlashgan barg plastinkasi",
                ],
                "causes": [
                    "Kuchli quyosh nuri yoki ildiz namligi tanqisligi",
                ],
                "treat": [
                    "Sug'orish me'yorini tartibga solish",
                    "Ildizdan tashqari oziqlantirish o'tkazish",
                ],
                "prev": [
                    "Soyabon to'rlaridan foydalanish",
                ],
                "call": "Yangi novdalar rivojlanmasa agronom maslahatini oling.",
            },
            {
                "crop": "Uzum",
                "field": "Bog' maydoni",
                "class": Scan.CLASS_HEALTHY,
                "disease": "",
                "dtype": "none",
                "severity": "none",
                "conf": 0.99,
                "days_ago": 150,
                "summary": "Tok barglari to'liq sog'lom, hosildorlik ko'rsatkichlari yuqori.",
                "obs": ["Toza yashil barglar", "G'o'ralar bir tekis"],
                "causes": [],
                "treat": ["Mavsumiy agrotexnika"],
                "prev": ["Doimiy monitoring"],
                "call": "Zarurat yo'q.",
            },
            {
                "crop": "Kartoshka",
                "field": "1-dala",
                "class": Scan.CLASS_HEALTHY,
                "disease": "",
                "dtype": "none",
                "severity": "none",
                "conf": 0.97,
                "days_ago": 165,
                "summary": "Kartoshka palagi sog'lom va mustahkam rivojlanmoqda.",
                "obs": ["Kasallik va hasharot belgilari yo'q"],
                "causes": [],
                "treat": ["Oziqlantirish"],
                "prev": ["Begona o'tlardan tozalash"],
                "call": "Zarurat yo'q.",
            },
        ]

        created_scans = 0
        for item in sample_dataset:
            # Generate leaf placeholder image
            leaf_img = create_placeholder_leaf_image(
                crop_name=item["crop"],
                result_class=item["class"],
            )
            thumb_img = generate_thumbnail(leaf_img)
            leaf_img.seek(0)

            scan = Scan.objects.create(
                user=user,
                image=leaf_img,
                thumbnail=thumb_img,
                crop_type=item["crop"],
                field_name=item["field"],
                notes=f"{item['crop']} holati tekshiruvi.",
                status=Scan.STATUS_OK,
                result_class=item["class"],
                plant_name=item["crop"],
                disease_name=item["disease"],
                disease_type=item["dtype"],
                severity=item["severity"],
                confidence=item["conf"],
                summary=item["summary"],
                observations=item["obs"],
                causes=item["causes"],
                treatment=item["treat"],
                prevention=item["prev"],
                when_to_call_agronomist=item["call"],
                raw_response={"seed": True, "class": item["class"]},
            )

            # Update created_at timestamp to simulate 6 months historical trend
            created_date = now - timedelta(days=item["days_ago"])
            Scan.objects.filter(id=scan.id).update(created_at=created_date)
            created_scans += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Muvaffaqiyatli! {created_scans} ta tekshiruv demo hisobiga kiritildi."
            )
        )
