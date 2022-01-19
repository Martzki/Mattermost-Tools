#!/usr/bin/python3
# coding=utf-8
from http.server import HTTPServer, BaseHTTPRequestHandler
from auto_reply import AutoReplyTool
import logging
import json
import yaml
import urllib
import threading
import os
import time
import sys

if sys.platform == 'win32':
	from pystray import MenuItem
	from pystray import Icon
	from PIL import Image
	import webbrowser


SERVER_URL = '0.0.0.0'
SERVER_PORT = 6655
CONF = 'mm_conf.yaml'

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
			image = Image.open("web_console/images/favicon.ico")
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
	def do_GET(self):
		result = urllib.parse.urlparse(self.path)
		path = result.path
		args = result.query.split('&') if result.query != '' else []

		if path == '/':
			self.resource_handler('web_console/index.html', 'text/html')
		elif path == '/js/auto_reply.js':
			self.resource_handler('web_console/js/auto_reply.js', 'application/x-javascript')
		elif path == '/images/favicon.ico':
			self.resource_handler('web_console/images/favicon.ico', 'image/x-icon')
		elif path == '/refresh':
			self.refresh_handler()
		else:
			self.response(-1, "Invalid request: %s." % (path))

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

	def resource_handler(self, path, header):
		self.send_response(200)
		self.send_header("Content-type", header)
		self.end_headers()

		if header == 'image/x-icon':
			with open(path, 'rb') as resource:
				for line in resource.readlines():
					self.wfile.write(bytes(line))
		else:
			with open(path, 'r') as resource:
				for line in resource.readlines():
					self.wfile.write(bytes(line, encoding='utf-8'))

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
	logging.basicConfig(level=logging.INFO)

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
				conf.flush()
		except Exception as e:
			logging.critical("Init config %s failed: %s." % (CONF, e))
			exit(-1)

	try:
		web_console = WebConsoleServer((SERVER_URL, SERVER_PORT), WebConsoleHandler)
	except OSError as e:
		logging.critical("Init web console server(%s:%s) failed: %s." %\
						 (SERVER_URL, SERVER_PORT))
		exit(-1)

	web_console.start()
