import inspect
from abc import ABCMeta, abstractmethod

import pyVmomi
from pyVmomi import vim, vmodl


class FactoryMeta(ABCMeta):
    """
    Factory meta class
    The mechanism works by class registration - using reflection.
    '"""
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, 'registry'):
            cls.registry = {}
        if not inspect.isabstract(cls):
            factory_id = getattr(cls, '_factory_id', cls.__name__)
            cls.registry[factory_id] = cls
        super(FactoryMeta, cls).__init__(name, bases, dct)

    @abstractmethod
    def __call__(cls, *args, **kwargs):
        return super(FactoryMeta, cls).__call__(*args, **kwargs)


class OperationMeta(FactoryMeta):
    def __call__(cls, operation_type, *args, **kwargs):
        operation_cls = cls.registry.get(operation_type)
        if operation_cls is None:
            raise TypeError('Invalid operation {0}'.format(operation_type))
        return super(OperationMeta, operation_cls).__call__(*args, **kwargs)

    create = __call__


class Operation(object):
    # __metaclass__ = ABCMeta
    __metaclass__ = OperationMeta

    def __init__(self, operation, vm, *args):
        self.operation = operation
        self.vm = vm
        self.cls_name = self.__class__.__name__
        self.logger_string = 'Operation: {} VM: {}'.format(self.operation, self.vm.name)

    def logger_string(self):
        return self.logger_string

    @abstractmethod
    def task(self):
        return


class OperationOn(Operation):
    _factory_id = 'on'

    def __init__(self, vm, *args):
        super(OperationOn, self).__init__('on', vm)

    def task(self):
        return self.vm.PowerOnVM_Task()


class OperationOff(Operation):
    _factory_id = 'off'

    def __init__(self, vm, *args):
        super(OperationOff, self).__init__('off', vm)

    def task(self):
        return self.vm.PowerOffVM_Task()


class OperationRestartGuest(Operation):
    _factory_id = 'restart_guest'

    def __init__(self, vm):
        super(OperationRestartGuest, self).__init__('restart_guest', vm)

    def task(self):
        return self.vm.RebootGuest()


class OperationRestartVM(Operation):
    _factory_id = 'restart_vm'

    def __init__(self, vm, *args):
        super(OperationRestartVM, self).__init__('restart_vm', vm)

    def task(self):
        return self.vm.ResetVM_Task()


class OperationShutdownGuest(Operation):
    _factory_id = 'shut'

    def __init__(self, vm, *args):
        super(OperationShutdownGuest, self).__init__('shut', vm)

    def task(self):
        return self.vm.ShutdownGuest()


class OperationSnapCreate(Operation):
    _factory_id = 'snap.create'

    def __init__(self, vm, *args):
        super(OperationSnapCreate, self).__init__('snap.create', vm)

    def task(self):
        return self.vm.CreateSnapshot_Task(name=self.vm.name, memory=True, quiesce=False)


class OperationSnapRemoveAll(Operation):
    _factory_id = 'snap.del'

    def __init__(self, vm, *args):
        super(OperationSnapRemoveAll, self).__init__('snap.del', vm)

    def task(self):
        return self.vm.RemoveAllSnapshots_Task()


class OperationDel(Operation):
    _factory_id = 'del'

    def __init__(self, vm, *args):
        super(OperationDel, self).__init__('del', vm)

    def task(self):
        return self.vm.Destroy_Task()


class OperationVMotion(Operation):
    _factory_id = 'vmotion'

    def __init__(self, vm, operation_dst, *args):
        super(OperationVMotion, self).__init__('vmotion', vm)
        self.hostsystem = operation_dst
        self.logger_string = 'Operation: {} VM: {} to host: {}'.format(self.operation,
                                                                       self.vm.name,
                                                                       self.hostsystem.name)

    def task(self):
        return self.vm.MigrateVM_Task(host=self.hostsystem, priority='highPriority')


class OperationvNnicChange(Operation):
    _factory_id = 'change.vnic'

    def __init__(self, vm, operation_dst, *args):
        super(OperationvNnicChange, self).__init__('change.vnic', vm)
        self.target_pg = operation_dst
        self.logger_string = 'Operation: {} VM: {} to portgroup: {}'.format(self.operation,
                                                                            self.vm.name,
                                                                            self.target_pg.name)
        self.device_change = []
        for device in self.vm.config.hardware.device:
            net_adapter_id = 2
            dev_id = 'Network adapter' + ' ' + str(net_adapter_id)

            if device.deviceInfo.label == dev_id:

                self.logger_string = 'VM: {} vNIC Mac Address is: {}'.format(vm.name, device.macAddress)

                nicspec = vim.vm.device.VirtualDeviceSpec()
                nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.wakeOnLanEnabled = True

                dvs_port_connection = vim.dvs.PortConnection()
                dvs_port_connection.portgroupKey = self.target_pg.key
                dvs_port_connection.switchUuid = self.target_pg.config.distributedVirtualSwitch.uuid
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
                nicspec.device.backing.port = dvs_port_connection

                self.device_change.append(nicspec)
                break

        self.config_spec = vim.vm.ConfigSpec(deviceChange=self.device_change)

    def task(self):
        return self.vm.ReconfigVM_Task(self.config_spec)


class OperationvNnicChangeMac(Operation):
    _factory_id = 'change.vnic.mac'

    def __init__(self, vm, *args):
        super(OperationvNnicChangeMac, self).__init__('change.vnic.mac', vm)
        self.logger_string = "Operation: {} VM: {}".format(self.operation, self.vm.name)
        self.device_change = []
        for device in self.vm.config.hardware.device:
            if 3999 < device.key < 5000:
                self.logger_string = "VM: {} is macAddress changed".format(vm.name)

                nicspec = vim.vm.device.VirtualDeviceSpec()
                nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.macAddress = "00:50:56:1a:ff:ff"
                nicspec.device.addressType = "Generated"
                nicspec.device.macAddress = ""
                self.device_change.append(nicspec)

        self.config_spec = vim.vm.ConfigSpec(deviceChange=self.device_change)

    def task(self):
        return self.vm.ReconfigVM_Task(self.config_spec)

class OperationVMRemoteCmd(Operation):
    _factory_id = 'rcmd'

    def __init__(self, vm, operation_dst, *args):
        super(OperationVMRemoteCmd, self).__init__('rcmd', vm)
        self.vm = vm
        self.cmd = "Future"
        self.si = operation_dst
        self.logger_string = 'Operation: {} VM: {} cmd : {}'.format(self.operation,
                                                                       self.vm.name,
                                                                       self.cmd)

    def task(self):

        # Credentials used to login to the guest system
        creds = pyVmomi.vim.vm.guest.NamePasswordAuthentication(
            username='root',
            password='Password123!'
        )

        pm = self.si.content.guestOperationsManager.processManager

        ps = vim.vm.guest.ProcessManager.ProgramSpec(
            programPath="/usr/bin/fio",
            # programPath="/opt/io/nvme_tcp_repro/vdbench/vdbench",
            # arguments="-f /opt/io/nvme_tcp_repro/vdbench/ioExt"
            # arguments="--ioengine=libaio --bs=1-512k --iodepth=32 --rw=randwrite --size=40G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --time_based --runtime=9555"
            # arguments="--ioengine=libaio --bs=32-512k --iodepth=128 --rw=randwrite --size=40G --direct=1 --numjobs=1 --name=io1 --filename=/dev/sdb --time_based --runtime=555"
            # arguments="--ioengine=libaio --bs=1k-512k --iodepth=128 --rw=randwrite --size=100G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --time_based --runtime=5"
            # arguments="--ioengine=libaio --bs=1m --iodepth=128 --rw=randtrim --size=10G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=36"
            # arguments="--ioengine=libaio --bs=1m --iodepth=128 --rw=randtrim --size=18G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=3600"
            # arguments="--ioengine=libaio --bs=1m --iodepth=128 --rw=readwrite --size=18G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=200"
            # arguments="--ioengine=libaio --bs=1k-1m --iodepth=128 --rw=readwrite --size=88G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=200"
            # arguments="--ioengine=libaio --bs=1m --iodepth=128 --rw=randwrite --size=18G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=360"
            # arguments="--ioengine=libaio --bs=1-16k --iodepth=32 --rw=readwrite --size=8G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=860"
            # arguments="--ioengine=libaio --bs=1-16k --iodepth=32 --rw=trimwrite --size=8G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=8"
            arguments="--ioengine=libaio --bs=1-256k --iodepth=128 --rw=trimwrite --size=80G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=8"
            # arguments="--ioengine=libaio --bs=1-16k --iodepth=32 --rw=readwrite --size=8G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --filename=/dev/nvme1n1 --filename=/dev/nvme1n2 --filename=/dev/nvme2n1 --filename=/dev/nvme2n2 --time_based --runtime=8"
            # arguments="--ioengine=libaio --bs=1k --iodepth=64 --rw=randwrite --size=10G --direct=1 --numjobs=1 --name=io1 --filename=/dev/nvme0n1 --time_based --runtime=115"
        )

        # pm.StartProgramInGuest(self.vm, creds, ps)
        return pm.StartProgramInGuest(self.vm, creds, ps)