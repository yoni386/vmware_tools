
import argparse
from fnc1 import *
from fnc2 import *
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl
import logging
import random

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
                        help='The password. If not `spec`ified, prompt will be at runtime for a password',
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
                        help='The name of the first VM will be <basename>-<count> and then basename+2, (default = 2)',
                        dest='count',
                        type=int,
                        default=[2])

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

    parser.add_argument('-DL',
                        required=False,
                        action='store',
                        default=None,
                        dest='ds_local_name',
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

    args = parser.parse_args()
    return args


args = get_args()

#
# def vm_clone_handler_wrapper(args):
#     """
#     Wrapping around clone vm_clone_handler
#     """
#     return vm_clone_handler(**args)


# def vm_clone_handler(si, logger, vm_name, resource_pool_name, folder_name, power_on, template, template_vm, ips,
#                      ds_name, cpu, ram, memory_reservation_locked_to_max, nocustos):


class DsList(object):
    def __int__(self):
        self._allDs = list()

    def add_ds(self, ds):
        self._allDs.append(ds)

    def get_ds_list(self):
        return self._allDs

    def sort(self):
        sorted(self._allDs)

    def get_max_size(self):
        return sorted(self.get_ds_list(), key=lambda d: d.size)


class Ds(object):

    def __init__(self, name, size, is_local, mo_ref):
        self._name = name
        self._size = size
        self._is_local = is_local
        self._mo_ref = mo_ref

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self.name = name

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = size

    @property
    def is_local(self):
        return self._is_local

    @is_local.setter
    def _is_local(self, value):
        self._is_local = value


def get_datastore_for_vm_relocate(si, host_vm, datastore, ds_type, ds_free_space, ds_to_exclude, vm):
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

        return_host_ds = Host().get_host_datastores(si, host_vm)

        return [ds for ds in return_host_ds
                if ds.name not in ds_to_exclude and
                ds.summary.type in ds_type and
                (ds.summary.freeSpace - vm.summary.storage.committed) / 1024 / 1024 >
                (ds_free_space * 1024)]

    return get_negate_vm_datastores() if datastore == 'any' else Datastore().return_datastores(si, datastore)


def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
    """
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


def vm_clone_handler(args):
    """
    Will handle the thread handling to clone a virtual machine and return task
    """
    # print args['trusted']
    # print args['fast']
    si = args['si']
    logger = args['logger']
    vm_name = args['vm_name']
    resource_pool_name = args['resource_pool_name']
    folder_name = args['folder_name']
    power_on = args['power_on']
    template = args['template']
    template_vm = args['template_vm']
    adapters_specs = args['adapters_specs']
    cpu = args['cpu']
    ram = args['ram']
    memory_reservation_locked_to_max = args['memory_reservation_locked_to_max']
    datastore = args['datastore']
    host_system = args['host_system']
    owner = args['owner']

    run_loop = True
    vm = None

    logger.debug('THREAD %s - started' % vm_name)
    logger.info('THREAD %s - Trying to clone: %s to: %s' % (vm_name, template, vm_name))

    # Find the correct Resource Pool

    if resource_pool_name:
        resource_pool = get_obj(si.RetrieveContent(), [vim.ResourcePool], resource_pool_name)
    # else:
    #     resource_pool = cluster.resourcePool

    # Find the correct folder
    folder = None
    if folder_name is not None:
        logger.debug('THREAD %s - Finding folder %s' % (vm_name, folder_name))
        folder = find_folder(si, logger, folder_name)
        if folder is None:
            logger.critical('THREAD %s - Unable to find folder %s' % (vm_name, folder_name))
            return 1
        logger.info('THREAD %s - Folder %s found' % (vm_name, folder_name))
    else:
        logger.info('THREAD %s - Setting folder to template folder as default' % vm_name)
        folder = template_vm.parent

    # Creating necessary specs
    logger.debug('THREAD %s - Creating relocate spec' % vm_name)

    relocate_spec = vim.vm.RelocateSpec()
    # relocate_spec.disk.diskId = 0

    # relocate_spec.datastore = template_vm.datastore[0]
    #
    # for device in template_vm.config.hardware.device:
    #     if isinstance(device, vim.vm.device.VirtualDisk):
    #         relocate_spec.disk.append(vim.vm.RelocateSpec.DiskLocator(diskId=device.key, datastore=datastore))

    # disk1 = vim.vm.RelocateSpec.DiskLocator(diskId=vim.vm.device, datastore=datastore)
    # disk2 = vim.vm.RelocateSpec.DiskLocator(diskId=2, datastore=datastore)
    # relocate_spec.disk = [disk1, disk2]
    # relocate_spec.disk = []

    # relocate_spec.datastore = datastore

    #
    # disk1 = vim.vm.RelocateSpec.DiskLocator()
    # disk1.diskId = 1
    # disk1.datastore = datastore
    #
    #
    # disk2 = vim.vm.RelocateSpec.DiskLocator()
    # disk2.diskId = 2
    # disk2.datastore = datastore
    #
    # relocate_spec.disk = [disk1, disk2]

    # dds = get_datastore_for_vm_relocate(si, host_system, 'any', 'VMFS', 30, 'local', template_vm) # TODO: need to change as only ds with max

    for device in template_vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualDisk):
            if device.deviceInfo.label == "Hard disk 1":
                relocate_spec.disk.append(vim.vm.RelocateSpec.DiskLocator(diskId=device.key, datastore=datastore[0])) # TODO: need to change as only ds with max free space is needed
            else:
                relocate_spec.disk.append(vim.vm.RelocateSpec.DiskLocator(diskId=device.key, datastore=datastore[1]))

    # relocate_spec.disk.diskId = 1
    # relocate_spec.datastore = datastore
    # relocate_spec_disk = relocate_spec.disk.diskId
    # relocate_spec_disk_0 = relocate_spec_disk.diskId
    # relocate_spec_disk_0 =
    #
    # relocate_spec_disk = relocate_spec.disk.diskId
    # relocate_spec_disk = 1
    # relocate_spec_disk_0 = relocate_spec_disk.diskId
    #
    # # relocate_spec_disk_diskId = 1



    # for device in template_vm.config.hardware.device:
    #     if isinstance(device, vim.vm.device.VirtualDisk):
    #         relocate_spec.disk.append(vim.vm.RelocateSpec.DiskLocator(diskId=device.key, datastore=datastore))

    # VirtualDeviceConfigSpec = vim.vm.device.VirtualDeviceSpec
    # VirtualDeviceConfigSpec.

    # VirtualMachineRelocateSpecDiskLocator = vim.vm.RelocateSpec.DiskLocator

    if host_system:
        relocate_spec.host = host_system
        logger.debug('Clone VM {} to Esx host {}'.format(vm_name, host_system.name))

    # relocate_spec.pool = resource_pool

    # ResourceAllocationInfo resources reservation
    # res_alloc = vim.ResourceAllocationInfo()
    # mem_res = res_alloc
    # mem_res.reservation = ram * 1024

    config_spec = vim.vm.ConfigSpec()
    config_spec.numCPUs = cpu
    config_spec.memoryMB = 1024
    config_spec.cpuHotAddEnabled = True
    config_spec.memoryHotAddEnabled = True
    # config_spec.memoryReservationLockedToMax = True
    # config_spec.memoryAllocation = mem_res

    config_spec.annotation = "{0}\n{1}\n{2}".format(owner,
                                                    adapters_specs[0]['ipv4'],
                                                    adapters_specs[1]['ipv4'])

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relocate_spec
    # clonespec.powerOn = True  -> temp pending to delete

    if adapters_specs is not None:

        adaptermaps = []
        for adapter_spec in adapters_specs:
            guest_map = vim.vm.customization.AdapterMapping()
            guest_map.adapter = vim.vm.customization.IPSettings()
            if adapter_spec == 'dhcp':
                guest_map.adapter.ip = vim.vm.customization.DhcpIpGenerator()
                logger.debug('Customize set for DHCP DhcpIpGenerator')
            else:
                guest_map.adapter.ip = vim.vm.customization.FixedIp()
                guest_map.adapter.ip.ipAddress = adapter_spec['ipv4']

                guest_map.adapter.subnetMask = str(adapter_spec['subnet'])

                if adapter_spec['ipv6']:

                    try:
                        guest_map.adapter.ipV6Spec = vim.vm.customization.IPSettings.IpV6AddressSpec()

                        ipv6_spec = vim.vm.customization.FixedIpV6()

                        ipv6_spec.ipAddress = str(adapter_spec['ipv6'])

                        ipv6_spec.subnetMask = adapter_spec['subnet_ipv6']

                        guest_map.adapter.ipV6Spec.ip = [ipv6_spec]
                    except ValueError:
                        pass
                try:
                    guest_map.adapter.gateway = str(adapter_spec['dg'])
                except ValueError:
                    pass

            adaptermaps.append(guest_map)

        # IP

        globalip = vim.vm.customization.GlobalIPSettings(dnsServerList=["192.168.30.7", "192.168.30.3"], dnsSuffixList=["cmpsys.com"])

        # Hostname settings
        ident = vim.vm.customization.LinuxPrep()
        ident.domain = 'cmpsys.com'
        ident.hostName = vim.vm.customization.FixedName()
        ident.hostName.name = vm_name

        # Putting all these pieces together in a custom spec
        # custom_os = vim.vm.customization.Specification(nicSettingMap=[adaptermap],

        custom_os = vim.vm.customization.Specification(nicSettingMap=adaptermaps,
                                                       globalIPSettings=globalip,
                                                       identity=ident)

        clonespec.config = config_spec
        clonespec.customization = custom_os

    else:
        logger.debug('THREAD {} custom os is not enabled'.format(vm_name))

    relocate_spec.pool = resource_pool

    if resource_pool is not None:
        logger.debug('THREAD %s - Resource pool found, using' % vm_name)
        # relocate_spec = vim.vm.RelocateSpec(pool=resource_pool) > temp pending to delete
        # relocate_spec.pool = resource_pool -> temp pending to delete

        # relocate_spec.pool = resource_pool -> temp pending to delete
    else:
        logger.debug('THREAD %s - No resource pool found, continuing without it' % vm_name)
        # relocate_spec = vim.vm.RelocateSpec() -> temp pending to delete

        relocate_spec.pool = resource_pool

        logger.debug('THREAD %s - Creating clone spec' % vm_name)

    # print clonespec -> temp debug pending to delete

    # find_vm = False

    # if find_vm(si, logger, vm_name, True):
    #     logger.warning('THREAD %s - Virtual machine already exists, not creating' % vm_name)
    #     run_loop = False
    # else:
    #     logger.debug('THREAD %s - Creating clone task' % vm_name)
    #
    #     task = template_vm.Clone(folder=folder, name=vm_name, spec=clonespec)
    #
    #     logger.info('THREAD %s - Cloning task created' % vm_name)
    #     logger.info('THREAD %s - Checking task for completion. This might take a while' % vm_name)

    task = template_vm.Clone(folder=folder, name=vm_name, spec=clonespec)
    # tasks = []
    while run_loop:

        info = task.info

        logger.debug('THREAD %s - Checking clone task' % vm_name)
        if info.state == vim.TaskInfo.State.success:
            logger.info('THREAD %s - Cloned and running' % vm_name)

            vm = info.result

            # tasks.append(task.info)
            # tasks.append(task.info.result)

            run_loop = False

            break
        elif info.state == vim.TaskInfo.State.running:
            logger.debug('THREAD %s - Cloning task is at %s percent' % (vm_name, info.progress))
        elif info.state == vim.TaskInfo.State.queued:
            logger.debug('THREAD %s - Cloning task is queued' % vm_name)
        elif info.state == vim.TaskInfo.State.error:
            if info.error.fault:
                logger.info(
                        'THREAD %s - Cloning task has quit with error: %s' % (vm_name, info.error.fault.msg))
            else:
                logger.info('THREAD %s - Cloning task has quit with cancellation' % vm_name)
            run_loop = False
            break
        logger.debug('THREAD %s - Sleeping 2 seconds for new check' % vm_name)
        sleep(0.1)

    if vm and power_on:
        logger.info('THREAD %s - Powering on VM. This might take a couple of seconds' % vm_name)
        power_on_task = vm.PowerOn()
        logger.debug('THREAD %s - Waiting fo VM to power on' % vm_name)
        run_loop = True
        while run_loop:
            info = task.info
            if info.state == vim.TaskInfo.State.success:
                run_loop = False
                break
            elif info.state == vim.TaskInfo.State.error:
                if info.error.fault:
                    logger.info(
                            'THREAD %s - Power on has quit with error: %s' % (vm_name, info.error.fault.faultMessage))
                else:
                    logger.info('THREAD %s - Power on has quit with cancelation' % vm_name)
                run_loop = False
                break
            sleep(0.1)

        # return tasks
        return vm
    return
    # return task


def clone_vm():
    """
    Clone a VM or template into multiple VMs with logical names with numbers and allow for post-processing
    """

    args = get_args()

    amount = args.amount[0]
    basename = None
    if args.basename:
        basename = args.basename[0]
    count = args.count[0]
    debug = args.debug
    folder_name = None
    if args.folder:
        folder_name = args.folder[0]
    host = args.host[0]
    log_file = None
    if args.logfile:
        log_file = args.logfile[0]
    password = None
    if args.password:
        password = args.password[0]
    power_on = not args.nopoweron
    host_system_name = args.host_system_name if args.host_system_name else None
    resource_pool_name = args.resource_pool
    # if args.resource_pool: -> temp decide if pending to delete
    #     resource_pool_name = args.resource_pool[0] -> temp debug pending to delete
    # nosslcheck = args.nosslcheck  -> temp debug pending to delete
    template = args.template[0]
    threads = args.threads[0]
    username = args.username[0]
    verbose = args.verbose
    ds_name = args.ds_name
    ds_local_name = args.ds_local_name
    cpu = args.cpu
    ram = args.ram
    memory_reservation_locked_to_max = args.memory_reservation_locked_to_max

    if memory_reservation_locked_to_max:
        memory_reservation_locked_to_max = ast.literal_eval(memory_reservation_locked_to_max)

    dry_run = args.dry_run if args.dry_run else None

    #ip_range = args.ip_range if args.ip_range else None
    ip_range = None

    # Logging settings

    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    if log_file:
        logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    else:
        logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(lineno)d %(message)s', level=log_level)
    logger = logging.getLogger(__name__)

    # Disabling SSL

    logger.debug('Disabling SSL certificate verification.')
    requests.packages.urllib3.disable_warnings()
    import ssl

    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    # Getting user password
    if password is None:
        logger.debug('No command line password received, requesting password from user')
        password = getpass.getpass(prompt='Enter password for vCenter %s for user %s: ' % (host, username))

    try:
        si = vc_si(args)

        # Find the correct VM
        logger.debug('Finding template %s' % template)
        # template_vm = find_vm(si, logger, template, False)
        template_vm = VirtualMachine().return_vms(si, template)
        if template_vm is None:
            logger.error('Unable to find template %s' % template)
            return 1
        logger.info('Template %s found' % template)

        # Pool handling
        logger.debug('Setting up pools and threads')
        pool = ThreadPool(threads)
        vm_specs = []
        logger.debug('Pools created with %s threads' % threads)

        logger.debug('Creating thread specifications, this may take a while.')

        all_vms = VirtualMachine().return_vms(si, 'any')
        all_vms_names = []
        while all_vms:
            all_vms_names.append(all_vms.pop(0).name)

        vm_names = []
        # for a in range(1, amount + 1):
        #     if count > 99:
        #         vm_names.append('{}-{}'.format(basename, count))
        #     elif count > 9:
        #         vm_names.append('{}-0{}'.format(basename, count))
        #     else:
        #         vm_names.append('{}-00{}'.format(basename, count))
        #     count += 1

        machineDetialsHashMap = {
         'DEV101': ['esx1.vmware.local', '172.30.16.101', '172.30.15.101', 'DanD'],
         'DEV102': ['esx2.vmware.local', '172.30.16.102', '172.30.15.102', "RamiN"],
         'DEV103': ['esx3.vmware.local', '172.30.16.103', '172.30.15.103', 'Yacob'],
         'DEV104': ['esx1.vmware.local', '172.30.16.104', '172.30.15.104', 'OrenG'],
         # 'LIN01': ['esx2', '172.30.16.102', '172.30.15.102'],
         # 'dev104': ['esx1', '172.30.16.104', '172.30.15.104'],
         # 'dev105': ['esx2', '172.30.16.105', '172.30.15.105'],
         # 'dev106': ['esx3', '172.30.16.106', '172.30.15.106'],
         # 'dev107': ['esx1', '172.30.16.107', '172.30.15.107'],
         # 'dev108': ['esx2', '172.30.16.108', '172.30.15.108'],
         # 'dev109': ['esx2', '172.30.16.109', '172.30.15.109'],
         # 'dev110': ['esx3', '172.30.16.110', '172.30.15.110'],
        }


        # try:
        #     ips_trusted = generate_ip_range(ip_range[0], ip_range[1])
        #     ips_fast = generate_ip_range(ip_range[2], ip_range[3])
        # except:
        #     pass

        def ipv4_to_ipv6(ip):
            """
            Convert ipv4 to ipv6
            :param ip:
            :return:
            """
            numbers = list(map(int, ip.split('.')))
            return '2002:{:02x}{:02x}:{:02x}{:02x}::'.format(*numbers)

        def ipv6generator():
            """
            Generator ipv6
            :return: string
            """
            m = 16 ** 4
            return "2001:cafe:4ae:936f:{0}".format(":".join(("%x" % random.randint(0, m) for i in range(4))))

        datastore = Datastore().return_datastores(si, ds_name)
        datastore_local = Datastore().return_datastores(si, ds_local_name)
        # host_system = Host().return_hosts(si, host_system_name) if host_system_name else None

        vm_names_hash_map = machineDetialsHashMap.keys()
        for vm_name in vm_names_hash_map:

            def return_vnic1_spec():

                return {'ipv4': machineDetialsHashMap.get(vm_name)[1],
                        'subnet': '255.255.255.0',
                        'ipv6': '',
                        'subnet_ipv6': '',
                        'dg': '172.30.16.1'}

            def return_vnic2_spec():
                return {'ipv4': machineDetialsHashMap.get(vm_name)[2],
                        'subnet': '255.255.255.0',
                        'ipv6': '',
                        'subnet_ipv6': '',
                        'dg': ''}

                # return ip_spec

            def vnics():
                vnic1 = return_vnic1_spec()
                vnic2 = return_vnic2_spec()

                return [vnic1, vnic2]

            adapters_specs = vnics()

            dic_spec = {
                'si': si,
                'logger': logger,
                'vm_name': vm_name,
                'resource_pool_name': resource_pool_name,
                'folder_name': folder_name,
                'power_on': power_on,
                'template': template,
                'template_vm': template_vm,
                'adapters_specs': adapters_specs,
                'cpu': cpu,
                'ram': ram,
                'memory_reservation_locked_to_max': memory_reservation_locked_to_max,
                'datastore': [datastore, datastore_local],
                'host_system': Host().return_hosts(si, machineDetialsHashMap.get(vm_name)[0]),
                'owner': machineDetialsHashMap.get(vm_name)[3],
            }

            if vm_name not in all_vms_names:
                vm_specs.append(dic_spec)
                logger.info('Creating spec for vm {}'.format(vm_name))
            else:
                logger.warning('THREAD VM {} already exists, not creating'.format(vm_name))

        logger.debug('vm_specs {}'.format(vm_specs))
        return_threads = []

        if not dry_run:
            # thread = pool.map(vm_clone_handler_wrapper, vm_specs)
            thread = pool.map(vm_clone_handler, vm_specs)
            return_threads.extend(thread)

            logger.debug('Closing virtual machine clone pool')
            pool.close()
            pool.join()

    except KeyboardInterrupt:
        logger.info('Received interrupt, exiting')
        return 1

    except vmodl.MethodFault as err:
        logger.critical('Caught vmodl fault: %s' % err.msg)
        return 1
    except Exception as err:
        logger.critical('Caught exception: %s' % str(err))
        return 1

    logger.info('Finished all tasks')

    return return_threads


if __name__ == "__main__":
    clone_vm()
    #
    # d = Ds("d", 500, True, "o")
    #
    # print(d.name)
    # d.name = "1"


