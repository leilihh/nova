__author__ = 'psteam'

"""
A HP-UX Nova Compute driver.
"""

from nova import db
from nova.virt import driver
from nova.virt.hpux import hostops
from nova.virt.hpux import vparops
from oslo.config import cfg

hpux_opts = [
    cfg.StrOpt('username',
               default='root',
               help='Username for ssh command'),
    cfg.StrOpt('password',
               default='root',
               help='Password for ssh command'),
    cfg.StrOpt('ignite_ip',
               default='192.168.172.51',
               help='IP for ignite server'),
    cfg.IntOpt('ssh_timeout_seconds',
               default=20,
               help='Number of seconds to wait for ssh command'),
    cfg.IntOpt('lanboot_timeout_seconds',
               default=1200,
               help='Number of seconds to wait for lanboot command'),
    cfg.StrOpt('vg_name',
               default='/dev/vg00',
               help='Volume group of nPar for creating logical volume'),
    cfg.StrOpt('management_network',
               default='sitelan',
               help='Management network for vPar'),
    cfg.StrOpt('production_network',
               default='localnet',
               help='Production network for vPar'),
    ]

CONF = cfg.CONF
CONF.register_opts(hpux_opts, 'hpux')


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

        This method is called when nova-compute launches    , and
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
        :num_cpu:         (int) the number of virtual CPUs for the domain
        """
        return self._vparops.get_info(instance)

    def get_num_instances(self):
        """Get the current number of vpar

        Return integer with the number of running instances
        """
        instances_list = self._vparops.list_instances()
        return len(instances_list)

    def scheduler_dispatch(self, context, vPar_info):
        """Lookup target nPar.

        :param context:
        :param vPar_info: (dict) the required vPar info
        :returns: dictionary containing nPar info
        """
        nPar_list = db.npar_get_all(context)
        nPar = self._hostops.nPar_lookup(vPar_info, nPar_list)
        return nPar

    def instance_exists(self, instance_name):
        """Check if target instance exists.

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
        if self.instance_exists(instance['display_name']):
            self._vparops.destroy(context, instance, network_info)

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        """Spawn new vPar

        :param context:
        :param instance:
        :param image_meta:
        :param injected_files:
        :param admin_password:
        :param network_info:
        :param block_device_info:
        :return:
        """
        fixed_ip = '192.168.169.105'
        gateway = '192.168.168.1'
        mask = '255.255.248.0'
        lv_dic = {
            'lv_size': instance['instance_type']['root_gb'] * 1024,
            'lv_name': 'lv-' + str(instance['id']),
            'vg_path': CONF.hpux.vg_name,
            'host': instance['host']
        }
        lv_path = self._vparops.create_lv(lv_dic)
        vpar_info = {
            'vpar_name': instance['display_name'],
            'host': instance['host'],
            'mem': instance['instance_type']['memory_mb'],
            'cpu': instance['instance_type']['vcpus'],
            'lv_path': lv_path
        }
        self._vparops.define_vpar(vpar_info)
        self._vparops.init_vpar(vpar_info)
        mac = self._vparops.get_mac_addr(vpar_info)
        vpar_info['mac'] = mac
        vpar_info['ip_addr'] = fixed_ip
        vpar_info['gateway'] = gateway
        vpar_info['mask'] = mask
        self._vparops.register_vpar_into_ignite(vpar_info)
        self._vparops.lanboot_vpar_by_efi(vpar_info)
