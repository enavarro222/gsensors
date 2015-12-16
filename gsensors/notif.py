#-*- coding:utf-8 -*-
import smtplib
import email.utils
from email.MIMEText import MIMEText

class EmailNotification(object):
    def __init__(self, dest, server, sender, username, password, port=587):
        self.mid = {} # id of msg by alarm
        self.dest = dest
        self.server = server
        self.port = port
        self.sender = sender
        self.username = username
        self.password = password

    def notify_for(self, alarm): #TODO: one may add options here
        alarm.on_trigger(self.send_alert)
        alarm.on_release(self.send_release)
        #alarm.on_recal(self.send_recal)

    def _email_id(self, alarm):
        mid, aid = self.mid.get(alarm.name, (None, None))
        if mid is None or aid != alarm.id:
            mid = email.utils.make_msgid("%s#%d" % (alarm.name, alarm.id))
            self.mid[alarm.name] = (mid, alarm.id)
        return mid

    def _send_email(self, msg):
        #http://ilostmynotes.blogspot.fr/2014/11/smtp-email-conversation-threads-with.html
        msg['From'] = self.sender # some SMTP servers will do this automatically, not all
        msg['To'] = " ".join(self.dest)
        mailserver = smtplib.SMTP(self.server, self.port)
        # identify ourselves to smtp gmail client
        mailserver.ehlo()
        # secure our email with tls encryption
        mailserver.starttls()
        # re-identify ourselves as an encrypted connection
        mailserver.ehlo()
        mailserver.login(self.username, self.password)
        mailserver.sendmail(self.sender, self.dest, msg.as_string())
        mailserver.quit()

    def _email_subject(self, alarm):
        subject = "[ALERT %s#%d] %s" % (alarm.name, alarm.id, alarm.title)
        return subject

    def send_alert(self, alarm):
        mid = self._email_id(alarm)
        content = "Alarm *triggered* !\n"
        content += "Date: %s\n" % alarm.last_change
        content += "\n\n"
        content += "%s" % alarm.msg
        # Trigger at %{date} with the following msg:\n %{msg}
        msg = MIMEText(content, 'plain')
        msg['Subject'] = self._email_subject(alarm)
        
        msg.add_header("Message-ID", mid)
        self._send_email(msg)

    def send_release(self, alarm):
        mid = self._email_id(alarm)
        #TODO build alarm subject/msg form alarm
        content = "Ok, alarm _released_\n"
        content += "Date: %s\n" % alarm.last_change
        content += "\n\n"
        content += "%s" % alarm.msg

        msg = MIMEText(content, 'plain')
        msg['Subject'] = self._email_subject(alarm)
        msg.add_header("In-Reply-To", mid)
        msg.add_header("References", mid)
        self._send_email(msg)


