from datetime import datetime as real_datetime
from datetime import datetime

# Adapted from http://www.ryangallen.com/wall/11/mock-today-django-testing/
# and changed to datetime and python 2.x

class MockDateTimeType(type):

    def __init__(cls, name, bases, d):
        type.__init__(cls, name, bases, d)
        cls.year = 2015
        cls.month =  7
        cls.day = 1
        cls.hour = 17
        cls.minute = 0
        cls.second = 0

    def __instancecheck__(self, instance):
        return isinstance(instance, real_datetime)


class MockDateTime(datetime):

    __metaclass__ = MockDateTimeType

    @classmethod
    def utcnow(cls):
        return cls(cls.year, cls.month, cls.day, cls.hour, cls.minute, cls.second)
