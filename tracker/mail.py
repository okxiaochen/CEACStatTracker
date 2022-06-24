from tracker.const import CONFIG
from smtplib import SMTP_SSL
from email.mime.text import MIMEText

# from tracker.mongodb import Cache


def send_mail(message, subject, recipient):
    '''
    :param message: str 邮件内容
    :param subject: str 邮件主题描述
    :param recipient: str 收件人 多个收件人用','隔开如："xxx,xxxx"

    '''
    # 填写真实的发邮件服务器用户名、密码
    user = CONFIG["email_user"]
    password = CONFIG["email_password"]
    # 邮件内容
    msg = MIMEText(message, 'html', _charset="utf-8")
    # 邮件主题描述
    msg["Subject"] = subject
    # 发件人显示，不起实际作用
    msg["from"] = user
    # 收件人显示，不起实际作用
    msg["to"] = recipient
    with SMTP_SSL(host=CONFIG["email_host"]) as smtp:
        # 登录发邮件服务器
        smtp.login(user=user, password=password)
        # 实际发送、接收邮件配置
        smtp.sendmail(from_addr=user, to_addrs=recipient.split(','), msg=msg.as_string())


if __name__ == '__main__':
    Subject = 'Visa status updated!'
    # 显示发送人
    to_addrs = 'xxxx'
    # if Cache.objects(key=to_addrs).count() == 1:
    #     print("already")
    #     exit()
    # else:
    #     Cache(key=to_addrs).save()
    #     print("no")
    #     exit()
    # 显示收件人

    text = "ApplicationID: %s<br>Status: <span style=\"color:red;\">%s</span><br>Message: %s" % (
        "AAAA", "ISSUED", "test message")
    send_mail(text, Subject, to_addrs)
