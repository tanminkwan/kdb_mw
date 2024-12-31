from datetime import datetime
from testGetWasStatus import getAccessToken, getWasStatus, getNotRunningWasList
from testXlsx import createDailyCheckXlsx
from testSelenium import getTasks
from testHwp2 import recreateHwp
from testSmtp import send_kdbMail
from auto_report import run_auto_report

run_auto_report()