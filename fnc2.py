__author__ = 'Yoni Shperling'

import atexit
# import csv
import getpass
import json
import multiprocessing
import logging
import os.path
import re
import requests
import subprocess
import sys
from time import sleep
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
from multiprocessing.dummy import Pool as ThreadPool
import ast
import argparse
# from fnc1 import *
import random

from tools import tasks


def vc_si(args):
    """
    function connect to vc and return si (service instance)
    """

    logger = logging.getLogger(__name__)

    host = args.host[0]
    username = args.username[0]
    password = args.password[0]
    port = args.port[0]

    si = None
    try:
        si = SmartConnect(
            host=host,
            user=username,
            pwd=password,
            port=port)

        logger.info('Connecting to VC %s:%s with username %s' % (host, port, username))
        '''two below test'''
        logger.info("Connecting to VC '{}'".format(host))

    except IOError as e:
        logger.error('Could not connect to host %s with user %s and specified password' % (host, username))
        return 1
    logger.debug('Registering disconnect at exit')
    atexit.register(Disconnect, si)

    return si


def get_obj(si, vimtype, name):
    """
    Return an object by name, if name is any the
    all objects are returned

    :param si: service instance
    :param vimtype: vib object
    :param name:
    :return: obj
    """

    if type(name) is str:
        content = si.content
        obj = None
        objs = []
        container = content.viewManager.CreateContainerView(
            content.rootFolder, vimtype, True)
        for c in container.view:
            if name and not name == 'any':
                if c.name == name:
                    obj = c
                    break
            else:
                objs.append(c)
                obj = objs
        return obj
    else:
        return name


class VimObj:
    def __init__(self):
        self.data = []

    def dc(self, si, dc_name):
        return get_obj(si, [vim.Datacenter], dc_name)

    def cl(self, si, cl_name):
        return get_obj(si, [vim.ComputeResource], cl_name)

    def cl_res(self, si, cl_name):
        """
        check if I need that insted cl ComputeResource
        :param si:
        :param cl_name:
        :return:
        """
        return get_obj(si, [vim.ClusterComputeResource], cl_name)

    def hs(self, si, hs_name):
        return get_obj(si, [vim.HostSystem], hs_name)

    def ds(self, si, ds_name):
        return get_obj(si, [vim.Datastore], ds_name)

    def pg(self, si, pg_name):
        return get_obj(si, [vim.dvs.DistributedVirtualPortgroup], pg_name)

    def vm(self, si, vm_name):
        return get_obj(si, [vim.VirtualMachine], vm_name)


class DataCenter(VimObj):
    def __init__(self):
        VimObj.__init__(self)

    def return_dcs(self, si, dc_name):
        """
        return object dc by name,
        if name is any objects are returned
        :return: return_obj == dc
        """

        return VimObj.dc(self, si, dc_name)


class Network(VimObj):
    def __init__(self):
        VimObj.__init__(self)

    def get_pg(self, si, pg_name):
        """
        Return port-group
        :param si:
        :param pg_name:
        :return:
        """

        return VimObj.pg(self, si, pg_name)


class Cluster(VimObj):
    def __init__(self):
        VimObj.__init__(self)

    def return_clusters(self, si, cl_name):
        """
        return object cluster by name,
        if name is any objects are returned
        :return: return_obj == cluster
        """

        return VimObj.cl(self, si, cl_name)

    def get_hosts_of_cluster(self, si, cl_name):
        """
        return object host of cluster
        :return: return_obj ==
         cluster
        """
        # print [host.host for host in Cluster.return_clusters(self, si, cl_name)][0]
        return Cluster.return_clusters(self, si, cl_name)[0].host

    def get_ready_hosts_of_cluster(self, si, cl_name):
        return [host for host in Cluster.get_hosts_of_cluster(self, si, cl_name)
                if host.runtime.connectionState == 'connected' and
                host.runtime.inMaintenanceMode is False]


        # return [host for host in Cluster.return_clusters(self, si, cl_name)[0].host]


class Host(VimObj):
    def __init__(self):
        VimObj.__init__(self)

    def return_hosts(self, si, hs_name):
        """
        return object host by name,
        if name is any objects are returned
        :return: return_obj == host

        """

        return VimObj.hs(self, si, hs_name)

    def return_all_hosts(self, si):
        """
        return object all hosts

        :return: return_obj == host

        """

        return VimObj.hs(self, si, hs_name='any')

    def return_all_hosts_on_cluster(self, si, cl_name):
        """
        get all hosts of a cluster and return it
        :param cl_name:

        :return: object hosts
        """

        return [host for host in Host.return_all_hosts(self, si)
                if host.parent == Cluster().return_clusters(si, cl_name)]

    def return_all_hosts_ready(self, si):
        """
        return all host that is connected and not in maintenance
        :param si:
        :return: all hosts that are connected and not in MaintenanceMode
        """

        return [host for host in Host.return_all_hosts(self, si)
                if host.runtime.connectionState == 'connected' and
                host.runtime.inMaintenanceMode is False]

    def return_ready_hosts_of_cluster(self, si, cl_name):
        """
        return hosts of cluster host that are connected and not in maintenance
        :param si:
        :param cl_name: cluster_name
        :return: hosts of a cluster that are connected and not in MaintenanceMode
        """

        return [host for host in Cluster().get_hosts_of_cluster(si, cl_name)
                if host.runtime.connectionState == 'connected' and
                host.runtime.inMaintenanceMode is False]

    def return_hosts_ready(self, si, hosts):
        """
        return hosts that are connected and not in maintenance
        :param si:
        :param hosts:
        :return: hosts that are connected and not in MaintenanceMode
        """

        return [host for host in Host.return_hosts(self, si, hosts)
                if host.runtime.connectionState == 'connected' and
                host.runtime.inMaintenanceMode is False]

    def get_host_datastores(self, si, host):
        """
        :param si:
        :param host:
        :return: all datastores of host
        """

        return [ds for ds in Host.return_hosts(self, si, host).datastore]


class Datastore(VimObj):
    def __init__(self):
        VimObj.__init__(self)

    def return_datastores(self, si, ds_name):
        """
        return object datastore by name,
        if name is any objects are returned
        :return: return_obj == datastore
        """
        return VimObj.ds(self, si, ds_name)

    def get_datastore_for_vm_relocate(self, si, datastore, ds_type, ds_free_space, ds_to_exclude, vm):
        """
        return 'any' == datastore with free space more
        than 300GB and not the current ds for vm and or the ds object
        :param si:
        :param datastore:
        :param ds_type:
        :param ds_free_space:
        :param ds_to_exclude:
        :param vm:
        :return:
        """

        def get_negate_vm_datastores():
            """
            :return: random datastore
            """
            return_host_vm = VirtualMachine().get_vm_host(si, vm)

            return_host_ds = Host().get_host_datastores(si, return_host_vm)

            return [ds for ds in return_host_ds
                    if not ds == vm.datastore[0] and
                    ds.name not in ds_to_exclude and
                    ds.summary.type in ds_type and
                    (ds.summary.freeSpace - vm.summary.storage.committed) / 1024 / 1024 >
                    (ds_free_space * 1024)]

        return get_negate_vm_datastores() if datastore == 'any' else Datastore().return_datastores(si, datastore)


class VirtualMachine(VimObj):
    def __init__(self):
        VimObj.__init__(self)
        # DataCenter.__init__(self)
        # VimObj.Network.__init__(self)
        # Cluster.__init__(self)
        # Host.__init__(self)

    def return_vms(self, si, vm_name):
        """
        return object vm by name,
        if name is any objects are returned
        :return: return_obj == vm
        """

        return VimObj.vm(self, si, vm_name)

    def get_all_vms(self, si, vm_name='any'):
        """
        return all object vm
        :return: return_obj == vm
        """
        return VimObj.vm(self, si, vm_name)

    def get_vm_cluster(self, si, vm_name):

        """
        get all vm of a datastore and return it
        :param datastore:
        :return: object vms
        """

        return [VirtualMachine.return_vms(self, si, vm_name).resourcePool.parent]

    def get_vm_host(self, si, vm_name):

        """
        get vm system host and return it
        :param vm_name:
        :return: object host
        """

        return VirtualMachine.return_vms(self, si, vm_name).runtime.host

    def get_vm_datastore(self, si, vm_name):

        """
        get all vm of a datastore and return it
        :param datastore:
        :return: object vms
        """

        return VirtualMachine.return_vms(self, si, vm_name).datastore

    def get_all_vms_of_port_group(self, si, pg_name):

        """
        get all vms of port group
        :param si:
        :param pg_name:
        :return: vms
        """

        return VirtualMachine.get_pg(self, si, pg_name).vm

    def get_all_vms_ips(self, si, vms):

        """
        get all vms ip address
        :param si:
        :param vms:
        :return: ips
        """
        vnic_4000, vnic_4001 = [], []
        while vms:
            try:
                vm = vms.pop(0).guest.net[0]
                vnic_4000.append(vm.ipAddress[0]) if vm.deviceConfigId == 4000 else vnic_4001.append(vm.ipAddress[0])
            except:
                pass

        return vnic_4000, vnic_4001

    def get_vm_port_group(self, si, vm_name):

        """
        get prot group of vm, ony if vm has one vnic - need to improved
        :param si:
        :param vm_name:
        :return:
        """

        return VirtualMachine.return_vms(self, si, vm_name).network

    def get_all_powered_on_vms(self, si, vm_name):
        """
        return all object vm by name and if pwoer state == powered_on
        if name is any objects are returned
        :return: return_obj == vm
        """

        return [vm for vm in VimObj.vm(self, si, vm_name) if vm.runtime.powerState == 'poweredOn']

    def get_all_vms_on_datastore(self, si, ds_name):
        """
        get all vm of a datastore and return it
        :param datastore:
        :return: object vms
        """

        return Datastore().return_datastores(si, ds_name).vm

    def get_all_vms_on_cluster(self, si, cl_name):
        """
        get all vm of a cluster and return it
        :param cl_name:
        :return: object vms
        """

        return [vm for vm in VirtualMachine().return_vms(si, vm_name='any')
                if vm.resourcePool.parent == Cluster().return_clusters(si, cl_name)]

    def create_vm(self, si, dc_name, cl_name, ds_name, vm_name):

        """
        :param si:
        :param dc_name:
        :param cl_name:
        :param ds_name:
        :param vm_name:
        :return:
        """

        datacenter = DataCenter().return_dcs(si, dc_name)
        cluster = Cluster().return_clusters(si, cl_name)

        datastore_path = '[' + ds_name + ']'

        vmx_file = vim.vm.FileInfo(logDirectory=None,
                                   snapshotDirectory=None,
                                   suspendDirectory=None,
                                   vmPathName=datastore_path)

        vm_folder = datacenter.vmFolder

        resource_pool = cluster.resourcePool

        config_spec = vim.vm.ConfigSpec()
        config_spec.numCPUs = 1
        config_spec.memoryMB = 1024
        config_spec.cpuHotAddEnabled = True
        config_spec.memoryHotAddEnabled = True
        config_spec.version = 'vmx-07'
        config_spec.guestId = 'dosGuest'
        config_spec.name = vm_name
        config_spec.files = vmx_file

        print ("Creating VM {}...".format(vm_name))
        task = vm_folder.CreateVM_Task(config=config_spec, pool=resource_pool)
        tasks.wait_for_tasks(si, [task])

        return task

    def create_snap(self, si, vm_name, snap_name):
        """
        :param si:
        :param vm_name:
        :param snap_name:
        :return:
        """

        vm = VirtualMachine.return_vms(self, si, vm_name)

        print ("Creating sanpshot {} for VM {}...".format(snap_name, vm_name))

        task = vm.CreateSnapshot_Task(name=snap_name,
                                      memory=True,
                                      quiesce=False)

        tasks.wait_for_tasks(si, [task])

    def remove_all_snap(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :param snap_name:
        :return:
        """

        vm = VirtualMachine.return_vms(self, si, vm_name)

        print ("Remove all sanpshot for VM {}...".format(vm_name))

        task = vm.RemoveAllSnapshots_Task()

        tasks.wait_for_tasks(si, [task])

    def revert_to_current_snap(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :param snap_name:
        :return:
        """

        vm = VirtualMachine.return_vms(self, si, vm_name)

        print ("Revert current sanpshot for VM {}...".format(vm_name))

        task = vm.RevertToCurrentSnapshot_Task()

        tasks.wait_for_tasks(si, [task])

    def reboot_guest(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :return:
        """

        print ("Reboot Guest VM {}...".format(vm_name))

        vm = VirtualMachine.return_vms(self, si, vm_name)

        try:
            vm.RebootGuest()

        except vmodl.MethodFault as error:

            print ("Caught vmodl fault : " + error.msg)

            return 1

        return 0

    def power_on(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :return:
        """

        print ("Powering On VM {}...".format(vm_name))

        vm = VirtualMachine.return_vms(self, si, vm_name)

        task = vm.PowerOnVM_Task()

        tasks.wait_for_tasks(si, [task])

        return task

    def power_off(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :return:
        """

        print ('Powering Off VM {}'.format(vm_name.name))

        vm = VirtualMachine.return_vms(self, si, vm_name)

        task = vm.PowerOffVM_Task()

        # - need to check if want wait and how
        # tasks.wait_for_tasks(si, task)

        return task

    def shutdown_guest(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :return:
        """

        print ("Shutdowning Guest VM {}...".format(vm_name))

        vm = VirtualMachine.return_vms(self, si, vm_name)

        try:
            vm.ShutdownGuest()

        except vmodl.MethodFault as error:

            print ("Caught vmodl fault : " + error.msg)

            return 1

        return 0

    def destroy_vm(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :return:
        """

        print ('Destroy VM {}'.format(vm_name.name))

        try:
            vm = VirtualMachine.return_vms(self, si, vm_name)

            task = vm.Destroy_Task()

        except vmodl.MethodFault as error:

            print ("Caught vmodl fault : " + error.msg)

            return 1

        return task

    def vm_state(self, si, vm_name):
        """
        :param si:
        :param vm_name:
        :return:
        """

        try:
            vm = VirtualMachine.return_vms(self, si, vm_name)

            vm_state = vm.runtime.powerState

        except vmodl.MethodFault as error:

            print ("Caught vmodl fault : " + error.msg)

            return 1

        print ("VM {} state is {}".format(vm_name, vm_state))

        return vm

    def migrate_vm(self, si, vm_name, host):
        """
        :param si:
        :param vm_name:
        :param host:
        :return:
        """

        try:

            vm = VirtualMachine.return_vms(self, si, vm_name)

            if host == 'any':

                # def return_hosts(host):
                #
                #     hosts = Host().return_all_hosts_on_cluster(si, vm.resourcePool.parent)
                #
                #     hosts = Host().return_all_hosts_ready(si)
                #
                #     return [host for host in hosts if not host == vm.runtime.host]
                #
                # hosts = return_hosts(host)
                #
                # host = (random.choice(hosts))

                def return_hosts():
                    """
                    return relevant ready
                    :return:
                    """
                    return_cluster = VirtualMachine().get_vm_cluster(si, vm)

                    return_rdy_hosts = Cluster().get_ready_hosts_of_cluster(si, return_cluster)

                    return [host for host in return_rdy_hosts if not host == vm.runtime.host]

                hosts = return_hosts()

                host = (random.choice(hosts))

            else:

                # vm = VirtualMachine.return_vms(self, si, vm_name) -> delete

                host = Host().return_hosts(si, host)

            task = vm.MigrateVM_Task(host=host, priority='highPriority')

            print ('Migrate VM {} to host {}'.format(vm_name, host.name))

            tasks.wait_for_tasks(si, [task])

        except vmodl.MethodFault as error:

            print ('Caught vmodl fault : ' + error.msg)

            return 1

        return task

    def relocate_vm(self, si, vm_name, datastore):
        """
        :param si:
        :param vm_name:
        :param datastore:
        :return:
        """
        try:

            vm = VirtualMachine.return_vms(self, si, vm_name)

            datastore = Datastore().get_datastore_for_vm_relocate(si, datastore, vm)

            relocate_spec = vim.vm.RelocateSpec()
            relocate_spec.datastore = datastore

            task = vm.RelocateVM_Task(spec=relocate_spec, priority='highPriority')

            print ('Migrate VM {} from {} to datastore {}'.format(vm_name, vm.datastore[0].name, datastore.name))

            tasks.wait_for_tasks(si, [task])

        except vmodl.MethodFault as error:

            print ('Caught vmodl fault : ' + error.msg)

            return 1

        return task
