import urllib2
import sys
import urllib
import json
import time
import random
import urlparse
import hashlib
import hmac
import collections
import functools
import cPickle


# Read memoized data, if available
debug_memoize = False

#do requests, but write the result
write_only_memoize = False 

# Exit if memoize is on but the required data/file is not there
# This is mostly for debugging purposes and can be ignored
debug_crash_on_no_cache = False

# The file name where to save the memoized data
memoize_file = "memoi.ze"

# The internal memoize cache
memoize_cache = None

if (debug_memoize):
    print "Warning, MEMOIZE ON"

def memoize(obj):
    global memoize_cache
    def loadmemdata():
        if not debug_memoize: return {}
        try:
            fp = open(memoize_file, "r")
            x = fp.read()
            fp.close()
            return cPickle.loads(x)
        except:
            if debug_crash_on_no_cache:
                print "trying to empty cache.. exit"
                sys.exit()
            return {}
    def savememdata(x):
        fp = open(memoize_file, "w")
        fp.write(cPickle.dumps(x))
        fp.close()
    def keyhash(args, kwargs):
        return obj.__name__ + str(kwargs)
    # load the cache
    memoize_cache = loadmemdata()

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if not debug_memoize and not write_only_memoize:
            return obj(*args, **kwargs)
        key = keyhash(args, kwargs)
        if write_only_memoize:
            memoize_cache[key] = obj(*args, **kwargs)
            savememdata(memoize_cache)
            return memoize_cache[key]
        if key not in memoize_cache:
            memoize_cache[key] = obj(*args, **kwargs)
            savememdata(memoize_cache)
        return memoize_cache[key]
    return memoizer

class cryptsy_api(object):

    def __init__(self, api_key, priv_secret_key):
        self.api_key = api_key
        self.priv_secret_key = priv_secret_key

    pubapi_url = "http://pubapi.cryptsy.com"
    authapi_url = "https://www.cryptsy.com/api"

    def public_api_call(self, params):
        if debug_crash_on_no_cache:
            sys.exit()
        if not params['method']:
            return None
        if not params['action']:
            return None
        url = urlparse.urljoin(self.pubapi_url, params['action'])

        params.pop('action')
        paramString = "&".join(map(lambda x: str(x) + "=" + str(params[x]), params))
        finalURL = "%s?%s" % (url, paramString)
        req = urllib2.Request(finalURL)
        r = urllib2.urlopen(req)

        return self.denclosure_from_data(r.read())

    def aquire_nonce_token(self):
        return str(str(time.time()).split(".")[0])

    def denclosure_from_data(self, data):
        d = json.loads(data)
        if int(d['success']) == 1:
            return d['return']
        else:
            return d['error']
        
    def auth_api_call(self, params):
        if debug_crash_on_no_cache:
            sys.exit()
        def hash_for_text(txt):
            m = hmac.HMAC(self.priv_secret_key, txt, hashlib.sha512)
            return m.hexdigest()
        if not params['method']:
            return None
        url = self.authapi_url

        params['nonce'] = self.aquire_nonce_token()
        paramString = urllib.urlencode(params)

        req = urllib2.Request(url, data=paramString)
        req.get_method = lambda: "POST"
        req.add_header("Key", self.api_key)
        req.add_header("Sign", hash_for_text(paramString))
        r = urllib2.urlopen(req)
        fx = r.read()
        return self.denclosure_from_data(fx)

    @memoize
    def marketdata(self, market = None):
        params = {"action": "api.php",
                  "method": "marketdatav2"
        }
        if market != None:
            params.update({"method": "singlemarketdata",
                           "marketid": market})
        return self.public_api_call(params)

    @memoize
    def orderbookdata(self, market = None):
        params = {"action": "api.php",
                  "method": "orderdata"
        }
        if market != None:
            params.update({"method": "singleorderdata",
                           "marketid": market})
        return self.public_api_call(params)

    @memoize
    def getinfo(self):
        return self.auth_api_call({"method": "getinfo"})

    @memoize
    def getmarkets(self):
        return self.auth_api_call({"method": "getmarkets"})

    @memoize
    def markettrades(self, marketid):
        return self.auth_api_call({"method": "markettrades",
                                   "marketid": marketid})

    @memoize
    def markettrades(self, marketid):
        return self.auth_api_call({"method": "marketorders",
                                   "marketid": marketid})

    @memoize
    def createorder(self, marketid, ordertype, quantity, price):
        """
          marketid: -> integer market id
          ordertype: -> 'Buy'/'Sell'
          quantity: -> amount of units, i.e. 3
          price: -> price per unit, i.e. 133.5
        returns: order id
        """
        return self.auth_api_call({"method": "createorder",
                                   "marketid": marketid,
                                   "ordertype": ordertype,
                                   "quantity": quantity,
                                   "price": price})

    @memoize
    def calculatefees(self, ordertype, quantity, price):
        return self.auth_api_call({"method": "calculatefees",
                                   "ordertype": ordertype,
                                   "quantity": quantity,
                                   "price": price})

    @memoize
    def mytransactions(self):
        """
        Outputs: Array of Deposits and Withdrawals on your account 
        
        currency	Name of currency account
        timestamp	The timestamp the activity posted
        datetime	The datetime the activity posted
        timezone	Server timezone
        type	Type of activity. (Deposit / Withdrawal)
        address	Address to which the deposit posted or Withdrawal was sent
        amount	Amount of transaction (Not including any fees)
        fee	Fee (If any) Charged for this Transaction (Generally only on Withdrawals)
        trxid	Network Transaction ID (If available)
        """
        return self.auth_api_call({"method": "mytransactions",})


