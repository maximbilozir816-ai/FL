FROM python:3.10-slim

# Встановлюємо системні залежності для OpenCV та WeasyPrint (Pango, Cairo, GDK-PixBuf тощо)
# + ШРИФТИ. Без цього блоку контейнер не має ЖОДНОГО шрифту, і кирилиця
# в PDF-звітах (WeasyPrint) виводиться квадратиками/крапками, хоча локально
# на Windows все ок, бо шрифти вже стоять у системі.
# fonts-dejavu-core і fonts-liberation2 повністю покривають кирилицю.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libx11-6 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fontconfig \
    fonts-dejavu-core \
    fonts-liberation2 \
    fonts-noto-core \
    && fc-cache -f -v \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]