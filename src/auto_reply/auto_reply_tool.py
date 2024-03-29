#!/usr/bin/python3
# coding=utf-8
from http.server import HTTPServer, BaseHTTPRequestHandler
from logging.handlers import RotatingFileHandler
from auto_reply import AutoReplyTool
import argparse
import logging
import json
import multiprocessing
import os
import queue
import signal
import sys
import threading
import time
import urllib
import yaml

if sys.platform == 'win32':
	from pystray import MenuItem
	from pystray import Icon
	from PIL import Image
	import webbrowser


SERVER_URL = '127.0.0.1'
SERVER_PORT = 6655
CONF = 'mm_conf.yaml'
LOG = None
LOG_LEVEL = logging.INFO

def get_logger(mod, level):
	logger = logging.getLogger(mod)
	logger.setLevel(logging.DEBUG)

	format = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(name)s - %(pathname)s[line:%(lineno)d]: %(message)s", datefmt="%Y/%m/%d %H:%M:%S")

	sh = logging.StreamHandler()
	sh.setLevel(logging.INFO)
	sh.setFormatter(format)

	fh = RotatingFileHandler(filename=mod + '.log', encoding='utf-8', maxBytes=1024 * 1024 * 20)
	fh.setLevel(level)
	fh.setFormatter(format)

	logger.addHandler(sh)
	logger.addHandler(fh)

	return logger


def resource_path_prefix():
	return sys._MEIPASS + '/' if getattr(sys, 'frozen', False) else './'


class WebConsoleServer(HTTPServer):
	def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
		HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=True)
		self.auto_reply_tool = None
		self.work_proc = None
		self.icon = None
		self.icon_thread = None
		self.icon_stop = True
		self.icon_clicked = False
		self.relogin_event = None
		self.stop_event = multiprocessing.Event()
		self.config_queue = multiprocessing.Queue(1)

	def stop(self):
		if type(self.work_proc) == multiprocessing.Process:
			self.stop_event.set()
			self.work_proc.join()
			LOG.info('Stop auto reply work process done.')

		if type(self.icon_thread) == threading.Thread:
			self.icon_stop = True
			self.icon.stop()
			LOG.info('Stop icon thread done.')

		self.shutdown()
		LOG.info('Stop web console server done.')

	def icon_start(self):
		# Only create icon GUI thread on win32 platform.
		if sys.platform == 'win32':
			image = Image.open(resource_path_prefix() + "web_console/images/favicon.ico")
			menu = (MenuItem('HomePage', self.icon_home_page_handler, default=True),
					MenuItem('Exit', self.icon_exit_handler))
			self.icon = Icon("MattermostTools", image, "MattermostTools", menu)

			self.relogin_event = multiprocessing.Event()

			self.icon_thread = threading.Thread(target=self.icon.run, args=[self.icon_setup])
			self.icon_thread.start()

	def icon_setup(self, icon):
		self.icon_stop = False
		icon.visible = True
		icon.notify("Web Console is working at: http://%s:%s" % \
					(self.server_address[0], self.server_address[1]), "MattermostTools")

		webbrowser.open("http://%s:%s" % (self.server_address[0], self.server_address[1]))

		while not self.icon_stop:
			if not self.relogin_event.wait(3):
				continue

			# Notify every 60s.
			last_notify = 0
			while not self.icon_stop and not self.icon_clicked:
				if time.time() - last_notify > 60:
					icon.notify("Authentication is invalid, need to login again.", "MattermostTools")
					last_notify = time.time()

				time.sleep(3)

			# Notify finished.
			icon.remove_notification()
			self.icon_clicked = False
			self.relogin_event.clear()

	def icon_home_page_handler(self):
		self.icon_clicked = True
		self.relogin_event.clear()
		webbrowser.open("http://%s:%s" % (self.server_address[0], self.server_address[1]))

	def icon_exit_handler(self):
		self.stop()


class WebConsoleHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args):
		LOG.info('%s - %s' % (self.address_string(), format%args))

	def log_error(self, format, *args):
		LOG.error('%s - %s' % (self.address_string(), format%args))

	def do_GET(self):
		result = urllib.parse.urlparse(self.path)
		path = result.path
		args = result.query.split('&') if result.query != '' else []

		if path == '/refresh':
			self.refresh_handler()
		else:
			self.resource_handler(path)

	def do_POST(self):
		result = urllib.parse.urlparse(self.path)
		path = result.path

		if path == '/login':
			self.login()
		elif path == '/apply_config':
			self.apply_config()
		else:
			self.response(-1, "Invalid request: %s." % (path))

	def response(self, ret, msg, info=None):
		resp = {
			'result': ret,
			'msg': msg,
			'info': info
		}
		self.send_response(200)
		self.send_header("Content-type", "application/json")
		self.end_headers()
		self.wfile.write(bytes(json.dumps(resp), encoding='utf-8'))

	def resource_handler(self, path):
		if path == '/':
			path = '/index.html'

		path = resource_path_prefix() + 'web_console' + path

		if not os.path.exists(path):
			self.send_response(404)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.wfile.write(bytes("page not found", encoding='utf-8'))
			return

		content_type = "text/html"
		if path.endswith(".ico"):
			content_type = "image/x-icon"
		elif path.endswith(".js"):
			content_type = "application/x-javascript"
		elif path.endswith(".css"):
			content_type = "text/css"
		elif path.endswith(".svg"):
			content_type = "image/svg+xml"

		self.send_response(200)
		self.send_header("Content-type", content_type)
		self.end_headers()

		with open(path, 'rb') as resource:
				for line in resource.readlines():
					self.wfile.write(bytes(line))

	def refresh_handler(self):
		try:
			with open(CONF, 'r') as file:
				conf = yaml.safe_load(file.read())
				url = conf['url']
				protocol = conf['protocol']
				login_id = conf['login_id']
				password = conf['password']
				token = conf['token']
				reply_interval = conf['reply_config']['reply_interval']
				max_reply_interval = conf['reply_config']['max_reply_interval']
				reply_message = conf['reply_config']['reply_message']
				extend_message = conf['reply_config']['extend_message']
				whitelist = conf['reply_config']['whitelist']

			resp = {
				'url': url,
				'protocol': protocol,
				'login_id': login_id,
				'password': password,
				'token': token,
				'reply_config': {
					'reply_interval': reply_interval,
					'max_reply_interval': max_reply_interval,
					'reply_message': reply_message,
					'extend_message': extend_message,
					'whitelist': whitelist
				},
				'work_status': 1 if self.server.work_proc and self.server.work_proc.is_alive() else -1
			}

			self.send_response(200)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.wfile.write(bytes(json.dumps(resp), encoding='utf-8'))
		except Exception as e:
			self.response(-1, 'Refresh failed: %s' % (e))

	def login(self):
		if self.server.work_proc and self.server.work_proc.is_alive():
			self.response(0, "Login successed.")
			return

		data = self.rfile.read(int(self.headers['content-length']))
		data = eval(str(data, encoding='utf-8').replace('\n', '\\n'))

		options = {'url': data['url'],
				   'port': 443 if data['protocol'] == 'HTTPS' else 8065,
				   'keepalive': True,
				   'keepalive_delay': 5,
				   'scheme': data['protocol'].lower(),
				   'login_id': data['login_id'],
				   'password': data['password'],
				   'token': data['token'],
				   'timeout': 3,
				   'debug': False}

		reply_message = data['reply_config']['reply_message']
		if reply_message.endswith('\n'):
			reply_message = reply_message[:-1]

		config = {'reply_message': reply_message,
				  'extend_message': data['reply_config']['extend_message'].replace('\n', ''),
				  'reply_interval': data['reply_config']['reply_interval'],
				  'max_reply_interval': data['reply_config']['max_reply_interval'],
				  'whitelist': data['reply_config']['whitelist'].split()
		}

		self.server.auto_reply_tool = AutoReplyTool(options,
													config,
													get_logger('auto_reply', LOG_LEVEL),
													self.server.relogin_event,
													self.server.stop_event,
													self.server.config_queue)

		if not self.server.auto_reply_tool.login():
			LOG.error("Login failed.")
			self.response(-1, "Login failed.")
			self.server.work_proc = None
			return

		self.server.work_proc = multiprocessing.Process(target=self.server.auto_reply_tool.work)
		self.server.work_proc.start()

		self.response(0, "Login successed.")
		self.update_config(data)

	def apply_config(self):
		if self.server.work_proc is None:
			self.response(-1, "Apply config failed: Login first and try again.")
			return

		data = self.rfile.read(int(self.headers['content-length']))
		data = eval(str(data, encoding='utf-8'))

		try:
			self.server.config_queue.put_nowait(data['reply_config'])
		except queue.Full:
			self.response(-1, "Apply config failed: Please wait and retry.")
			return

		self.update_config(data)
		self.response(0, "Apply config successed.")

	def update_config(self, data):
		try:
			with open(CONF, 'r') as file:
				org_conf = yaml.safe_load(file.read())

			with open(CONF, 'w') as file:
				for each in org_conf:
					if each in data:
						org_conf[each] = data[each]

				yaml.dump(org_conf, file, sort_keys=False)
			LOG.info("Config %s updated." % (CONF))
		except Exception as e:
			LOG.error("Update config %s faield: %s." % (CONF, e))


if __name__ == '__main__':
	arg_parser = argparse.ArgumentParser()

	arg_parser.add_argument('--debug', required=False, action="store_const", const="True", help='Enable debug mode.')
	arg_parser.add_argument('--address', required=False, help='Listen on this address. Default: 127.0.0.1.')
	arg_parser.add_argument('--port', required=False, help='Listen on this port. Default: 6655.')

	args = arg_parser.parse_args()

	server_url = SERVER_URL if args.address is None else args.address
	server_port = SERVER_PORT if args.port is None else int(args.port)

	LOG_LEVEL = logging.DEBUG if args.debug else logging.INFO
	LOG = get_logger('web_console', LOG_LEVEL)

	# Init default config.
	if not os.path.exists(CONF):
		data = {
			'url': 'undefined',
			'protocol': 'HTTP',
			'login_id': 'undefined',
			'password': 'undefined',
			'token': 'undefined',
			'reply_config': {
				'reply_interval': 1800,
				'max_reply_interval': 86400,
				'reply_message': 'This is an auto reply message.',
				'extend_message': 'I got it',
				'whitelist': ''
			}
		}
		try:
			with open(CONF, 'w', encoding='utf-8') as conf:
				yaml.dump(data, conf, sort_keys=False)
				LOG.info("Init default config: %s done." % (CONF))
		except Exception as e:
			LOG.critical("Init config %s failed: %s." % (CONF, e))
			exit(-1)

	try:
		LOG.info("Init web console at: %s:%s." % (server_url, server_port))
		web_console = WebConsoleServer((server_url, server_port), WebConsoleHandler)
	except OSError as e:
		LOG.critical("Init web console at %s:%s failed: %s." %\
						 (server_url, server_port))
		exit(-1)

	try:
		web_console.icon_start()
		LOG.info("Start web console.")
		web_console.serve_forever()
	except KeyboardInterrupt:
		web_console.stop()
