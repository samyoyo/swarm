#!/user/bin/python
# -*- coding: utf-8 -*-

import multiprocessing
import Queue
import time
from multiprocessing.managers import BaseManager
from lib.core.logger import LOG

class SwarmManager(BaseManager):
	"""
	Task and Result Queue Manager.
	Use its subclass MSwarmManager and SSwarmManager to complete communication.
	"""
	def __init__(self,address=None,authkey=None):
		super(SwarmManager, self).__init__(address=address,authkey=authkey)


class MSwarmManager(SwarmManager):
	"""
	Task manager for master host.
	There should be only one master manager.
	"""
	def __init__(self,timeout,address=None,authkey=None):
		super(MSwarmManager, self).__init__(address=address,authkey=authkey)
		self._timeout=timeout
		self._task_queue=multiprocessing.Queue()
		self._result_queue=multiprocessing.Queue()
		# register these queue
		SwarmManager.register('get_task_queue',callable=lambda:self._task_queue)
		SwarmManager.register('get_result_queue',callable=lambda:self._result_queue)
		# start self
		self.start()

	def init_task_statistics(self):
		# used for recording current task queue info 
		self._cur_task_list=[]
		self._task_confirm_list=[]
		# start from 0 
		self._cur_task_num=0
		self._task_confirm_num=0

	def put_task(self,pre_str,task):
		"""
		Put task into task queue, update current task list and current task number meanwhile.
		"""
		task="|".join([pre_str,str(self._cur_task_num),task])
		LOG.debug('put task into queue:%s'%task)
		self._task_queue.put(task)
		self._cur_task_num+=1
		self._cur_task_list.append(task)

	def prepare_get_result(self):
		self._task_confirm_list=[0 for x in range(self._cur_task_num)]
		self._task_confirm_num=0

	def get_result(self):
		"""
		Get result from result queue, do task index confirm meanwhile
		Return '' if all tasks have been confirmed
		"""
		# check whether all task has been confirmed
		# if so, return ''
		if self._task_confirm_num==self._cur_task_num:
			return ''
		try:
			task_result=self._result_queue.get(block=True,timeout=self._timeout)
		except Queue.Empty, e:
			# maybe some slave host has lost response
			# put lost task again
			for cur_index,cur in enumerate(self._task_confirm_list):
				if cur==0:
					LOG.debug('put task into queue:%s'%self._cur_task_list[cur_index])
					self._task_queue.put(self._cur_task_list[cur_index])
			time.sleep(5)
			return self.get_result()
		resultl=task_result.split('|') 
		index=int(resultl[1],10)
		result=resultl[2]
		# do confirm
		# if it is duplicate, try to get result again
		if self._task_confirm_list[index]!=0:
			return self.get_result()
		self._task_confirm_list[index]=1
		self._task_confirm_num+=1
		LOG.info('task index:%d result:%s'%(index,result))
		return result


class SSwarmManager(SwarmManager):
	"""
	Task manager for slave host.
	"""
	def __init__(self,address=None,authkey=None):
		super(SSwarmManager, self).__init__(address=address,authkey=authkey)
		SwarmManager.register('get_task_queue')
		SwarmManager.register('get_result_queue')
		# connect to master
		self.connect()
		# get queue from master
		self._task_queue=self.get_task_queue()
		self._result_queue=self.get_result_queue()
		self._cur_task_index=0
		self._cur_task_flag=''
		
	def get_task(self):
		task=self._task_queue.get()
		LOG.debug('get task:%s'%task)
		taskl=task.split('|')
		self._cur_task_flag=taskl[0]
		self._cur_task_index=taskl[1]
		task=taskl[2:]
		return self._cur_task_flag,task

	def put_result(self,result):
		result="|".join([self._cur_task_flag,self._cur_task_index,result])
		LOG.debug('put result:%s'%result)
		self._result_queue.put(result)



