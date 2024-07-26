import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from flask import Flask
from flask_migrate import Migrate
from flask_appbuilder import AppBuilder, SQLA, IndexView
from pymongo import MongoClient

from flask_apscheduler import APScheduler
from .producer4Kafka import Producer4Kafka
from .admin4Kafka import Admin4Kafka
from kafka.errors import NoBrokersAvailable
#from .ksql4Kafka import Ksql4Kafka

"""
 Logging configuration
"""
class MyIndexView(IndexView):
    index_template = 'my_index.html'

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(message)s")
#log = logging.getLogger()
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#hdl = RotatingFileHandler('Hennry.log', mode='a', maxBytes=10*1024*1024, backupCount=50, encoding='utf-8', delay=0)
#hdl = TimedRotatingFileHandler('Hennry.log', when='D', interval=1, backupCount=50, encoding='utf-8', delay=0)
#hdl.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s:%(message)s"))
#hdl.suffix = '%Y%m%d'
#log.addHandler(hdl)

app = Flask(__name__)
app.config.from_object("config")

print('GGG KAFKA_BROKERS :',  app.config['KAFKA_BROKERS'])

db = SQLA(app)
migrate = Migrate(app, db)

appbuilder = AppBuilder(app, db.session, indexview=MyIndexView)

#Kafka
producer4Kafka =None
admin4Kafka=None
KAFKA_BROKERS=[]
KAFKA_CONSUMER_4_WAS_MONITORING=''

#ksql4Kafka = None

#if app.config.get('KSQL_URL'):
#    ksql4Kafka = Ksql4Kafka(app.config['KSQL_URL'])

if app.config.get('KAFKA_BROKERS'):

    print('JJJ : ', app.config['KAFKA_BROKERS'])
    try:
        producer4Kafka = Producer4Kafka(app.config['KAFKA_BROKERS'])
        admin4Kafka = Admin4Kafka(app.config['KAFKA_BROKERS'])
        KAFKA_BROKERS = app.config['KAFKA_BROKERS']
    except NoBrokersAvailable as e:
        print('Brokers are not connected.')
        pass


#Current WAS Status
WAS_STATUS = dict()
consumer4WasMonitoring = None

#
if app.config.get('KAFKA_CONSUMER_4_WAS_MONITORING'):
    KAFKA_CONSUMER_4_WAS_MONITORING = app.config['KAFKA_CONSUMER_4_WAS_MONITORING']


#GitLab
gitConfig = dict()
if app.config.get('GITLAB_CONFIG'):
    gitConfig = app.config['GITLAB_CONFIG']

#Constant Values
con_val = dict(
    TAG_ONCHARGE   = '담당자-'
   ,TAG_EMAILS     = '이메일-'
   ,TAG_SYSTEM     = '시스템-'
   ,KDB_SMTP_IP    = '10.6.20.40'
   ,KDB_SMTP_PORT  = 50025
)
#MongoDB
mongoClient = MongoClient("mongodb://localhost:27017/")
dbMongo = mongoClient["WHEREAMI"]
footprint = dbMongo["Footprint"]
vv_P_secs = dbMongo["VV_P_SECS"]

#scheduler = BlockingScheduler(timezone='Asia/Seoul')
#os.environ['TZ']='Asia/Seoul'
scheduler = APScheduler()
scheduler.init_app(app)

scheduler.start()

"""
from sqlalchemy.engine import Engine
from sqlalchemy import event

#Only include this for SQLLite constraints
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    # Will force sqllite contraint foreign keys
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
"""

from . import views, views_util, views_agent, views_monitor, views_com, views_api, views_git, dmlsForJeus, dmlsForWebtob, sqls_agent, sqls_mw, sqls_monitor, scheduled_jobs