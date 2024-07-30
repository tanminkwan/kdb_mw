from kafka import KafkaAdminClient, KafkaConsumer
from kafka.structs import TopicPartition
import sys

class Admin4Kafka:

    def __init__(self, brokers):
        self.admin = KafkaAdminClient(bootstrap_servers=brokers)
        self.brokers = brokers

    def delete_topic(self, topic):

        try:
            self.admin.delete_topics([topic])
            return 1
        except Exception as e:
            excType, excValue, traceback = sys.exc_info()
            print(excType, excValue, traceback)
            log.error('deleteTopic Error Occured : %s %s %s', excType, excValue, traceback)
            return -1

    def get_offsets(self, topic, partition):

        results = []
        try:

            tp = TopicPartition(topic=topic, partition=partition)
            con = KafkaConsumer(bootstrap_servers=self.brokers)
            end_offsets = con.end_offsets([tp])[tp]
            con.close()

            tl = self.admin.list_consumer_groups()

            for g in tl:
                #if g[1] == 'consumer':
                t2 = self.admin.list_consumer_group_offsets(g[0], partitions=[tp])
                offset = getattr(t2[tp],'offset')
                if t2.get(tp) and offset != -1:
                    r_dict = dict(
                            group = g[0]
                           ,topic = topic
                           ,partition = partition
                           ,offset = offset
                           ,current_offset = end_offsets
                    )

                    results.append(r_dict)

            return results, 1
        except Exception as e:
            excType, excValue, traceback = sys.exc_info()
            print(excType, excValue, traceback)
            log.error('sendMessage Error Occured : %s %s %s', excType, excValue, traceback)
            return [], -1
