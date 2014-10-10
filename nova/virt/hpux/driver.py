__author__ = 'psteam'

"""
A HP-UX Nova Compute driver.
"""

from nova import db
from nova.virt import driver
from nova.virt.hpux import hostops
from nova.virt.hpux import vparops


class HPUXDriver(driver.ComputeDriver):
    def __init__(self, virtapi,
                 vparops=vparops.VParOps(),
                 hostops=hostops.HostOps()):
        super(HPUXDriver, self).__init__(virtapi)
        self._vparops = vparops
        self._hostops = hostops

    def init_host(self, host):
        pass

    def list_instances(self):
        return self._vparops.list_instances()

    def get_host_stats(self, refresh=False):
        """Return the current state of the host.

        If 'refresh' is True, run update the stats first.
        """
        return self._hostops.get_host_stats(refresh=refresh)

    def get_available_resource(self, nodename):
        """Retrieve resource information.

        This method is called when nova-compute launches, and
        as part of a periodic task that records the results in the DB.

        :param nodename: will be put in PCI device
        :returns: dictionary containing resource info
        """
        return self._hostops.get_available_resource()

    def get_info(self, instance):
        """Get the current status of an instance, by name (not ID!)

        :param instance: nova.objects.instance.Instance object

        Returns a dict containing:

        :state:           the running state, one of the power_state codes
        :max_mem:         (int) the maximum memory in KBytes allowed
        :mem:             (int) the memory in KBytes used by the domain
        :num_cpu:         (int) the number of virtual CPUs for the domain
        :cpu_time:        (int) the CPU time used in nanoseconds
        """
        return self._vparops.get_info(instance)

    def scheduler_dispatch(self, vPar_info):
        """Lookup target nPar.

        :param vPar_info: (dict) the required vPar info
        :returns: dictionary containing nPar info
        """
        nPar_list = db.nPar_get_all()
        nPar = self._hostops.nPar_lookup(vPar_info, nPar_list)
        return nPar

    def instance_exists(self, instance_name):
        """Check target instance exists or not.

        :param instance_name:
        :return:
        :True:
        :False:
        """
        instance_list = self.list_instances()
        for inst_name in instance_list:
            if instance_name == inst_name:
                return True
            continue
        return False

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True):
        """Destroy specific vpar

        :param context:
        :param instance:
        :param network_info:
        :param block_device_info:
        :param destroy_disks:
        :return:
        """
        self._vparops.destroy(context, instance, network_info)

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        """Spawn new vapr

        :param context:
        :param instance:
        :param image_meta:
        :param injected_files:
        :param admin_password:
        :param network_info:
        :param block_device_info:
        :return:
        """
        self._vparops.spawn(context, instance, image_meta, injected_files,
                            admin_password, network_info=None,
                            block_device_info=None)

    def connect_npar(self, nPar_id):
        """Get npar resource info via exec_remote_cmd()

        :param nPar_id:

        Returns a dict containing nPar resource info
        """
        return {}

    def connect_igserver(self, ip_addr):
        """Get npar list from ig_server via exec_remote_cmd()

        :param ip_addr:

        Returns npar list
        """
        return []

    def collect_nPar_resource(self):
        """Get nPar total resource.(cpu, memory, disk for now)

        Returns a dict containing total resource info of npar
        """
        npar_id = {
            'npar_id': 1,
            'ip_addr': '192.168.0.2'
        }
        npar_stats_total = {}
        nPar_list = self.connect_igserver('192.68.0.1')
        for nPar in nPar_list:
            nPar_info = self.connect_npar(npar_id)
            npar_stats_total = self._hostops.nPar_resource(nPar_info)
        return npar_stats_total
