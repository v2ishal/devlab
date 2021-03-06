#!/usr/bin/python

import subprocess
import os
import sys
import re
import time
import pprint

import tweepy
import json
import hvac
from lib.logger import logit
#import logger
import inspect

import sys
from time import sleep
import boto3
from botocore.exceptions import ClientError

def import_load_tweet_conf():

	global VAULT_TOKEN
	global VAULT_URL
	global VAULT_SECRET
	global AWS_DD_TABLE
	global LOGS_PATH

	try:
		import load_tweet_conf
		reload(load_tweet_conf)
	except Importerror:
		print "Unable to import config"

	if load_tweet_conf:
		config = load_tweet_conf.get_config()
		VAULT_TOKEN = config['vault_token']
		VAULT_URL = config['vault_url']
		VAULT_SECRET = config['vault_secret']
		AWS_DD_TABLE = config['aws_dd_table']
	return

def lineno():
	"""Returns the current line number in program."""
	return inspect.currentframe().f_back.f_lineno


def add(key, value):
	temp = dict()
	temp[key] = value


def aws_dynamodb_upload(upload_list):
	print "Running upload to %s table..."%AWS_DD_TABLE
	cnt = 1
	table = boto3.resource("dynamodb").Table(AWS_DD_TABLE)
	pprint.pprint(table)
	try:
		with table.batch_writer() as batch:
			list_len = len(upload_list)
			for line in upload_list:
				#batch.put_item(Item={"id": i, "name": "Paquito Pinhorn"})
				print "Count - %d line - %s" %(cnt,line)
				if cnt != list_len:
					cnt += 1
			
				#print(table.scan()["Items"])
	except ClientError as e:
		print(e)

def tweet_auth(conf):
	auth = tweepy.OAuthHandler(conf['data']['CONSUMER_KEY'],conf['data']['CONSUMER_SECRET'])
	auth.set_access_token(conf['data']['ACCESS_TOKEN'],conf['data']['ACCESS_TOKEN_SECRET'])


	api = tweepy.API(auth)
	try:
		api.verify_credentials()
		print("Authentication OK")
		auth = 1
	except:
		print("Error during twitter authentication")
		auth = 0
		exit(0)

	return api


def tweet_read(api):
	public_tweets = api.home_timeline(count=5)
	print len(public_tweets)
	list1 = []
	for tweet in public_tweets:
		tweet_str = tweet.text
		
		tweet_asc = tweet_str.encode('ascii', 'ignore')
		tweettxt,tweeturl = rebuild_payload(tweet_asc)
		time.sleep(2)
		load_str = tweettxt + "|" + tweeturl
		list1.append(load_str)
	return list1

def rebuild_payload(tweetstr):

	pattern1 = re.compile("(.?)https:\/\/.*(.?)")
	
	# URL extract
	u =  pattern1.search(tweetstr)
	if u:
		url = u.group(0)
	else:
		url = "NO URL"
	# Text extraction
	if "\n\n" in tweetstr:
		tweetstr =  tweetstr.replace("\n\n"," ")
	
	if "\n" in tweetstr:
                tweetstr = tweetstr.replace("\n"," ")

	temp = tweetstr.split("https")
	return temp[0] , url

def vault_status():

	command = "vault status | grep -i Sealed | awk -F' ' '{print $2}'"
	output = run_command(command)
	return output

def vault_read_keys(vault_url,vault_token,vault_secret):
	client = hvac.Client(vault_url, vault_token)
	sec = client.read(vault_secret)
	return sec


def run_command(cmd):
	outputobj = os.popen(cmd)
	output = outputobj.readline()
	return output

if __name__ == "__main__":


	import_load_tweet_conf()

	print "Validating vault is unseal/seal"
	vault_output = vault_status()
	vault_output.strip()
	if vault_output == 'false':
		print "Vault is unsealed :)"
	else:
		print "Vault Sealed"

	conf = vault_read_keys(VAULT_URL,VAULT_TOKEN,VAULT_SECRET)
	apiobj = tweet_auth(conf)

	upload1 = tweet_read(apiobj)
	aws_dynamodb_upload(upload1)
