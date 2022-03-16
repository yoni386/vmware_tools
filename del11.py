from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect
import logging
from fnc1 import *
from fnc2 import *
import ssl


def vc_si(h, u, p, po=443):
    """
    function connect to vc and return si (service instance)
    """

    # logger = logging.getLogger(__name__)

    # host = args.host[0]
    # username = args.username[0]
    # password = args.password[0]
    # port = args.port[0]
    ssl._create_default_https_context = ssl._create_unverified_context
    requests.packages.urllib3.disable_warnings()

    # if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

    si = None
    try:
        si = SmartConnect(
            host=h,
            user=u,
            pwd=p,
            port=po)

    #     logger.info('Connecting to VC %s:%s with username %s' % (host, port, username))
    #     '''two below test'''
    #     logger.info("Connecting to VC '{}'".format(host))
    #
    except IOError as err:
        print('Could not connect to host %s with user %s and specified password, error: %s' % (h, u, err))
        return 1
    # logger.debug('Registering disconnect at exit')
    atexit.register(Disconnect, si)

    return si


def main():
    si = vc_si("10.130.254.191", "yoni", "BaniSperling85!")
    # vim.dvs.VmwareDistributedVirtualSwitch.VlanSpec
    print(si)


# if __name__ == "__main__":
main()
