#!/usr/bin/python3
# coding=utf-8
from mattermostdriver import Driver
import datetime
import json
import logging
import asyncio


class AutoReplyTool(object):
	"""docstring for AutoReplyTool"""
	def __init__(self, options, reply_message, extend_message, reply_interval, max_reply_interval, whitelist):
		super(AutoReplyTool, self).__init__()
		self.mm_driver = Driver(options)
		self.username = ''
		self.config = {
			'reply_message': reply_message[:-1] if reply_message.endswith('\n') else reply_message,
			'extend_message': extend_message.replace('\n', ''),
			'reply_interval': reply_interval,
			'max_reply_interval': max_reply_interval,
			'whitelist': whitelist
		}
		self.update_config_cache = {'updated': False}
		self.reply_record = {}
		self.login_status = 0 # 0: uninitailized, 1: successed, -1 failed
		self.event_loop = None

	def stop(self):
		self.mm_driver.disconnect()

	def login(self):
		try:
			self.mm_driver.login()
			self.login_status = 1
		except Exception as e:
			logging.error("Login failed: %s" % (e))
			self.login_status = -1
			return

		self.username = self.mm_driver.client.username
		self.config['whitelist'].append(self.username)

		self.event_loop = asyncio.new_event_loop()
		asyncio.set_event_loop(self.event_loop)

		self.mm_driver.init_websocket(self.mm_event_handler)
		# self.event_loop.close()

	async def mm_event_handler(self, message):
		msg = json.loads(message)

		logging.debug('mm msg: %s' % json.dumps(msg, indent=2))

		post = self.post_handler(msg)

		if post is None:
			return

		self.auto_reply_handler(post)

	def post_handler(self, msg):
		if 'event' not in msg:
			return None

		if msg['event'] != 'posted':
			return None

		if 'data' not in msg:
			return None

		if 'post' not in msg['data']:
			return None

		if 'sender_name' not in msg['data']:
			return None

		# Skip '@'.
		if msg['data']['sender_name'][1:] in self.config['whitelist']:
			return None

		return json.loads(msg['data']['post'])

	def auto_reply_handler(self, post):
		if 'message' not in post or 'channel_id' not in post:
			return

		self.do_update_config()

		member_num = len(self.mm_driver.channels.get_channel_members(post['channel_id']))

		if member_num > 2:
			self.group_chat_reply_handler(post)
		else:
			self.chat_reply_handler(post)

	def group_chat_reply_handler(self, post):
		return

	def chat_reply_handler(self, post):
		channel_id = post['channel_id']
		message = post['message']

		if channel_id not in self.reply_record:
			self.reply_record[channel_id] = {'extend': False}

		if message == self.config['extend_message']:
			self.reply_record[channel_id]['extend'] = True
			return

		interval = self.config['max_reply_interval'] if self.reply_record[channel_id]['extend'] else self.config['reply_interval']
		prev = self.mm_driver.posts.get_posts_for_channel(channel_id, 'before=%s&per_page=1' % (post['id']))

		if len(prev['order']) == 1:
			prev_create_at = prev['posts'][prev['order'][0]]['create_at'] / 1000
			create_at = post['create_at'] / 1000

			logging.debug("prev_create_at: %s, create_at: %s, interval: %s." % (prev_create_at, create_at, interval))
			if create_at - prev_create_at < float(interval):
				return

		self.reply_record[channel_id]['extend'] = False

		extend_prompt = '\nSend `%s` to extend auto reply interval to `%s`. (Default: `%s`)' % \
						(self.config['extend_message'], datetime.timedelta(seconds=int(self.config['max_reply_interval'])),
						 datetime.timedelta(seconds=int(self.config['reply_interval'])))

		self.mm_driver.posts.create_post({'channel_id': channel_id,
										  'message': ('##### [Auto Reply] ' + self.config['reply_message'] + extend_prompt).replace('\n', '\n##### [Auto Reply] ')})

		# Mark new post unread so that we won't lose notification.
		self.mm_driver.client.make_request('post', '/users/%s/posts/%s/set_unread' % (self.mm_driver.client.userid, post['id']))

	def update_config(self, config):
		if 'reply_config' not in config:
			return

		for each in self.config:
			if each in config['reply_config']:
				self.update_config_cache[each] = config['reply_config'][each]

		self.update_config_cache['updated'] = True

	def do_update_config(self):
		if not self.update_config_cache['updated']:
			return

		for each in self.config:
			if each not in self.update_config_cache:
				continue

			value = self.update_config_cache[each]
			if each == 'reply_message' and value.endswith('\n'):
				value = value[:-1]

			if each == 'extend_message':
				value = value.replace('\n', '')

			if each == 'reply_interval' or each == 'max_reply_interval':
				self.reply_record = {}

			if each == 'whitelist':
				value = value.split()
				value.append(self.username)

			self.config[each] = value

		self.update_config_cache['updated'] = False

	# TODO: clean self.reply_record periodically.
	def clean_cache(self):
		pass