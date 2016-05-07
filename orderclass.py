import random
import json
from collections import defaultdict


def jdefault(o):
    return o.__dict__


def JsonLoad(o):
	return eval(o)

class Order:
	def __init__(self,item,qty,cost):
		self.item=item
		self.qty=qty
		self.cost=cost

	def getcost(self):
		return self.cost

	def getitem(self):
		return self.item

	def getqty(self):
		return self.qty



class OrderWrapper:
	def __init__(self,userid):
		self.userid=userid
		self.items=[]
	def addorder(self,order):
		self.items.append(order)

	def getorders(self):
		return self.items
