__author__ = 'psteam'

import mock

from nova import test
from nova.virt.hpux import driver as hpux_driver
from nova.virt.hpux import hostops
from nova.virt.hpux import vparops


class FakeInstance(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class HPUXDriverTestCase(test.NoDBTestCase):
    """Unit tests for HP-UX driver calls."""

    @mock.patch.object(vparops.VParOps, 'list_instances')
    def test_list_instances(self, mock_list_instances):
        fake_instances = ['fake1', 'fake2']
        mock_list_instances.return_value = fake_instances
        conn = hpux_driver.HPUXDriver(None, vparops=vparops.VParOps())
        instances = conn.list_instances()
        self.assertEqual(fake_instances, instances)
        mock_list_instances.assert_called_once_with()

    @mock.patch.object(hostops.HostOps, 'get_host_stats')
    def test_get_host_stats(self, mock_get_host_stats):
        fake_stats = {
            'supported_instances': [],
            'vcpus': 2,
            'memory_mb': 2048,
            'local_gb': 100,
            'vcpus_used': 0,
            'memory_mb_used': 1024,
            'local_gb_used': 10,
            'hypervisor_type': 'hpux',
            'hypervisor_version': '201409',
            'hypervisor_hostname': 'hpux'
        }
        mock_get_host_stats.return_value = fake_stats
        conn = hpux_driver.HPUXDriver(None, hostops=hostops.HostOps())
        host_stats = conn.get_host_stats(refresh=True)
        self.assertEqual(fake_stats, host_stats)
        mock_get_host_stats.assert_called_once_with(refresh=True)

    @mock.patch.object(hostops.HostOps, 'get_available_resource')
    def test_get_available_resource(self, mock_get_available_resource):
        fake_resource = {
            'supported_instances': [],
            'vcpus': 2,
            'memory_mb': 2048,
            'local_gb': 100,
            'vcpus_used': 0,
            'memory_mb_used': 1024,
            'local_gb_used': 10,
            'hypervisor_type': 'hpux',
            'hypervisor_version': '201409',
            'hypervisor_hostname': 'hpux'
        }
        mock_get_available_resource.return_value = fake_resource
        conn = hpux_driver.HPUXDriver(None, hostops=hostops.HostOps())
        available_resource = conn.get_available_resource(None)
        self.assertEqual(fake_resource, available_resource)
        mock_get_available_resource.assert_called_once_with()

    @mock.patch.object(vparops.VParOps, 'get_info')
    def test_get_info(self, mock_get_info):
        fake_info = {
            'state': 'power_state.RUNNING',
            'max_mem': 4096,
            'mem': 2048,
            'num_cpu': 2,
            'cpu_time': None
        }
        fake_instance = FakeInstance()
        mock_get_info.return_value = fake_info
        conn = hpux_driver.HPUXDriver(None, vparops=vparops.VParOps())
        instance_info = conn.get_info(fake_instance)
        self.assertEqual(fake_info, instance_info)
        mock_get_info.assert_called_once_with(fake_instance)
