import json
from decimal import Decimal
#import decimal
from datetime import date, datetime

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal) or  type(obj).__name__ in ["Decimal128"]:
            #return {'__Decimal__': str(obj)}
            return str(obj)
        if isinstance(obj, datetime) or isinstance(obj, date) :
            return str(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)