#!/usr/bin/python3
# coding=utf-8
from auto_reply import AutoReplyTool
import logging
import yaml

if __name__ == '__main__':
	logging.basicConfig(level=logging.INFO)

	with open('mm_conf.yaml', 'r') as conf:
		mm_conf = yaml.safe_load(conf.read())
		url = mm_conf['url']
		port = mm_conf['port']
		login_id = mm_conf['login_id']
		password = mm_conf['password']
		token = mm_conf['token']
		reply_message = mm_conf['reply_config']['message']
		extend_message = mm_conf['reply_config']['extend_message']
		reply_interval = int(mm_conf['reply_config']['interval'])
		max_reply_interval = int(mm_conf['reply_config']['max_interval'])

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