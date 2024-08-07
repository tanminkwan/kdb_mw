from kafka import KafkaConsumer
from json import loads
import sys

class Consumer4Kafka:

    def __init__(self, brokers, topic, group_id):
        self.consumer = KafkaConsumer(
                topic
              , group_id=group_id
              , auto_offset_reset='latest'
              , bootstrap_servers=brokers
              , key_deserializer=lambda x: x.decode('utf-8')
              , value_deserializer=lambda x: loads(x.decode('utf-8'))
              , consumer_timeout_ms=3000
              )

        self.stop_flag = False

    def getMessage(self):

        try:

            while self.stop_flag == False:
                for rec in self.consumer:
                    yield rec.key, rec.value

                self.consumer.commit()

        except Exception as e:
            excType, excValue, traceback = sys.exc_info()
            print(excType, excValue, traceback)
            return -1
        finally:
            self.consumer.close()
            print('Consumer4Kafka is Killed!!')

if __name__ == "__main__":
    con = Consumer4Kafka(['10.6.16.102:9092'], 'S_PROD_JMX_RESULT_BY_SERVER', 'g_mw_server')
    for key, value in con.getMessage():
        print(key, value)