class UserOperation(object):
    UNDEALED = 'UNDEALED'
    PARTICIAL_DEALED = 'PARTICIAL_DEALED'
    DEALED = 'DEALED'
    CANCELED = 'CANCELED'

    OP_BUY = 'buy'
    OP_SELL = 'sell'

    OP_LONG = 'long'
    OP_STOP_LONG = 'stop_long'

    OP_SHORT = 'short'
    OP_STOP_SHORT = 'stop_short'

    def __init__(self, op, price, amount, callback_ops=[]):
        self._user = None
        self.op = op
        self.price = float(price)
        self.amount = float(amount)
        self.status = UserOperation.UNDEALED
        self.next_op = None
        self._order = None
        self.set_callback_ops(callback_ops)

    def set_callback_ops(self, callback_ops=[]):
        self.callback_ops = callback_ops
        if not callback_ops:
            return
        i = 0 
        while i < len(callback_ops)-1:
            callback_ops[i].next_op = callback_ops[i+1]
            i += 1
        callback_ops[i].next_op = callback_ops[0]

    def bind_user(self, user):
        if self._user is not None:
            raise ''
        self._user = user
        return self

    def bind_order(self, order):
        if self._order is not None:
            raise ''
        self._order = order

    def cancel(self):
        if self.status != UserOperation.UNDEALED:
            raise ''
        self.status = UserOperation.CANCELED

    @property
    def user(self):
        return self._user

    @property
    def order(self):
        return self._order

    @property
    def canceled(self):
        return self.status == UserOperation.CANCELED

    @property
    def dealed(self):
        return self.order is not None and self.order.dealed

    def __str__(self):
        return '{op} {amount} {price}'.format(op=self.op, amount=self.amount, price=self.price)


class MaxOperation(UserOperation):
    def __lt__(self, other):
        return self.price < other.price

class MinOperation(UserOperation):

    def __lt__(self, other):
        return self.price > other.price

class Command(object):
    order_commands = {}
    check_commands = {}

    @classmethod
    def decode(cls):
        raise NotImplementedError

    @classmethod
    def process(cls):
        raise NotImplementedError

    @classmethod
    def order(cls, _class):
        cls.order_commands[_class._name] = _class

    @classmethod
    def check(cls, _class):
        cls.check_commands[_class._name] = _class

@Command.order
class MarketBuyCommand(Command):

    _name = 'marketbuy'

    @classmethod
    def decode(cls, cmds):
        return MaxOperation('', '', '')

    @classmethod
    def help(cls):
        return cls._name

@Command.order
class MaxLongCommand(Command):

    _name = 'maxlong'

    @classmethod
    def decode(cls, cmds):
        for i in range(len(cmds), 5):
            cmds.append(None)

        price, amount, target_profit, target_loss = cmds[1:]
        max_operation = MaxOperation(UserOperation.OP_LONG, price, amount)
        if target_profit and target_loss:
            stop_long_operation = MaxOperation(UserOperation.OP_STOP_LONG, target_profit, amount)
            stop_loss_operation = MinOperation(UserOperation.OP_STOP_LONG, target_loss, amount)
            max_operation.set_callback_ops([stop_long_operation, stop_loss_operation])

        return max_operation

    @classmethod
    def help(cls):
        return cls._name + ' price amount [target_profix] [target_loss]'

@Command.order
class MaxShortCommand(Command):

    _name = 'maxshort'

    @classmethod
    def decode(cls, cmds):
        for i in range(len(cmds), 5):
            cmds.append(None)

        price, amount, target_profit, target_loss = cmds[1:]
        max_operation = MaxOperation(UserOperation.OP_SHORT, price, amount)
        stop_short_operation = MinOperation(UserOperation.OP_STOP_SHORT, target_profit, amount)
        stop_loss_operation = MaxOperation(UserOperation.OP_STOP_SHORT, target_loss, amount)
        max_operation.set_callback_ops([stop_short_operation, stop_loss_operation])

        return max_operation

    @classmethod
    def help(cls):
        return cls._name + ' price amount [target_profix] [target_loss]'


@Command.order
class MinLongCommand(Command):

    _name = 'minlong'

    @classmethod
    def decode(cls, cmds):
        for i in range(len(cmds), 5):
            cmds.append(None)

        price, amount, target_profit, target_loss = cmds[1:]
        min_operation = MinOperation(UserOperation.OP_LONG, price, amount)
        stop_long_operation = MaxOperation(UserOperation.OP_STOP_LONG, target_profit, amount)
        stop_loss_operation = MinOperation(UserOperation.OP_STOP_LONG, target_loss, amount)
        min_operation.set_callback_ops([stop_long_operation, stop_loss_operation])

        return min_operation

    @classmethod
    def help(cls):
        return cls._name + ' price amount [target_profix] [target_loss]'


@Command.order
class MinShortCommand(Command):

    _name = 'minshort'

    @classmethod
    def decode(cls, cmds):
        for i in range(len(cmds), 5):
            cmds.append(None)

        price, amount, target_profit, target_loss = cmds[1:]
        min_operation = MinOperation(UserOperation.OP_SHORT, price, amount)
        stop_short_operation = MinOperation(UserOperation.OP_STOP_SHORT, target_profit, amount)
        stop_loss_operation = MaxOperation(UserOperation.OP_STOP_SHORT, target_loss, amount)
        min_operation.set_callback_ops([stop_short_operation, stop_loss_operation])

        return min_operation

    @classmethod
    def help(cls):
        return cls._name + ' price amount [target_profix] [target_loss]'


@Command.check
class CheckUndealedOperationCommand(Command):

    _name = 'cund'

    @classmethod
    def process(cls, user, platform):
        operations = platform.checkUserUndealedOperations(user)
        print operations
        return '\n'.join([str(op) for op in operations])

    @classmethod 
    def help(cls):
        return cls._name
