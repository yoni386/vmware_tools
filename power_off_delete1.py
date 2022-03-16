
# import re

from fnc1 import *
from fnc2 import *
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

    return parser.parse_args()


def main():
    """
    poweroff & delete vms
    """
    args = get_args()
    # amount = args.amount[0]
    basename = None
    if args.basename:
        basename = args.basename[0]
    debug = args.debug
    # host = args.host[0]
    log_file = None
    # if args.logfile:
    #     log_file = args.logfile[0]
    password = None
    if args.password:
        password = args.password[0]
    # host_system_name = args.host_system_name if args.host_system_name else None
    threads = args.threads[0]
    username = args.username[0]
    verbose = args.verbose
    dry_run = args.dry_run if args.dry_run else False

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

    args = get_args()
    si = vc_si(args)

    class VmOerations(object):
        def __init__(self, si):
            self.si = si

        def power_off(self, vm):
            """
            Poweroff VM
            :param vm: vm object
            :return: task
            """
            try:
                logger.debug('Powering Off VM {}'.format(vm.name))
                task = vm.PowerOffVM_Task()
                wait_for_tasks(self.si, [task])

            except vmodl.MethodFault as error:
                print ('Caught vmodl fault : ' + error.msg)
                return 1
            return task

        def destroy_vm(self, vm):
            """
            Destroy VM
            :param vm: vm object
            :return: task
            """
            logger.debug('Destroy VM {}'.format(vm.name))
            try:

                task = vm.Destroy_Task()
                wait_for_tasks(self.si, [task])
            except vmodl.MethodFault as error:
                print ('Caught vmodl fault : ' + error.msg)
                return 1

            return task

        def power_off_delete(self, vm):
            try:
                self.power_off(vm)
                self.destroy_vm(vm)
            except vmodl.MethodFault as error:
                print ('Caught vmodl fault : ' + error.msg)
                return 1

    # def power_off(vm):
    #     """
    #     :param vm:
    #     :return:
    #     """
    #
    #     try:
    #         logger.debug('Powering Off VM {}'.format(vm.name))
    #         task = vm.PowerOffVM_Task()
    #         wait_for_tasks(si, [task])
    #
    #     except vmodl.MethodFault as error:
    #         print ('Caught vmodl fault : ' + error.msg)
    #         return 1
    #     return task
    #
    # def destroy_vm(vm):
    #     """
    #     :param vm:
    #     :return:
    #     """
    #     logger.debug('Destroy VM {}'.format(vm.name))
    #     try:
    #
    #         task = vm.Destroy_Task()
    #         wait_for_tasks(si, [task])
    #     except vmodl.MethodFault as error:
    #         print ('Caught vmodl fault : ' + error.msg)
    #         return 1
    #
    #     return task
    #
    # def power_off_delete(vm):
    #     power_off(vm)
    #     destroy_vm(vm)

    vo = VmOerations(si)

    try:
        pool = ThreadPool(threads)

        vm = VirtualMachine()
        ls_all_vms = vm.get_all_vms(si)

        vms = [x for x in ls_all_vms if re.findall(basename, x.name)]
        return_threads = []

        logger.info('Dry Run mode') if dry_run else None

        logger.info('Number of VMs is {}'.format(len(vms)))
        logger.info('VMs to poweroff & delete {}'.format([vm.name for vm in vms]))

        if len(vms) and not dry_run:
            thread = pool.map(vo.power_off_delete, vms)
            return_threads.extend(thread)
            logger.debug('Closing pool')
            pool.close()
            pool.join()

        else:
            logger.info('exiting')
            sys.exit(1)
    except Exception, e:
        logger.critical('Caught exception: %s' % str(e))
        return 1
    except KeyboardInterrupt:
        logger.info('Received interrupt, exiting')
        return 1


if __name__ == "__main__":
        main()
