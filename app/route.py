import datetime
import json
from typing import List

import requests
from flask import request, flash, abort, make_response, Blueprint
from flask.templating import render_template
from werkzeug.utils import redirect
from flask_apscheduler import APScheduler

from app.const import parse_date, EXTENT_DAYS, STAT_RESULT_CACHE, STAT_RESULT_CACHE_TIME, LocationDict, LocationList
from app.crawler import query_ceac_state, query_ceac_state_safe
from app.mongodb import Case, Record
from app.wechat import config as wx_config, check_wx_signature, xmltodict

mod = Blueprint("router", __name__, template_folder="templates")
scheduler = APScheduler()


# @crontab.job(hour="*", minute="32")
# def crontab_task():
#     last_seem_expire = datetime.datetime.now() - datetime.timedelta(hours=3)
#     case_list : List[Case] = Case.objects(expire_date__gte=datetime.datetime.today(), last_seem__lte=last_seem_expire)
#     soup = None
#     for case in case_list:
#         result, soup = query_ceac_state_safe(case.location, case.case_no, soup)
#         if isinstance(result, tuple):
#             case.updateRecord(result)

def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


@scheduler.task('cron', id='do_job_1', minute="32")
def crontab_task_remote():
    # requests.get("http://127.0.0.1:5000/aa.html")
    last_seem_expire = datetime.datetime.now() - datetime.timedelta(hours=6)
    case_list: List[Case] = Case.objects(expire_date__gte=datetime.datetime.today(), last_seem__lte=last_seem_expire)
    for chunk in divide_chunks(case_list, 50):
        req_data = [(case.location, case.case_no) for case in chunk]
        result_dict = query_ceac_state(req_data)
        for case in chunk:
            result = result_dict[case.case_no]
            if isinstance(result, list):
                case.updateRecord(result)


# @mod.route("/task")
# def crontab_task_debug():
#     if not mod.debug:
#         return "disabled"
#     crontab_task_remote()
#     return "ok"


@mod.route("/import", methods=["GET", "POST"])
def import_case():
    if not mod.debug:
        return "disabled"
    error_list = []
    if request.method == "POST":
        req = request.form.get("lst")
        for line in req.splitlines():
            case_no, location = line.split()[:2]
            if not location or location not in LocationDict.keys():
                error_list.append(line + "\t># No Location")
                continue

            if Case.objects(case_no=case_no).count() == 1:
                case = Case.objects(case_no=case_no).first()
            else:
                case = Case(case_no=case_no, location=location, created_date=parse_date(result[1]))
            result, soup = query_ceac_state_safe(location, case_no)
            if isinstance(result, str):
                error_list.append(line + "\t># " + result)
                continue
            case.save()
            case.updateRecord(result, push_msg=False)
            case.renew()
        flash("ok", category="success")
    return render_template("import.html", lst="\n".join(error_list))


@mod.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        case_no = request.form.get("case_no", None)
        location = request.form.get("location", None)
        if not case_no:
            flash("Invaild case no", category="danger")
            return render_template("index.html", case_no=case_no, location=location, LocationList=LocationList)
        if Case.objects(case_no=case_no).count() == 1:
            case = Case.objects(case_no=case_no).first()
            return redirect("detail/" + str(case.id))
        if not location or location not in LocationDict.keys():
            flash("Invaild location", category="danger")
            return render_template("index.html", case_no=case_no, location=location, LocationList=LocationList)
        result, soup = query_ceac_state_safe(location, case_no)
        if isinstance(result, str):
            flash(result, category="danger")
            return render_template("index.html", case_no=case_no, location=location, LocationList=LocationList)
        case = Case(case_no=case_no, location=location, created_date=parse_date(result[1]))
        case.save()
        case.updateRecord(result)
        case.renew()
        flash("Created a new case for you.", category="success")
        return redirect("detail/" + str(case.id))
    return render_template("index.html", LocationList=LocationList)


@mod.route("/detail/<case_id>", methods=["GET", "POST"])
def detail_page(case_id):
    case = Case.objects.get_or_404(id=case_id)  # type: Case
    if request.method == "POST":
        act = request.form.get("act", None)
        if act == "delete":
            case.delete()
            flash("Completely deleted this case, See you.", category="success")
            return redirect("/")
        if act == "renew":
            flash(f"Expire +{EXTENT_DAYS} days", category="success")
            case.renew()
        if act == "refresh":
            result, soup = query_ceac_state_safe(case.location, case.case_no)
            if isinstance(result, str):
                flash(result, category="danger")
            else:
                case.updateRecord(result)
        interview_date = request.form.get("interview_date", None)
        if interview_date:
            case.interview_date = datetime.datetime.strptime(interview_date, "%Y-%m-%d")
        case.save()
    record_list = Record.objects(case=case).order_by('-status_date')
    return render_template("detail.html", case=case, record_list=record_list, location_str=LocationDict[case.location])


@mod.route("/stat.js")
def stat_result():
    global STAT_RESULT_CACHE, STAT_RESULT_CACHE_TIME
    if STAT_RESULT_CACHE is None or datetime.datetime.now() - STAT_RESULT_CACHE_TIME > datetime.timedelta(minutes=5):
        this_week = datetime.datetime.today() - datetime.timedelta(days=datetime.datetime.today().weekday())
        date_range = this_week - datetime.timedelta(days=52 * 7)
        pipeline = [
            {"$match": {"interview_date": {"$gte": date_range}}},
            {"$lookup": {
                "from": "record",
                "localField": "last_update",
                "foreignField": "_id",
                "as": "last_update"
            }
            }, {
                "$group": {
                    "_id": {
                        "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$interview_date"}},
                        "status": "$last_update.status"
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        result = Case.objects().aggregate(pipeline)
        tmp = {}
        for line in result:
            date = datetime.datetime.strptime(line["_id"]["date"], "%Y-%m-%d")
            date -= datetime.timedelta(days=date.weekday())
            date = date.strftime("%m-%d")
            status = line["_id"]["status"][0]
            count = int(line["count"])
            if status not in tmp:
                tmp[status] = {}
            if date not in tmp[status]:
                tmp[status][date] = 0
            tmp[status][date] += count

        labels = [(this_week - datetime.timedelta(days=i * 7)).strftime("%m-%d") for i in range(52)]
        STAT_RESULT_CACHE_TIME = datetime.datetime.now()
        result = {
            "_labels_": labels,
            "_update_time_": STAT_RESULT_CACHE_TIME.strftime("%Y-%m-%d %H:%M")
        }
        for s in tmp:
            result[s] = [tmp[s].get(i, 0) for i in labels]
        STAT_RESULT_CACHE = "STAT_RESULT = " + json.dumps(result) + ";"
    response = make_response(STAT_RESULT_CACHE)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


@mod.route('/endpoint', methods=["GET", "POST"])
def wechat_point():
    if not check_wx_signature(
            request.args.get("signature"),
            request.args.get("timestamp"),
            request.args.get("nonce"),
            wx_config["serverToken"]):
        return abort(500)
    if request.method == "GET":
        return request.args.get("echostr")

    req = xmltodict(request.data)
    EventKey = ""
    if req["MsgType"] == "event" and req["Event"] == "subscribe" and "EventKey" in req and req["EventKey"]:
        EventKey = req["EventKey"][8:]  # qrscene_
    if req["MsgType"] == "event" and req["Event"] == "SCAN":
        EventKey = req["EventKey"]

    if EventKey:
        Case.bind(EventKey, req["FromUserName"])

    return ""
