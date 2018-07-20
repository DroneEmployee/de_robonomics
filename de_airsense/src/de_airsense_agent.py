#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from robonomics_lighthouse.msg import Ask, Bid
from std_msgs.msg import String
from std_srvs.srv import Empty
import rospy
from web3 import Web3, HTTPProvider
import threading


class Agent:

	current_measurement = None

    def __init__(self):
        rospy.init_node('de_airsense_agent')

        self.model = rospy.get_param('~model')
        self.token = rospy.get_param('~token')
        self.bid_lifetime = rospy.get_param('~bid_lifetime')
        self.web3 = Web3(HTTPProvider(rospy.get_param('~web3_http_provider')))
        self.signing_bid_pub = rospy.Publisher('lighthouse/infochan/signing/bid', Bid, queue_size=10)

        def incoming_ask(ask_msg):
            if ask_msg.model == self.model and ask_msg.token == self.token:
                rospy.loginfo('Incoming ask with right model and token.')
                self.make_bid(ask_msg)
            else:
                rospy.loginfo('Incoming ask with wrong model and token, skip.')
        rospy.Subscriber('lighthouse/infochan/incoming/ask', Ask, incoming_ask)

        def measurements(hash_msg):
            self.current_measurement = hash_msg.data
            rospy.loginfo('Received measurements in IPFS file: ' + hash_msg.data)
        rospy.Subscriber('de_airsense_waspmore_ipfs/result/measurements', String, measurements)

        rospy.wait_for_service('liability/finish')
        self.finish_srv = rospy.ServiceProxy('liability/finish', Empty)

        threading.Thread(target=self.process, daemon=True).start()

    def make_bid(self, incoming_ask):
        rospy.loginfo('Making bid...')

        bid = Bid()
        bid.model = self.model
        bid.objective = incoming_ask.objective
        bid.token = self.token
        bid.cost = incoming_ask.cost
        bid.lighthouseFee = 0
        bid.deadline = self.web3.eth.getBlock('latest').number + self.bid_lifetime
        self.signing_bid_pub(bid)

    def process(self):
        while True:
            while not self.current_measurement:
                rospy.sleep(1)
            self.current_measurement = None
            self.finish_srv()
            rospy.loginfo('Liability finished')
    
    def spin(self):
        rospy.spin()

if __name__ == '__main__':
    Agent().spin()
