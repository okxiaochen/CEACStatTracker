import datetime
import hashlib
import smtplib

from mongoengine.queryset.base import CASCADE

from tracker.app import db
from tracker.const import EXTENT_DAYS, HOST, parse_date, LocationList, CONFIG

from tracker.mail import send_mail


class Case(db.Document):
    case_no = db.StringField(max_length=20, unique=True)
    location = db.StringField(max_length=5, choice=LocationList)
    last_update = db.ReferenceField("Record")
    created_date = db.DateField(format)
    last_seem = db.DateTimeField(default=datetime.datetime.now)

    push_channel = db.StringField(max_length=50, default="")
    expire_date = db.DateField(null=True)
    interview_date = db.DateField(null=True)

    def updateRecord(self, result, push_msg=True):
        self.last_seem = datetime.datetime.now()
        self.save()

        status, _, status_date, message = result
        status_date = parse_date(status_date)
        if self.last_update != None and \
                self.last_update.status_date == status_date and \
                self.last_update.status == status and \
                self.last_update.message == message:
            # no update needed
            return
        new_record = Record(case=self, status_date=status_date, status=status, message=message)
        new_record.save()
        self.last_update = new_record
        if status == "Issued":
            # mark as expired now
            self.expire_date = None
        self.save()
        if self.push_channel:
            text = "ApplicationID: %s<br>Status: <span style=\"color:red;\">%s</span><br>Message: %s%s" % (
                self.case_no, self.last_update.status, self.last_update.message, self.unsubscribe_text())
            send_mail(text, "Visa Status Updates", self.push_channel)

    def renew(self, days=EXTENT_DAYS):
        if self.last_update and self.last_update.status == "Issued":
            return
        self.expire_date = (datetime.datetime.today() + datetime.timedelta(days=days)).date()
        self.save()

    def bind(self, email):
        try:
            if Cache.objects(key=email).count() == 1:
                return "One email is only allowed to be bound once within 5 minutes"
            if self.push_channel == email:
                return "Same email"
            cache = Cache(key=email).save()
            text = "Subscribed successfully%s" % self.unsubscribe_text(email)
            send_mail(text, "Visa status updates will be pushed here", email)
            self.push_channel = email
            self.save()
            return True
        except smtplib.SMTPRecipientsRefused as e:
            return "Email address is not valid"

    def unsubscribe_text(self, email=None):
        if email is None:
            email = self.push_channel
        email_hash = hashlib.md5(email.encode('utf-8')).hexdigest()[:9]
        unsubscribe_link = "%s/unsubscribe/%s_%s" % (CONFIG["domain"], str(self.id), email_hash)
        text = "<br><p style='font-size:small;-webkit-text-size-adjust:none;color:#666;'>-<br>You have subscribed visa status from %s<br> <a href='%s'>Unsubscribe from the list</a><p>" % (
            CONFIG["domain"], unsubscribe_link)
        return text


class Record(db.Document):
    case = db.ReferenceField(Case, reverse_delete_rule=CASCADE)
    status_date = db.DateField()
    status = db.StringField()
    message = db.StringField()


class Cache(db.Document):
    key = db.StringField()
    created = db.DateTimeField(default=datetime.datetime.utcnow() - datetime.timedelta(seconds=60))
    meta = {
        'indexes': [
            'key',  # single-field index
            '$key',  # text index
            '#key',  # hashed index
            {
                'fields': ['created'],
                'expireAfterSeconds': 300  # ttl index
            }
        ]
    }
