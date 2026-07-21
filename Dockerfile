FROM python:3.11-slim

WORKDIR /app

# 使用阿里云pip源
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

COPY . .

RUN mkdir -p uploads

EXPOSE 5000

ENV FLASK_DEBUG=false

CMD ["python", "app.py"]