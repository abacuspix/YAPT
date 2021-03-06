# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER
# Copyright (c) 2018 Juniper Networks, Inc.
# All rights reserved.
# Use is subject to license terms.
#
# Author: cklewar

import datetime
import os
import lib.constants as c
import jinja2

from ansible.errors import AnsibleFileNotFound
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.vars.manager import VariableManager

from collections import namedtuple
from tempfile import NamedTemporaryFile
from lib.logmsg import LogAnsibleTask as logmsg
from lib.logmsg import LogCommon
from lib.tasks.provision.external.utils.callback import CallbackModule
from lib.tasks.task import Task
from lib.tools import Tools


class AnsibleapiTask(Task):
    CHECK_SCHEMA = True
    TASK_TYPE = c.TASK_TYPE_PROVISION
    TASK_VERSION = 1.0
    TASK_DESCENT = 'Configuration'

    def __init__(self, sample_device=None, shared=None):
        super(AnsibleapiTask, self).__init__(sample_device=sample_device, shared=shared)
        self.logger.debug(Tools.create_log_msg(self.task_name, self.sample_device.deviceSerial,
                                               LogCommon.IS_SUBCLASS.format(self.task_name,
                                                                            issubclass(AnsibleapiTask, Task))))

    def pre_run_task(self):
        pass

    def run_task(self):

        status_dev_cfg, dev_data_file = Tools.get_config(lookup_type=c.CONFIG_LOOKUP_TYPE_GET_DEVICE_CFG_FILE,
                                                         sample_device=self.sample_device)
        status_template, template_file = Tools.get_config(lookup_type=c.CONFIG_LOOKUP_TYPE_GET_TEMPLATE_FILE,
                                                          sample_device=self.sample_device)
        if status_dev_cfg:

            if status_template:

                loader = DataLoader()

                try:
                    ds = loader.load_from_file(
                        os.getcwd() + '/' + self.grp_cfg.TASKS.Provision.Configuration.Ansibleapi.PlaybookPath + self.grp_cfg.TASKS.Provision.Configuration.Ansibleapi.Playbook)
                except AnsibleFileNotFound as afnf:
                    self.update_task_state(new_task_state=c.TASK_STATE_FAILED,
                                           task_state_message=logmsg.PLAYBOOK_NOT_FOUND.format(afnf))
                    Tools.emit_log(task_name=self.task_name, sample_device=self.sample_device,
                                   message=logmsg.PLAYBOOK_NOT_FOUND.format(afnf))
                    return

                # Dynamic Inventory
                inventory = """
                    [YAPT]
                     {{ hosts }}
        
                    [YAPT:vars]
                      junos_user={{ junos_user }}
                      junos_password={{ junos_password }}
                      template_src={{ template_src }}
                      template_dst={{ template_dst }}
                      device_vars={{ device_vars }}
                      heading={{ heading }}
                    """

                inventory_template = jinja2.Template(inventory)
                '''
                ## Last changed: 2017-10-16-2139 version 12.1X47-D35.2;
                '''
                heading = """## Last changed: {0} version {1};
                    """.format(datetime.datetime.now().strftime('%Y-%m-%d-%H%M'), self.sample_device.softwareVersion)

                rendered_inventory = inventory_template.render({
                    'hosts': self.sample_device.deviceIP,
                    'junos_user': c.conf.YAPT.DeviceUsr,
                    'junos_password': Tools.get_password(c.YAPT_PASSWORD_TYPE_DEVICE),
                    'template_src': template_file,
                    'template_dst': os.getcwd() + '/history/' + self.sample_device.deviceSerial + '-' + datetime.datetime.now().strftime(
                        '%Y-%m-%d-%H%M') + '.conf',
                    'device_vars': dev_data_file,
                    'heading': heading
                })

                self.logger.debug(
                    Tools.create_log_msg(self.task_name, self.sample_device.deviceSerial, rendered_inventory))

                # Create a temporary file and write the template string to it
                hosts = NamedTemporaryFile(delete=False)
                hosts.write(rendered_inventory)
                hosts.close()
                inventory = InventoryManager(loader=loader, sources=hosts.name)
                variable_manager = VariableManager(loader=loader, inventory=inventory)

                Options = namedtuple('Options',
                                     ['listtags', 'listtasks', 'listhosts', 'syntax', 'connection', 'module_path',
                                      'forks',
                                      'remote_user', 'private_key_file', 'ssh_common_args', 'ssh_extra_args',
                                      'sftp_extra_args', 'scp_extra_args', 'become', 'become_method', 'become_user',
                                      'verbosity', 'check', 'diff'])
                options = Options(listtags=False, listtasks=False, listhosts=True, syntax=False, connection='ssh',
                                  module_path=None, forks=100, remote_user=None,
                                  private_key_file=None, ssh_common_args=None, ssh_extra_args=None,
                                  sftp_extra_args=None, scp_extra_args=None, become=False, become_method=None,
                                  become_user=None, verbosity=None, check=False, diff=False)

                passwords = dict(vault_pass=Tools.get_password(c.YAPT_PASSWORD_TYPE_DEVICE))
                play = Play.load(data=ds[0], variable_manager=variable_manager, loader=loader)

                results_callback = CallbackModule(sample_device=self.sample_device, shared=self.shared,
                                                  update_task_state=self.update_task_state)
                tqm = None

                try:
                    tqm = TaskQueueManager(
                        inventory=inventory,
                        variable_manager=variable_manager,
                        loader=loader,
                        options=options,
                        passwords=passwords,
                        stdout_callback=results_callback,
                    )

                    result = tqm.run(play)

                    if result > 0:
                        self.update_task_state(new_task_state=c.TASK_STATE_FAILED,
                                               task_state_message=logmsg.ANSIBLE_ERROR)
                        Tools.emit_log(task_name=self.task_name, sample_device=self.sample_device,
                                       message=logmsg.ANSIBLE_ERROR)
                        os.remove(hosts.name)
                        return

                    else:
                        self.update_task_state(new_task_state=c.TASK_STATE_PROGRESS,
                                               task_state_message=logmsg.PLAYBOOK_FINISHED_SUCCESS)
                        self.sample_device.deviceConnection.facts_refresh()
                        self.sample_device.deviceConnection.facts_refresh(keys='hostname')
                        self.sample_device.deviceName = self.sample_device.deviceConnection.facts['hostname']
                        self.update_task_state(new_task_state=c.TASK_STATE_DONE,
                                               task_state_message=c.TASK_STATE_MSG_DONE)
                        Tools.emit_log(task_name=self.task_name,
                                       task_state={'taskState': self.task_state,
                                                   'taskStateMsg': c.TASK_STATE_MSG_DONE},
                                       sample_device=self.sample_device, grp_cfg=self.grp_cfg,
                                       shared=self.shared,
                                       message=logmsg.PLAYBOOK_FINISHED_SUCCESS,
                                       scope=c.LOGGER_SCOPE_ALL, level=c.LOGGER_LEVEL_INFO)
                        os.remove(hosts.name)

                except Exception as e:
                    self.update_task_state(new_task_state=c.TASK_STATE_FAILED,
                                           task_state_message=logmsg.PLAYBOOK_ERROR.format(e))
                    Tools.emit_log(task_name=self.task_name, sample_device=self.sample_device,
                                   message=logmsg.PLAYBOOK_ERROR.format(e))
                    return

                finally:
                    if tqm is not None:
                        tqm.cleanup()
            else:
                self.update_task_state(new_task_state=c.TASK_STATE_FAILED,
                                       task_state_message=logmsg.ERROR_DEV_CFG_FILE)
                Tools.emit_log(task_name=self.task_name, sample_device=self.sample_device,
                               message=logmsg.ERROR_DEV_TEMPLATE_FILE.format(template_file))
        else:
            self.update_task_state(new_task_state=c.TASK_STATE_FAILED,
                                   task_state_message=logmsg.ERROR_DEV_CFG_FILE)
            Tools.emit_log(task_name=self.task_name, sample_device=self.sample_device,
                           message=logmsg.ERROR_DEV_CFG_FILE.format(dev_data_file))
            return

    def post_run_task(self):
        pass
