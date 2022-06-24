FROM python:3.8.13

WORKDIR /myapp

COPY requirements.txt requirements.txt
RUN echo "Asia/Shanghai" > /etc/timezone &&  rm -f /etc/localtime && dpkg-reconfigure -f noninteractive tzdata && apt-get update && apt-get install -y cron && pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .



