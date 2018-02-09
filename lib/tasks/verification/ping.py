# Copyright (c) 1999-2017, Juniper Networks Inc.
# All rights reserved.
#
# Authors: cklewar@juniper.net
#

from lib.tasks.task import Task
from lib.tools import Tools


class PingVerifyTask(Task):
    CHECK_SCHEMA = False
    TASK_TYPE = Tools.TASK_TYPE_VERIFICATION
    TASK_VERSION = 1.0

    def __init__(self, sample_device=None, shared=None):

        super(PingVerifyTask, self).__init__(sample_device=sample_device, shared=shared)
        self.logger.debug('Subclass: %s', issubclass(PingVerifyTask, Task))
        self.logger.debug('Instance: %s', isinstance(PingVerifyTask, Task))

    def pre_run_task(self):
        pass

    def run_task(self):

        if self.sample_device.connected:

            result = self.sample_device.deviceConnection.rpc.ping(host=Tools.conf.VERIFICATION.Ping.Destination,
                                                                  count=self.grp_cfg.VERIFICATION.Ping.Count)
            pktloss = result.findtext('.//packet-loss').lstrip('\n').strip('\n')

            if pktloss == '0':
                self.logger.info('VerifyPing-[%s]: Test successfull', self.sample_device.deviceIP)
                self.sample_device.deviceVerificationTasksStates['Ping'] = 'Success'

            else:
                self.logger.info('VerifyPing-[%s]: Test failed', self.sample_device.deviceIP)
                self.sample_device.deviceVerificationTasksStates['Ping'] = 'Failed'

        else:
            self.logger.info('VerifyPing-[%s]: Error in device connection', self.sample_device.deviceIP)

    def post_run_task(self):
        pass