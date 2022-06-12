from common_helpers import *
# from cls_operations import Operation
import re
import logging
from operator import attrgetter
from pyVmomi import vim, vmodl
from tools import cluster, datacenter

__author__ = 'Yoni Shperling'


def get_args():
    """
     arguments for script
    """

    parser = argparse.ArgumentParser(
        description="Make a Datacenter and Cluster.")

    parser.add_argument('-H', '--host',
                        nargs=1,
                        required=True,
                        help='The vCenter or ESXi host to connect to',
                        dest='host',
                        type=str)

    parser.add_argument('-u', '--username',
                        nargs=1,
                        required=False,
                        help='The username to connect to si',
                        dest='username',
                        default='administrator@vsphere.local',
                        type=str)

    parser.add_argument('-p', '--password',
                        nargs=1,
                        required=False,
                        help='The password. If not specified, prompt will be at runtime for a password',
                        dest='password',
                        default='Password123!',
                        type=str)

    parser.add_argument('-o', '--port',
                        nargs=1,
                        required=False,
                        help='Server port to connect to (default = 443)',
                        dest='port',
                        type=int,
                        default=[443])


    parser.add_argument('-d', '--debug',
                        required=False,
                        help='Enable debug output',
                        dest='debug',
                        action='store_true')

    parser.add_argument('-l', '--log-file',
                        nargs=1, required=False,
                        help='File to log to (default = stdout)',
                        dest='logfile', type=str)

    parser.add_argument('-D', '--datacenter-name',
                        required=False,
                        action='store',
                        default=None,
                        dest='dc_name',
                        help='Name of the Datacenter you \
                                    wish to use. If omitted, the first \
                                    datacenter will be used.')

    parser.add_argument('-S', '--datastore-name',
                        required=False,
                        action='store',
                        default=None,
                        dest='ds_name',
                        type=str,
                        nargs='+',
                        help='Datastore to use\
                                    If left blank, first two \
                                    datastore will be elected')

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

    parser.add_argument('-C', '--cluster',
                        required=False,
                        help='Cluster Name',
                        dest='cl_name',
                        type=str)

    # parser.add_argument('-O', '--operations',
    #                     required=False,
    #                     help='off, on, del',
    #                     dest='operations',
    #                     type=str,
    #                     choices=['off', 'on', 'restart_vm', 'del', 'shut', 'snap.create', 'snap.del', 'vmotion',
    #                              'change.vnic', "change.vnic.mac"],
    #                     nargs='+')
    #
    # parser.add_argument('-E', '--exclude_vms',
    #                     nargs='+',
    #                     required=False,
    #                     help='List of VMs to exclude',
    #                     dest='exclude_vms',
    #                     type=str)
    #
    # parser.add_argument('-N',
    #                     required=False,
    #                     help='Duplicate operations (default = 1)',
    #                     dest='doperations',
    #                     type=int)

    # parser.add_argument('-V',
    #                     required=False,
    #                     help='Esx migrate to',
    #                     dest='hostsystem',
    #                     type=str)

    # parser.add_argument('-D', '--t_pg_name',
    #                     required=False,
    #                     help='Target Destination port group name',
    #                     dest='target_pg',
    #                     type=str)
    #
    # parser.add_argument('-n',
    #                     required=False,
    #                     help='max number of vm (default = 0)',
    #                     dest='max_vms',
    #                     default=0,
    #                     type=int)

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

def new_cluster(name, dc, spec=None):
    """

    :param spec: vim.cluster.ConfigSpecEx()
    :param dc: vim.Datacenter
    :type name: str
    """
    if spec is None:
        spec = vim.cluster.ConfigSpecEx()
        spec.drsConfig = vim.cluster.DrsConfigInfo()
        # spec.drsConfig.defaultVmBehavior = fullyAutomated
        spec.drsConfig.vmotionRate = 3
        spec.drsConfig.enabled = True
        spec.dasConfig = vim.cluster.DasConfigInfo()
        spec.dasConfig.admissionControlEnabled = True
        spec.dasConfig.vmMonitoring = 'vmMonitoringDisabled'
        spec.dasConfig.admissionControlPolicy = vim.cluster.FailoverResourcesAdmissionControlPolicy()
        spec.dasConfig.admissionControlPolicy.memoryFailoverResourcesPercent = 0
        spec.dasConfig.admissionControlPolicy.cpuFailoverResourcesPercent = 0
        spec.dasConfig.enabled = True
        spec.dasConfig.hostMonitoring = 'enabled'
        spec.vsanConfig = vim.vsan.cluster.ConfigInfo()
        spec.vsanConfig.enabled = False
        spec.dpmConfig = vim.cluster.DpmConfigInfo()
        spec.inHciWorkflow = True

    try:
        return cluster.create_cluster(datacenter=dc, name=name, cluster_spec=spec)
    except:
        return None


def set_cluster(cls, heartbeat_datastore=None, spec=None):
    """

    :type cls: vim.Cluster
    :param heartbeat_datastore:
    :param spec: vim.cluster.ConfigSpecEx()
    """
    if spec is None:
        spec = vim.cluster.ConfigSpecEx()
        spec.orchestration = vim.cluster.OrchestrationInfo()
        spec.orchestration.defaultVmReadiness = vim.cluster.VmReadiness()
        spec.orchestration.defaultVmReadiness.readyCondition = 'none'
        spec.orchestration.defaultVmReadiness.postReadyDelay = 0
        spec.drsConfig = vim.cluster.DrsConfigInfo()
        spec.dasConfig = vim.cluster.DasConfigInfo()
        spec.dasConfig.admissionControlEnabled = True
        spec.dasConfig.defaultVmSettings = vim.cluster.DasVmSettings()
        spec.dasConfig.defaultVmSettings.restartPriority = 'medium'
        spec.dasConfig.defaultVmSettings.vmComponentProtectionSettings = vim.cluster.VmComponentProtectionSettings()
        spec.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForPDL = 'restartAggressive'
        spec.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmReactionOnAPDCleared = 'none'
        spec.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmStorageProtectionForAPD = 'restartConservative'
        spec.dasConfig.defaultVmSettings.vmComponentProtectionSettings.vmTerminateDelayForAPDSec = 180
        spec.dasConfig.defaultVmSettings.restartPriorityTimeout = 600
        spec.dasConfig.defaultVmSettings.isolationResponse = 'none'
        spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings = vim.cluster.VmToolsMonitoringSettings()
        spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.minUpTime = 120
        spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailures = 3
        spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.maxFailureWindow = -1
        spec.dasConfig.defaultVmSettings.vmToolsMonitoringSettings.failureInterval = 30
        spec.dasConfig.vmMonitoring = 'vmMonitoringDisabled'

        spec.dasConfig.heartbeatDatastore = [] if heartbeat_datastore else heartbeat_datastore
        # spec.dasConfig.HBDatastoreCandidatePolicy = 'allFeasibleDsWithUserPreference'
        spec.dasConfig.admissionControlPolicy = vim.cluster.FailoverResourcesAdmissionControlPolicy()
        spec.dasConfig.admissionControlPolicy.failoverLevel = 1
        spec.dasConfig.admissionControlPolicy.autoComputePercentages = True
        # spec.dasConfig.admissionControlPolicy.PMemAdmissionControlEnabled = False
        spec.dasConfig.admissionControlPolicy.memoryFailoverResourcesPercent = 0
        spec.dasConfig.admissionControlPolicy.cpuFailoverResourcesPercent = 0
        spec.dasConfig.admissionControlPolicy.resourceReductionToToleratePercent = 100
        spec.dasConfig.vmComponentProtecting = 'enabled'
        spec.dasConfig.enabled = True
        spec.dasConfig.hostMonitoring = 'enabled'
        spec.dpmConfig = vim.cluster.DpmConfigInfo()
    modify = True

    # this creates reconfigure task the set cluster spec
    cls.ReconfigureComputeResource_Task(spec, modify)


def tear_down(si, name=""):
    # si.getSupportedOption()  # OptionManager-VpxSettings
    changedValue_0 = vim.option.OptionValue()
    changedValue_0.value = 'False'
    changedValue_0.key = 'config.vcls.clusters.domain-c6867.enabled'
    changedValue = [changedValue_0]
    opt_mgr = si.RetrieveContent().setting
    opt_mgr.UpdateValues(changedValue)
    # si.UpdateOptions(changedValue)  # OptionManager-VpxSettings


def main():
    """
    Make new Datacenter and Cluster
    """

    args = get_args()
    si = vc_si(args)
    debug = args.debug
    log_file = None
    verbose = args.verbose
    dry_run = args.dry_run if args.dry_run else False

    dcName = args.dc_name
    clName = args.cl_name
    dsList = args.ds_name

    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=log_level)
    logger = logging.getLogger(__name__)

    dc = DataCenter().return_dcs(si, dcName)
    cl = Cluster().return_clusters(si, clName)
    datastores = Datastore().return_datastores(si, dsList)

    # logger.info('datacenters are {}'.format([dc.name for dc in datacenters]))
    # logger.info('clusters are {}'.format([cl.name for cl in clusters]))
    # logger.info('datastores are {}'.format([ds.name for ds in datastores]))

    try:
        tear_down(si)

    # if dcName in datacenters:
    #     logger.warning('datacenter already exist {}'.format(dcName))

        logger.info('Dry Run mode') if dry_run else None

    except Exception as err:
        logger.exception('Caught exception: {}'.format(str(err)))
        return 1
    except KeyboardInterrupt:
        logger.exception('Received interrupt, exiting')
        return 1


if __name__ == "__main__":
    main()



