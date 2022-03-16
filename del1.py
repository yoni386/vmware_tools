# from fnc2 import *
#
# from pyVim.connect import SmartConnect, Disconnect
#
# si = SmartConnect(
#         host='172.17.30.110',
#         user='vmware\sa-py1',
#         pwd='3tango11',
#         port=443)
#
# vm1 = VirtualMachine().return_vms(si, 'dhcp-test-1005')
# vm2 = VirtualMachine().return_vms(si, 'dhcp-test-51-1004')


import argparse
from fnc1 import *
# from fnc2 import *
from pyVim.connect import SmartConnect, Disconnect
# from pyVmomi import vim, vmodl
# import logging

from clone_vm_del_vm import *

__author__ = 'Yoni Shperling'


def get_args():
    """
     arguments for vc
    """

    parser = argparse.ArgumentParser(
            description="Deploy a template into multiple VM's.")

    parser.add_argument('-H', '--host',
                        nargs=1,
                        required=True,
                        help='The vCenter or ESXi host to connect to',
                        dest='host',
                        type=str)

    parser.add_argument('-u', '--username',
                        nargs=1,
                        required=True,
                        help='The username to connect to si',
                        dest='username',
                        type=str)

    parser.add_argument('-p', '--password',
                        nargs=1,
                        required=False,
                        help='The password. If not specified, prompt will be at runtime for a password',
                        dest='password',
                        type=str)

    parser.add_argument('-o', '--port',
                        nargs=1,
                        required=False,
                        help='Server port to connect to (default = 443)',
                        dest='port',
                        type=int,
                        default=[443])

    parser.add_argument('-b', '--basename',
                        nargs=1,
                        required=False,
                        help='Basename of the newly deployed VMs (Prefix)',
                        dest='basename',
                        type=str)

    parser.add_argument('-c', '--count',
                        nargs=1,
                        required=False,
                        help='The name of the first VM will be <basename>-<count> and then basename+1, (default = 1)',
                        dest='count',
                        type=int,
                        default=[1])

    parser.add_argument('-d', '--debug',
                        required=False,
                        help='Enable debug output',
                        dest='debug',
                        action='store_true')

    parser.add_argument('-f', '--folder',
                        nargs=1, required=False,
                        help='The folder in which the new VMs should reside (default = same folder as source VM)',
                        dest='folder',
                        type=str)

    parser.add_argument('-l', '--log-file',
                        nargs=1, required=False,
                        help='File to log to (default = stdout)',
                        dest='logfile', type=str)

    parser.add_argument('-n', '--number',
                        nargs=1,
                        required=False,
                        help='Amount of VMs to deploy (default = 1)',
                        dest='amount',
                        type=int,
                        default=[1])

    parser.add_argument('-P', '--disable-power-on',
                        required=False,
                        help='Disable power on of cloned VMs',
                        dest='nopoweron',
                        action='store_true')

    parser.add_argument('-E', '--esx_host',
                        required=False,
                        help='Esx host to clone into',
                        dest='host_system_name',
                        default='False')

    parser.add_argument('-r', '--resource-pool',
                        nargs=1,
                        required=False,
                        help='Resource pool of new VMs, (default = Resources, the root resource pool)',
                        dest='resource_pool',
                        type=str,
                        default=['Resources'])

    parser.add_argument('-t', '--template',
                        nargs=1,
                        required=True,
                        help='Template to deploy',
                        dest='template',
                        type=str)

    parser.add_argument('-T', '--threads',
                        nargs=1,
                        required=False,
                        help='Amount of threads to use. Consider i/o (default = 1)',
                        dest='threads',
                        type=int,
                        default=[1])

    parser.add_argument('-v', '--verbose',
                        required=False,
                        help='Enable verbose output',
                        dest='verbose',
                        action='store_true')

    parser.add_argument('--datacenter-name',
                        required=False,
                        action='store',
                        default=None,
                        dest='dc_name',
                        help='Name of the Datacenter you \
                                    wish to use. If omitted, the first \
                                    datacenter will be used.')

    parser.add_argument('-D', '--datastore-name',
                        required=False,
                        action='store',
                        default=None,
                        dest='ds_name',
                        help='Datastore clone VM to \
                                    If left blank, VM will be put on the same \
                                    datastore as the template')

    parser.add_argument('-C', '--cpus',
                        type=int,
                        required=False,
                        action='store',
                        default=2,
                        dest='cpu',
                        help='Number of vCPUs')

    parser.add_argument('-R', '--ram',
                        type=int,
                        required=False,
                        action='store',
                        default=1,
                        dest='ram',
                        help='RAM Size in GB')

    parser.add_argument('-I', '--ip-range',
                        required=False,
                        help='IP prefix example [10.130.245.2, 10.130.245.220, 192.169.245.2, 192.168.245.220]',
                        dest='ip_range',
                        type=str,
                        nargs='+')

    parser.add_argument('-L', '--mem-res-lock',
                        required=False,
                        help='memoryReservationLockedToMax (default = False)',
                        dest='memory_reservation_locked_to_max',
                        default=False)

    parser.add_argument('-y', '--dry_run',
                        required=False,
                        help='Only simulate value is True',
                        dest='dry_run',
                        type=str)

    return parser.parse_args()

args = get_args()

si = SmartConnect(
        host='172.17.30.110',
        user='vmware\sa-py1',
        pwd='3tango11',
        port=443)


from fnc1 import *
from fnc2 import *
threads = 4
pool = ThreadPool(threads)

import re


vm = VirtualMachine()
ls_vms = vm.get_all_vms(si)


def power_off(vm):
    """
    :param vm:
    :return:
    """

    try:
        print ('Powering Off VM {}'.format(vm.name))
        task = vm.PowerOffVM_Task()
        wait_for_tasks(si, [task])

    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return 1
    return task


def destroy_vm(vm):
    """
    :param vm_name:
    :return:
    """

    print ('Destroy VM {}'.format(vm.name))
    try:

        task = vm.Destroy_Task()
        wait_for_tasks(si, [task])
    except vmodl.MethodFault as error:
        print "Caught vmodl fault : " + error.msg
        return 1

    return task


def power_off_delete(vm):
    power_off(vm)
    destroy_vm(vm)

vms = [x for x in ls_vms if re.findall('reg-esx5-vl', x.name)]
# print vms[0]
dry_run = True
return_threads = []
if not dry_run:
    # thread = pool.map(vm_clone_handler_wrapper, vm_specs)
    thread = pool.map(power_off_delete, vms)
    return_threads.extend(thread)
#
#     # logger.debug('Closing virtual machine clone pool')
    pool.close()
    pool.join()