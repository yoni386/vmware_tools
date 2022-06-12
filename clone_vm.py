
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
                        default=1024,
                        dest='ram',
                        help='RAM Size in MB')

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

    args = parser.parse_args()
    return args


args = get_args()


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

    run_loop = True
    vm = None

    logger.debug('THREAD %s - started' % vm_name)
    logger.info('THREAD %s - Trying to clone %s to new virtual machine' % (vm_name, template))

    # Find the correct Resource Pool
    resource_pool = None
    if resource_pool_name is not None:
        logger.debug('THREAD %s - Finding resource pool %s' % (vm_name, resource_pool_name))
        resource_pool = find_resource_pool(si, logger, resource_pool_name)
        if resource_pool is None:
            logger.critical('THREAD %s - Unable to find resource pool %s' % (vm_name, resource_pool_name))
            logger.info('THREAD %s - Resource pool %s found' % (vm_name, resource_pool_name))
            return 1

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

    # ips = iprange('10.0.0.1', '10.0.0.5')  -> temp debug

    relocate_spec = vim.vm.RelocateSpec()
    relocate_spec.datastore = datastore

    if host_system:
        relocate_spec.host = host_system
        logger.debug('Clone VM {} to Esx host {}'.format(vm_name, host_system))

    config_spec = vim.vm.ConfigSpec()
    config_spec.numCPUs = cpu
    config_spec.memoryMB = ram
    config_spec.cpuHotAddEnabled = True
    config_spec.memoryHotAddEnabled = True
    # config_spec.memoryReservationLockedToMax = True
    # config_spec.memoryAllocation = mem_res

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relocate_spec

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

        globalip = vim.vm.customization.GlobalIPSettings(dnsServerList=["10.7.77.192", "10.7.77.135"], dnsSuffixList=["mtl.labs.mlnx.", "mtr.labs.mlnx.", "labs.mlnx.", "mlnx.", "mtl.com"])

        # Hostname settings
        ident = vim.vm.customization.LinuxPrep()
        ident.domain = 'vmware.local'
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

    else:
        logger.debug('THREAD %s - No resource pool found, continuing without it' % vm_name)
        # relocate_spec = vim.vm.RelocateSpec() -> temp pending to delete

        relocate_spec.pool = resource_pool

        logger.debug('THREAD %s - Creating clone spec' % vm_name)

    task = template_vm.Clone(folder=folder, name=vm_name, spec=clonespec)
    # tasks = []
    while run_loop:

        info = task.info

        logger.debug('THREAD %s - Checking clone task' % vm_name)
        if info.state == vim.TaskInfo.State.success:
            logger.info('THREAD %s - Cloned and running' % vm_name)

            vm = info.result

            run_loop = False

            break
        elif info.state == vim.TaskInfo.State.running:
            logger.debug('THREAD %s - Cloning task is at %s percent' % (vm_name, info.progress))
        elif info.state == vim.TaskInfo.State.queued:
            logger.debug('THREAD %s - Cloning task is queued' % vm_name)
        elif info.state == vim.TaskInfo.State.error:
            if info.error.fault:
                logger.info(
                        'THREAD %s - Cloning task has quit with error: %s' % (vm_name, info.error.fault.faultMessage))
            else:
                logger.info('THREAD %s - Cloning task has quit with cancelation' % vm_name)
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
    resource_pool_name = None
    # if args.resource_pool: -> temp decide if pending to delete
    #     resource_pool_name = args.resource_pool[0] -> temp debug pending to delete
    # nosslcheck = args.nosslcheck  -> temp debug pending to delete
    template = args.template[0]
    threads = args.threads[0]
    username = args.username[0]
    verbose = args.verbose
    ds_name = args.ds_name
    cpu = args.cpu
    ram = args.ram
    memory_reservation_locked_to_max = args.memory_reservation_locked_to_max

    if memory_reservation_locked_to_max:
        memory_reservation_locked_to_max = ast.literal_eval(memory_reservation_locked_to_max)

    dry_run = args.dry_run if args.dry_run else None

    ip_range = args.ip_range if args.ip_range else None

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
        logging.basicConfig(filename=log_file, format='%(asctime)s %(levelname)s %(message)s', level=log_level)
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

        vms = VirtualMachine().return_vms(si, 'any')
        vms_names = []
        while vms:
            vms_names.append(vms.pop(0).name)

        vm_names = []
        for a in range(1, amount + 1):
            if count > 99:
                vm_names.append('{}-{}'.format(basename, count))
            elif count > 9:
                vm_names.append('{}-0{}'.format(basename, count))
            else:
                vm_names.append('{}-00{}'.format(basename, count))
            count += 1

        try:
            ips_trusted = generate_ip_range(ip_range[0], ip_range[1])
            ips_fast = generate_ip_range(ip_range[2], ip_range[3])
        except:
            pass

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
        host_system = Host().return_hosts(si, host_system_name) if host_system_name else None

        for vm_name in vm_names:

            def return_vnic1_spec():

                return {'ipv4': ips_trusted.pop(0),
                        'subnet': '255.255.0.0',
                        'ipv6': '',
                        'subnet_ipv6': '',
                        'dg': '10.130.0.1'}

            def return_vnic2_spec():
                return {'ipv4': ips_fast.pop(0),
                        'subnet': '255.255.0.0',
                        'ipv6': ipv6generator(),
                        'subnet_ipv6': 64,
                        'dg': ''}

                # return ip_spec

            def vnics():
                vnic1 = 'dhcp' if ip_range[0] == 'dhcp' else return_vnic1_spec()
                vnic2 = 'dhcp' if ip_range[2] == 'dhcp' else return_vnic2_spec()

                return [vnic1, vnic2]

            adapters_specs = vnics() if ip_range else None

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
                'datastore': datastore,
                'host_system': host_system}

            if vm_name not in vms_names:
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
