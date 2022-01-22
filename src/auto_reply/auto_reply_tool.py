#!/usr/bin/python3
# coding=utf-8
from http.server import HTTPServer, BaseHTTPRequestHandler
from auto_reply import AutoReplyTool
import argparse
import logging
import json
import os
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
LOG_FILE = 'MattermostTools.log'

def resource_path_prefix():
	return sys._MEIPASS + '/' if getattr(sys, 'frozen', False) else './'

class WebConsoleServer(HTTPServer):
	def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
		HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=True)
		self.auto_reply_tool = None
		self.work_thread = None
		self.gui_thread = None
		self.icon = None

	def start(self):
		# Only create icon GUI thread on win32 platform.
		if sys.platform == 'win32':
			image = Image.open(resource_path_prefix() + "web_console/images/favicon.ico")
			menu = (MenuItem('HomePage', self.icon_home_page_handler, default=True),
					MenuItem('Exit', self.icon_exit_handler))
			self.icon = Icon("MattermostTools", image, "MattermostTools", menu)

			self.gui_thread = threading.Thread(target=self.icon.run, args=[self.icon_setup])
			self.gui_thread.start()

		try:
			self.serve_forever()
		except KeyboardInterrupt:
			self.stop()
			exit(0)

	def stop(self):
		# TODO: the code below can't stop gracefully.
		# if type(self.auto_reply_tool) == AutoReplyTool:
		# 	self.auto_reply_tool.stop()
		# 	logging.info('Stop auto reply tool done.')

		# if type(self.work_thread) == threading.Thread:
		# 	self.work_thread.join()
		# 	logging.info('Stop auto reply work thread done.')

		if type(self.gui_thread) == threading.Thread:
			self.icon.stop()
			logging.info('Stop GUI thread done.')

		self.shutdown()
		logging.info('Stop web console server done.')

	def icon_setup(self, icon):
		icon.visible = True
		icon.notify("Web Console is working at: http://127.0.0.1:%s" % \
					(SERVER_PORT), "MattermostTools")

		webbrowser.open("http://127.0.0.1:%s" % (SERVER_PORT))

	def icon_home_page_handler(self):
		webbrowser.open("http://127.0.0.1:%s" % (SERVER_PORT))

	def icon_exit_handler(self):
		self.stop()


class WebConsoleHandler(BaseHTTPRequestHandler):
	def log_message(self, format, *args):
		logging.info('%s - %s' % (self.address_string(), format%args))

	def log_error(self, format, *args):
		logging.error('%s - %s' % (self.address_string(), format%args))

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
					'extend_message': extend_message
				},
				'work_status': self.server.auto_reply_tool.login_status \
								if self.server.auto_reply_tool is not None else -1
			}

			self.send_response(200)
			self.send_header("Content-type", "text/html")
			self.end_headers()
			self.wfile.write(bytes(json.dumps(resp), encoding='utf-8'))
		except Exception as e:
			self.response(-1, 'Refresh failed: %s' % (e))

	def login(self):
		if self.server.work_thread is not None:
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
				   'token': data['token']}

		reply_message = data['reply_config']['reply_message']
		extend_message = data['reply_config']['extend_message']
		reply_interval = data['reply_config']['reply_interval']
		max_reply_interval = data['reply_config']['max_reply_interval']

		self.server.auto_reply_tool = AutoReplyTool(options,
							 reply_message=reply_message,
							 extend_message=extend_message,
							 reply_interval=reply_interval,
							 max_reply_interval=max_reply_interval)

		self.server.work_thread = threading.Thread(target=self.server.auto_reply_tool.login)
		self.server.work_thread.start()

		for i in range(100):
			if self.server.auto_reply_tool.login_status == 1 or \
				self.server.auto_reply_tool.login_status == -1:
				break

			time.sleep(0.1)

		if self.server.auto_reply_tool.login_status == 1:
			self.response(0, "Login successed.")
			self.update_config(data)
		elif self.server.auto_reply_tool.login_status == -1:
			self.response(-1, "Login failed.")
			self.server.work_thread.join()
			self.server.work_thread = None

	def apply_config(self):
		if self.server.work_thread is None:
			self.response(-1, "Apply config failed: Login first and try again.")
			return

		data = self.rfile.read(int(self.headers['content-length']))
		data = eval(str(data, encoding='utf-8').replace('\n', '\\n'))

		self.server.auto_reply_tool.update_config(data)
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
			logging.info("Config %s updated." % (CONF))
		except Exception as e:
			logging.error("Update config %s faield: %s." % (CONF, e))


if __name__ == '__main__':
	arg_parser = argparse.ArgumentParser()

	arg_parser.add_argument('--debug', required=False, action="store_const", const="True", help='Enable debug mode.')
	arg_parser.add_argument('--address', required=False, help='Listen on this address. Default: 127.0.0.1.')
	arg_parser.add_argument('--port', required=False, help='Listen on this port. Default: 6655.')

	args = arg_parser.parse_args()

	server_url = SERVER_URL if args.address is None else args.address
	server_port = SERVER_PORT if args.port is None else int(args.port)

	logging.basicConfig(level=logging.INFO if args.debug is None else logging.DEBUG,
						filename=None if args.debug is None else LOG_FILE,
						filemode='a',
						format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s')

	# Init default config.
	if not os.path.exists(CONF):
		data = {
			'url': 'your.mattermost.server.com',
			'protocol': 'HTTPS',
			'login_id': 'login_id',
			'password': 'password',
			'token': 'token',
			'reply_config': {
				'reply_interval': 1800,
				'max_reply_interval': 86400,
				'reply_message': 'This is an auto reply message.',
				'extend_message': 'I got it'
			}
		}
		try:
			with open(CONF, 'w', encoding='utf-8') as conf:
				yaml.dump(data, conf, sort_keys=False)
				logging.info("Init default config: %s done." % (CONF))
		except Exception as e:
			logging.critical("Init config %s failed: %s." % (CONF, e))
			exit(-1)

	try:
		web_console = WebConsoleServer((server_url, server_port), WebConsoleHandler)
	except OSError as e:
		logging.critical("Init web console server(%s:%s) failed: %s." %\
						 (server_url, server_port))
		exit(-1)

	web_console.start()
