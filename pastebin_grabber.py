#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import pymongo
from configparser import ConfigParser
import os
from modules.mod_pastebin import Pastebin
import urllib.request
import json
from multiprocessing.dummy import Pool

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('logs_snout.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
scrlog = logging.StreamHandler()
scrlog.setFormatter(logging.Formatter("[%(levelname)s] - %(message)s"))
logger.addHandler(scrlog)

if (sys.version_info < (3, 0)):
	logger.warning("ERROR: Please, use Python3.X")
	sys.exit()

def read_config(option ,section='scheduler', filename='config.ini'):
	parser = ConfigParser()
	parser.read(filename)
	if parser.has_section(section):
		if parser.has_option(section, option):
			value = parser.get(section, option)
		else:
			raise Exception('{0} option not found in the {1} section'.format(option, section))
	else:
		raise Exception('{0} section not found in the {1} file'.format(section, filename))
	return value

if __name__ == "__main__":

	# Connect to DB
	try:
		mongohost = read_config('host', 'mongodb')
		mongoport = read_config('port', 'mongodb')
		dbname = read_config('database', 'mongodb')

		connection = pymongo.MongoClient(mongohost, int(mongoport), serverSelectionTimeoutMS=1)
		connection.server_info()
		db = connection[dbname]
		logger.info('Connected to MongoDB')
	except pymongo.errors.ServerSelectionTimeoutError as e:
		logger.warning("Mongod is not started. Tape \"sudo mongod\" in a terminal")
		if not os.path.exists("/data/db"):
			os.makedirs("/data/db")
			logger.info('database created')
		logger.warning("Error %s", e)
		sys.exit()

	if not os.path.exists("Data/"):
		os.makedirs("Data/")
		logger.info('Data Dir created')
	if not os.path.exists("Data/pastebin"):
		os.makedirs("Data/pastebin")
		logger.info('pastebin Dir created')

	# Module Pastebin
	logger.info("Launching pastes downloads...")
	pb = Pastebin(db, logger)
	keys = []

	try:
		response = urllib.request.urlopen("https://pastebin.com/api_scraping.php?limit=250").read().decode('utf-8')
		jsonObj = json.loads(response)
		for i in jsonObj:
			if db.pastes.find({"key": i['key']}).count() == 0:
				keys.append(i['key'])

		size = int(len(keys)/5)#(limit/100))
		pool = Pool(int(5))#(limit/100))
		logger.debug(len(keys))
		pool.map(pb.pastes_download, keys, size)
		pool.close() 
		pool.join()

	except Exception as e:
		logger.debug(e)
