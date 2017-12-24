import sys
import os

sys.path.append(os.path.abspath('.'))

from twisted.internet import reactor, task, protocol
from twisted.internet.defer import inlineCallbacks
from twisted.application import service, strports
from twisted.protocols import basic
from twisted.python.log import PythonLoggingObserver
from twisted.python import log

from ecoin_trade.platforms.okcoin import OKEXBTCFutureSeasonCoin
from ecoin_trade.commands import Command
from ecoin_trade.heap import MinHeap


class User(object):

    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def __eq__(self, other):
        return self.__key() == other.__key()

    def __hash__(self):
        return hash(self.__key())

    def __key(self):
        return (self.api_key, self.secret_key)

    def __repr__(self):
        return str(self.__key())


class CommandProtocol(basic.LineReceiver):

    def __init__(self):
        self.user = None
        self.coin_platform = None

    def connectionMade(self):
        temp = range(1, len(self.factory.coin_platforms)+1)
        zipped = zip(temp, self.factory.coin_platforms)
        platforms = reduce(lambda a, b: a + str(str(b[0]) + '. ' + str(b[1]) + '\r\n'), zipped, '')
        self.transport.write('''
Welcome to the control panel.
Please choose the platfrom amoung the ones below and then input your token for the api.
{}
'''.format(platforms))

    def login(self, line):
        if self.user is not None:
            return True
        if line.startswith('login'):
            keys = line.split(' ')
            if len(keys) != 3:
                self.transport.write('wrong format')
                return False
            self.user = User(keys[1], keys[2])
            return True
        self.transport.write('must login first.Use [login api_key secere_key]\r\n')
        return False
    
    def select_coin_platform(self, line):
        if self.coin_platform is not None:
            return True
        try:
            platform = int(line)
        except:
            self.transport.write('please select a right number.\r\n')
            return False
        else:
            self.coin_platform = self.factory.coin_platforms[platform-1]
            self.transport.write('%s selected.\r\n' % str(self.coin_platform))
            return True

    def write_support_command(self, line):
        commands = '''
Order Commands:
\t{order_commands}

Check Commands:
\t{check_commands}
'''.format(order_commands='\r\n\t'.join([cmd.help() for cmd  in Command.order_commands.values()]),
    check_commands='\r\n\t'.join([cmd.help() for cmd in Command.check_commands.values()])
)
        self.transport.write(commands)

    def lineReceived(self, line):
        if not self.select_coin_platform(line):
            return
        if not self.login(line):
            return

        cmds = line.split(' ')
        if cmds[0] in Command.order_commands:
            operation = Command.order_commands[cmds[0]].decode(cmds)
            operation.bind_user(self.user)
            self.coin_platform.add_operation(operation)
        elif cmds[0] in Command.check_commands:
            ret = Command.check_commands[cmds[0]].process(self.user, self.coin_platform)
            self.transport.write(ret)
        else:
            self.write_support_command(line)
            

class EcoinService(service.Service):

    def __init__(self):
        self.coin_platforms = [
            OKEXBTCFutureSeasonCoin()
        ]

    def getControllerFactory(self):
        f = protocol.ServerFactory()
        f.protocol = CommandProtocol
        f.coin_platforms = self.coin_platforms
        return f

    @inlineCallbacks
    def _watch_prices(self):
        for platform in self.coin_platforms:
            price = yield platform.check_price()
            log.msg(price)

    @inlineCallbacks
    def _check_deal(self):
        for platform in self.coin_platforms:
            yield platform.check_deal()

    def startService(self):
        self.price_task = task.LoopingCall(self._watch_prices)
        self.price_task.start(1.0)
        self.check_deal_task = task.LoopingCall(self._check_deal)
        self.check_deal_task.start(1.0)
        service.Service.startService(self)

    def stopService(self):
        service.Service.stopService(self)

class trade_log_observer(PythonLoggingObserver):

    file_log = open('trade.log', 'a')

    def emit(self, eventDict):
        message = eventDict['message']
        self.file_log.write(''.join(message))

log.startLoggingWithObserver(trade_log_observer().emit, setStdout=False)

application = service.Application('ecoin')
serviceCollection = service.IServiceCollection(application)
ecoin_service = EcoinService()
ecoin_service.setServiceParent(serviceCollection)

strports.service('tcp:8000', ecoin_service.getControllerFactory()).setServiceParent(serviceCollection)