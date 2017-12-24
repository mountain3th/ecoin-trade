import json
import traceback
from urllib import urlencode

from zope.interface import implements
from twisted.web.iweb import IBodyProducer
from twisted.internet.defer import inlineCallbacks, returnValue, succeed
from twisted.web.client import Agent, readBody
from twisted.web.http_headers import Headers
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet.ssl import ClientContextFactory

from .base import Coin, build_sign, Order

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class WebClientContextFactory(ClientContextFactory):
    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)

class OKCoinApiMixin(object):

    @inlineCallbacks
    def future_ticker(self, symbol, contract_type):
        try:
            response = yield Agent(reactor, WebClientContextFactory()).request(
                'GET',
                'https://www.okex.com/api/v1/future_ticker.do?symbol={}&contract_type={}'.format(symbol, contract_type)
            )
            result = yield readBody(response)
            data = json.loads(result)
            returnValue(float(data['ticker']['last']))
        except Exception as exc:
            traceback.print_exc()

    @inlineCallbacks
    def get_order_info(self, user, symbol, contract_type, order_id):
        sign = build_sign(user.secret_key,
            api_key=user.api_key,
            symbol=symbol,
            contract_type=contract_type,
            order_id=order_id
        )
        try:
            body = urlencode({
                'symbol': symbol,
                'contract_type': contract_type,
                'api_key': user.api_key,
                'sign': sign,
                'order_id': order_id
            })
            response = yield Agent(reactor, WebClientContextFactory()).request(
                'POST',
                'https://www.okex.com/api/v1/future_order_info.do',
                Headers({
                    'Content-Type': ['application/x-www-form-urlencoded;charset=utf-8']
                }),
                bodyProducer=StringProducer(body)
            )
            result = yield readBody(response)
            print result
            data = json.loads(result)
            if not data['result']:
                returnValue(None)
            else:
                ret_order = data['orders'][0]
                order = Order.build(ret_order['order_id'], ret_order['type'], ret_order['amount'])
                order.deal(ret_order['price_avg'], ret_order['deal_amount'], ret_order['status'])
                returnValue(order)
        except Exception as exc:
            traceback.print_exc()
            returnValue(None)

    @inlineCallbacks
    def trade(self, user, symbol, contract_type, price, amount, type, match_price, lever_rate):
        sign = build_sign(user.secret_key, 
            api_key=user.api_key,
            symbol=symbol, 
            contract_type=contract_type, 
            price=price,
            amount=amount,
            type=type,
            match_price=match_price,
            lever_rate=lever_rate
        )
        try:
            body = urlencode({
                'symbol': symbol,
                'contract_type': contract_type,
                'price': price,
                'amount': amount,
                'type': type,
                'match_price': match_price,
                'lever_rate': lever_rate,
                'api_key': user.api_key,
                'sign': sign
            })
            response = yield Agent(reactor, WebClientContextFactory()).request(
                'POST',
                'https://www.okex.com/api/v1/future_trade.do',
                Headers({"Content-Type" : ["application/x-www-form-urlencoded;charset=utf-8"]}),
                bodyProducer=StringProducer(body)
            )
            result = yield readBody(response)
            data = json.loads(result)
            if not data['result']:
                returnValue(None)
            else:
                returnValue((yield self.get_order_info(user, symbol, contract_type, data['order_id'])))

        except Exception as exc:
            traceback.print_exc()

    @inlineCallbacks
    def do_long(self, user, symbol, contract_type, price, amount, match_price=0, lever_rate=10):
        returnValue((yield self.trade(user, symbol, contract_type, price, amount, 1, match_price, lever_rate)))

    @inlineCallbacks
    def do_stop_long(self, user, symbol, contract_type, price, amount, match_price=0, lever_rate=10):
        returnValue((yield self.trade(user, symbol, contract_type, price, amount, 3, match_price, lever_rate)))

    @inlineCallbacks
    def do_short(self, user, symbol, contract_type, price, amount, match_price=0, lever_rate=10):
        returnValue((yield self.trade(user, symbol, contract_type, price, amount, 2, match_price, lever_rate)))

    @inlineCallbacks
    def do_stop_short(self, user, symbol, contract_type, price, amount, match_price=0, lever_rate=10):
        returnValue((yield self.trade(user, symbol, contract_type, price, amount, 4, match_price, lever_rate)))


class OKEXBTCFutureSeasonCoin(Coin, OKCoinApiMixin):

    __name__ = 'OKEX BTC Future Season Coin'

    @inlineCallbacks
    def check_price(self):
        price = yield self.future_ticker('btc_usd', 'quarter')
        while not self.max_operations.is_empty() and price >= self.max_operations.peek().price:
            self.process_operation(self.max_operations.pop())
        while not self.min_operations.is_empty() and price <= self.min_operations.peek().price:
            self.process_operation(self.min_operations.pop())
        yield price


    def _handle_result(self, operation, order):
        if order is None:
            return
        operation.bind_order(order)
        self.add_to_dealing_operation(operation)

    @inlineCallbacks
    def long(self, operation):
        order = yield self.do_long(operation.user, 'btc_usd', 'quarter', operation.price, operation.amount)
        self._handle_result(operation, order)

    @inlineCallbacks
    def stop_long(self, operation):
        order = yield self.do_stop_long(operation.user, 'btc_usd', 'quarter', operation.price, operation.amount)
        self._handle_result(operation, order)
    
    @inlineCallbacks
    def short(self, operation):
        order = yield self.do_short(operation.user, 'btc_usd', 'quarter', operation.price, operation.amount)
        self._handle_result(operation, order)

    @inlineCallbacks
    def stop_short(self, operation):
        order = yield self.do_stop_short(operation.user, 'btc_usd', 'quarter', operation.price, operation.amount)
        self._handle_result(operation, order)

    @inlineCallbacks
    def check_deal(self):
        for operation in self.dealing_operations:
            if operation.dealed:
                for op in operation.callback_ops:
                    op.bind_user(operation.user)
                    self.add_operation(op)
                next_op = operation.next_op
                while next_op != operation and next_op is not None:
                    next_op.cancel()
                    next_op = next_op.next_op
                self.dealing_operations.remove(operation)
            else:
                yield self.get_order_info(user=operation.user, symbol='btc_usd', contract_type='quarter', order_id=operation.order.order_id)

    def __str__(self):
        return self.__name__

if __name__ == '__main__':
    from twisted.internet import reactor 
    from twisted.internet.defer import inlineCallbacks
    from ecoin_trade.main import User
    from ecoin_trade.commands import MaxLongCommand

    @inlineCallbacks
    def test_long():
        coin = OKEXBTCFutureSeasonCoin()
        op = MaxLongCommand.decode(['maxlong', '4360', '1', '4370', '4350'])
        op.bind_user(User('fdbd4121-9f49-4bf3-89e1-acdd1a4f2bf4', 'B7C77280354B9BB02C1668DDC33FC3EE'))
        result = yield coin.long(op)

    reactor.callLater(0, test_long)
    reactor.run()