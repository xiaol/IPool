# /usr/local/bin python
# coding=utf-8


import re
import time
import json
import logging
import logging.handlers

import datetime
import requests

import tornado
from tornado import httpserver, gen
import tornado.ioloop, tornado.web

LOG_FILENAME='router_server.log'

handler = logging.handlers.RotatingFileHandler(
    LOG_FILENAME, maxBytes=200000, backupCount=5)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

headers = {'User-Agent' : 'Mozilla/5.0 (X11; Linux i686; rv:8.0) Gecko/20100101 Firefox/8.0'}

http_address = "http://192.168.199.1/cgi-bin/turbo/admin_web"
route_address = "http://192.168.199.1/cgi-bin/turbo/;"

update_ip_address = 'http://120.27.162.246:8000/update_ip'



class TestHander(tornado.web.RequestHandler):
    def get(self):
        logger = logging.getLogger('test')
        logger.setLevel(logging.INFO)
        logger.info('test')

        self.write('hello, world')


logger = logging.getLogger('re_ip_router')
logger.setLevel(logging.INFO)
logger.addHandler(handler)
fh = logging.FileHandler(LOG_FILENAME)
# fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
logger.addHandler(fh)

class ReplaceIPHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        try:
            global obselete_ip
            global logger
            username = self.get_argument("username", "")
            password = self.get_argument("password", "")
            params = {'username' :username, 'password': password}
            session = requests.Session()
            ret = session.post(http_address, headers = headers,params = params, timeout=5)
            web_page = ret._content

            get_wanip_pat = "stok=.*?network\/get_wan_info"
            target_list = re.findall(get_wanip_pat, web_page)
            wanip_address = route_address + target_list[0]
            wanip_ret = session.get(wanip_address)
            wanip_dict = json.loads(wanip_ret._content)
            obselete_ip = wanip_dict['ipv4'][0]['ip']

            logger.info('obselete ip : %s', obselete_ip)

            re_ip_pat = "stok=.*?openapi_proxy\/call"
            target_list = re.findall(re_ip_pat, web_page)
            form_data = {"method":"network.wan.set_pppoe","data":{"network_type":"pppoe","type":"pppoe","pppoe_name":"400000299119", "pppoe_passwd":"j9j5s2z9","static_ip":"","static_mask":"","static_gw":"","static_dns":"","static_dns2":"","ssid":"", "channel":"","bssid":"","encryption":"","ssid_select_mode":"","key":"","key_show":"","override_dns":"","override_dns2":"","uptime":"0","switch_status_wan":"auto"}}
            re_ip_http_address = route_address+target_list[0]
            re_ip_ret = session.post(re_ip_http_address, headers = headers, json = form_data, timeout=1)# cookies=web_cookies)
        except Exception, e:
            logger.error(e)
        finally:
            logger.info("Replace ip sucessfully")



wanip_logger = logging.getLogger('get_wanip')
wanip_logger.setLevel(logging.INFO)
wanip_logger.addHandler(handler)
fh = logging.FileHandler(LOG_FILENAME)
# fh.setLevel(logging.INFO)
fh.setFormatter(formatter)
wanip_logger.addHandler(fh)
wanip_logger.handler_set = True

@gen.engine
def get_wanip_task():
    try:
        global obselete_ip
        global wanip_logger
        username = 'admin'
        password = 'jiama369'
        params = {'username' :username, 'password': password}
        session = requests.Session()
        ret = session.post(http_address, headers = headers,params = params, timeout=5)
        web_page = ret._content
        get_wanip_pat = "stok=.*?network\/get_wan_info"
        target_list = re.findall(get_wanip_pat, web_page)
        wanip_address = route_address+target_list[0]
        wanip_ret = session.get(wanip_address)
        wanip_dict = json.loads(wanip_ret._content)
        new_ip_address = wanip_dict['ipv4'][0]['ip']
        wanip_logger.info('new_ip %s', new_ip_address)
        data = {'obselete_ip_address' : obselete_ip, 'new_ip_address' : new_ip_address}
        update_ip_ret = requests.post(update_ip_address, data, timeout = 5)
        wanip_logger.info('get wan ip successfully')
    except Exception, e:
        wanip_logger.error(e)
    finally:
        wanip_logger.info('end of task')

        # tornado.ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=5), get_wanip_task)

def route_admin_server():
    return tornado.web.Application([
        (r"/",TestHander),
        (r"/re_ip", ReplaceIPHandler)
    ])

if __name__ == "__main__":
    obselete_ip = ''
    app = route_admin_server()
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(4000)
    main_loop = tornado.ioloop.IOLoop.instance()
    shed = tornado.ioloop.PeriodicCallback(get_wanip_task, 5000)
    shed.start()
    #main_loop.add_timeout(datetime.timedelta(seconds=5), get_wanip_task)
    main_loop.start()

