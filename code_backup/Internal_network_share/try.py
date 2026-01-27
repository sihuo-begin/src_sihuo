import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 创建邮件对象
msg = MIMEMultipart()
msg['From'] = "simon.huo@flex.com"
msg['To'] = "simon.huo@flex.com"
msg['Subject'] = "Test Email"
body = "Hello, this is a test email."
msg.attach(MIMEText(body, 'plain'))  # 'plain' 表示纯文本格式，也可以使用 'html'

# SMTP服务器配置和登录
# smtp_server = "smtp.gmail.com"
smtp_server = "smtp-mail.outlook.com"
smtp_server = "10.200.147.8"
port = 8000  # 或者使用465，取决于服务器的要求
username = "sihuo"
password = "123456"
print("start")
# server = smtplib.SMTP(smtp_server, port)
# print("server is {}".format(server))
# # server.starttls()  # 如果使用SSL，则不需要这行，直接使用 server.login(username, password) 即可
# server.login(username, password)
# server.send_message(msg)
# print("success")
# server.quit()  # 关闭连接
