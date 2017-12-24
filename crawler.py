import requests
import time
import json

file = open('btc_usd.data', 'a')

while True:
    data1 = json.loads(requests.get('https://www.okex.com/api/v1/future_ticker.do?symbol=btc_usd&contract_type=quarter').text)
    data2 = json.loads(requests.get('https://www.okex.com/api/v1/future_hold_amount.do?symbol=btc_usd&contract_type=quarter').text)
    content = ' '.join([str(data1['ticker']['vol']), str(data2[0]['amount']), str(data1['ticker']['last'])])
    file.write(content+'\n')
    time.sleep(60)
