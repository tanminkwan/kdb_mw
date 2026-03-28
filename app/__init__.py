import logging
import os
import sys
from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_appbuilder import AppBuilder, SQLA, IndexView
#from pymongo import MongoClient

from flask_apscheduler import APScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
#from .kafka.kafka_producer import Producer4Kafka
#from .kafka.kafka_admin import Admin4Kafka
#from kafka.errors import NoBrokersAvailable
#from .ksql4Kafka import Ksql4Kafka

class MyIndexView(IndexView):
    index_template = 'my_index.html'

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config.from_object("config")
app.config['SCHEDULER_JOBSTORES'] = {
    'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
}
app.config['SCHEDULER_API_ENABLED'] = True

"""
 Logging configuration
"""
logging.basicConfig(
    level=app.config['LOGGING_LEVEL'],
    format=app.config['LOGGING_FORMAT'],
    stream=sys.stdout
)
#logging.getLogger('werkzeug').setLevel(app.config['LOGGING_LEVEL'])

db = SQLA(app)
migrate = Migrate(app, db)

appbuilder = AppBuilder(app, db.session, indexview=MyIndexView)
#Kafka
kafka_producer =None
kafka_admin=None
KAFKA_BROKERS=[]
KAFKA_CONSUMER_4_WAS_MONITORING=''

#ksql4Kafka = None

#if app.config.get('KSQL_URL'):
#    ksql4Kafka = Ksql4Kafka(app.config['KSQL_URL'])

'''
if app.config.get('KAFKA_BROKERS'):

    try:
        kafka_producer = Producer4Kafka(app.config['KAFKA_BROKERS'])
        kafka_admin = Admin4Kafka(app.config['KAFKA_BROKERS'])
        KAFKA_BROKERS = app.config['KAFKA_BROKERS']
    except NoBrokersAvailable as e:
        print('Brokers are not connected.')
        pass
'''
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

#Constant Values (loaded from config.py)
con_val = dict(
    TAG_EMAILS     = app.config['TAG_EMAILS']
   ,KDB_SMTP_IP    = app.config['KDB_SMTP_IP']
   ,KDB_SMTP_PORT  = app.config['KDB_SMTP_PORT']
   ,SMTP_USE_TLS   = app.config['SMTP_USE_TLS']
   ,SMTP_USERNAME  = app.config['SMTP_USERNAME']
   ,SMTP_PASSWORD  = app.config['SMTP_PASSWORD']
   ,SMTP_SENDER    = app.config['SMTP_SENDER']
   ,KROKI_URL      = app.config['KROKI_URL']
)

PLANTUML_URL = app.config.get('PLANTUML_URL')
#MongoDB
#mongoClient = MongoClient("mongodb://localhost:27017/")
#dbMongo = mongoClient["WHEREAMI"]
#footprint = dbMongo["Footprint"]
#vv_P_secs = dbMongo["VV_P_SECS"]

#scheduler = BlockingScheduler(timezone='Asia/Seoul')
#os.environ['TZ']='Asia/Seoul'
scheduler = APScheduler()

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
from . import models
from app.views import was, agent, monitor, knowledge, git, itam
from app.sqls import was, agent, monitor, knowledge, batch, server, itam_compare
from app.api import was_api, agent_api, common_api, model_api, grid_api, batch_api, itam_compare_api
from . import jobs

scheduler.init_app(app)
scheduler.start()

from app.idp_auth import idp_auth_bp, init_oauth
init_oauth(app)
app.register_blueprint(idp_auth_bp, url_prefix='/idp')

# with app.app_context():
#     db.create_all()