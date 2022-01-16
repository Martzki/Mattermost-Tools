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

SERVER_URL = '0.0.0.0'
SERVER_PORT = 6655
CONF = 'mm_conf.yaml'

class WebConsoleServer(HTTPServer):
	def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
		HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate=True)
		self.auto_reply_tool = None
		self.work_thread = None


class WebConsoleHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		result = urllib.parse.urlparse(self.path)
		path = result.path
		args = result.query.split('&') if result.query != '' else []

		if path == '/':
			self.show_page('web_console/index.html')
		elif path == '/js/auto_reply.js':
			self.show_page('web_console/js/auto_reply.js')
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

	def show_page(self, page):
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		with open(page, "r") as html:
			for line in html.readlines():
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
				   'scheme': data['protocol'],
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
				'interval': 1800,
				'max_interval': 86400,
				'message': 'This is an auto reply message.',
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

	web_console_mode = True

	if web_console_mode:
		web_console = WebConsoleServer((SERVER_URL, SERVER_PORT), WebConsoleHandler)
		web_console.serve_forever()
	else:
		with open(CONF, 'r') as conf:
			mm_conf = yaml.safe_load(conf.read())
			url = mm_conf['url']
			port = mm_conf['port']
			login_id = mm_conf['login_id']
			password = mm_conf['password']
			token = mm_conf['token']
			reply_message = mm_conf['reply_config']['message']
			extend_message = mm_conf['reply_config']['extend_message']
			reply_interval = mm_conf['reply_config']['interval']
			max_reply_interval = mm_conf['reply_config']['max_interval']

		options = {'url': url,
				   'port': port,
				   'keepalive': True,
				   'keepalive_delay': 5,
				   'scheme': 'https' if port == 443 else 'http',
				   'login_id': login_id,
				   'password': password,
				   'token': token}

		tool = AutoReplyTool(options,
							 reply_message=reply_message,
							 extend_message=extend_message,
							 reply_interval=reply_interval,
							 max_reply_interval=max_reply_interval)

		tool.login()