from __future__ import print_function

import pyVmomi
import ssl

import requests
from pyVim.connect import SmartConnect
from pyVmomi import vim, vmodl

def main():

    print('Disabling SSL certificate verification.')
    requests.packages.urllib3.disable_warnings()

    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context

    si = SmartConnect(
        user='administrator@vsphere.local',
        pwd='Password123!',
        host='uplusvcenter03.xiolab.lab.emc.com'
    )

    # Credentials used to login to the guest system
    creds = pyVmomi.vim.vm.guest.NamePasswordAuthentication(
        username='root',
        password='Password123!'
    )

    # Get a view ref to all VirtualMachines
    view_ref = si.content.viewManager.CreateContainerView(
        container=si.content.rootFolder,
        type=[pyVmomi.vim.VirtualMachine],
        recursive=True
    )

    # Pick up the first VM
    vm = view_ref.view[110]
    print("VM Name: {}".format(vm.name))

    # Get VM processes
    processes = si.content.guestOperationsManager.processManager.ListProcessesInGuest(
        vm=vm,
        auth=creds
    )

    # Print some process info
    print("Process name: {}".format(processes[0].name))
    print("Process owner: {}".format(processes[0].owner))
    print("Process PID: {}".format(processes[0].pid))

    try:
        pm = si.content.guestOperationsManager.processManager

        ps = vim.vm.guest.ProcessManager.ProgramSpec(
            programPath="/usr/bin/sleep",
            arguments="500"
        )
        res = pm.StartProgramInGuest(vm, creds, ps)

        if res > 0:
            print("Program executed, PID is {}".format(res))

    except IOError, e:
        print(e)
    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1


if __name__ == '__main__':
    main()
