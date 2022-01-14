#!/usr/bin/python3
# coding=utf-8
from mattermostdriver import Driver
import datetime
import json
import logging


class AutoReplyTool(object):
	"""docstring for AutoReplyTool"""
	def __init__(self, options, reply_message, extend_message, reply_interval, max_reply_interval):
		super(AutoReplyTool, self).__init__()
		self.mm_driver = Driver(options)
		self.username = ''
		self.reply_message = reply_message
		self.extend_message = extend_message
		self.reply_interval = reply_interval
		self.max_reply_interval = max_reply_interval
		self.reply_record = {}

	def login(self):
		self.mm_driver.login()

		self.username = '@' + self.mm_driver.client.username

		self.mm_driver.init_websocket(self.mm_event_handler)

	async def mm_event_handler(self, message):
		msg = json.loads(message)

		logging.debug(json.dumps(msg, indent=2))

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

		if msg['data']['sender_name'] == self.username:
			return None

		return json.loads(msg['data']['post'])

	def auto_reply_handler(self, post):
		if 'message' not in post or 'channel_id' not in post:
			return

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

		now_time = datetime.datetime.now()

		if message == self.extend_message:
			self.reply_record[channel_id] = now_time + datetime.timedelta(seconds=self.max_reply_interval - self.reply_interval)

		if channel_id in self.reply_record:
			delta = (now_time - self.reply_record[channel_id]).seconds
			if now_time < self.reply_record[channel_id] or \
				(now_time > self.reply_record[channel_id] and delta < self.reply_interval):
				return

		self.reply_record[channel_id] = now_time

		extend_prompt = '\nSend `%s` to extend auto reply interval to %s.(Default: %s)' % \
						(self.extend_message, datetime.timedelta(seconds=self.max_reply_interval),
						 datetime.timedelta(seconds=self.reply_interval))

		self.mm_driver.posts.create_post({'channel_id': channel_id,
										  'message': ('##### [Auto Reply] ' + self.reply_message + extend_prompt).replace('\n', '\n##### [Auto Reply] ')})

		## Mark new post as unread so that we won't lose notification.
		self.mm_driver.client.make_request('post', '/users/%s/posts/%s/set_unread' % (self.mm_driver.client.userid, post['id']))
