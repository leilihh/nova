__author__ = 'psteam'

"""
Management class for basic vPar operations.
"""

import os
import pexpect
import time

from nova import exception
from nova.openstack.common.gettextutils import _
from nova.openstack.common import log as logging
from nova.virt.hpux import hostops
from nova.virt.hpux import utils
from oslo.config import cfg

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class VParOps(object):

    def __init__(self):
        pass

    def get_instance_host_name(self, ip_addr):
        # Will get the host name (napr_name) of given vpar reading from DB.
        pass

    def _get_vpar_resource_info(self, vpar_name, npar_ip_addr):
        """Get vPar resource info.

        :returns: A dict including CPU, memory and run state info.
        """
        vpar_info = {}
        cmd_for_vpar = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': npar_ip_addr,
            'command': '/opt/hpvm/bin/vparstatus -p ' + vpar_name + ' -v'
        }
        exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_vpar)
        results = exec_result.strip().split('\n')
        for item in results:
            if 'RunState' in item:
                # item as 'RunState: UP'
                vpar_info['run_state'] = item.split(':')[1].strip()
            elif 'System assigned [Count]' in item:
                # item as 'System assigned [Count]:  5\r'
                vpar_info['CPU'] = int(item.split(':')[1].strip())
            elif 'Total Memory(MB)' in item:
                # item as 'Total Memory(MB):  2048\r'
                vpar_info['Total_memory'] = int(item.split(':')[1].strip())
            else:
                continue
        return vpar_info

    def list_instances(self):
        """Get the up(running) vPar name list of all nPars.

        :returns: A list of up(running) vPar name
        """
        vpar_names = []
        # Here, we should get nPar list from db
        # to avoid frequent interaction with ignite server.
        #admin_context = context.get_admin_context()
        #npar_list = db.npar_get_all(admin_context)
        npar_list, vpar_list = hostops.HostOps()._get_client_list()
        # TODO(Sunny): Delete the hard code "npar_list"
        # Do the deletion after all functions are ready,
        # here 'npar_list' is just for testing.
        npar_list = [{'ip_addr': u'192.168.169.100',
                      'name': u'bl890npar1', 'hostname': u'bl890npar1',
                      'cpus': 8, 'memory': 66994944 / 1024,
                      'model': u'ia64 hp Integrity BL890c i4 nPar'}]
        for npar in npar_list:
            cmd_for_npar = {
                'username': CONF.hpux.username,
                'password': CONF.hpux.password,
                'ip_address': npar['ip_addr'],
                'command': '/opt/hpvm/bin/vparstatus'
            }
            exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_npar)
            results = exec_result.strip().split('\n')
            for ret in results:
                # ret likes '  2 vpar-test  UP  Active \r'
                if 'UP' in ret:
                    vpar_names.append(ret.split()[1])
        return vpar_names

    def get_info(self, instance):
        """Get status of given vPar instance.

        :returns: A dict including CPU, memory, disk info and
        run state of required vPar.
        """
        # TODO(Lei Li): This will be replaced since nPar_list
        # will get by reading from DB directly. Cut such code for now.
        #napr_list, vpar_list = hostops.HostOps()._get_client_list()
        #for vpar in vpar_list:
            #if vpar['name'] is instance['name']:
        vpar_info = self._get_vpar_resource_info(instance['vpar_name'],
                                                 instance['npar_ip_addr'])
        if not vpar_info:
            raise exception.VparNotFound(instance['name'])
        else:
            return vpar_info

    def destroy(self, instance):
        #power off the vpar before vparremove
        exec_result = None
        try:
            cmd_for_destroy = {
                'username': CONF.hpux.username,
                'password': CONF.hpux.password,
                'ip_address': instance['host'],
                'command': '/opt/hpvm/bin/vparreset -p ' +
                           instance['display_name'] + ' -d -f'
            }
            exec_result = utils.ExecRemoteCmd().\
                exec_remote_cmd(**cmd_for_destroy)
            # delete a vPar
            # vparremove -p <vpar_name> -f
            if exec_result != None:
                cmd_for_destroy = {
                    'username': CONF.hpux.username,
                    'password': CONF.hpux.password,
                    'ip_address': instance['host'],
                    'command': '/opt/hpvm/bin/vparremove -p ' +
                               instance['display_name'] + ' -f'
                 }
            exec_result = utils.ExecRemoteCmd().exec_remote_cmd(
                **cmd_for_destroy)
        except utils.ExceptionPexpect as e:
            raise exception.Invalid(("Destroy instance error UNKNOWN"))
        finally:
            return exec_result

    def define_dbprofile(self, prof_define_info):
        """Define dbprofile in EFI shell to prepare later vPar installing.
        :param: A dict contains all of the needed info for dbprofile define,
                - vPar name (vpar_name)
                - nPar IP address (ip_address)
                - Ignite-UX server IP address (sip)
                - Ignite client IP address (cip)
                - Ignite client  server Gateway IP address (gip)
                - Ignite client  server Network mask (mask)
        :return: Name of defined profile if success.
        """
        prof_name = 'profile_hpux'
        #Hard code the Ignite-UX server IP address for now
        prof_define_info['sip'] = '192.168.172.51'
        try:
            cmd_for_dbprofile_define = {
                'username': CONF.hpux.username,
                'vpar_name': prof_define_info['vpar_name'],
                'ip_address': prof_define_info['ip_address'],
                'remote_command': '/opt/hpvm/bin/vparconsole -p ' +
                                  prof_define_info['vpar_name'],
                'efi_command': 'dbprofile -dn ' + prof_name + ' -sip ' +
                                  prof_define_info['sip'] + ' -cip ' +
                                  prof_define_info['cip'] + ' -gip ' +
                                  prof_define_info['gip'] + ' -m ' +
                                  prof_define_info['mask']
            }
            utils.ExecRemoteCmd.exec_efi_cmd(**cmd_for_dbprofile_define)
        except utils.ExceptionPexpect as e:
            raise exception.Invalid(("Failed to define dbprofile"))
        finally:
            if not e:
                return prof_name

    def update_dbprofile(self, prof_update_info):
        """Update defined dbprofile
        :param: A dict contains,
                - vPar name (vpar_name)
                - nPar IP address (ip_address)
                - Name of defined dbprofile (prof_name)
                - Boot file name (boot_fname)
        :return True in success
        """
        #Hard code the Ignite-UX server IP address for now
        prof_update_info['sip'] = '192.168.172.51'
        try:
            cmd_for_dbprofile_update = {
                'username': CONF.hpux.username,
                'vpar_name': prof_update_info['vpar_name'],
                'ip_address': prof_update_info['ip_address'],
                'remote_command': '/opt/hpvm/bin/vparconsole -p ' +
                                  prof_update_info['vpar_name'],
                'efi_command': 'dbprofile -dn ' +
                               prof_update_info['prof_name'] + ' -b ' +
                               prof_update_info['boot_fname']
            }
            utils.ExecRemoteCmd.exec_efi_cmd(**cmd_for_dbprofile_update)
        except utils.ExecRemoteCmd as e:
            raise exception.Invalid(("Failed to update dbprofile"))
        finally:
            if not e:
                return True

    def spawn(self, context, instance, volume_dic, prof_define_info,
              vhba_info, prof_update_info, network_info=None):
        """Spawn vPar including before register stage and after register stage
           - Before register stage:
             - create lv
             - define vPar
             - init vPar
             - get mac address
             - register (configuration)
           - After register stage:
             - connect vPar console
             - enter EFI shell
             - define dbprofile
             - select lanboot
             - set vHBA
             - update dbprofile
        """
        # Before register stage action, rough coding for now.
        self.create_lv(volume_dic)
        self.define_vpar(instance)
        self.init_vpar(instance)
        self.get_mac_addr(network_info['ip_addr'])
        self.register_vpar_into_ignite(instance)
        # After register stage action.
        prof_name = self.define_dbprofile(prof_define_info)
        self.ft_boot_vpar(network_info['ip_addr'], prof_name)
        self.init_vhba(vhba_info)
        self.update_dbprofile(prof_update_info)

    def create_lv(self, lv_dic):
        """Create logical volume for vPar on specified nPar.

        :param: A dict containing:
             :lv_size: The size of logical volume
             :lv_name: The name of logical volume
             :vg_path: The path of volume group
             :ip_addr: The IP address of specified nPar
        :returns: created_lv_path: The path of created logical volume
        """
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': lv_dic['ip_addr'],
            'command': 'lvcreate -L ' + lv_dic['lv_size'] +
                       ' -n ' + lv_dic['lv_name'] +
                       ' ' + lv_dic['vg_path']
        }
        created_lv_path = lv_dic['vg_path'] + '/r' + lv_dic['lv_name']
        LOG.debug(_("Begin to create logical volume %s.")
                  % lv_dic['lv_name'])
        result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
        if created_lv_path in result:
            LOG.debug(_("Create logical volume %s successfully.")
                      % created_lv_path)
            return created_lv_path
        return None

    def define_vpar(self, vpar_dic):
        """create  vpar
        :param: dict,include vparname, memory size, path, ipaddress, CPU
                numbers
        :returns: A list of up(running) vPar name
        """
        cmd_for_vparcreate = {
                'username': CONF.hpux.username,
                'password': CONF.hpux.password,
                'ip_address': vpar_dic['ip_addr'],
                'command': '/opt/hpvm/bin/vparcreate -p ' + vpar_dic['vpar_nm'] +
                           ' -a mem::' + str(vpar_dic['mem_size']) + ' -a cpu::' +
                           str(vpar_dic['vcpu']) + ' -a disk:avio_stor::lv:' +
                           vpar_dic['path'] + ' -a network:avio_lan::vswitch:' +
                           'sitelan' + ' -a network:avio_lan::vswitch:' +
                            'localnet'
        }
        utils.ExecRemoteCmd().exec_remote_cmd(
                **cmd_for_vparcreate)
        ret = self.get_info(vpar_dic['vpar_nm'])
        if 'DOWN' in ret['run_state']:
            return True
        else:
            return False

    def init_vpar(self, vpar_info):
        """Initialize the specified vPar so that could enter live console mode.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :ip_addr: The IP address of specified nPar
        :return: True if vPar boot successfully
        """
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['ip_addr'],
            'command': '/opt/hpvm/bin/vparboot -p ' +
                       vpar_info['vpar_name']
        }
        LOG.debug(_("Begin to initialize vPar %s.") % vpar_info['vpar_name'])
        result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
        if 'Successful start initiation' in result:
            LOG.debug(_("Initialize vPar %s successfully.")
                      % vpar_info['vpar_name'])
            return True
        return False

    def get_mac_addr(self, vpar_info):
        """Get "sitelan" MAC address of vPar from specified nPar.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :ip_addr: The IP address of specified nPar
        :return: mac_addr: The MAC address of vPar
        """
        mac_addr = None
        cmd = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['ip_addr'],
            'command': '/opt/hpvm/bin/vparstatus -p ' +
                       vpar_info['vpar_name'] + ' -v'
        }
        exec_result = utils.ExecRemoteCmd().exec_remote_cmd(**cmd)
        results = exec_result.strip().split('\n')
        for item in results:
            if CONF.hpux.management_network in item:
                io_details = item.split()
                for io in io_details:
                    if CONF.hpux.management_network in io:
                        mac_addr = io.split(':')[2].split(',')[2]
        return mac_addr

    def register_vpar_into_ignite(self, vpar_info):
        """Register vPar into ignite server.

        :param: A dict containing:
             :vpar_name: The name of vPar
             :mac: The mac address of vPar
             :ip_addr: The IP address of vPar
             :gateway: The gateway of vPar
             :mask: The mask of vPar
        :return: True if no error in the process of registration
        """
        # Add vPar network info into the end of /etc/bootptab on ignite server
        cmd_for_network = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': CONF.hpux.ignite_ip,
            'command': 'cat >> /etc/bootptab <<EOF\r\n'
                       + vpar_info['vpar_name'] + ':\\'
                       + '\r\n\ttc=ignite-defaults:\\'
                       + '\r\n\tha=' + vpar_info['mac'] + ':\\'
                       + '\r\n\tbf=/opt/ignite/boot/Rel_B.11.31/nbp.efi:\\'
                       + '\r\n\tgw=' + vpar_info['gateway'] + ':\\'
                       + '\r\n\tip=' + vpar_info['ip_addr'] + ':\\'
                       + '\r\n\tsm=' + vpar_info['mask']
                       + '\r\nEOF'
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_network)

        # Create config file for client(vPar)
        cmd_for_create_config = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': CONF.hpux.ignite_ip,
            'command': 'mkdir /var/opt/ignite/clients/' + vpar_info['mac'] +
                       '&& touch /var/opt/ignite/clients/' + vpar_info['mac'] +
                       '/config'
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_create_config)

        # Add config info into the end of /var/opt/ignite/clients/<MAC>/config
        cmd_for_config = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': CONF.hpux.ignite_ip,
            'command': 'cat >> /var/opt/ignite/clients/'
                       + vpar_info['mac'] + '/config <<EOF'
                       + '\r\ncfg "HP-UX B.11.31.1403 golden_image"=TRUE'
                       + '\r\n_hp_cfg_detail_level="v"'
                       + '\r\nfinal system_name="'
                       + vpar_info['vpar_name'] + '"'
                       + '\r\n_hp_keyboard="USB_PS2_DIN_US_English"'
                       + '\r\nroot_password="1uGsgzGKG95gU"'
                       + '\r\n_hp_root_disk="0/0/0/0.0x0.0x0"'
                       + '\r\n_my_second_disk_path=""'
                       + '\r\nEOF'
        }
        utils.ExecRemoteCmd().exec_remote_cmd(**cmd_for_config)
        return True

    def ft_boot_vpar(self, ip_addr, profile_name):
        child_pid = os.fork()
        if child_pid == 0:
            cmd_for_lanboot = 'lanboot select -dn ' + profile_name
            ssh = pexpect.spawn('ssh %s@%s "%s"' % ('root',
                                                    ip_addr, cmd_for_lanboot))
            expect_ret = ssh.expect(['Password:',
                                     'continue connecting (yes/no)?'],
                                    timeout=CONF.hpux.ssh_timeout_seconds)
            if expect_ret == 0:
                ssh.sendline('root')
            elif expect_ret == 1:
                ssh.sendline("yes\n")
                ssh.expect("password:")
                ssh.sendline('root')
            else:
                raise exception.Invalid(_("ssh connection error UNKNOWN"))
            ssh.expect("NIC")
            ssh.sendline('01')
            ssh.close()
        else:
            ret = 1
            while ret > 0:
                cmd_for_lanboot = 'ps aux | grep lanboot'
                execute_result = utils.ExecRemoteCmd.exec_remote_cmd(
                                                           **cmd_for_lanboot)
                stat = execute_result.split()
                ret = stat[1]
                time.sleep(60)
        return True

    def init_vhba(self, vhba_info):
        #Attach vhba
        cmd_for_vhba = {
            'username': 'root',
            'password': 'root',
            'ip_address': vhba_info['host'],
            'command': 'vparreset -f -p ' + vhba_info['vpar_name'] + ' -d'
        }
        utils.ExecRemoteCmd.exec_remote_cmd(**cmd_for_vhba)
        #Force to reset vPar, must succeed:
        cmd_for_vhba = {
            'username': 'root',
            'password': 'root',
            'ip_address': vhba_info['host'],
            'command': 'vparmodify -p ' + vhba_info['vpar_name'] + ' -a ' +
                       vhba_info['vpar_component'] + ':avio_stor:,,' +
                       vhba_info['wwpn'] + ',' + vhba_info['wwnn'] +
                       ':npiv:/dev/fcd0'
        }
        utils.ExecRemoteCmd.exec_remote_cmd(**cmd_for_vhba)
        return True

    def boot_vpar(self, vpar_info):
        cmd_for_boot = {
            'username': CONF.hpux.username,
            'password': CONF.hpux.password,
            'ip_address': vpar_info['host'],
            'command': 'vparboot -p ' + vpar_info['vpar_name']
        }
        return utils.ExecRemoteCmd.exec_remote_cmd(**cmd_for_boot)
