import hashlib

from twisted.internet.defer import inlineCallbacks

from ecoin_trade.heap import MinHeap
from ecoin_trade.commands import UserOperation, MaxOperation, MinOperation


class Coin(object):

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Coin, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.min_operations = MinHeap([])
        self.max_operations = MinHeap([])
        self.dealing_operations = []

    def add_operation(self, operation):
        if isinstance(operation, MaxOperation):
            self.max_operations.push(operation)
        elif isinstance(operation, MinOperation):
            self.min_operations.push(operation)
        else:
            raise ''

    def add_to_dealing_operation(self, operation):
        self.dealing_operations += [operation]

    @inlineCallbacks
    def process_operation(self, operation):
        if operation.canceled:
            return
        if operation.op == UserOperation.OP_LONG:
            yield self.long(operation)
        elif operation.op == UserOperation.OP_STOP_LONG:
            yield self.stop_long(operation)
        elif operation.op == UserOperation.OP_SHORT:
            yield self.short(operation)
        elif operation.op == UserOperation.OP_STOP_SHORT:
            yield self.stop_short(operation)

    def check_price(self):
        raise NotImplementedError

    def check_deal(self):
        raise NotImplementedError

    def long(self, operation):
        raise NotImplementedError

    def stop_long(self, operation):
        raise NotImplementedError

    def short(self, operation):
        raise NotImplementedError

    def stop_short(self, operation):
        raise NotImplementedError

    def checkUserUndealedOperations(self, user):
        operations = filter(lambda op: op.user == user and not op.dealed and not op.canceled, self.max_operations.heap_list + self.min_operations.heap_list + self.dealing_operations)
        return operations

class Order(object):

    orders = {}

    @classmethod
    def build(cls, order_id, type, total_amount):
        if order_id not in cls.orders:
            cls.orders[order_id] = Order(order_id, type, total_amount)
        return cls.orders[order_id]

    def __init__(self, order_id, type, total_amount):
        self._order_id = order_id
        self._type = type
        self._total_amount = total_amount
        self._price_avg = 0
        self._deal_amount = 0
        self._status = 0

    def deal(self, price_avg, deal_amount, status):
        self._price_avg = price_avg
        self._deal_amount = deal_amount
        self._status = status

    def _key(self):
        return (self._order_id,)

    def __eq__(self, other):
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    @property
    def order_id(self):
        return self._order_id

    @property
    def dealed(self):
        return self._status == 2

    @property
    def deal_amount(self):
        return self._deal_amount
        
    @property
    def remain_amount(self):
        return self._total_amount - self._deal_amount

def build_sign(secret_key, **kwargs):
    sign = ''
    for key in sorted(kwargs.keys()):
        sign += key + '=' + str(kwargs[key]) +'&'
    data = sign + 'secret_key=' + secret_key
    return  hashlib.md5(data.encode("utf8")).hexdigest().upper()
