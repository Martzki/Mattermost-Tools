#!/usr/bin/python3
# coding=utf-8
from mattermostdriver import Driver
from mattermostdriver.exceptions import NoAccessTokenProvided
import datetime
import logging
import json
import queue
import signal
import threading

LOG = None


class AutoReplyTool(object):
	"""docstring for AutoReplyTool"""
	def __init__(self, options, config, logger, relogin_event, stop_event, config_queue):
		super(AutoReplyTool, self).__init__()
		self.mm_driver = Driver(options)
		self.username = ''
		self.config = config
		self.reply_record = {}
		self.relogin_event = relogin_event
		self.stop_event = stop_event
		self.config_queue = config_queue
		global LOG
		LOG = logger

	def stop_handler(self):
		self.stop_event.wait()
		self.mm_driver.disconnect()
		LOG.info('Stop auto reply tool done.')

	def login(self):
		try:
			self.mm_driver.login()
		except Exception as e:
			LOG.error("Login failed: %s" % (e))
			return False

		self.username = self.mm_driver.client.username
		self.config['whitelist'].append(self.username)

		return True

	def work(self):
		LOG.info('Auto reply started.')

		def ignore_signal(sig, frame):
			LOG.info("Ignore signal: %s frame: %s." % (sig, frame))

		signal.signal(signal.SIGINT, ignore_signal)

		stop_handler = threading.Thread(target=self.stop_handler)
		stop_handler.start()

		self.mm_driver.init_websocket(self.mm_event_handler)

		LOG.info('Auto reply finished.')

	async def mm_event_handler(self, message):
		msg = json.loads(message)

		# Log will record user's message to log file so disable by default.
		# LOG.debug('mm msg: %s' % json.dumps(msg, indent=2))

		post = self.post_handler(msg)

		if post is None:
			return

		try:
			self.auto_reply_handler(post)
		except NoAccessTokenProvided as e:
			LOG.error('Authentication is invalid: %s' % e)
			self.relogin_event.set()
			self.mm_driver.disconnect()

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

		LOG.debug('Handle message in channel %s.' % (channel_id))

		if channel_id not in self.reply_record:
			self.reply_record[channel_id] = {'extend': False}

		if message == self.config['extend_message']:
			LOG.debug('Extend reply interval.')
			self.reply_record[channel_id]['extend'] = True
			return

		interval = self.config['max_reply_interval'] if self.reply_record[channel_id]['extend'] else self.config['reply_interval']
		prev = self.mm_driver.posts.get_posts_for_channel(channel_id, 'before=%s&per_page=1' % (post['id']))

		if len(prev['order']) == 1:
			prev_create_at = prev['posts'][prev['order'][0]]['create_at'] / 1000
			create_at = post['create_at'] / 1000

			LOG.debug("prev_create_at: %s, create_at: %s, interval: %s." % (prev_create_at, create_at, interval))
			if create_at - prev_create_at < float(interval):
				return

		self.reply_record[channel_id]['extend'] = False

		extend_prompt = '\nSend `%s` to extend auto reply interval to `%s`. (Default: `%s`)' % \
						(self.config['extend_message'], datetime.timedelta(seconds=int(self.config['max_reply_interval'])),
						 datetime.timedelta(seconds=int(self.config['reply_interval'])))

		reply = ('##### [Auto Reply] ' + self.config['reply_message'] + extend_prompt).replace('\n', '\n##### [Auto Reply] ')
		self.mm_driver.posts.create_post({'channel_id': channel_id, 'message': reply})
		LOG.debug('Send reply to channel %s.' % (channel_id))

		# Mark new post unread so that we won't lose notification.
		self.mm_driver.client.make_request('post', '/users/%s/posts/%s/set_unread' % (self.mm_driver.client.userid, post['id']))

	def do_update_config(self):
		try:
			config = self.config_queue.get_nowait()
		except queue.Empty:
			return

		LOG.info('Get new config: %s' % (config))
		for each in self.config:
			if each not in config:
				continue

			value = config[each]
			if each == 'reply_message' and value.endswith('\n'):
				value = value[:-1]

			if each == 'extend_message':
				value = value.replace('\n', '')

			if each == 'reply_interval' or each == 'max_reply_interval':
				self.reply_record = {}

			if each == 'whitelist':
				value = value.split()
				value.append(self.username)

			LOG.info('Config %s is updated from %s to %s.' % (each, self.config[each], value))
			self.config[each] = value

	# TODO: clean self.reply_record periodically.
	def clean_cache(self):
		pass