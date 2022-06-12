

# from fnc1 import *
from common_helpers import *
from cls_operations import Operation
from pyVmomi import vim, vmodl
import re
import logging


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
                        nargs=1,
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
                        choices=['off', 'on', 'del', 'shut', 'snap.create', 'snap.del'],
                        nargs='+')

    parser.add_argument('-E', '--exclude_vms',
                        required=False,
                        help='List of VMs to exclude',
                        dest='exclude_vms',
                        type=str,
                        nargs='+')

    parser.add_argument('-N',
                        required=False,
                        help='Duplicate operations (default = 1)',
                        dest='doperations',
                        type=int)

    return parser.parse_args()


class Builder(object):
    def __init__(self, vms, operations, dry_run):
        self.vms = vms
        self.operations = operations
        self.dry_run = dry_run

    def operation_builder(self):
        """
        :return:
        """
        array = []
        for vm in self.vms:
            for operation in self.operations:
                obj_op = Operation.create(operation, vm)
                array.append({'vm': vm, 'task': obj_op.task,
                              'log': obj_op.logger_string,
                              'dry_run': self.dry_run})
        return array


class VmOperations(object):
    def __init__(self, args, si):
        self.args = args
        self.si = si
# TODO => check if si will be created in main or class or while init obj build        # self.si = vc_si(self.args)

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
            print('Caught vmodl fault : ' + error.msg)
            return 1


def main():
    """
    poweroff & delete vms
    """

    args = get_args()
    si = vc_si(args)
    basename = None
    if args.basename:
        basename = args.basename[0]
    debug = args.debug
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

        vms = [vm for vm in ls_all_vms if re.match(basename, vm.name) and vm.name not in ls_exclude_vms]

        obj_array = Builder(vms, operations, dry_run)
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

            thread = pool.map(vo.multi_oper, array)
            return_threads.extend(thread)
            logger.debug('Closing pool')
            pool.close()
            pool.join()

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
