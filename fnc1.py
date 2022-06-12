

# import argparse
import atexit
import csv
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

from fnc2 import *

__author__ = 'Yoni'


def vc_si(args):
    """
    function connect to vc and return si (service instance)
    """

    logger = logging.getLogger(__name__)

    host = args.host[0]
    username = args.username[0]
    password = args.password[0]
    port = args.port[0]

    # TODO ssl issue on py6
    # import ssl
    # ssl._create_default_https_context = ssl._create_unverified_context

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

    except IOError:
        logger.error('Could not connect to host %s with user %s and specified password' % (host, username))
        return 1
    logger.debug('Registering disconnect at exit')
    atexit.register(Disconnect, si)

    return si


def wait_for_tasks(si, tasks):
    """
    Given the service instance si and tasks, it returns after all the
    tasks are complete
    """

    # args = args.args
    #
    # si = vc_si(args)

    property_collector = si.content.propertyCollector
    task_list = [str(task) for task in tasks]
    # Create filter
    obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task) for task in tasks]
    property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task, pathSet=[], all=True)
    filter_spec = vmodl.query.PropertyCollector.FilterSpec()
    filter_spec.objectSet = obj_specs
    filter_spec.propSet = [property_spec]
    pcfilter = property_collector.CreateFilter(filter_spec, True)
    try:
        version, state = None, None
        # Loop looking for updates till the state moves to a completed state.
        while len(task_list):
            update = property_collector.WaitForUpdates(version)
            for filter_set in update.filterSet:
                for obj_set in filter_set.objectSet:
                    task = obj_set.obj
                    for change in obj_set.changeSet:
                        if change.name == 'info':
                            state = change.val.state
                        elif change.name == 'info.state':
                            state = change.val
                        else:
                            continue

                        if not str(task) in task_list:
                            continue

                        if state == vim.TaskInfo.State.success:
                            # Remove task from taskList
                            task_list.remove(str(task))
                        elif state == vim.TaskInfo.State.error:
                            raise task.info.error
            # Move to next version
            version = update.version
    finally:
        if pcfilter:
            pcfilter.Destroy()


def generate_ip_range(start_ip, end_ip):
    """
    Create range of ip and return ips.
    """

    start = list(map(int, start_ip.split(".")))
    end = list(map(int, end_ip.split(".")))
    temp = start
    ips = []

    ips.append(start_ip)
    while temp != end:
        start[3] += 1
        for i in (3, 2, 1):
            if temp[i] == 256:
                temp[i] = 0
                temp[i - 1] += 1
        ips.append(".".join(map(str, temp)))

    return ips


def find_vm(si, logger, vm_names):
    """
    Find a virtual machine by it's name and return it
    """

    # content = si.content
    # obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    # vm_list = obj_view.view
    #
    vms = VirtualMachine().return_vms(si, 'any')

    for vm in vms:
        logger.debug('THREAD - Checking VM {} 111'.format(vm.name))
        if vm.name == vm_names:
            logger.debug('Found Found VM {}'.format(vm.name))
            pass
            # return True
        else:
            return False
    # return


def find_resource_pool(si, logger, name):
    """
    Find a resource pool by it's name and return it
    """

    content = si.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.ResourcePool], True)
    rp_list = obj_view.view

    for rp in rp_list:
        logger.debug('Checking resource pool %s' % rp.name)
        if rp.name == name:
            logger.debug('Found resource pool %s' % rp.name)
            return rp
    return None


def find_folder(si, logger, name):
    """
    Find a folder by it's name and return it
    """

    content = si.content
    obj_view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Folder], True)
    folder_list = obj_view.view

    for folder in folder_list:
        logger.debug('Checking folder %s' % folder.name)
        if folder.name == name:
            logger.debug('Found folder %s' % folder.name)
            return folder
    return None


def get_obj(si, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
    content = si.content
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:
            obj = c
            break

    return obj


def get_objs(si, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned !!!test!!! > delete
    """
    content = si.content
    obj = None
    objs = []
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:

            objs.append(c)
            # break

    return objs

#
# def vm_clone_handler_wrapper(args):
#     """
#     Wrapping around clone vm_clone_handler
#     """
#     return vm_clone_handler(*args)
#
#
# def vm_clone_handler(si, logger, vm_name, resource_pool_name, folder_name, power_on, template, template_vm, ip,
#                      ds_name, cpu, ram, memory_reservation_locked_to_max, nocustos):
#     """
#     Will handle the thread handling to clone a virtual machine and return task
#     """
#
#     run_loop = True
#     vm = None
#
#     logger.debug('THREAD %s - started' % vm_name)
#     logger.info('THREAD %s - Trying to clone %s to new virtual machine' % (vm_name, template))
#
#     # Find the correct Resource Pool
#     resource_pool = None
#     if resource_pool_name is not None:
#         logger.debug('THREAD %s - Finding resource pool %s' % (vm_name, resource_pool_name))
#         resource_pool = find_resource_pool(si, logger, resource_pool_name)
#         if resource_pool is None:
#             logger.critical('THREAD %s - Unable to find resource pool %s' % (vm_name, resource_pool_name))
#             return 1
#             logger.info('THREAD %s - Resource pool %s found' % (vm_name, resource_pool_name))
#
#     # Find the correct folder
#     folder = None
#     if folder_name is not None:
#         logger.debug('THREAD %s - Finding folder %s' % (vm_name, folder_name))
#         folder = find_folder(si, logger, folder_name)
#         if folder is None:
#             logger.critical('THREAD %s - Unable to find folder %s' % (vm_name, folder_name))
#             return 1
#         logger.info('THREAD %s - Folder %s found' % (vm_name, folder_name))
#     else:
#         logger.info('THREAD %s - Setting folder to template folder as default' % vm_name)
#         folder = template_vm.parent
#
#     # Creating necessary specs
#     logger.debug('THREAD %s - Creating relocate spec' % vm_name)
#
#     # datastore_name = 'ds_lun100'  -> temp debug
#
#     datastore = get_obj(si, [vim.Datastore], ds_name)
#
#     # ips = iprange('10.0.0.1', '10.0.0.5')  -> temp debug
#
#     relocate_spec = vim.vm.RelocateSpec()
#     relocate_spec.datastore = datastore
#     # relocate_spec.pool = resource_pool
#
#     # ResourceAllocationInfo resources reservation
#     res_alloc = vim.ResourceAllocationInfo()
#     mem_res = res_alloc
#     mem_res.reservation = ram * 1024
#
#     config_spec = vim.vm.ConfigSpec()
#     config_spec.numCPUs = cpu
#     config_spec.memoryMB = ram
#     config_spec.cpuHotAddEnabled = True
#     config_spec.memoryHotAddEnabled = True
#     # config_spec.memoryReservationLockedToMax = True
#     # config_spec.memoryAllocation = mem_res
#
#     # config_spec.deviceChange = devices -> future
#
#     # # Network adapter settings
#     # nic = vim.vm.device.VirtualDeviceSpec()
#     # nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.add  # or edit if a device exists
#     # nic.device = vim.vm.device.VirtualVmxnet3()
#     # nic.device.wakeOnLanEnabled = True
#     # nic.device.addressType = 'assigned'
#     # nic.device.key = 4000  # 4000 seems
#
#     adaptermap = vim.vm.customization.AdapterMapping()
#     adaptermap.adapter = vim.vm.customization.IPSettings()
#     adaptermap.adapter.ip = vim.vm.customization.FixedIp()
#     adaptermap.adapter.ip.ipAddress = ip
#     adaptermap.adapter.subnetMask = str('255.255.255.0')
#     adaptermap.adapter.gateway = str('10.200.216.1')
#
#     # IP
#
#     globalip = vim.vm.customization.GlobalIPSettings(dnsServerList=['10.1.64.20'])
#
#     # Hostname settings
#     ident = vim.vm.customization.LinuxPrep()
#     ident.domain = 'vmware.local'
#     ident.hostName = vim.vm.customization.FixedName()
#     ident.hostName.name = vm_name
#
#     # Putting all these pieces together in a custom spec
#     custom_os = vim.vm.customization.Specification(nicSettingMap=[adaptermap],
#                                                    globalIPSettings=globalip,
#                                                    identity=ident)
#     clonespec = vim.vm.CloneSpec()
#     clonespec.location = relocate_spec
#     # clonespec.powerOn = True  -> temp pending to delete
#     clonespec.config = config_spec
#
#     '''
#     test to control custom os - not wokring yet
#     '''
#
#     if nocustos:
#         logger.debug('THREAD %s - custom os is set to %s' % vm_name, nocustos)
#
#     else:
#         # clonespec.customization = custom_os
#         print True
#
#     relocate_spec.pool = resource_pool
#
#     if resource_pool is not None:
#         logger.debug('THREAD %s - Resource pool found, using' % vm_name)
#         # relocate_spec = vim.vm.RelocateSpec(pool=resource_pool) > temp pending to delete
#         # relocate_spec.pool = resource_pool -> temp pending to delete
#
#         # relocate_spec.pool = resource_pool -> temp pending to delete
#     else:
#         logger.debug('THREAD %s - No resource pool found, continuing without it' % vm_name)
#         # relocate_spec = vim.vm.RelocateSpec() -> temp pending to delete
#
#         relocate_spec.pool = resource_pool
#
#         logger.debug('THREAD %s - Creating clone spec' % vm_name)
#
#     # print clonespec -> temp debug pending to delete
#
#     if find_vm(si, logger, vm_name, True):
#         logger.warning('THREAD %s - Virtual machine already exists, not creating' % vm_name)
#         run_loop = False
#     else:
#         logger.debug('THREAD %s - Creating clone task' % vm_name)
#
#         task = template_vm.Clone(folder=folder, name=vm_name, spec=clonespec)
#
#         logger.info('THREAD %s - Cloning task created' % vm_name)
#         logger.info('THREAD %s - Checking task for completion. This might take a while' % vm_name)
#
#     # tasks = []
#     while run_loop:
#
#         info = task.info
#
#         logger.debug('THREAD %s - Checking clone task' % vm_name)
#         if info.state == vim.TaskInfo.State.success:
#             logger.info('THREAD %s - Cloned and running' % vm_name)
#
#             vm = info.result
#
#             # tasks.append(task.info)
#             # tasks.append(task.info.result)
#
#             run_loop = False
#
#             break
#         elif info.state == vim.TaskInfo.State.running:
#             logger.debug('THREAD %s - Cloning task is at %s percent' % (vm_name, info.progress))
#         elif info.state == vim.TaskInfo.State.queued:
#             logger.debug('THREAD %s - Cloning task is queued' % vm_name)
#         elif info.state == vim.TaskInfo.State.error:
#             if info.error.fault:
#                 logger.info(
#                     'THREAD %s - Cloning task has quit with error: %s' % (vm_name, info.error.fault.faultMessage))
#             else:
#                 logger.info('THREAD %s - Cloning task has quit with cancelation' % vm_name)
#             run_loop = False
#             break
#         logger.debug('THREAD %s - Sleeping 10 seconds for new check' % vm_name)
#         sleep(3)
#
#     if vm and power_on:
#         logger.info('THREAD %s - Powering on VM. This might take a couple of seconds' % vm_name)
#         power_on_task = vm.PowerOn()
#         logger.debug('THREAD %s - Waiting fo VM to power on' % vm_name)
#         run_loop = True
#         while run_loop:
#             info = task.info
#             if info.state == vim.TaskInfo.State.success:
#                 run_loop = False
#                 break
#             elif info.state == vim.TaskInfo.State.error:
#                 if info.error.fault:
#                     logger.info(
#                         'THREAD %s - Power on has quit with error: %s' % (vm_name, info.error.fault.faultMessage))
#                 else:
#                     logger.info('THREAD %s - Power on has quit with cancelation' % vm_name)
#                 run_loop = False
#                 break
#             sleep(5)
#
#         # return tasks
#         return vm
#     return
#     # return task


def get_all_vms_on_datastore(datastore):
    """
    get all vm of a datastore and return it
    :param datastore:
    :return: object vms
    """

    return [vm for vm in datastore.vm]


# def power_off_vm_handler_wrapper(vm):
#     """
#     Wrapping around PowerOff vm_state_handler
#     :param vm:
#     :return:
#     """
#     return power_off_vm(vm)
#
#
# def power_off_vm(vm):
#     """
#     PowerOff vms
#     :param vm:
#     :return: task
#     """
#
#     logger = logging.getLogger(__name__)
#
#     run_loop = True
#     if vm.runtime.powerState == "poweredOff":
#         run_loop = False
#
#     else:
#         task = vm.PowerOffVM_Task()
#         while run_loop:
#             if task.info.state == vim.TaskInfo.State.success:
#                 run_loop = False
#                 break
#             elif task.info.state == vim.TaskInfo.State.running:
#                 logger.debug('THREAD %s - PowerOff task is at %s percent' % (vm, task.info.progress))
#             elif task.info.state == vim.TaskInfo.State.queued:
#                 logger.debug('THREAD %s - PowerOff task is queued' % vm)
#             elif task.info.state == vim.TaskInfo.State.error:
#                 if task.info.error.fault:
#                     logger.task.info(
#                         'THREAD %s - PowerOff task has quit with error: %s' % (vm, task.info.error.fault.faultMessage))
#                 else:
#                     logger.task.info('THREAD %s - PowerOff task has quit with cancelation' % vm)
#                 run_loop = False
#                 break
#             print('THREAD %s - Sleeping 10 seconds for new check' % vm)
#             sleep(3)
#         return task
#     return


def power_on_vm_handler_wrapper(vm):
    """
    Wrapping around vm_state_handler
    """
    return power_on_vm(vm)


def power_on_vm(vm):
    """
    PowerOn all vms on a datastore
    :param vm:
    :return:
    """

    run_loop = True

    if vm.runtime.powerState == "poweredOn":
        run_loop = False
        print (False)

    else:
        task = vm.PowerOnVM_Task()

        while run_loop:

            if task.info.state == vim.TaskInfo.State.success:

                run_loop = False

                break

            elif task.info.state == vim.TaskInfo.State.running:
                print('THREAD %s - PowerOff task is at %s percent' % (vm, task.info.progress))
            elif task.info.state == vim.TaskInfo.State.queued:
                print('THREAD %s - PowerOff task is queued' % vm)
            elif task.info.state == vim.TaskInfo.State.error:
                if task.info.error.fault:
                    print(
                        'THREAD %s - PowerOff task has quit with error: %s' % (vm, task.info.error.fault.faultMessage))
                else:
                    print('THREAD %s - PowerOff task has quit with cancelation' % vm)
                run_loop = False
                break
            print('THREAD %s - Sleeping 10 seconds for new check' % vm)
            sleep(3)

        return task
    return


def vm_pg(args):
    """
    :param vm:
    :return: return_threads
    """
    si = args.si
    vms = args.vms
    network = args.network
    is_VDS = args.is_VDS

    ar = []
    for vm in vms:
        ar.append((si, vm, network, is_VDS))

    threads = 60
    pool = ThreadPool(threads)

    return_threads = []
    thread = pool.map(change_vm_pg_handler_wrapper, ar)
    return_threads.extend(thread)

    pool.close()
    pool.join()

    return return_threads


def change_vm_pg_handler_wrapper(args):
    """
    Wrapping around vm_change_pg_handler
    """
    # print dir(args)

    return change_vm_pg(*args)


def change_vm_pg(si, vms, network, is_VDS):
    """
    change pg of all vms on a datastore
    :param vm:
    :return:
    """

    vm = vms

    run_loop = True

    try:

        content = si.RetrieveContent()

        # This code is for changing only one Interface. For multiple Interface
        # Iterate through a loop of network names.
        device_change = []
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                nicspec = vim.vm.device.VirtualDeviceSpec()
                nicspec.operation = \
                    vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.wakeOnLanEnabled = True

                # args = []
                # args.is_V
                # DS = False
                # args.network_name = network
                network_name = 'pg_autod_test1_vlan_4000'

                if not is_VDS:
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                    nicspec.device.backing.network = network
                        # get_obj(content, [vim.Network], args.network_name)
                    # nicspec.device.backing.deviceName = args.network_name
                    nicspec.device.backing.deviceName = network_name

                else:

                    # network = get_obj(content,
                    #                   [vim.dvs.DistributedVirtualPortgroup],
                    #                   args.network_name)
                    dvs_port_connection = vim.dvs.PortConnection()
                    dvs_port_connection.portgroupKey = network.key
                    dvs_port_connection.switchUuid = \
                        network.config.distributedVirtualSwitch.uuid
                    nicspec.device.backing = \
                        vim.vm.device.VirtualEthernetCard. \
                            DistributedVirtualPortBackingInfo()
                    nicspec.device.backing.port = dvs_port_connection

                nicspec.device.connectable = \
                    vim.vm.device.VirtualDevice.ConnectInfo()
                nicspec.device.connectable.connected = True
                nicspec.device.connectable.startConnected = True
                nicspec.device.connectable.allowGuestControl = True
                device_change.append(nicspec)
                break

        config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
        print ("Waiting to changed network for %s" % vm.name)
        task = vm.ReconfigVM_Task(config_spec)
        wait_for_tasks(si, [task])
        print ("Successfully changed network for %s" % task.info.entityName)

    except vmodl.MethodFault as error:

        print ("Caught vmodl fault : " + error.msg)

        return -1

    return 0

# def delete_vm_handler_wrapper(vm):
#     """
#     Wrapping around delete vm_state_handler
#     :param vm:
#     :return:
#     """
#     return delete_vm_old(vm)
#
#
# def delete_vm_old(vm):
#     """
#     delete vms
#     :param vm:
#     :return: task
#     """
#
#     logger = logging.getLogger(__name__)
#
#     run_loop = True
#     if vm.runtime.powerState == "poweredOn":
#         run_loop = False
#
#     else:
#         task = vm.Destroy_Task()
#         while run_loop:
#             if task.info.state == vim.TaskInfo.State.success:
#                 run_loop = False
#                 break
#             elif task.info.state == vim.TaskInfo.State.running:
#                 logger.debug('THREAD %s - Destroy task is at %s percent' % (vm, task.info.progress))
#             elif task.info.state == vim.TaskInfo.State.queued:
#                 logger.debug('THREAD %s - Destroy task is queued' % vm)
#             elif task.info.state == vim.TaskInfo.State.error:
#                 if task.info.error.fault:
#                     logger.task.info(
#                         'THREAD %s - Destroy task has quit with error: %s' % (vm, task.info.error.fault.faultMessage))
#                 else:
#                     logger.task.info('THREAD %s - Destroy task has quit with cancelation' % vm)
#                 run_loop = False
#                 break
#             print('THREAD %s - Sleeping 10 seconds for new check' % vm)
#             sleep(3)
#         return task
#     return

def poweroff_vms(vm):
    """
    :param vm:
    :return: return_threads
    """
    threads = 4
    pool = ThreadPool(threads)

    return_threads = []
    thread = pool.map(poweroff_vms_handler_wrapper, vm)
    return_threads.extend(thread)

    pool.close()
    pool.join()

    return return_threads


def poweroff_vms_handler_wrapper(vm):
    """
    Wrapping around delete vm_state_handler
    :param vm:
    :return: poweroff_vm
    """

    def poweroff_vm(vm):
        """
        delete vms
        :param vm:
        :return: task
        """

        logger = logging.getLogger(__name__)

        run_loop = True
        if vm.runtime.powerState == "poweredOff":
            run_loop = False

        else:
            task = vm.PowerOffVM_Task()
            while run_loop:
                if task.info.state == vim.TaskInfo.State.success:
                    run_loop = False
                    break
                elif task.info.state == vim.TaskInfo.State.running:
                    logger.debug('THREAD %s - poweredOff task is at %s percent' % (vm, task.info.progress))
                elif task.info.state == vim.TaskInfo.State.queued:
                    logger.debug('THREAD %s - poweredOff task is queued' % vm)
                elif task.info.state == vim.TaskInfo.State.error:
                    if task.info.error.fault:
                        logger.task.info(
                            'THREAD %s - poweredOff task has quit with error: %s' % (
                                vm, task.info.error.fault.faultMessage))
                    else:
                        logger.task.info('THREAD %s - poweredOff task has quit with cancelation' % vm)
                    run_loop = False
                    break
                print('THREAD %s - Sleeping 10 seconds for new check' % vm)
                sleep(3)
            return task
        return

    return poweroff_vm(vm)


def initiate_snapshot_for_vm(client, snap_basename, vm, quiesce=True, memory=False):
    vm_name = "<unknown>"
    try:
        vm_name = vm.name
        log.uinfo('Creating snapshot for vm {} (quiesce = {} memory = {})', vm_name, quiesce, memory)
        task = vm.CreateSnapshot_Task(name=snap_basename, memory=memory, quiesce=quiesce)
    except:
        log.uwarn('Snapshot creation failed for VM {}', vm_name)
        task = None
    return task


def destroy_vms(vm):
    """
    :param vm:
    :return: return_threads
    """
    threads = 4
    pool = ThreadPool(threads)

    return_threads = []
    thread = pool.map(destroy_vms_handler_wrapper, vm)
    return_threads.extend(thread)

    pool.close()
    pool.join()

    return return_threads


def destroy_vms_handler_wrapper(vm):
    """
    Wrapping around destroy_vm
    :param vm:
    :return: delete_vm
    """

    def destroy_vm(vm):
        """
        delete vms
        :param vm:
        :return: task
        """

        logger = logging.getLogger(__name__)

        run_loop = True
        if vm.runtime.powerState == "poweredOn":
            run_loop = False

        else:
            task = vm.Destroy_Task()
            while run_loop:
                if task.info.state == vim.TaskInfo.State.success:
                    run_loop = False
                    break
                elif task.info.state == vim.TaskInfo.State.running:
                    logger.debug('THREAD %s - Destroy task is at %s percent' % (vm, task.info.progress))
                elif task.info.state == vim.TaskInfo.State.queued:
                    logger.debug('THREAD %s - Destroy task is queued' % vm)
                elif task.info.state == vim.TaskInfo.State.error:
                    if task.info.error.fault:
                        logger.task.info(
                            'THREAD %s - Destroy task has quit with error: %s' % (
                                vm, task.info.error.fault.faultMessage))
                    else:
                        logger.task.info('THREAD %s - Destroy task has quit with cancelation' % vm)
                    run_loop = False
                    break
                print('THREAD %s - Sleeping 10 seconds for new check' % vm)
                sleep(3)
            return task
        return

    return destroy_vm(vm)


# def clone_vm():
#     """
#     Clone a VM or template into multiple VMs with logical names with numbers and allow for post-processing
#     """
#
#     args = args.args
#
#     amount = args.amount[0]
#     basename = None
#     if args.basename:
#         basename = args.basename[0]
#     count = args.count[0]
#     debug = args.debug
#     folder_name = None
#     if args.folder:
#         folder_name = args.folder[0]
#     host = args.host[0]
#     log_file = None
#     if args.logfile:
#         log_file = args.logfile[0]
#     password = None
#     if args.password:
#         password = args.password[0]
#     power_on = not args.nopoweron
#     nocustos = not args.nocustos
#     resource_pool_name = None
#     # if args.resource_pool: -> temp decide if pending to delete
#     #     resource_pool_name = args.resource_pool[0] -> temp debug pending to delete
#     # nosslcheck = args.nosslcheck  -> temp debug pending to delete
#     template = args.template[0]
#     threads = args.threads[0]
#     username = args.username[0]
#     verbose = args.verbose
#     ds_name = args.ds_name
#     cpu = args.cpu
#     ram = args.ram
#     memory_reservation_locked_to_max = args.memory_reservation_locked_to_max
#
#     if memory_reservation_locked_to_max:
#         memory_reservation_locked_to_max = ast.literal_eval(memory_reservation_locked_to_max)
#
#     # Logging settings
#
#     if debug:
#         log_level = logging.DEBUG
#     elif verbose:
#         log_level = logging.INFO
#     else:
#         log_level = logging.WARNING
#
#     if log_file:
#         logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
#     else:
#         logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
#     logger = logging.getLogger(__name__)
#
#     # Disabling SSL
#
#     logger.debug('Disabling SSL certificate verification.')
#     requests.packages.urllib3.disable_warnings()
#     import ssl
#
#     if hasattr(ssl, '_create_unverified_context'):
#         ssl._create_default_https_context = ssl._create_unverified_context
#
#     # Getting user password
#     if password is None:
#         logger.debug('No command line password received, requesting password from user')
#         password = getpass.getpass(prompt='Enter password for vCenter %s for user %s: ' % (host, username))
#
#     try:
#         si = vc_si(args)
#
#         # Find the correct VM
#         logger.debug('Finding template %s' % template)
#         template_vm = find_vm(si, logger, template, False)
#         if template_vm is None:
#             logger.error('Unable to find template %s' % template)
#             return 1
#         logger.info('Template %s found' % template)
#
#         # Pool handling
#         logger.debug('Setting up pools and threads')
#         pool = ThreadPool(threads)
#         # mac_ip_pool = ThreadPool(threads)
#         # mac_ip_pool_results = []
#         vm_specs = []
#         logger.debug('Pools created with %s threads' % threads)
#
#         logger.debug('Creating thread specifications')
#         vm_names = []
#         for a in range(1, amount + 1):
#             vm_names.append('%s-%i' % (basename, count))
#             count += 1
#
#         # print vm_names -> debug pending to delete
#
#         # vm_names.sort() -> pending to delete ''' vm sort for now disable '''
#
#         ips = generate_ip_range('10.0.0.1', '10.0.0.200')
#
#         for vm_name in vm_names:
#             vm_specs.append((
#                 si, logger, vm_name, resource_pool_name, folder_name, power_on, template,
#                 template_vm, ips.pop(0), ds_name, cpu, ram, memory_reservation_locked_to_max,
#                 nocustos
#             ))
#
#         ''' print for debug - temp '''
#         # print vm_specs
#
#         logger.debug('Running virtual machine clone pool')
#
#         return_threads = []
#         thread = pool.map(vm_clone_handler_wrapper, vm_specs)
#         return_threads.extend(thread)
#
#         logger.debug('Closing virtual machine clone pool')
#         pool.close()
#         pool.join()
#
#         # logger.debug('Waiting for all mac, ip and post-script processes')
#         # for running_task in mac_ip_pool_results:
#         #     running_task.wait()
#         #
#         # logger.debug('Closing mac, ip and post-script processes')
#         # mac_ip_pool.close()
#         # mac_ip_pool.join()
#
#     except vmodl.MethodFault, e:
#         logger.critical('Caught vmodl fault: %s' % e.msg)
#         return 1
#     except Exception, e:
#         logger.critical('Caught exception: %s' % str(e))
#         return 1
#
#     logger.info('Finished all tasks')
#
#     # return threads
#
#     # print dir(thread)
#     return return_threads
#     # return return_threads
#
#     # return 0, res
#     # return res
