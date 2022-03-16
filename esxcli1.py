from pyVmomi.VmomiSupport import CreateAndLoadManagedType
from pyVmomi.ManagedMethodExecutorHelper import MMESoapStubAdapter
from pyVmomi.VmomiSupport import F_OPTIONAL
# from ..errors import CLITypeException
from fnc1 import *
from fnc2 import *



# Copy of SmartConnect + Connect, but login is optional and keyfile/certfile passed all the way

from pyVim.connect import GetServiceVersions, __FindSupportedVersion, SoapStubAdapter
from pyVim.connect import versionMap, _rx
from pyVmomi import vim
import re
import sys
import ssl
from six import reraise
from logging import getLogger

logger = getLogger(__name__)


class SoapStubAdapterWithLogging(SoapStubAdapter):
    def _debug(self, messsage, *args, **kwargs):
        try:
            logger.debug(messsage.format(*args, **kwargs))
        except:
            pass

    def InvokeMethod(self, mo, info, args, outerStub=None):
        self._debug("{} --> {}", mo, info.wsdlName)
        try:
            return SoapStubAdapter.InvokeMethod(self, mo, info, args, outerStub)
        finally:
            self._debug("{} <-- {}", mo, info.wsdlName)


def _create_stub(host, protocol="https", port=443,
                 namespace=None, path="/sdk",
                 version=None, keyfile=None, certfile=None, sslContext=None):

    port = protocol == "http" and -int(port) or int(port)

    try:
        info = re.match(_rx, host)
        if info is not None:
            host = info.group(1)
            if host[0] == '[':
                host = info.group(1)[1:-1]
            if info.group(2) is not None:
                port = int(info.group(2)[1:])
    except ValueError:
        pass

    if namespace:
        assert(version is None)
        version = versionMap[namespace]
    elif not version:
        version = "vim.version.version6"

    # Create the SOAP stub adapter
    if certfile is not None and keyfile is not None:
        # SSL Tunnel
        return SoapStubAdapterWithLogging('sdkTunnel', 8089, version=version, path=path,
                                          certKeyFile=keyfile, certFile=certfile, httpProxyHost=host, sslContext=sslContext)
    else:
        return SoapStubAdapterWithLogging(host, port, version=version, path=path, sslContext=sslContext)

def Connect(host, protocol="https", port=443, user=None, pwd=None,
            namespace=None, path="/sdk",
            preferredApiVersions=None, keyfile=None, certfile=None, sslContext=None):
    """
    Determine the most preferred API version supported by the specified server,
    then connect to the specified server using that API version, login and return
    the service instance object.
    Throws any exception back to caller. The service instance object is
    also saved in the library for easy access.
    @param host: Which host to connect to.
    @type  host: string
    @param protocol: What protocol to use for the connection (e.g. https or http).
    @type  protocol: string
    @param port: Port
    @type  port: int
    @param user: User
    @type  user: string
    @param pwd: Password
    @type  pwd: string
    @param namespace: Namespace *** Deprecated: Use version instead ***
    @type  namespace: string
    @param path: Path
    @type  path: string
    @param preferredApiVersions: Acceptable API version(s) (e.g. vim.version.version3)
                                 If a list of versions is specified the versions should
                                 be ordered from most to least preferred.  If None is
                                 specified, the list of versions support by pyVmomi will
                                 be used.
    @type  preferredApiVersions: string or string list
    @param keyfile: ssl key file path
    @type  keyfile: string
    @param certfile: ssl cert file path
    @type  certfile: string
    """

    if preferredApiVersions is None:
        preferredApiVersions = GetServiceVersions('vim25')

    supportedVersion = __FindSupportedVersion(protocol,
                                              host,
                                              port,
                                              path,
                                              preferredApiVersions,
                                              sslContext)
    if supportedVersion is None:
        raise Exception("%s:%s is not a VIM server" % (host, port))
    version = supportedVersion

    stub = _create_stub(host, protocol, port, namespace, path, version, keyfile, certfile, sslContext)

    # Get Service instance
    si = vim.ServiceInstance("ServiceInstance", stub)
    try:
        content = si.RetrieveContent()
    except vim.MethodFault:
        raise
    except Exception as e:
        # NOTE (hartsock): preserve the traceback for diagnostics
        # pulling and preserving the traceback makes diagnosing connection
        # failures easier since the fault will also include where inside the
        # library the fault occurred. Without the traceback we have no idea
        # why the connection failed beyond the message string.
        (type, value, traceback) = sys.exc_info()
        if traceback:
            fault = vim.fault.HostConnectFault(msg=str(e))
            reraise(vim.fault.HostConnectFault, fault, traceback)
        else:
            raise vim.fault.HostConnectFault(msg=str(e))

    if user is not None and pwd is not None:
        content.sessionManager.Login(user, pwd, None)

    return si

class PyvmomiWrapperException(Exception):
    pass

class ExtensionNotRegisteredException(PyvmomiWrapperException):
    pass

class ExtensionAlreadyRegisteredException(PyvmomiWrapperException):
    pass

class CreateTaskException(PyvmomiWrapperException):
    pass

class TimeoutException(PyvmomiWrapperException):
    pass

class CLITypeException(PyvmomiWrapperException):
    pass

from pyVmomi import vim
# from .connect import Connect
# from .errors import TimeoutException


def get_reference_to_managed_object(mo):
    motype = mo.__class__.__name__.split(".")[-1]       # stip "vim." prefix
    return "{}:{}".format(motype, mo._moId)


class Client(object):
    def __init__(self, vcenter_address, username=None, password=None, certfile=None, keyfile=None, sslContext=None):
        self.service_instance = Connect(vcenter_address,
                                        user=username, pwd=password,
                                        certfile=certfile, keyfile=keyfile, sslContext=sslContext)
        self.service_content = self.service_instance.content
        self.session_manager = self.service_content.sessionManager
        self.root = self.service_content.rootFolder
        self.host = vcenter_address
        self.property_collectors = {}

    def login(self, user, pwd):
        self.session_manager.Login(user, pwd, None)
        self.property_collectors = {}

    def login_extension_by_certificate(self, extension_key, locale=None):
        if not locale:
            locale = getattr(self.session_manager, 'defaultLocale', 'en_US')
        self.session_manager.LoginExtensionByCertificate(extension_key, locale)
        self.property_collectors = {}

    def logout(self):
        self.session_manager.Logout()
        self.property_collectors = {}

    def wait_for_tasks(self, tasks, timeout=None):
        from time import time
        from .property_collector import TaskPropertyCollector
        if len(tasks) == 0:
            return
        # create a copy of 'tasks', because we're going to use 'remove' and we don't want to change the user's list
        tasks = tasks[:]
        property_collector = TaskPropertyCollector(self, tasks)
        start_time = time()
        remaining_timeout = None
        while len(tasks) > 0:
            if timeout is not None:
                remaining_timeout = int(timeout - (time() - start_time))
                if remaining_timeout <= 0:
                    raise TimeoutException("Time out while waiting for tasks")
            update = property_collector.iter_task_states_changes(timeout_in_seconds=remaining_timeout)
            for task, state in update:
                if state == vim.TaskInfo.State.success and task in tasks:
                    tasks.remove(task)
                elif state == vim.TaskInfo.State.error:
                    raise task.info.error

    def wait_for_task(self, task, timeout=None):
        return self.wait_for_tasks([task], timeout)

    def _create_traversal_spec(self, name, managed_object_type, property_name, next_selector_names=[]):
        return vim.TraversalSpec(name=name, type=managed_object_type, path=property_name,
                                 selectSet=[vim.SelectionSpec(name=selector_name) for selector_name in next_selector_names])

    def _build_full_traversal(self):
        rpToRp = self._create_traversal_spec("rpToRp", vim.ResourcePool, "resourcePool", ["rpToRp", "rpToVm"])
        rpToVm = self._create_traversal_spec("rpToVm", vim.ResourcePool, "vm")
        crToRp = self._create_traversal_spec("crToRp", vim.ComputeResource, "resourcePool", ["rpToRp", "rpToVm"])
        crToH = self._create_traversal_spec("crToH", vim.ComputeResource, "host")
        dcToHf = self._create_traversal_spec("dcToHf", vim.Datacenter, "hostFolder", ["visitFolders"])
        dcToVmf = self._create_traversal_spec("dcToVmf", vim.Datacenter, "vmFolder", ["visitFolders"])
        HToVm = self._create_traversal_spec("HToVm", vim.HostSystem, "vm", ["visitFolders"])
        dcToDs = self._create_traversal_spec("dcToDs", vim.Datacenter, "datastore", ["visitFolders"])
        visitFolders = self._create_traversal_spec("visitFolders", vim.Folder, "childEntity",
                                                   ["visitFolders", "dcToHf", "dcToVmf", "crToH", "crToRp", "HToVm", "dcToDs"])
        return [visitFolders, dcToVmf, dcToHf, crToH, crToRp, rpToRp, HToVm, rpToVm, dcToDs]

    def _retrieve_properties(self, managed_object_type, props=[], collector=None, root=None, recurse=True):
        if not collector:
            collector = self.service_content.propertyCollector
        if not root:
            root = self.service_content.rootFolder

        property_spec = vim.PropertySpec(type=managed_object_type, pathSet=props)
        selection_specs = list(self._build_full_traversal()) if recurse else []
        object_spec = vim.ObjectSpec(obj=root, selectSet=selection_specs)

        spec = vim.PropertyFilterSpec(propSet=[property_spec], objectSet=[object_spec])
        options = vim.RetrieveOptions()
        objects = []
        retrieve_result = collector.RetrievePropertiesEx(specSet=[spec], options=options)
        while retrieve_result is not None and retrieve_result.token:
            objects.extend(retrieve_result.objects)
            retrieve_result = collector.ContinueRetrievePropertiesEx(retrieve_result.token)
        if retrieve_result is not None:
            objects.extend(retrieve_result.objects)
        return objects

    def retrieve_properties(self, managed_object_type, props=[], collector=None, root=None, recurse=True):
        retrieved_properties = self._retrieve_properties(managed_object_type, props, collector, root, recurse)
        data = []
        for obj in retrieved_properties:
            properties = dict((prop.name, prop.val) for prop in obj.propSet)
            properties['obj'] = obj.obj
            data.append(properties)
        return data

    def get_decendents_by_name(self, managed_object_type, name=None):
        retrieved_properties = self._retrieve_properties(managed_object_type, ["name"])
        objects = [item.obj for item in retrieved_properties]
        if not name:
            return objects
        for obj in objects:
            if obj.name == name:
                return obj

    def get_host_systems(self):
        return self.get_decendents_by_name(vim.HostSystem)

    def get_host_system(self, name):
        return self.get_decendents_by_name(vim.HostSystem, name=name)

    def get_datacenters(self):
        return self.get_decendents_by_name(vim.Datacenter)

    def get_datacenter(self, name):
        return self.get_decendents_by_name(vim.Datacenter, name=name)

    def get_resource_pools(self):
        return self.get_decendents_by_name(vim.ResourcePool)

    def get_resource_pool(self, name):
        return self.get_decendents_by_name(vim.ResourcePool, name=name)

    def get_virtual_machines(self):
        return self.get_decendents_by_name(vim.VirtualMachine)

    def get_virtual_machine(self, name):
        return self.get_decendents_by_name(vim.VirtualMachine, name=name)

    def get_virtual_apps(self):
        return self.get_decendents_by_name(vim.VirtualApp)

    def get_virtual_app(self, name):
        return self.get_decendents_by_name(vim.VirtualApp, name=name)

    def get_folders(self):
        return self.get_decendents_by_name(vim.Folder)

    def get_folder(self, name):
        return self.get_decendents_by_name(vim.Folder, name=name)

    def get_host_clusters(self):
        return self.get_decendents_by_name(vim.ClusterComputeResource)

    def get_host_cluster(self, name):
        return self.get_decendents_by_name(vim.ClusterComputeResource, name=name)

    def get_datastores(self):
        return self.get_decendents_by_name(vim.Datastore)

    def get_datastore(self, name):
        return self.get_decendents_by_name(vim.Datastore, name=name)

    def get_reference_to_managed_object(self, mo):
        return get_reference_to_managed_object(mo)

    def get_managed_object_by_reference(self, moref):
        motype, moid = moref.split(":")
        moclass = getattr(vim, motype)
        return moclass(moid, stub=self.service_instance._stub)






class EsxCLI(object):
    _loaded_types = {}

    def __init__(self, host):
        self._host = host
        self._host_api_version = host.summary.config.product.apiVersion

    def _load_type(self, type_info):
        if type_info.name not in self._loaded_types:
            methods = []
            for method in type_info.method:
                params = [(param.name, param.type, param.version, F_OPTIONAL, method.privId) for param in method.paramTypeInfo]
                return_type = (0, method.returnTypeInfo.type, method.returnTypeInfo.type)
                methods.append((method.name, method.wsdlName, method.version, params, return_type, method.privId, list(method.fault)))

            cls = CreateAndLoadManagedType(type_info.name, type_info.wsdlName, type_info.base[0], type_info.version, [], methods)
            self._loaded_types[type_info.name] = cls
        return self._loaded_types[type_info.name]

    def get(self, name):
        type_name = "vim.EsxCLI." + name
        mme = self._host.RetrieveManagedMethodExecuter()
        stub = MMESoapStubAdapter(mme)
        stub.versionId = 'urn:vim25/{}'.format(self._host_api_version)
        dm = self._host.RetrieveDynamicTypeManager()
        type_to_moId = {moi.moType: moi.id for moi in dm.DynamicTypeMgrQueryMoInstances()}
        if type_name in type_to_moId:
            moId = type_to_moId[type_name]
            ti = dm.DynamicTypeMgrQueryTypeInfo()
            for type_info in ti.managedTypeInfo:
                if type_info.name == type_name:
                    cls = self._load_type(type_info)
                    return cls(moId, stub)
        raise CLITypeException("CLI type '{}' not found".format(name))

# from infi.pyvmomi_wrapper import Client
# from infi.pyvmomi_wrapper.esxcli import EsxCLI

# first open a "regular" client


def get_host_systems(self):
    return self.get_decendents_by_name(vim.HostSystem)


def get_host_system(self, name):
    return self.get_decendents_by_name(vim.HostSystem, name=name)

# si = SmartConnect(
#     host='172.17.30.110',
#     user='vmware\sa-py1',
#     pwd='3tango11',
#     port=443)


# obj_host = Host()

# host = obj_host.return_hosts(si, 'esx12.vmware.local')

client = Client("172.17.30.110", username="vmware\sa-py1", password="3tango11")

# get a host to run on
host = client.get_host_systems()[0]

cli = EsxCLI(host)

# get time
time_cli = cli.get("system.time")
print (time_cli.Get())

# list SATP rules
rule_cli = cli.get("storage.nmp.satp.rule")
print (rule_cli.List())