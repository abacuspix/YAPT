# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
# Copyright (c) 2018 Juniper Networks, Inc.
# All rights reserved.
# Use is subject to license terms.
#
# Author: cklewar

import argparse

from lib.backend.backend import Backend
import lib.constants as c
from lib.pluginfactory import BackendPluginFactory
from lib.pluginfactory import EmitterPlgFact
from lib.tools import Tools


class YaptBackend(object):

    if __name__ == '__main__':

        Tools.create_config_view(c.CONFIG_TYPE_MAIN)
        EmitterPlgFact()

        parser = argparse.ArgumentParser()
        parser.add_argument("amqpIp", help="provide amqp bus ip")
        args = parser.parse_args()
        c.conf.AMQP.Host = args.amqpIp

        BackendPluginFactory(plugin_name=c.conf.BACKEND.Module, target=Backend,
                             name=c.AMQP_PROCESSOR_BACKEND)
