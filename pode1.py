from common_helpers import *
from cls_operations import Operation
import re
import logging
from operator import attrgetter
from pyVmomi import vim, vmodl

__author__ = 'Yoni Shperling'


def get_args():
    """
     arguments for script
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
                        nargs='+',
                        required=True,
                        help='Basename of VMs',
                        dest='basename',
                        type=str)

    parser.add_argument('-d', '--debug',
                        required=False,
                        help='Enable debug output',
                        dest='debug',
                        action='store_true')

    parser.add_argument('-l', '--log-file',
                        nargs=1, required=False,
                        help='File to log to (default = stdout)',
                        dest='logfile', type=str)

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

    parser.add_argument('-y', '--dry_run',
                        required=False,
                        nargs='?',
                        const=True,
                        help='Only simulate value if True',
                        dest='dry_run',
                        type=bool)

    parser.add_argument('-O', '--operations',
                        required=True,
                        help='off, on, del',
                        dest='operations',
                        type=str,
                        choices=['off', 'on', 'restart_vm', 'del', 'shut', 'snap.create', 'snap.del', 'vmotion',
                                 'change.vnic', "change.vnic.mac"],
                        nargs='+')

    parser.add_argument('-E', '--exclude_vms',
                        nargs='+',
                        required=False,
                        help='List of VMs to exclude',
                        dest='exclude_vms',
                        type=str)

    parser.add_argument('-N',
                        required=False,
                        help='Duplicate operations (default = 1)',
                        dest='doperations',
                        type=int)

    parser.add_argument('-V',
                        required=False,
                        help='Esx migrate to',
                        dest='hostsystem',
                        type=str)

    parser.add_argument('-D', '--t_pg_name',
                        required=False,
                        help='Target Destination port group name',
                        dest='target_pg',
                        type=str)

    parser.add_argument('-n',
                        required=False,
                        help='max number of vm (default = 0)',
                        dest='max_vms',
                        default=0,
                        type=int)

    return parser.parse_args()


class Builder(object):
    def __init__(self, operations, vms, dry_run, operation_dst):
        self.operations = operations
        self.vms = vms
        self.dry_run = dry_run
        self.operation_dst = operation_dst

    def operation_builder(self):
        """
        :return:
        """

        array = []
        for index, vm in enumerate(self.vms):
            for self.operation in self.operations:
                obj_op = Operation.create(self.operation, vm, self.operation_dst)
                array.append({'index': index, 'vm': vm,
                              'task': obj_op.task,
                              'log': obj_op.logger_string,
                              'dry_run': self.dry_run})
        return array


class VmOperations(object):
    def __init__(self, args, si):
        self.args = args
        self.si = si

    # TODO => check if si will be created in main or class or while init obj build  # self.si = vc_si(self.args)

    def multi_oper(self, args):
        """
        Preform multi operation task as object method and log
        :return: task
        """
        logger = logging.getLogger(__name__)
        try:
            logger.debug(args['log'].format(args['vm'].name))
            if not args['dry_run']:
                task = args['task']()
                wait_for_tasks(self.si, [task])
                return task

        except vmodl.MethodFault as error:
            print ('Caught vmodl fault : ' + error.msg)
            return 1


def main():
    """
    poweroff & delete vms
    """

    args = get_args()
    si = vc_si(args)
    # amount = args.amount[0]
    basename = None
    if args.basename:
        basename = args.basename[0]
    debug = args.debug
    # log_file = None
    # host_system_name = args.host_system_name if args.host_system_name else None
    threads = args.threads[0]
    verbose = args.verbose
    dry_run = args.dry_run if args.dry_run else False
    exclude_vms = args.exclude_vms if args.exclude_vms else False
    operations = args.operations if args.operations else None
    operations = operations * args.doperations if args.doperations else operations

    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    logger = logging.getLogger(__name__)

    try:

        obj_vm = VirtualMachine()
        vo = VmOperations(args, si)
        pool = ThreadPool(threads)

        ls_all_vms = obj_vm.get_all_vms(si)

        ls_exclude_vms = ['Vc1', 'Dc1']
        ls_exclude_vms.extend(exclude_vms) if exclude_vms else None

        operation_dst = si

        if args.hostsystem:
            obj_host = Host()
            operation_dst = obj_host.return_hosts(si, args.hostsystem)

        if args.target_pg:
            obj_net = Network()
            operation_dst = obj_net.get_pg(si, args.target_pg)

        vms = [vm for vm in ls_all_vms if re.match(basename, vm.name) and vm.name not in ls_exclude_vms]
        if args.max_vms:
            max_vms = args.max_vms
            if len(vms) > max_vms:
                vms.sort(key=attrgetter("name"))
                logger.debug(
                    "Number of VMs to remove: is {}, VMs to removed are: {}".format(max_vms,
                                                                                    [vm.name for vm in vms[:max_vms]]))
                vms = vms[:max_vms]

        opers = ["slob.create", "slob.reindex", "slob.drop"]

        obj_array = Builder(operations, vms, dry_run, operation_dst)
        array = obj_array.operation_builder()

        logger.info('Dry Run mode') if dry_run else None
        logger.info('Number of VMs is {}'.format(len(vms)))
        logger.debug('Number of operations is {}'.format(len(operations)))
        logger.debug('Int to multiply operations is {}'.format(args.doperations))
        logger.debug('VMs to exclude are {}'.format(ls_exclude_vms))
        logger.info('Operations to perform {}'.format([operation for operation in operations]))
        logger.info('Operations will be preformed on VMs {}'.format([vm.name for vm in vms]))

        return_threads = []
        if len(vms):
            try:
                thread = pool.map(vo.multi_oper, array, chunksize=len(operations))
                return_threads.extend(thread)
                logger.debug('Closing pool')
                # pool.close()
                pool.join()
                pool.close()
            except:
                pass

        else:
            logger.info('Number of VMs is 0, exiting')
            sys.exit(1)
    except Exception as err:
        logger.exception('Caught exception: {}'.format(str(err)))
        return 1
    except KeyboardInterrupt:
        logger.exception('Received interrupt, exiting')
        return 1


if __name__ == "__main__":
    main()
