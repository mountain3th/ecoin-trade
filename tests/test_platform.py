from unittest.case import TestCase

import mock
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

from ecoin_trade.main import User
from ecoin_trade.commands import MaxLongCommand
from ecoin_trade.platforms.okcoin import OKEXBTCFutureSeasonCoin


class TestCoinCase(TestCase):
    _parents = {}

    def setUp(self):
        super(TestCoinCase, self).setUp()
        self.coin = OKEXBTCFutureSeasonCoin()

    def tearDown(self):
        super(TestCoinCase, self).tearDown()

    
    @inlineCallbacks
    def test_long(self):
        op = MaxLongCommand.decode(['maxlong', '3700', '0.1'])
        op.bind_user(User('fdbd4121-9f49-4bf3-89e1-acdd1a4f2bf4', 'B7C77280354B9BB02C1668DDC33FC3EE'))
        result = yield self.coin.long(op)
        print 'ss'
        self.assertEqual(result, 0)

