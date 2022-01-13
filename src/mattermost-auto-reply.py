#!/usr/bin/python3
# coding=utf-8
from mattermostdriver import Driver
import datetime
import json
import logging
import yaml


MM = None
USERNAME = ''
REPLY_MESSAGE = ''
EXTEND_MESSAGE = ''
REPLY_INTERVAL = 60
REPLY_RECORD = {}
MAX_REPLY_INTERVAL = 300

def auto_reply_handler(post, sender_name):
	if 'message' not in post or 'channel_id' not in post:
		return

	channel_id = post['channel_id']
	message = post['message']

	logging.debug("channel_id: %s, msg: %s" % (channel_id, message))

	member_num = len(MM.channels.get_channel_members(channel_id))

	if member_num > 2:
		return

	now_time = datetime.datetime.now()

	if message == EXTEND_MESSAGE:
		REPLY_RECORD[channel_id] = now_time + datetime.timedelta(seconds=MAX_REPLY_INTERVAL - REPLY_INTERVAL)

	if channel_id in REPLY_RECORD:
		delta = (now_time - REPLY_RECORD[channel_id]).seconds
		if now_time < REPLY_RECORD[channel_id] or \
			(now_time > REPLY_RECORD[channel_id] and delta < REPLY_INTERVAL):
			return

	REPLY_RECORD[channel_id] = now_time

	extend_prompt = '\nSend `%s` to extend auto reply interval to %s.(Default: %s)' % \
					(EXTEND_MESSAGE, datetime.timedelta(seconds=MAX_REPLY_INTERVAL),
					 datetime.timedelta(seconds=REPLY_INTERVAL))

	MM.posts.create_post({'channel_id': channel_id, 'message': REPLY_MESSAGE + extend_prompt})


def post_handler(msg):
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

	if msg['data']['sender_name'] == USERNAME:
		return None

	return json.loads(msg['data']['post'])


async def mm_event_handler(message):
	msg = json.loads(message)

	#logging.debug(json.dumps(msg, indent=2))

	post = post_handler(msg)

	if post is None:
		return

	auto_reply_handler(post, msg['data']['sender_name'])


if __name__ == '__main__':
	url = None
	port = None
	login_id = None
	password = None
	token = None

	logging.basicConfig(level=logging.INFO)

	with open('mm_conf.yaml', 'r') as conf:
		mm_conf = yaml.safe_load(conf.read())
		url = mm_conf['url']
		port = mm_conf['port']
		login_id = mm_conf['login_id']
		password = mm_conf['password']
		token = mm_conf['token']
		REPLY_MESSAGE = mm_conf['reply_config']['message']
		EXTEND_MESSAGE = mm_conf['reply_config']['extend_message']
		REPLY_INTERVAL = int(mm_conf['reply_config']['interval'])
		MAX_REPLY_INTERVAL = int(mm_conf['reply_config']['max_interval'])

	options = {'url': url,
			   'port': port,
			   'keepalive': True,
			   'keepalive_delay': 5,
			   'scheme': 'http',
			   'login_id': login_id,
			   'password': password,
			   'token': token}

	mm = Driver(options)

	try:
		mm.login()
	except Exception as e:
		logging.critical("login failed: %s" % (e))
		exit(0)

	MM = mm
	USERNAME = '@' + mm.client.username

	mm.init_websocket(mm_event_handler)
