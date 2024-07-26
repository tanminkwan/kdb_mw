from kafka import KafkaProducer
from json import dumps
import sys

class Producer4Kafka:

    def __init__(self, brokers):
        self.producer = KafkaProducer(
                acks=0
              , compression_type=None
              , bootstrap_servers=brokers
              , key_serializer=lambda x: dumps(x).encode('utf-8')
              , value_serializer=lambda x: dumps(x).encode('utf-8'))

    def sendMessage(self, topic, message, key=''):

        try:
            self.producer.send(topic, key=key, value=message).get(timeout=3)
            self.producer.flush()
            return 1
        except Exception as e:
            excType, excValue, traceback = sys.exc_info()
            print(excType, excValue, traceback)
            #log.error('sendMessage Error Occured : %s %s %s', excType, excValue, traceback)
            return -1
