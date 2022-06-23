import datetime
from mongoengine.queryset.base import CASCADE

from app.app import db
from app.const import EXTENT_DAYS, HOST, parse_date, LocationList
from app.wechat import wechat_msg_push, get_qr_code_url


class Case(db.Document):
    case_no = db.StringField(max_length=20, unique=True)
    location = db.StringField(max_length=5, choice=LocationList)
    last_update = db.ReferenceField("Record")
    created_date = db.DateField(format)
    last_seem = db.DateTimeField(default=datetime.datetime.now)

    push_channel = db.StringField(max_length=50)
    qr_code_url = db.StringField(max_length=100)
    qr_code_expire = db.DateTimeField(null=True)
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
        if self.push_channel and push_msg:
            self.push_msg()

    def renew(self, days=EXTENT_DAYS):
        if self.last_update and self.last_update.status == "Issued":
            return
        self.expire_date = (datetime.datetime.today() + datetime.timedelta(days=days)).date()
        self.save()

    def push_msg(self, first=None, remark=None):
        first = first or "你的签证状态有更新"
        keyword1 = self.case_no
        keyword2 = self.last_update.status
        remark = self.last_update.message
        wechat_msg_push(self.push_channel, msg_url=HOST + str(self.id),
                        first=first, keyword1=keyword1, keyword2=keyword2, remark=remark)

    def get_qr_code_url(self):
        if self.qr_code_expire is None or datetime.datetime.now() > self.qr_code_expire:
            self.qr_code_url = get_qr_code_url(str(self.id))
            self.qr_code_expire = datetime.datetime.now() + datetime.timedelta(seconds=2592000)
            self.save()
        return self.qr_code_url

    @staticmethod
    def bind(case_id, wx_userid):
        case = Case.objects(id=case_id).first()
        if not case:
            return
        case.push_channel = wx_userid
        case.save()
        case.push_msg(first="签证状态的更新会推送到这里")


class Record(db.Document):
    case = db.ReferenceField(Case, reverse_delete_rule=CASCADE)
    status_date = db.DateField()
    status = db.StringField()
    message = db.StringField()
