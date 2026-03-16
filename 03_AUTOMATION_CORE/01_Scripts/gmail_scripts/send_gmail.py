import os
from email.message import EmailMessage
import ssl
import smtplib

'''
username = os.environ.get('UNAME2')
password = os.environ.get('GPASS2')

print(username)
print(password)
'''


email_sender = 'lg.train4life@gmail.com'

email_password = 'ewtyyncxgpgkilmc'

email_receiver = 'linogillies@gmail.com'


subject = ' Sign Up Special'

body = '''


    
    
-Lino
Train Hard, Train Smart, Train 4 Life

'''

em =EmailMessage()
em[ 'From' ] = email_sender 
em[ 'To' ] = email_receiver
em['Subject'] = subject
em.set_content(body)

context = ssl.create_default_context()

with smtplib.SMTP_SSL( 'smtp.gmail.com', 465, context=context) as smtp:
    smtp.login(email_sender, email_password)
    smtp.sendmail(email_sender, email_receiver, em.as_string())
