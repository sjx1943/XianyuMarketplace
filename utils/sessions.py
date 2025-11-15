#coding=utf-8

import uuid
import pickle
#tornado框架没有提供session工具，需要自己封装
class Session(object):
    def __init__(self):
        self._sessionid = uuid.uuid4().get_hex()
        self.cache = {}


    def set(self,key,value):
        self.cache[key] = value

    def get(self,key,default=None):
        return self.cache.get(key,default)

    def clear(self):
        self.cache.clear()

    @property
    def sessionid(self):
        return self._sessionid

    #序列化session对象
    def serialization(self):
        return pickle.dumps(self)

    #反序列化session字符串
    @staticmethod
    def deserialization(str):
        return pickle.loads(str)

import redis
class SessionManager(object):
    #建立redis数据库的连接
    conn = redis.Redis()

    @classmethod
    def cache2redis(cls,sessionobj):
        cls.conn.set(sessionobj.sessionid,sessionobj.serialization(),ex=14*24*60*60)

    @classmethod
    def getSessionObjBySid(cls,sessionid):
        sessionobj = Session.deserialization(cls.conn.get(sessionid)) if cls.conn.get(sessionid) else None


        if not sessionobj:
            sessionobj = Session()

        return sessionobj
